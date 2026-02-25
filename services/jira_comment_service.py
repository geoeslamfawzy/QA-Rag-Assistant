"""
Jira Comment Service Module

Orchestrates comment formatting and posting to Jira.
Single point of responsibility for comment operations.
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, TYPE_CHECKING
from enum import Enum

from jira_client import JiraClient

if TYPE_CHECKING:
    from services.rag_context_builder import RAGContext
    from formatters import BaseCommentFormatter, JiraComment

logger = logging.getLogger(__name__)


class CommentType(Enum):
    """Types of comments that can be posted."""
    ANALYZE = "analyze"
    REVIEW = "review"
    AMBIGUITY = "get-ambiguity"


@dataclass
class CommentPostResult:
    """Result of comment posting operation."""
    success: bool
    issue_key: str
    comment_type: CommentType
    has_findings: bool
    finding_count: int
    error: Optional[str] = None


class JiraCommentService:
    """
    Orchestrates Jira comment posting from RAG context.

    Design:
    - Receives RAGContext, not raw data (anti-hallucination)
    - Delegates formatting to specialized formatters
    - Calls JiraClient.post_comment() for actual posting
    - Returns structured result
    """

    def __init__(self, jira_client: JiraClient):
        """
        Initialize comment service.

        Args:
            jira_client: JiraClient instance for posting
        """
        self._client = jira_client
        self._formatters: Optional[Dict[CommentType, 'BaseCommentFormatter']] = None

    def _get_formatters(self) -> Dict[CommentType, 'BaseCommentFormatter']:
        """Lazy-load formatters to avoid circular imports."""
        if self._formatters is None:
            # Import here to avoid circular import with services/__init__.py
            from formatters import (
                AnalyzeCommentFormatter,
                ReviewCommentFormatter,
                AmbiguityCommentFormatter,
            )
            self._formatters = {
                CommentType.ANALYZE: AnalyzeCommentFormatter(),
                CommentType.REVIEW: ReviewCommentFormatter(),
                CommentType.AMBIGUITY: AmbiguityCommentFormatter(),
            }
        return self._formatters

    def post_comment(
        self,
        issue_key: str,
        context: 'RAGContext',
        comment_type: CommentType,
    ) -> CommentPostResult:
        """
        Format and post a comment to Jira.

        Args:
            issue_key: Jira issue key to comment on
            context: RAGContext with findings
            comment_type: Type of comment to generate

        Returns:
            CommentPostResult with status and details
        """
        try:
            # Get formatter for this comment type
            formatter = self._get_formatters().get(comment_type)
            if not formatter:
                return CommentPostResult(
                    success=False,
                    issue_key=issue_key,
                    comment_type=comment_type,
                    has_findings=False,
                    finding_count=0,
                    error=f"No formatter available for {comment_type.value}",
                )

            # Format the comment from RAG context
            jira_comment = formatter.format(context)

            # Convert to Jira wiki markup
            comment_body = jira_comment.to_jira_markup()

            # Post to Jira
            success = self._client.post_comment(issue_key, comment_body)

            if success:
                logger.info(
                    "Posted %s comment to %s (%d findings)",
                    comment_type.value,
                    issue_key,
                    jira_comment.finding_count,
                )
            else:
                logger.error(
                    "Failed to post %s comment to %s",
                    comment_type.value,
                    issue_key,
                )

            return CommentPostResult(
                success=success,
                issue_key=issue_key,
                comment_type=comment_type,
                has_findings=jira_comment.has_findings,
                finding_count=jira_comment.finding_count,
                error=None if success else "Jira API call failed",
            )

        except Exception as e:
            logger.exception("Error posting comment to %s: %s", issue_key, e)
            return CommentPostResult(
                success=False,
                issue_key=issue_key,
                comment_type=comment_type,
                has_findings=False,
                finding_count=0,
                error=str(e),
            )

    def format_preview(
        self,
        context: 'RAGContext',
        comment_type: CommentType,
    ) -> str:
        """
        Generate comment preview without posting.

        Useful for --dry-run scenarios or debugging.

        Args:
            context: RAGContext with findings
            comment_type: Type of comment to generate

        Returns:
            Formatted comment as string (Jira wiki markup)
        """
        formatter = self._get_formatters().get(comment_type)
        if not formatter:
            return f"No formatter available for {comment_type.value}"

        jira_comment = formatter.format(context)
        return jira_comment.to_jira_markup()
