"""
Analyze Comment Formatter Module

Formats analyze command output for Jira comments.
Includes: business gaps, rule violations, financial issues, state machine problems.
"""
from typing import List, Optional, TYPE_CHECKING

from .base_comment_formatter import BaseCommentFormatter, JiraComment, CommentSection

if TYPE_CHECKING:
    from services.rag_context_builder import RAGContext


class AnalyzeCommentFormatter(BaseCommentFormatter):
    """
    Formats analyze command findings for Jira comment.

    Sections:
    - Risk Assessment Summary
    - Business Rule Violations (from RuleEngine)
    - Financial Inconsistencies (from FinancialValidator)
    - State Machine Issues (from StateValidator)
    - Cross-Dependency Concerns (from CrossDepChecker)
    """

    @property
    def command_name(self) -> str:
        return "analyze"

    def format(self, context: 'RAGContext') -> JiraComment:
        """Format analysis findings into Jira comment."""
        if not self._has_findings(context):
            return self._format_no_findings(context)

        sections = []

        # Story header section
        sections.append(CommentSection(
            title="Story",
            content=self._build_story_header(context) + "\n" + self._build_risk_line(context),
        ))

        # Rule violations (from RuleEngine)
        rule_section = self._format_rule_violations(context)
        if rule_section:
            sections.append(rule_section)

        # Financial issues (from FinancialValidator)
        financial_section = self._format_financial_issues(context)
        if financial_section:
            sections.append(financial_section)

        # State machine issues (from StateValidator)
        state_section = self._format_state_machine_issues(context)
        if state_section:
            sections.append(state_section)

        # Cross-dependency issues (from CrossDepChecker)
        cross_dep_section = self._format_cross_dep_issues(context)
        if cross_dep_section:
            sections.append(cross_dep_section)

        return JiraComment(
            title="QA Analysis: Business Gaps Detected",
            sections=sections,
            has_findings=True,
            finding_count=self._count_findings(context),
            source_command=self.command_name,
        )

    def _format_rule_violations(self, context: 'RAGContext') -> Optional[CommentSection]:
        """Format RuleEngine findings."""
        validator_result = context.validation_results.get("RuleEngine", {})
        findings = validator_result.get("findings", [])

        if not findings:
            return None

        table = self._format_findings_table(
            findings,
            ["Severity", "Message", "Rule_ID"],
        )

        return CommentSection(
            title="Rule Violations",
            content=table,
            severity="ERROR",
        )

    def _format_financial_issues(self, context: 'RAGContext') -> Optional[CommentSection]:
        """Format FinancialValidator findings."""
        validator_result = context.validation_results.get("FinancialValidator", {})
        findings = validator_result.get("findings", [])

        if not findings:
            return None

        table = self._format_findings_table(
            findings,
            ["Severity", "Message", "Suggestion"],
        )

        return CommentSection(
            title="Financial Inconsistencies",
            content=table,
            severity="ERROR",
        )

    def _format_state_machine_issues(self, context: 'RAGContext') -> Optional[CommentSection]:
        """Format StateValidator findings."""
        validator_result = context.validation_results.get("StateValidator", {})
        findings = validator_result.get("findings", [])

        if not findings:
            return None

        table = self._format_findings_table(
            findings,
            ["Severity", "Message"],
        )

        return CommentSection(
            title="State Machine Issues",
            content=table,
            severity="WARNING",
        )

    def _format_cross_dep_issues(self, context: 'RAGContext') -> Optional[CommentSection]:
        """Format CrossDepChecker findings."""
        validator_result = context.validation_results.get("CrossDepChecker", {})
        findings = validator_result.get("findings", [])

        if not findings:
            return None

        table = self._format_findings_table(
            findings,
            ["Severity", "Message"],
        )

        return CommentSection(
            title="Cross-Dependency Concerns",
            content=table,
            severity="WARNING",
        )
