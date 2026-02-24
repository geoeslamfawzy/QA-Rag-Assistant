"""
Story Defect Template Module

Template for ./bin/write-story-defect command output.
Generates defect report for requirement issues.
Uses PromptLoader for static text with dynamic injection.
"""
from typing import Dict, Any
from datetime import datetime

from .base_template import BaseTemplate
from services.rag_context_builder import RAGContext
from utils.prompt_loader import PromptLoader


class StoryDefectTemplate(BaseTemplate):
    """
    Template for story defect output.
    Loads static prompt from qa-assistant/write-story-defect.prompt.md
    and injects dynamic RAG context data.

    Issue Types:
    - missing_ac: Missing acceptance criteria
    - unclear_requirement: Unclear or ambiguous requirement
    - incomplete_story: Story missing essential elements
    """

    # Issue type configurations
    ISSUE_TITLES = {
        "missing_ac": "Missing Acceptance Criteria",
        "unclear_requirement": "Unclear Requirement Detected",
        "incomplete_story": "Incomplete Story Definition",
    }

    ISSUE_SUMMARIES = {
        "missing_ac": "Story is missing acceptance criteria, making it impossible to validate implementation.",
        "unclear_requirement": "Story contains unclear or ambiguous requirements that need clarification.",
        "incomplete_story": "Story is missing essential elements required for implementation.",
    }

    @property
    def template_name(self) -> str:
        return "story-defect"

    def render(self, context: RAGContext, options: Dict[str, Any]) -> str:
        issue_type = options.get("issue_type", "missing_ac") if options else "missing_ac"

        # Load template with common footer
        prompt = PromptLoader.load_with_common("write-story-defect.prompt.md")

        # Inject header data
        story = context.story
        prompt.inject("STORY_KEY", story.get("key", "UNKNOWN"))
        prompt.inject("STORY_TITLE", story.get("title", story.get("summary", "Untitled")))
        prompt.inject("TIMESTAMP", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        prompt.inject("ISSUE_TITLE", self.ISSUE_TITLES.get(issue_type, "Story Issue"))
        prompt.inject("ISSUE_TYPE_TITLE", issue_type.replace('_', ' ').title())

        # Inject story metadata
        prompt.inject("STORY_URL", story.get("url", "#"))
        prompt.inject("STORY_STATUS", story.get("status", "N/A"))
        prompt.inject("STORY_ASSIGNEE", story.get("assignee", "Unassigned"))

        # Inject defect summary
        prompt.inject("DEFECT_SUMMARY", self.ISSUE_SUMMARIES.get(issue_type, "Story has quality issues that need addressing."))

        # Inject story content
        prompt.inject("STORY_DESCRIPTION", story.get('description', 'No description') or '*No description provided*')
        prompt.inject("ACCEPTANCE_CRITERIA", self._format_acceptance_criteria(story))

        # Inject issue description
        prompt.inject("ISSUE_PROBLEM", self._format_issue_problem(context, issue_type))
        prompt.inject("VALIDATOR_FINDINGS", self._format_validator_findings(context, issue_type))
        prompt.inject("RISK_FLAGS", self._format_risk_flags(context))

        # Inject impact assessment
        pre = context.pre_analysis
        prompt.inject("RISK_LEVEL", pre.risk_level.upper())
        prompt.inject("AFFECTED_DOMAINS", self._format_affected_domains(context))

        # Inject recommended actions
        prompt.inject("RECOMMENDED_ACTIONS", self._format_recommended_actions(issue_type))
        prompt.inject("VALIDATOR_SUGGESTIONS", self._format_validator_suggestions(context))

        return prompt.render()

    def _format_acceptance_criteria(self, story: dict) -> str:
        """Format acceptance criteria."""
        ac = story.get('acceptance_criteria')
        if ac:
            return ac if isinstance(ac, str) else "\n".join(ac)
        return "*No acceptance criteria defined*"

    def _format_issue_problem(self, context: RAGContext, issue_type: str) -> str:
        """Format the issue problem section."""
        story = context.story

        if issue_type == "missing_ac":
            return "\n".join([
                "The story does not have defined acceptance criteria. This causes:",
                "",
                "1. **Testing Ambiguity:** QA cannot create test cases without clear pass/fail criteria",
                "2. **Implementation Risk:** Developers may interpret requirements differently",
                "3. **Scope Creep:** Without clear boundaries, the story may expand uncontrollably",
            ])

        elif issue_type == "unclear_requirement":
            return "The following areas are unclear or ambiguous:"

        elif issue_type == "incomplete_story":
            lines = ["The story is missing essential elements:", ""]
            if len(story.get('description', '') or '') < 100:
                lines.append("- **Description:** Too brief (less than 100 characters)")
            if not story.get('acceptance_criteria'):
                lines.append("- **Acceptance Criteria:** Missing")
            if not story.get('assignee') or story.get('assignee') == 'Unassigned':
                lines.append("- **Assignee:** Not assigned")
            return "\n".join(lines)

        return ""

    def _format_validator_findings(self, context: RAGContext, issue_type: str) -> str:
        """Format validator findings for unclear requirements."""
        if issue_type != "unclear_requirement":
            return ""

        lines = []
        for name, result in context.validation_results.items():
            for finding in result.get("findings", []):
                lines.append(f"- **{name}:** {finding.get('message', '')}")

        return "\n".join(lines) if lines else ""

    def _format_risk_flags(self, context: RAGContext) -> str:
        """Format risk flags."""
        pre = context.pre_analysis
        if not pre.risk_flags:
            return ""

        lines = ["", "### Risk Flags"]
        for flag in pre.risk_flags:
            lines.append(f"- {flag}")
        return "\n".join(lines)

    def _format_affected_domains(self, context: RAGContext) -> str:
        """Format affected domains."""
        pre = context.pre_analysis
        if not pre.detected_domains:
            return ""

        lines = ["**Affected Domains:**"]
        for domain in pre.detected_domains[:5]:
            lines.append(f"- {domain}")
        return "\n".join(lines)

    def _format_recommended_actions(self, issue_type: str) -> str:
        """Format recommended actions based on issue type."""
        if issue_type == "missing_ac":
            return "\n".join([
                "1. **Add Acceptance Criteria:** Define clear, testable acceptance criteria",
                "2. **Review with PO:** Ensure product owner validates the criteria",
                "3. **Update Story:** Add criteria before moving to development",
            ])

        elif issue_type == "unclear_requirement":
            return "\n".join([
                "1. **Clarify with PO:** Schedule a refinement session",
                "2. **Document Assumptions:** List all assumptions explicitly",
                "3. **Add Examples:** Include concrete examples in the description",
                "4. **Update AC:** Ensure acceptance criteria are specific and measurable",
            ])

        elif issue_type == "incomplete_story":
            return "\n".join([
                "1. **Expand Description:** Add detailed requirements and context",
                "2. **Add AC:** Define acceptance criteria",
                "3. **Assign Owner:** Ensure story has an assignee",
                "4. **Review Dependencies:** Document any dependencies",
            ])

        return ""

    def _format_validator_suggestions(self, context: RAGContext) -> str:
        """Format validator suggestions."""
        suggestions = []
        for name, result in context.validation_results.items():
            for finding in result.get("findings", []):
                if finding.get("suggestion"):
                    suggestions.append(f"- {finding.get('suggestion')}")

        if not suggestions:
            return ""

        lines = ["### Validator Suggestions", ""]
        lines.extend(suggestions[:5])
        return "\n".join(lines)
