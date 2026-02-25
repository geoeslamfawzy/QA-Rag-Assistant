"""
Review Comment Formatter Module

Formats review command output for Jira comments.
Includes: coverage gaps, missing scenarios, validator-identified gaps.
"""
from typing import List, Optional, TYPE_CHECKING

from .base_comment_formatter import BaseCommentFormatter, JiraComment, CommentSection

if TYPE_CHECKING:
    from services.rag_context_builder import RAGContext


class ReviewCommentFormatter(BaseCommentFormatter):
    """
    Formats test coverage review for Jira comment.

    Sections:
    - Coverage Assessment
    - Missing High-Risk Scenarios
    - Validator-Identified Gaps
    - Priority Testing Areas
    """

    @property
    def command_name(self) -> str:
        return "review"

    def format(self, context: 'RAGContext') -> JiraComment:
        """Format review findings into Jira comment."""
        if not self._has_findings(context):
            return self._format_no_findings(context)

        sections = []

        # Story header section
        sections.append(CommentSection(
            title="Story",
            content=self._build_story_header(context) + "\n" + self._build_risk_line(context),
        ))

        # Coverage assessment
        coverage_section = self._format_coverage_assessment(context)
        sections.append(coverage_section)

        # Validator gaps (consolidated)
        gaps_section = self._format_validator_gaps(context)
        if gaps_section:
            sections.append(gaps_section)

        # Missing high-risk scenarios
        scenarios_section = self._format_missing_scenarios(context)
        if scenarios_section:
            sections.append(scenarios_section)

        # Priority testing areas
        priority_section = self._format_priority_areas(context)
        if priority_section:
            sections.append(priority_section)

        return JiraComment(
            title="Test Coverage Review",
            sections=sections,
            has_findings=True,
            finding_count=self._count_findings(context),
            source_command=self.command_name,
        )

    def _format_coverage_assessment(self, context: 'RAGContext') -> CommentSection:
        """Summarize overall coverage level based on validator scores."""
        scores = []
        for validator_name, result in context.validation_results.items():
            score = result.get("score", 1.0)
            scores.append(score)

        avg_score = sum(scores) / len(scores) if scores else 1.0

        if avg_score >= 0.8:
            level = "HIGH"
            desc = "Good coverage based on validators"
        elif avg_score >= 0.5:
            level = "MEDIUM"
            desc = "Some gaps identified by validators"
        else:
            level = "LOW"
            desc = "Significant gaps detected"

        return CommentSection(
            title="Coverage Assessment",
            content=f"*Level:* {level}\n*Score:* {avg_score:.0%}\n{desc}",
        )

    def _format_validator_gaps(self, context: 'RAGContext') -> Optional[CommentSection]:
        """Consolidate gaps from all validators."""
        gaps = []

        for validator_name, result in context.validation_results.items():
            findings = result.get("findings", [])
            for finding in findings:
                severity = finding.get("severity", "info")
                message = finding.get("message", "")
                if severity in ("error", "critical", "warning"):
                    color = self._severity_to_color(severity)
                    gaps.append(
                        f"* {{color:{color}}}{validator_name}:{{color}} {message}"
                    )

        if not gaps:
            return None

        return CommentSection(
            title="Coverage Gaps",
            content="\n".join(gaps),
            severity="WARNING",
        )

    def _format_missing_scenarios(self, context: 'RAGContext') -> Optional[CommentSection]:
        """Identify missing high-risk test scenarios from pre-analysis."""
        risk_flags = context.pre_analysis.risk_flags
        scenarios = []

        # Map risk flags to suggested test scenarios
        scenario_map = {
            "financial_impact": "Financial calculation edge cases",
            "state_transition": "State machine error handling scenarios",
            "data_integrity": "Data validation boundary conditions",
            "security": "Authentication and authorization scenarios",
            "integration": "External service failure scenarios",
        }

        for flag in risk_flags:
            if flag in scenario_map:
                scenarios.append(scenario_map[flag])

        # Add scenarios based on validator issues
        if context.validation_results.get("StateValidator", {}).get("findings"):
            if "State machine error handling scenarios" not in scenarios:
                scenarios.append("State machine error handling scenarios")

        if context.validation_results.get("FinancialValidator", {}).get("findings"):
            if "Financial calculation edge cases" not in scenarios:
                scenarios.append("Financial calculation edge cases")

        if not scenarios:
            return None

        return CommentSection(
            title="Missing High-Risk Scenarios",
            content=self._format_bullet_list(scenarios),
            severity="WARNING",
        )

    def _format_priority_areas(self, context: 'RAGContext') -> Optional[CommentSection]:
        """List priority testing areas based on detected domains."""
        domains = context.pre_analysis.detected_domains
        rule_types = context.pre_analysis.priority_rule_types

        areas = []
        if "state_machine" in rule_types or any("state" in d for d in domains):
            areas.append("State Machine transitions")
        if "financial_logic" in rule_types or any("payment" in d or "financial" in d for d in domains):
            areas.append("Financial Logic calculations")
        if "cross_dependency" in rule_types:
            areas.append("Cross-dependency integrations")
        if any("b2b" in d for d in domains):
            areas.append("B2B workflow validations")

        if not areas:
            return None

        numbered = "\n".join(f"# {area}" for area in areas)
        return CommentSection(
            title="Priority Testing Areas",
            content=numbered,
        )
