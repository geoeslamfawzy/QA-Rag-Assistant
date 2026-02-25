"""
Ambiguity Comment Formatter Module

Formats get-ambiguity command output for Jira comments.
Includes: unclear requirements, undefined states, missing boundaries, vague terms.
"""
from typing import List, Optional, TYPE_CHECKING

from .base_comment_formatter import BaseCommentFormatter, JiraComment, CommentSection

if TYPE_CHECKING:
    from services.rag_context_builder import RAGContext


class AmbiguityCommentFormatter(BaseCommentFormatter):
    """
    Formats ambiguity detection for Jira comment.

    Sections:
    - Ambiguity Summary
    - Unclear Requirements
    - Undefined States/Transitions
    - Missing Boundary Conditions
    - Suggested Clarification Questions
    """

    @property
    def command_name(self) -> str:
        return "get-ambiguity"

    def format(self, context: 'RAGContext') -> JiraComment:
        """Format ambiguity findings into Jira comment."""
        if not self._has_findings(context):
            return self._format_no_findings(context)

        sections = []
        finding_count = self._count_findings(context)

        # Story header with ambiguity level
        ambiguity_level = "HIGH" if finding_count > 3 else "MEDIUM" if finding_count > 0 else "LOW"
        sections.append(CommentSection(
            title="Story",
            content=(
                self._build_story_header(context) + "\n"
                f"*Ambiguity Level:* {ambiguity_level} ({finding_count} issue(s) found)"
            ),
        ))

        # Unclear requirements from validators
        unclear_section = self._format_unclear_requirements(context)
        if unclear_section:
            sections.append(unclear_section)

        # Undefined states from StateValidator
        states_section = self._format_undefined_states(context)
        if states_section:
            sections.append(states_section)

        # Missing specifications based on domains
        missing_section = self._format_missing_specifications(context)
        if missing_section:
            sections.append(missing_section)

        # Suggested clarification questions
        questions_section = self._format_clarification_questions(context)
        if questions_section:
            sections.append(questions_section)

        return JiraComment(
            title="Ambiguity Analysis",
            sections=sections,
            has_findings=True,
            finding_count=finding_count,
            source_command=self.command_name,
        )

    def _format_unclear_requirements(self, context: 'RAGContext') -> Optional[CommentSection]:
        """List unclear requirements from validators."""
        unclear_items = []

        for validator_name, result in context.validation_results.items():
            findings = result.get("findings", [])
            for finding in findings:
                severity = finding.get("severity", "info")
                message = finding.get("message", "")
                if message:
                    color = self._severity_to_color(severity)
                    unclear_items.append(
                        f"* {{color:{color}}}{validator_name}:{{color}} {message}"
                    )

        if not unclear_items:
            return None

        return CommentSection(
            title="Unclear Requirements",
            content="\n".join(unclear_items),
            severity="WARNING",
        )

    def _format_undefined_states(self, context: 'RAGContext') -> Optional[CommentSection]:
        """Identify undefined states from StateValidator details."""
        state_result = context.validation_results.get("StateValidator", {})
        details = state_result.get("details", {})

        mentioned_states = details.get("mentioned_states", [])
        if not mentioned_states:
            # Try to extract from findings
            findings = state_result.get("findings", [])
            for finding in findings:
                msg = finding.get("message", "")
                if "state" in msg.lower():
                    return CommentSection(
                        title="Undefined States",
                        content=f"* {msg}",
                        severity="WARNING",
                    )
            return None

        # If states are mentioned but no state machine found
        state_machines_loaded = details.get("state_machines_loaded", 0)
        if state_machines_loaded == 0 and mentioned_states:
            states_list = ", ".join(mentioned_states) if isinstance(mentioned_states, list) else str(mentioned_states)
            return CommentSection(
                title="Undefined States",
                content=f"States mentioned but no state machine definitions found: {states_list}",
                severity="WARNING",
            )

        return None

    def _format_missing_specifications(self, context: 'RAGContext') -> Optional[CommentSection]:
        """Identify missing specifications based on detected domains."""
        domains = context.pre_analysis.detected_domains
        missing = []

        domain_specs = {
            "payments": "Verify all payments-related rules are covered",
            "b2b_pricing": "Verify all b2b_pricing-related rules are covered",
            "trips": "Verify trip lifecycle states are fully defined",
            "programs": "Verify program rules and limits are specified",
            "gift_cards": "Verify gift card balance and redemption rules",
        }

        for domain in domains:
            if domain in domain_specs:
                missing.append(f"* *{domain}:* {domain_specs[domain]}")

        if not missing:
            return None

        return CommentSection(
            title="Missing Specifications",
            content="\n".join(missing),
            severity="INFO",
        )

    def _format_clarification_questions(self, context: 'RAGContext') -> Optional[CommentSection]:
        """Generate clarification questions based on findings."""
        questions = []

        # Based on StateValidator findings
        state_result = context.validation_results.get("StateValidator", {})
        if state_result.get("findings"):
            states = state_result.get("details", {}).get("mentioned_states", [])
            if states:
                state_name = states[0] if isinstance(states, list) else str(states)
                questions.append(f"What are the valid state transitions for {state_name}?")

        # Based on FinancialValidator findings
        financial_result = context.validation_results.get("FinancialValidator", {})
        if financial_result.get("findings"):
            questions.append("What error scenarios should be handled for financial operations?")

        # Based on risk flags
        if "security" in context.pre_analysis.risk_flags:
            questions.append("What are the authentication/authorization requirements?")

        if "integration" in context.pre_analysis.risk_flags:
            questions.append("What external services are involved and their failure modes?")

        if not questions:
            return None

        numbered = "\n".join(f"# {q}" for q in questions[:5])  # Limit to 5 questions
        return CommentSection(
            title="Suggested Clarification Questions",
            content=numbered,
        )
