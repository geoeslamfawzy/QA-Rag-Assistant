"""
Defect Builder Module

Builds structured Defect objects from RAG context.
Enforces anti-hallucination by using ONLY retrieved context.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from models.defect import Defect, COMPONENT_MAP
from services.rag_context_builder import RAGContext


@dataclass
class DefectBuildOptions:
    """Options for building a defect."""
    violation_type: str = "rule"  # rule, state, financial, cross_dep
    issue_type: str = "missing_ac"  # missing_ac, unclear_requirement, incomplete_story
    defect_type: str = "violation"  # violation, story_quality
    custom_summary: Optional[str] = None  # Override auto-generated summary
    custom_description: Optional[str] = None  # Override auto-generated description


class DefectBuilder:
    """
    Builds Defect objects from RAG context.

    Design:
    - Uses ONLY data from RAGContext (anti-hallucination)
    - Extracts validator findings and rule IDs
    - Maps domains to components
    - Marks "[Insufficient Context]" when required data is missing
    """

    # Violation type to validator name mapping
    VALIDATOR_NAMES: Dict[str, str] = {
        "rule": "RuleEngine",
        "state": "StateValidator",
        "financial": "FinancialValidator",
        "cross_dep": "CrossDepChecker",
    }

    # Violation type titles
    VIOLATION_TITLES: Dict[str, str] = {
        "rule": "Business Rule Violation",
        "state": "State Machine Violation",
        "financial": "Financial Calculation Violation",
        "cross_dep": "Cross-Dependency Violation",
    }

    # Issue type titles
    ISSUE_TITLES: Dict[str, str] = {
        "missing_ac": "Missing Acceptance Criteria",
        "unclear_requirement": "Unclear Requirement",
        "incomplete_story": "Incomplete Story Definition",
    }

    # Default risk levels by violation type
    DEFAULT_RISK_LEVELS: Dict[str, str] = {
        "rule": "HIGH",
        "state": "CRITICAL",
        "financial": "CRITICAL",
        "cross_dep": "MEDIUM",
    }

    def build_violation_defect(
        self,
        context: RAGContext,
        options: DefectBuildOptions
    ) -> Defect:
        """
        Build a violation defect from RAG context.

        Args:
            context: RAGContext from RAGContextBuilder
            options: Build options including violation_type

        Returns:
            Defect object ready for CSV export
        """
        violation_type = options.violation_type
        story = context.story

        # Use custom values if provided, otherwise auto-generate from RAG context
        summary = options.custom_summary or self._extract_violation_summary(context, options)
        preconditions = self._extract_preconditions(context)
        description = options.custom_description or self._extract_violation_description(context, options)
        steps = self._extract_steps_to_reproduce(context)
        expected = self._extract_expected_results(context, options)
        actual = self._extract_actual_results(context, options)
        rule_ids = self._extract_rule_ids(context, options)
        component = self._resolve_component(context)
        risk_level = self._resolve_risk_level(context, options)

        return Defect(
            summary=summary,
            preconditions=preconditions,
            description=description,
            steps_to_reproduce=steps,
            expected_results=expected,
            actual_results=actual,
            environment="Yassir Mobility B2B Platform",
            risk_level=risk_level,
            component=component,
            defect_type="violation",
            violation_type=violation_type,
            issue_type=None,
            rule_ids=rule_ids,
        )

    def build_story_defect(
        self,
        context: RAGContext,
        options: DefectBuildOptions
    ) -> Defect:
        """
        Build a story quality defect from RAG context.

        Args:
            context: RAGContext from RAGContextBuilder
            options: Build options including issue_type and custom_description

        Returns:
            Defect object ready for CSV export
        """
        issue_type = options.issue_type
        story = context.story

        # Use custom values if provided, otherwise auto-generate from RAG context
        summary = options.custom_summary or self._extract_story_defect_summary(context, options)
        preconditions = self._extract_preconditions(context)

        # Preserve user_description separately from auto-generated description
        user_description = options.custom_description or ""
        description = self._extract_story_defect_description(context, options) if not options.custom_description else ""

        steps = self._extract_story_review_steps(context, options)
        expected = self._extract_story_expected_results(context, options)
        actual = self._extract_story_actual_results(context, options)

        # Extract rule IDs from all validators for story defects
        rule_ids = self._extract_story_rule_ids(context)

        component = self._resolve_component(context)
        risk_level = self._resolve_risk_level(context, options)

        return Defect(
            summary=summary,
            preconditions=preconditions,
            description=description,
            user_description=user_description,
            steps_to_reproduce=steps,
            expected_results=expected,
            actual_results=actual,
            environment="Yassir Mobility B2B Platform",
            risk_level=risk_level,
            component=component,
            defect_type="story_quality",
            violation_type=None,
            issue_type=issue_type,
            rule_ids=rule_ids,
            parent_key=story.get("key", ""),  # Set parent to story key
        )

    def _extract_violation_summary(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> str:
        """Build defect summary from story and violation type."""
        story = context.story
        violation_type = options.violation_type
        title = self.VIOLATION_TITLES.get(violation_type, "Violation")
        story_title = story.get("title", story.get("summary", "Unknown Story"))
        story_key = story.get("key", "")

        return f"{title}: [{story_key}] {story_title}"

    def _extract_story_defect_summary(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> str:
        """Build story defect summary."""
        story = context.story
        issue_type = options.issue_type
        title = self.ISSUE_TITLES.get(issue_type, "Story Issue")
        story_title = story.get("title", story.get("summary", "Unknown Story"))
        story_key = story.get("key", "")

        return f"{title}: [{story_key}] {story_title}"

    def _extract_preconditions(self, context: RAGContext) -> str:
        """Extract preconditions from story context."""
        story = context.story
        preconditions = []

        # Extract from story description if available
        story_key = story.get("key", "")
        if story_key:
            preconditions.append(f"Story {story_key} exists in backlog")

        # Add domain context
        pre_analysis = context.pre_analysis
        if pre_analysis.detected_domains:
            domains = ", ".join(pre_analysis.detected_domains[:3])
            preconditions.append(f"User has access to {domains} module(s)")

        if not preconditions:
            return "[Insufficient Context: preconditions]"

        return "\n".join(preconditions)

    def _extract_violation_description(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> str:
        """Build description from validator findings."""
        violation_type = options.violation_type
        validator_name = self.VALIDATOR_NAMES.get(violation_type, "")
        result = context.validation_results.get(validator_name, {})

        if not result:
            return f"Potential {violation_type} violation detected during RAG analysis."

        lines = []
        summary = result.get("summary", "")
        if summary:
            lines.append(summary)

        # Add score if available
        score = result.get("score")
        if score is not None:
            lines.append(f"Validation Score: {score:.0%}")

        if not lines:
            return f"Potential {violation_type} violation detected during RAG analysis."

        return "\n".join(lines)

    def _extract_story_defect_description(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> str:
        """Build story defect description."""
        issue_type = options.issue_type
        story = context.story

        if issue_type == "missing_ac":
            return (
                "Story does not have defined acceptance criteria. "
                "This prevents proper test case creation and implementation validation."
            )
        elif issue_type == "unclear_requirement":
            # Extract unclear areas from validators
            unclear_areas = self._extract_unclear_areas(context)
            if unclear_areas:
                return f"Story contains unclear or ambiguous requirements:\n{unclear_areas}"
            return "Story contains unclear or ambiguous requirements that need clarification."
        elif issue_type == "incomplete_story":
            missing = []
            if not story.get("description") or len(story.get("description", "")) < 50:
                missing.append("- Description is missing or too brief")
            if not story.get("acceptance_criteria"):
                missing.append("- Acceptance criteria not defined")
            if not story.get("assignee") or story.get("assignee") == "Unassigned":
                missing.append("- No assignee specified")
            if missing:
                return "Story is missing essential elements:\n" + "\n".join(missing)
            return "Story is missing essential elements required for implementation."

        return "[Insufficient Context: description]"

    def _extract_unclear_areas(self, context: RAGContext) -> str:
        """Extract unclear areas from validator findings."""
        lines = []
        for name, result in context.validation_results.items():
            for finding in result.get("findings", []):
                severity = finding.get("severity", "")
                if severity in ("WARNING", "ERROR"):
                    message = finding.get("message", "")
                    if message:
                        lines.append(f"- {message}")
        return "\n".join(lines[:5]) if lines else ""

    def _extract_steps_to_reproduce(self, context: RAGContext) -> List[str]:
        """Extract steps from story context or use generic steps."""
        story = context.story
        violation_type = getattr(context, "_violation_type", "rule")

        # Generic steps based on story info
        steps = []
        story_key = story.get("key", "UNKNOWN")

        steps.append(f"Open story {story_key} in Jira")
        steps.append("Review the story description and acceptance criteria")
        steps.append("Compare against knowledge base rules and constraints")
        steps.append("Observe the violation in the defined requirements")

        return steps

    def _extract_story_review_steps(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> List[str]:
        """Extract steps for story review defects."""
        story = context.story
        story_key = story.get("key", "UNKNOWN")
        issue_type = options.issue_type

        steps = [f"Open story {story_key} in Jira"]

        if issue_type == "missing_ac":
            steps.append("Navigate to acceptance criteria section")
            steps.append("Observe that no acceptance criteria are defined")
        elif issue_type == "unclear_requirement":
            steps.append("Read the story description carefully")
            steps.append("Identify ambiguous or unclear statements")
        elif issue_type == "incomplete_story":
            steps.append("Review all story fields")
            steps.append("Identify missing required information")

        return steps

    def _extract_expected_results(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> str:
        """Build expected results from knowledge base rules."""
        violation_type = options.violation_type
        chunks = context.retrieved_chunks

        # Find relevant rules from knowledge base
        relevant_rules = []
        for chunk in chunks[:3]:
            rule_type = chunk.chunk.metadata.get("rule_type", "")
            if violation_type in rule_type.lower() or rule_type == "atomic_rule":
                content = chunk.chunk.content[:200]
                relevant_rules.append(content)

        if relevant_rules:
            return "According to knowledge base:\n" + "\n".join(
                f"- {rule[:150]}..." if len(rule) > 150 else f"- {rule}"
                for rule in relevant_rules[:2]
            )

        # Default expected results by violation type
        defaults = {
            "rule": "Story should comply with all applicable business rules.",
            "state": "Story should define valid state transitions only.",
            "financial": "Financial calculations should be accurate and auditable.",
            "cross_dep": "Cross-module dependencies should be clearly defined.",
        }
        return defaults.get(violation_type, "[Insufficient Context: expected_results]")

    def _extract_story_expected_results(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> str:
        """Build expected results for story defects."""
        issue_type = options.issue_type

        expectations = {
            "missing_ac": (
                "Story should have clear, testable acceptance criteria that define:\n"
                "- Success conditions\n"
                "- Edge cases to handle\n"
                "- Error scenarios"
            ),
            "unclear_requirement": (
                "Requirements should be clear, specific, and measurable with no ambiguity."
            ),
            "incomplete_story": (
                "Story should include:\n"
                "- Detailed description\n"
                "- Acceptance criteria\n"
                "- Assigned owner"
            ),
        }
        return expectations.get(issue_type, "[Insufficient Context: expected_results]")

    def _extract_actual_results(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> str:
        """Build actual results from validator findings."""
        violation_type = options.violation_type
        validator_name = self.VALIDATOR_NAMES.get(violation_type, "")
        result = context.validation_results.get(validator_name, {})

        if not result:
            return f"Potential {violation_type} issue detected during analysis."

        findings = result.get("findings", [])
        if findings:
            lines = []
            for finding in findings[:3]:
                severity = finding.get("severity", "INFO")
                message = finding.get("message", "")
                rule_id = finding.get("rule_id", "")
                if message:
                    line = f"[{severity}] {message}"
                    if rule_id:
                        line += f" (Rule: {rule_id})"
                    lines.append(line)
            if lines:
                return "\n".join(lines)

        return result.get("summary", f"Validation failed for {violation_type}.")

    def _extract_story_actual_results(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> str:
        """Build actual results for story defects."""
        issue_type = options.issue_type
        story = context.story

        if issue_type == "missing_ac":
            ac = story.get("acceptance_criteria")
            if not ac:
                return "No acceptance criteria defined in the story."
            return "Acceptance criteria field is empty or insufficient."

        elif issue_type == "unclear_requirement":
            return "Story contains ambiguous language that can be interpreted multiple ways."

        elif issue_type == "incomplete_story":
            missing = []
            desc = story.get("description", "")
            if not desc or len(desc) < 50:
                missing.append("Description is too brief")
            if not story.get("acceptance_criteria"):
                missing.append("No acceptance criteria")
            if not story.get("assignee") or story.get("assignee") == "Unassigned":
                missing.append("No assignee")
            if missing:
                return "Missing: " + ", ".join(missing)
            return "Story is incomplete."

        return "[Insufficient Context: actual_results]"

    def _extract_rule_ids(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> List[str]:
        """Extract rule IDs from validator findings."""
        violation_type = options.violation_type
        validator_name = self.VALIDATOR_NAMES.get(violation_type, "")
        result = context.validation_results.get(validator_name, {})

        rule_ids = []

        # Extract from findings
        for finding in result.get("findings", []):
            rule_id = finding.get("rule_id")
            if rule_id and rule_id not in rule_ids:
                rule_ids.append(rule_id)

        # Extract from knowledge chunks if no rule IDs found
        if not rule_ids:
            for chunk in context.retrieved_chunks[:3]:
                chunk_id = chunk.chunk.id
                if chunk_id and chunk_id not in rule_ids:
                    rule_ids.append(chunk_id)

        return rule_ids[:5]  # Limit to 5 rule IDs

    def _extract_story_rule_ids(self, context: RAGContext) -> List[str]:
        """
        Extract relevant rule IDs from all validators for story defects.

        Collects rule IDs from:
        - StateValidator (SM:* prefix for state machine violations)
        - FinancialValidator (FIN-* prefix for financial rules)
        - RuleEngine (business rules)
        - Knowledge chunks as fallback

        Returns:
            List of rule IDs (max 5)
        """
        rule_ids = []

        # Extract from all validation results
        for validator_name, result in context.validation_results.items():
            for finding in result.get("findings", []):
                rule_id = finding.get("rule_id")
                if rule_id and rule_id not in rule_ids:
                    rule_ids.append(rule_id)

        # Extract from retrieved chunks if no rule IDs found
        if not rule_ids:
            for chunk in context.retrieved_chunks[:5]:
                chunk_id = chunk.chunk.id
                if chunk_id and chunk_id not in rule_ids:
                    rule_ids.append(chunk_id)

        return rule_ids[:5]  # Limit to 5 rule IDs

    def _resolve_component(self, context: RAGContext) -> str:
        """Resolve component from detected domains."""
        pre_analysis = context.pre_analysis

        if pre_analysis.detected_domains:
            # Use first detected domain
            domain = pre_analysis.detected_domains[0].lower()
            return COMPONENT_MAP.get(domain, "WebApp")

        return "WebApp"

    def _resolve_risk_level(
        self, context: RAGContext, options: DefectBuildOptions
    ) -> str:
        """Resolve risk level from pre-analysis or violation type."""
        pre_analysis = context.pre_analysis

        # Use pre-analysis risk level if available
        if pre_analysis.risk_level:
            return pre_analysis.risk_level.upper()

        # Fall back to default based on violation type
        if options.defect_type == "violation":
            return self.DEFAULT_RISK_LEVELS.get(options.violation_type, "MEDIUM")

        return "MEDIUM"
