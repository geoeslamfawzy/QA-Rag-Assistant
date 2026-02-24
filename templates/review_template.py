"""
Review Template Module

Template for ./bin/review command output.
Analyzes test coverage gaps and provides recommendations.
Uses PromptLoader for static text with dynamic injection.
"""
from typing import Dict, Any
from datetime import datetime

from .base_template import BaseTemplate
from services.rag_context_builder import RAGContext
from utils.prompt_loader import PromptLoader


class ReviewTemplate(BaseTemplate):
    """
    Template for test case review output.
    Loads static prompt from qa-assistant/review.prompt.md
    and injects dynamic RAG context data.
    """

    @property
    def template_name(self) -> str:
        return "review"

    def render(self, context: RAGContext, options: Dict[str, Any]) -> str:
        # Load template with common footer
        prompt = PromptLoader.load_with_common("review.prompt.md")

        # Inject header data
        story = context.story
        prompt.inject("STORY_KEY", story.get("key", "UNKNOWN"))
        prompt.inject("STORY_TITLE", story.get("title", story.get("summary", "Untitled")))
        prompt.inject("TIMESTAMP", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Inject story section
        prompt.inject("STORY_SECTION", self._format_story_section(context))

        # Inject coverage analysis
        pre = context.pre_analysis
        prompt.inject("RISK_LEVEL", pre.risk_level.upper())
        prompt.inject("INTENTS_LIST", self._format_intents(context))
        prompt.inject("DOMAINS_LIST", ", ".join(pre.detected_domains) if pre.detected_domains else "No specific domains detected")

        # Inject gap detection
        prompt.inject("COVERAGE_GAPS", self._format_gaps(context))

        # Inject test patterns
        prompt.inject("TEST_PATTERNS", self._format_test_patterns(context))

        # Inject recommendations
        prompt.inject("PRIORITY_AREAS", self._format_priority_areas(context))
        prompt.inject("RISK_AREAS", self._format_risk_areas(context))

        return prompt.render()

    def _format_story_section(self, context: RAGContext) -> str:
        """Format story details section."""
        story = context.story
        lines = [
            f"- **Key:** {story.get('key', 'N/A')}",
            f"- **Status:** {story.get('status', 'N/A')}",
            f"- **Priority:** {story.get('priority', 'N/A')}",
            f"- **Type:** {story.get('issue_type', 'N/A')}",
            "",
            "### Description",
            "",
            story.get('description', 'No description') or 'No description',
        ]

        ac = story.get('acceptance_criteria')
        if ac:
            lines.extend([
                "",
                "### Acceptance Criteria",
                "",
                ac if isinstance(ac, str) else "\n".join(ac),
            ])

        return "\n".join(lines)

    def _format_intents(self, context: RAGContext) -> str:
        """Format detected intents list."""
        pre = context.pre_analysis
        if not pre.detected_intents:
            return "No specific intents detected."

        lines = []
        for intent in pre.detected_intents[:10]:
            lines.append(f"- **{intent.intent}** (confidence: {intent.confidence:.0%})")
        return "\n".join(lines)

    def _format_gaps(self, context: RAGContext) -> str:
        """Format coverage gaps from validators."""
        lines = []
        gaps_found = False

        for name, result in context.validation_results.items():
            if not result.get("passed", True):
                gaps_found = True
                lines.append(f"### {name} Gaps")
                lines.append("")

                for finding in result.get("findings", []):
                    severity = finding.get("severity", "INFO")
                    message = finding.get("message", "")
                    suggestion = finding.get("suggestion", "")

                    lines.append(f"- **[{severity}]** {message}")
                    if suggestion:
                        lines.append(f"  - *Suggestion:* {suggestion}")

                lines.append("")

        if not gaps_found:
            lines.append("No critical coverage gaps detected from validators.")

        return "\n".join(lines)

    def _format_test_patterns(self, context: RAGContext) -> str:
        """Extract test patterns from retrieved knowledge."""
        if not context.retrieved_chunks:
            return "No relevant test patterns found."

        lines = []
        by_type = {}
        for chunk in context.retrieved_chunks:
            rule_type = chunk.chunk.metadata.get("rule_type", "general")
            if rule_type not in by_type:
                by_type[rule_type] = []
            by_type[rule_type].append(chunk)

        for rule_type, chunks in by_type.items():
            lines.append(f"### {rule_type.replace('_', ' ').title()}")
            lines.append("")

            for chunk in chunks[:3]:
                lines.append(f"**{chunk.chunk.id}** (relevance: {chunk.final_score:.0%})")
                content = chunk.chunk.content[:300]
                if len(chunk.chunk.content) > 300:
                    content += "..."
                lines.append(f"> {content}")
                lines.append("")

        return "\n".join(lines)

    def _format_priority_areas(self, context: RAGContext) -> str:
        """Format priority testing areas."""
        pre = context.pre_analysis
        if not pre.priority_rule_types:
            return "No specific priority areas identified."

        lines = []
        for rule_type in pre.priority_rule_types:
            lines.append(f"1. {rule_type.replace('_', ' ').title()}")
        return "\n".join(lines)

    def _format_risk_areas(self, context: RAGContext) -> str:
        """Format risk areas requiring tests."""
        pre = context.pre_analysis
        if not pre.risk_flags:
            return "No specific risk areas identified."

        lines = []
        for flag in pre.risk_flags:
            lines.append(f"- {flag}")
        return "\n".join(lines)
