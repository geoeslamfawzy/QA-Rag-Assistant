"""
Ambiguity Template Module

Template for ./bin/get-ambiguity command output.
Detects unclear or ambiguous requirements.
Uses PromptLoader for static text with dynamic injection.
"""
from typing import Dict, Any
from datetime import datetime

from .base_template import BaseTemplate
from services.rag_context_builder import RAGContext
from utils.prompt_loader import PromptLoader


class AmbiguityTemplate(BaseTemplate):
    """
    Template for ambiguity detection output.
    Loads static prompt from qa-assistant/ambiguity.prompt.md
    and injects dynamic RAG context data.
    """

    # Vague language keywords to detect
    VAGUE_WORDS = ['should', 'might', 'could', 'possibly', 'maybe', 'etc',
                   'and so on', 'appropriate', 'suitable']

    # Keywords suggesting unstated assumptions
    ASSUMPTION_KEYWORDS = ['assume', 'default', 'implicit', 'standard', 'typical', 'usually']

    @property
    def template_name(self) -> str:
        return "ambiguity"

    def render(self, context: RAGContext, options: Dict[str, Any]) -> str:
        # Load template with common footer
        prompt = PromptLoader.load_with_common("ambiguity.prompt.md")

        # Inject header data
        story = context.story
        prompt.inject("STORY_KEY", story.get("key", "UNKNOWN"))
        prompt.inject("STORY_TITLE", story.get("title", story.get("summary", "Untitled")))
        prompt.inject("TIMESTAMP", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Inject story section
        prompt.inject("STORY_SECTION", self._format_story_section(context))

        # Inject ambiguity analysis
        prompt.inject("AMBIGUITY_SUMMARY", self._format_ambiguity_summary(context))

        # Inject unclear requirements
        prompt.inject("UNCLEAR_REQUIREMENTS", self._format_unclear_requirements(context))

        # Inject missing specifications
        prompt.inject("MISSING_SPECIFICATIONS", self._format_missing_specifications(context))

        # Inject unstated assumptions
        prompt.inject("UNSTATED_ASSUMPTIONS", self._format_unstated_assumptions(context))

        # Inject clarification questions
        prompt.inject("CLARIFICATION_QUESTIONS", self._format_clarification_questions(context))

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

    def _format_ambiguity_summary(self, context: RAGContext) -> str:
        """Analyze overall ambiguity level."""
        pre = context.pre_analysis
        story = context.story

        # Calculate ambiguity factors
        ambiguity_factors = []

        # Check description length
        desc = story.get('description', '') or ''
        if len(desc) < 100:
            ambiguity_factors.append("Short description may lack detail")

        # Check acceptance criteria
        ac = story.get('acceptance_criteria')
        if not ac:
            ambiguity_factors.append("Missing acceptance criteria")

        # Check for vague keywords
        desc_lower = desc.lower()
        found_vague = [w for w in self.VAGUE_WORDS if w in desc_lower]
        if found_vague:
            ambiguity_factors.append(f"Contains vague language: {', '.join(found_vague)}")

        # Risk assessment connection
        if pre.risk_level in ['high', 'critical']:
            ambiguity_factors.append(f"High risk level ({pre.risk_level}) may indicate unclear scope")

        # Build summary
        lines = []
        if ambiguity_factors:
            lines.append(f"**Ambiguity Level:** HIGH ({len(ambiguity_factors)} issues found)")
            lines.append("")
            lines.append("**Factors:**")
            for factor in ambiguity_factors:
                lines.append(f"- {factor}")
        else:
            lines.append("**Ambiguity Level:** LOW")
            lines.append("")
            lines.append("Requirements appear reasonably clear.")

        return "\n".join(lines)

    def _format_unclear_requirements(self, context: RAGContext) -> str:
        """Identify unclear requirements from validators."""
        lines = []
        unclear_found = False

        for name, result in context.validation_results.items():
            findings = result.get("findings", [])
            for finding in findings:
                severity = finding.get("severity", "")
                if severity.upper() in ["WARNING", "ERROR", "CRITICAL"]:
                    unclear_found = True
                    lines.append(f"- **{name}:** {finding.get('message', '')}")
                    if finding.get("suggestion"):
                        lines.append(f"  - *Action:* {finding.get('suggestion')}")

        if not unclear_found:
            lines.append("No unclear requirements detected from validation.")

        return "\n".join(lines)

    def _format_missing_specifications(self, context: RAGContext) -> str:
        """Detect missing specifications based on knowledge context."""
        pre = context.pre_analysis
        lines = []

        # Compare detected domains/intents with knowledge patterns
        if pre.detected_domains:
            lines.append("Based on detected domains, the following may need specification:")
            lines.append("")
            for domain in pre.detected_domains[:5]:
                lines.append(f"- **{domain}:** Verify all {domain}-related rules are covered")

        if pre.priority_rule_types:
            lines.append("")
            lines.append("Based on priority rule types:")
            lines.append("")
            for rule_type in pre.priority_rule_types[:5]:
                lines.append(f"- **{rule_type.replace('_', ' ').title()}:** Ensure complete specification")

        if not lines:
            lines.append("No missing specifications detected.")

        return "\n".join(lines)

    def _format_unstated_assumptions(self, context: RAGContext) -> str:
        """Identify potential unstated assumptions."""
        assumptions_found = []

        for chunk in context.retrieved_chunks[:10]:
            content_lower = chunk.chunk.content.lower()
            for keyword in self.ASSUMPTION_KEYWORDS:
                if keyword in content_lower:
                    assumptions_found.append({
                        "source": chunk.chunk.id,
                        "keyword": keyword,
                        "preview": chunk.chunk.content[:100],
                    })
                    break

        lines = []
        if assumptions_found:
            lines.append("The following assumptions may need explicit confirmation:")
            lines.append("")
            for assumption in assumptions_found[:5]:
                lines.append(f"- **Source:** {assumption['source']}")
                lines.append(f"  > {assumption['preview']}...")
        else:
            lines.append("No obvious unstated assumptions detected.")

        return "\n".join(lines)

    def _format_clarification_questions(self, context: RAGContext) -> str:
        """Generate clarification questions."""
        pre = context.pre_analysis
        story = context.story

        questions = []

        # Based on missing AC
        if not story.get('acceptance_criteria'):
            questions.append("What are the specific acceptance criteria for this story?")

        # Based on risk flags
        for flag in pre.risk_flags[:3]:
            questions.append(f"Regarding '{flag}': What is the expected behavior?")

        # Based on detected intents
        for intent in pre.detected_intents[:3]:
            questions.append(f"For '{intent.intent}': Are there any edge cases to consider?")

        # Standard questions
        questions.extend([
            "What error scenarios should be handled?",
            "Are there any performance requirements?",
            "What are the integration dependencies?",
        ])

        lines = []
        for i, q in enumerate(questions[:10], 1):
            lines.append(f"{i}. {q}")

        return "\n".join(lines)
