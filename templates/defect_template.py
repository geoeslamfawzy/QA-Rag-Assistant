"""
Defect Template Module

Template for ./bin/write-defect command output.
Generates defect report for rule/state/financial violations.
Uses PromptLoader for static text with dynamic injection.
"""
from typing import Dict, Any
from datetime import datetime

from .base_template import BaseTemplate
from services.rag_context_builder import RAGContext
from utils.prompt_loader import PromptLoader


class DefectTemplate(BaseTemplate):
    """
    Template for violation defect output.
    Loads static prompt from qa-assistant/write-defect.prompt.md
    and injects dynamic RAG context data.

    Violation Types:
    - rule: Rule engine violations
    - state: State machine violations
    - financial: Financial calculation violations
    - cross_dep: Cross-dependency violations
    """

    # Violation type configurations
    VIOLATION_TITLES = {
        "rule": "Business Rule Violation",
        "state": "State Machine Violation",
        "financial": "Financial Calculation Violation",
        "cross_dep": "Cross-Dependency Violation",
    }

    SEVERITY_MAP = {
        "rule": "High",
        "state": "Critical",
        "financial": "Critical",
        "cross_dep": "Medium",
    }

    VALIDATOR_NAMES = {
        "rule": "RuleEngine",
        "state": "StateValidator",
        "financial": "FinancialValidator",
        "cross_dep": "CrossDepChecker",
    }

    IMPACT_DESCRIPTIONS = {
        "rule": "Business rule violations can lead to incorrect system behavior and data inconsistencies.",
        "state": "State machine violations can cause invalid transitions and system instability.",
        "financial": "Financial violations can result in incorrect calculations, billing errors, or compliance issues.",
        "cross_dep": "Cross-dependency violations can cause integration failures and cascading errors.",
    }

    REMEDIATION_STEPS = {
        "rule": [
            "1. **Review Business Rules:** Verify the story aligns with documented business rules",
            "2. **Update Requirements:** Modify story to comply with rules",
            "3. **Add Validation:** Ensure implementation includes rule validation",
            "4. **Test Coverage:** Add test cases for rule compliance",
        ],
        "state": [
            "1. **Review State Machine:** Verify valid state transitions",
            "2. **Map Current State:** Document all possible states",
            "3. **Fix Transitions:** Ensure only valid transitions are allowed",
            "4. **Add Guards:** Implement transition guards",
        ],
        "financial": [
            "1. **Review Calculations:** Verify all financial formulas",
            "2. **Check Precision:** Ensure correct decimal handling",
            "3. **Validate Constraints:** Check min/max values, rounding",
            "4. **Add Audit Trail:** Ensure all financial changes are logged",
        ],
        "cross_dep": [
            "1. **Map Dependencies:** Document all module dependencies",
            "2. **Review Interfaces:** Verify API contracts",
            "3. **Add Integration Tests:** Cover cross-module scenarios",
            "4. **Update Documentation:** Document dependency requirements",
        ],
    }

    @property
    def template_name(self) -> str:
        return "defect"

    def render(self, context: RAGContext, options: Dict[str, Any]) -> str:
        violation_type = options.get("violation_type", "rule") if options else "rule"

        # Load template with common footer
        prompt = PromptLoader.load_with_common("write-defect.prompt.md")

        # Inject header data
        story = context.story
        prompt.inject("STORY_KEY", story.get("key", "UNKNOWN"))
        prompt.inject("STORY_TITLE", story.get("title", story.get("summary", "Untitled")))
        prompt.inject("TIMESTAMP", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        prompt.inject("VIOLATION_TITLE", self.VIOLATION_TITLES.get(violation_type, "Violation"))
        prompt.inject("VIOLATION_TYPE_TITLE", violation_type.replace('_', ' ').title())
        prompt.inject("SEVERITY", self.SEVERITY_MAP.get(violation_type, "High"))

        # Inject story metadata
        prompt.inject("STORY_URL", story.get("url", "#"))
        prompt.inject("STORY_STATUS", story.get("status", "N/A"))
        prompt.inject("ISSUE_TYPE", story.get("issue_type", "N/A"))

        # Inject violation summary
        prompt.inject("VIOLATION_SUMMARY", self._format_violation_summary(context, violation_type))

        # Inject violation details
        prompt.inject("VIOLATION_DETAILS", self._format_violation_details(context, violation_type))

        # Inject evidence
        prompt.inject("EVIDENCE", self._format_evidence(context, violation_type))

        # Inject impact analysis
        pre = context.pre_analysis
        prompt.inject("IMPACT_DESCRIPTION", self.IMPACT_DESCRIPTIONS.get(violation_type, "System behavior may be affected."))
        prompt.inject("RISK_LEVEL", pre.risk_level.upper())
        prompt.inject("AFFECTED_DOMAINS", self._format_affected_domains(context))

        # Inject remediation steps
        prompt.inject("REMEDIATION_STEPS", self._format_remediation_steps(violation_type))
        prompt.inject("VALIDATOR_SUGGESTIONS", self._format_validator_suggestions(context))

        return prompt.render()

    def _format_violation_summary(self, context: RAGContext, violation_type: str) -> str:
        """Format violation summary from validator results."""
        validator_name = self.VALIDATOR_NAMES.get(violation_type, "")
        result = context.validation_results.get(validator_name, {})

        lines = []
        if result:
            summary = result.get("summary", "Violation detected by validator.")
            score = result.get("score", 0)
            lines.append(f"**Validator:** {validator_name}")
            lines.append(f"**Score:** {score:.0%}")
            lines.append(f"**Status:** {'PASS' if result.get('passed') else 'FAIL'}")
            lines.append("")
            lines.append(summary)
        else:
            lines.append(f"Potential {violation_type} violation detected during analysis.")

        return "\n".join(lines)

    def _format_violation_details(self, context: RAGContext, violation_type: str) -> str:
        """Format violation details from validators."""
        validator_name = self.VALIDATOR_NAMES.get(violation_type, "")
        result = context.validation_results.get(validator_name, {})

        if not result:
            return "No detailed findings available from validator."

        lines = []
        findings = result.get("findings", [])

        if findings:
            lines.append("### Findings")
            lines.append("")

            for i, finding in enumerate(findings, 1):
                severity = finding.get("severity", "INFO")
                message = finding.get("message", "")
                rule_id = finding.get("rule_id", "")
                location = finding.get("location", "")

                lines.append(f"#### Finding {i}")
                lines.append("")
                lines.append(f"- **Severity:** {severity}")
                lines.append(f"- **Message:** {message}")
                if rule_id:
                    lines.append(f"- **Rule ID:** {rule_id}")
                if location:
                    lines.append(f"- **Location:** {location}")
                lines.append("")

        # Additional details
        details = result.get("details", {})
        if details:
            lines.append("### Additional Details")
            lines.append("")
            for key, value in details.items():
                if isinstance(value, list):
                    lines.append(f"**{key}:**")
                    for item in value[:5]:
                        lines.append(f"- {item}")
                else:
                    lines.append(f"- **{key}:** {value}")
            lines.append("")

        return "\n".join(lines) if lines else "No detailed findings available from validator."

    def _format_evidence(self, context: RAGContext, violation_type: str) -> str:
        """Format evidence from knowledge context."""
        # Filter chunks relevant to violation type
        relevant_chunks = []
        for chunk in context.retrieved_chunks:
            rule_type = chunk.chunk.metadata.get("rule_type", "")
            if violation_type in rule_type.lower() or rule_type == "general":
                relevant_chunks.append(chunk)

        if not relevant_chunks:
            relevant_chunks = context.retrieved_chunks[:3]

        if not relevant_chunks:
            return "No relevant knowledge base entries found."

        lines = []
        for chunk in relevant_chunks[:3]:
            lines.append(f"### {chunk.chunk.id}")
            lines.append(f"*Module: {chunk.chunk.metadata.get('module', 'unknown')} | Relevance: {chunk.final_score:.0%}*")
            lines.append("")

            content = chunk.chunk.content[:400]
            if len(chunk.chunk.content) > 400:
                content += "..."
            lines.append(f"> {content}")
            lines.append("")

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

    def _format_remediation_steps(self, violation_type: str) -> str:
        """Format remediation steps based on violation type."""
        steps = self.REMEDIATION_STEPS.get(violation_type, [])
        return "\n".join(steps) if steps else ""

    def _format_validator_suggestions(self, context: RAGContext) -> str:
        """Format validator suggestions."""
        suggestions = []
        for name, result in context.validation_results.items():
            for finding in result.get("findings", []):
                if finding.get("suggestion"):
                    suggestions.append(finding.get("suggestion"))

        if not suggestions:
            return ""

        unique_suggestions = list(set(suggestions))[:5]
        lines = ["### Validator Suggestions", ""]
        for suggestion in unique_suggestions:
            lines.append(f"- {suggestion}")
        return "\n".join(lines)
