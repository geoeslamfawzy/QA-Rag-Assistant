"""
Base Comment Formatter Module

Abstract base class for Jira comment formatters.
Enforces anti-hallucination by accepting ONLY RAGContext data.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from services.rag_context_builder import RAGContext


@dataclass
class CommentSection:
    """A section in a Jira comment."""
    title: str
    content: str
    severity: Optional[str] = None  # CRITICAL, HIGH, MEDIUM, LOW, INFO


@dataclass
class JiraComment:
    """Structured Jira comment ready for posting."""
    title: str
    sections: List[CommentSection] = field(default_factory=list)
    has_findings: bool = False
    finding_count: int = 0
    generated_at: datetime = field(default_factory=datetime.now)
    source_command: str = ""

    def to_jira_markup(self) -> str:
        """
        Convert to Jira wiki markup format.

        Returns:
            Formatted comment string for Jira API.
        """
        lines = []

        # Header with status indicator
        if self.has_findings:
            lines.append(f"h2. {{color:#de350b}}(x) {self.title}{{color}}")
        else:
            lines.append(f"h2. {{color:#00875a}}(/) {self.title}{{color}}")

        lines.append("")

        # Sections
        for section in self.sections:
            if section.content.strip():
                lines.append(f"h3. {section.title}")
                lines.append(section.content)
                lines.append("")

        # Footer
        lines.append("----")
        timestamp = self.generated_at.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(
            f"{{color:#6b778c}}_Based on RAG context and validators only. "
            f"Generated: {timestamp} | [QA RAG System]_{{color}}"
        )

        return "\n".join(lines)


class BaseCommentFormatter(ABC):
    """
    Abstract base for comment formatters.

    All formatters receive RAGContext and produce JiraComment.
    No data is invented - only validated findings are included.
    """

    @property
    @abstractmethod
    def command_name(self) -> str:
        """The command this formatter handles (analyze, review, get-ambiguity)."""
        pass

    @abstractmethod
    def format(self, context: 'RAGContext') -> JiraComment:
        """
        Format RAG context into a structured Jira comment.

        Args:
            context: RAGContext from RAGContextBuilder

        Returns:
            JiraComment ready for posting
        """
        pass

    def _has_findings(self, context: 'RAGContext') -> bool:
        """Check if there are any findings to report."""
        if not context.validation_results:
            return False

        for validator_name, result in context.validation_results.items():
            findings = result.get("findings", [])
            if findings:
                return True
        return False

    def _count_findings(self, context: 'RAGContext') -> int:
        """Count total findings across all validators."""
        count = 0
        if context.validation_results:
            for validator_name, result in context.validation_results.items():
                findings = result.get("findings", [])
                count += len(findings)
        return count

    def _format_no_findings(self, context: 'RAGContext') -> JiraComment:
        """Format comment when no findings detected."""
        story = context.story
        story_key = story.get("key", "Unknown")
        story_title = story.get("title", "Unknown")

        return JiraComment(
            title=f"QA {self.command_name.title()} Complete",
            sections=[
                CommentSection(
                    title="Story",
                    content=f"[{story_key}|/browse/{story_key}] - {story_title}",
                ),
                CommentSection(
                    title="Result",
                    content="No major issues detected based on current RAG context.",
                ),
            ],
            has_findings=False,
            finding_count=0,
            source_command=self.command_name,
        )

    def _build_story_header(self, context: 'RAGContext') -> str:
        """Build standard story reference header."""
        story = context.story
        story_key = story.get("key", "Unknown")
        story_title = story.get("title", "Unknown")
        return f"*Story:* [{story_key}|/browse/{story_key}] - {story_title}"

    def _build_risk_line(self, context: 'RAGContext') -> str:
        """Build risk level indicator line."""
        risk_level = context.pre_analysis.risk_level.upper()
        icon = self._risk_to_icon(risk_level)
        return f"*Risk Level:* {icon} {risk_level}"

    def _risk_to_icon(self, risk_level: str) -> str:
        """Map risk level to Jira icon."""
        icons = {
            "CRITICAL": "(x)",
            "HIGH": "(!)",
            "MEDIUM": "(/)",
            "LOW": "(/)",
        }
        return icons.get(risk_level, "(/)")

    def _severity_to_color(self, severity: str) -> str:
        """Map severity to Jira color."""
        colors = {
            "critical": "#de350b",
            "error": "#de350b",
            "warning": "#ffab00",
            "info": "#00875a",
        }
        return colors.get(severity.lower(), "#6b778c")

    def _format_findings_table(
        self,
        findings: List[dict],
        columns: List[str],
    ) -> str:
        """
        Format findings as a Jira table.

        Args:
            findings: List of finding dicts
            columns: Column names to include

        Returns:
            Jira wiki markup table string
        """
        if not findings:
            return ""

        lines = []
        # Header row
        header = "||" + "||".join(columns) + "||"
        lines.append(header)

        # Data rows
        for finding in findings:
            row_parts = []
            for col in columns:
                value = finding.get(col.lower(), "")
                if col.lower() == "severity":
                    color = self._severity_to_color(value)
                    value = f"{{color:{color}}}{value.upper()}{{color}}"
                row_parts.append(str(value) if value else "-")
            lines.append("|" + "|".join(row_parts) + "|")

        return "\n".join(lines)

    def _format_bullet_list(self, items: List[str]) -> str:
        """Format a bullet list in Jira markup."""
        if not items:
            return ""
        return "\n".join(f"* {item}" for item in items)
