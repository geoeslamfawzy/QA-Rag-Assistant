"""
Deterministic Generator for Deterministic QA Brain

Generates deterministic output based on rule coverage.
Builds reasoning chains and blocks generation when critical rules are missing.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set

from models.rule import Rule, RiskLevel
from models.required_rule_set import RequiredRuleSet, CategorizedRule
from models.reasoning_chain import (
    ReasoningChain,
    ReasoningContext,
    ReasoningStepType,
)
from models.evidence import EvidenceResult
from validators.coverage_validator import CoverageResult, CoverageStatus
from core.rule_graph import RuleDependencyGraph

logger = logging.getLogger(__name__)


@dataclass
class DeterministicOutput:
    """
    Output from deterministic generator.

    Contains reasoning chains, test implications, and generation metadata.
    """

    # Core output
    reasoning_context: ReasoningContext
    test_implications: List[Dict[str, Any]]

    # Coverage context
    required_rules: RequiredRuleSet
    coverage_result: CoverageResult

    # Generation metadata
    can_generate: bool
    generation_blocked_reason: Optional[str] = None
    confidence_score: float = 1.0

    # Impacted modules for cross-module testing
    impacted_modules: List[str] = field(default_factory=list)

    def to_prompt_section(self) -> str:
        """
        Format as prompt section for Claude.

        Returns formatted markdown for inclusion in QA prompts.
        """
        lines = []

        # Header
        lines.append("## DETERMINISTIC REASONING CONTEXT")
        lines.append("")

        # Generation status
        if self.can_generate:
            lines.append(f"**Status:** GENERATION ALLOWED (Confidence: {self.confidence_score:.0%})")
        else:
            lines.append(f"**Status:** GENERATION BLOCKED")
            lines.append(f"**Reason:** {self.generation_blocked_reason}")
            lines.append("")
            lines.append("The following analysis is incomplete due to missing critical rules.")

        lines.append("")

        # Coverage summary
        lines.append("### Coverage Summary")
        lines.append(f"- Required Rules: {len(self.coverage_result.required_rules)}")
        lines.append(f"- Retrieved Rules: {len(self.coverage_result.retrieved_rules)}")
        lines.append(f"- Coverage: {self.coverage_result.coverage_percentage:.0%}")
        lines.append(f"- Critical Coverage: {self.coverage_result.critical_coverage:.0%}")

        if self.coverage_result.missing_critical:
            lines.append("")
            lines.append("**MISSING CRITICAL RULES:**")
            for rule_id in self.coverage_result.missing_critical:
                lines.append(f"- `{rule_id}` (REQUIRED)")

        lines.append("")

        # Reasoning chains
        if self.reasoning_context.chains:
            lines.append(self.reasoning_context.to_markdown())
        else:
            lines.append("*No reasoning chains generated - insufficient rule coverage*")

        lines.append("")

        # Test implications
        if self.test_implications:
            lines.append("### Test Implications")
            for impl in self.test_implications[:10]:
                test_type = impl.get('type', 'unknown')
                description = impl.get('description', '')
                rule_id = impl.get('rule_id', '')
                lines.append(f"- **[{test_type.upper()}]** {description}")
                if rule_id:
                    lines.append(f"  - Based on: `{rule_id}`")

        # Impacted modules
        if self.impacted_modules:
            lines.append("")
            lines.append("### Cross-Module Impact")
            lines.append(f"The following modules are affected and should be tested:")
            for module in self.impacted_modules:
                lines.append(f"- {module}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Export for serialization."""
        return {
            "can_generate": self.can_generate,
            "generation_blocked_reason": self.generation_blocked_reason,
            "confidence_score": self.confidence_score,
            "impacted_modules": self.impacted_modules,
            "reasoning_chains": self.reasoning_context.to_dict(),
            "test_implications": self.test_implications,
            "coverage": self.coverage_result.to_dict(),
            "required_rules": self.required_rules.to_dict(),
        }


class DeterministicGenerator:
    """
    Generates deterministic output based on rule coverage.

    Key behaviors:
    1. References rule semantics (description, not just ID)
    2. Builds reasoning chains: Rule -> State -> Impact -> Expected
    3. Includes dependency effects in reasoning
    4. Lists impacted modules for cross-testing
    5. Blocks generation when critical rules missing (strict mode)

    Example:
        generator = DeterministicGenerator(rule_graph, strict_mode=True)
        output = generator.generate(
            story=story,
            required_rules=required_rules,
            coverage_result=coverage_result,
            knowledge_context=knowledge_context
        )

        if output.can_generate:
            # Use reasoning chains for test generation
            print(output.to_prompt_section())
        else:
            # Handle blocked generation
            print(f"Blocked: {output.generation_blocked_reason}")
    """

    def __init__(
        self,
        rule_graph: RuleDependencyGraph,
        strict_mode: bool = True
    ):
        """
        Initialize the deterministic generator.

        Args:
            rule_graph: The rule dependency graph
            strict_mode: If True, blocks generation when critical rules missing
        """
        self.graph = rule_graph
        self.strict_mode = strict_mode

    def generate(
        self,
        story: Dict[str, Any],
        required_rules: RequiredRuleSet,
        coverage_result: CoverageResult,
        knowledge_context: List[Dict[str, Any]]
    ) -> DeterministicOutput:
        """
        Generate deterministic output based on coverage.

        If strict_mode and critical rules missing, returns blocked output.

        Args:
            story: Story dictionary
            required_rules: The required rule set
            coverage_result: Coverage validation result
            knowledge_context: Retrieved knowledge chunks

        Returns:
            DeterministicOutput with reasoning chains or blocked status
        """
        # Check if generation should be blocked
        if self.strict_mode and coverage_result.missing_critical:
            return self._create_blocked_output(
                required_rules,
                coverage_result,
                f"Missing critical rules: {', '.join(coverage_result.missing_critical)}"
            )

        # Build reasoning chains
        reasoning_context = self._build_reasoning_context(
            story,
            required_rules,
            coverage_result
        )

        # Extract test implications
        test_implications = self._extract_test_implications(
            reasoning_context,
            required_rules
        )

        # Collect impacted modules
        impacted_modules = self._collect_impacted_modules(required_rules)

        # Calculate confidence score
        confidence = self._calculate_confidence(
            coverage_result,
            reasoning_context
        )

        return DeterministicOutput(
            reasoning_context=reasoning_context,
            test_implications=test_implications,
            required_rules=required_rules,
            coverage_result=coverage_result,
            can_generate=True,
            generation_blocked_reason=None,
            confidence_score=confidence,
            impacted_modules=impacted_modules,
        )

    def _create_blocked_output(
        self,
        required_rules: RequiredRuleSet,
        coverage_result: CoverageResult,
        reason: str
    ) -> DeterministicOutput:
        """Create a blocked output when generation is not allowed."""
        return DeterministicOutput(
            reasoning_context=ReasoningContext(),
            test_implications=[],
            required_rules=required_rules,
            coverage_result=coverage_result,
            can_generate=False,
            generation_blocked_reason=reason,
            confidence_score=0.0,
            impacted_modules=[],
        )

    def _build_reasoning_context(
        self,
        story: Dict[str, Any],
        required_rules: RequiredRuleSet,
        coverage_result: CoverageResult
    ) -> ReasoningContext:
        """
        Build reasoning chains for all matched rules.

        Creates a reasoning chain for each rule that includes:
        - Rule match evidence
        - State transitions if applicable
        - Impact chain
        - Expected behaviors
        """
        context = ReasoningContext(
            story_key=story.get('key', ''),
        )

        story_text = self._get_story_text(story)

        # Build chain for each rule in the required set
        # Prioritize by risk level
        for cat_rule in sorted(
            required_rules.all_rules,
            key=lambda cr: cr.rule.risk_level,
            reverse=True
        ):
            rule = cat_rule.rule

            # Only build chains for rules we have coverage for
            if rule.rule_id not in coverage_result.retrieved_rules:
                continue

            chain = self._build_chain_for_rule(
                rule,
                story_text,
                cat_rule.reason
            )

            if chain.links:  # Only add if chain has content
                context.add_chain(chain)

        return context

    def _build_chain_for_rule(
        self,
        rule: Rule,
        story_text: str,
        match_reason: str
    ) -> ReasoningChain:
        """
        Build complete reasoning chain for a rule.

        INTEGRITY FIX: Evidence is now verified through EvidenceResult.
        Unverified evidence is marked explicitly - NO fabrication allowed.

        Steps:
        1. Rule match with VERIFIED evidence from story
        2. State transitions if rule has lifecycle_states
        3. Impact chain from rule.impacts
        4. Expected behaviors from rule.validation
        """
        chain = ReasoningChain(
            primary_rule_id=rule.rule_id,
            primary_rule=rule,
            story_snippet=self._extract_relevant_snippet(story_text, rule),
        )

        # Step 1: Find evidence (may be unverified)
        evidence_result = self._find_evidence(story_text, rule)

        # Handle unverified evidence explicitly - NO fabrication
        if not evidence_result.is_verified:
            logger.warning(
                f"Unverified evidence for rule {rule.rule_id}: "
                f"{evidence_result.unverified_reason}"
            )
            # Use honest description instead of fabrication
            chain.add_rule_match(
                rule=rule,
                evidence=evidence_result.get_evidence_text(),  # "[UNVERIFIED - ...]"
                description=f"{rule.rule_id}: {rule.description} (evidence not verified)"
            )
            # Mark chain as having unverified evidence
            chain.confidence = 0.5  # Reduce confidence for unverified
        else:
            # Verified evidence - use the actual snippet
            chain.add_rule_match(
                rule=rule,
                evidence=evidence_result.matched_snippet,
                description=f"{rule.rule_id}: {rule.description}"
            )

        # Step 2: State transitions (if applicable)
        if rule.lifecycle_states:
            for state in rule.lifecycle_states:
                chain.add_state_transition(
                    from_state="*",
                    to_state=state,
                    trigger=f"When {rule.condition or 'rule condition met'}",
                    rule=rule,
                    evidence=rule.condition
                )

        # Step 3: Dependencies (if any)
        if rule.depends_on:
            for dep_id in rule.depends_on[:3]:  # Limit to top 3
                dep_rule = self.graph.get_rule(dep_id)
                if dep_rule:
                    chain.add_dependency(
                        dependent_rule=dep_rule,
                        parent_rule_id=rule.rule_id,
                        evidence=f"{dep_rule.rule_id}: {dep_rule.description}"
                    )

        # Step 4: Impacts
        for impact in rule.impacts[:5]:  # Limit to top 5
            chain.add_impact(
                impacted_module=impact,
                impact_description=f"Rule {rule.rule_id} affects {impact} module",
                source_rule=rule
            )

        # Step 5: Expected behavior
        if rule.validation:
            chain.add_expected_behavior(
                expected=rule.validation,
                based_on_rule=rule,
                evidence=rule.validation
            )

        # Step 6: Test implication
        test_type = self._determine_test_type(rule)
        chain.add_test_implication(
            test_description=f"Verify: {rule.validation or rule.description}",
            test_type=test_type,
            based_on_rule=rule
        )

        return chain

    def _find_evidence(self, story_text: str, rule: Rule) -> EvidenceResult:
        """
        Find and VERIFY evidence from story text that matches rule keywords.

        INTEGRITY FIX: This method NEVER fabricates evidence. If no keywords
        match, it returns an unverified EvidenceResult instead of a fake claim.

        Args:
            story_text: The story text to search
            rule: The rule to find evidence for

        Returns:
            EvidenceResult with is_verified=True if keywords match,
            is_verified=False otherwise (NEVER fabricated)
        """
        story_lower = story_text.lower()
        matched_keywords = []
        best_snippet = None

        # Search for all matching keywords (up to 10)
        for keyword in rule.keywords[:10]:
            kw_lower = keyword.lower()
            pos = story_lower.find(kw_lower)
            if pos != -1:
                matched_keywords.append(keyword)
                # Capture the first match as the best snippet
                if best_snippet is None:
                    start = max(0, pos - 50)
                    end = min(len(story_text), pos + len(keyword) + 100)
                    snippet = story_text[start:end].strip()
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(story_text):
                        snippet = snippet + "..."
                    best_snippet = snippet

        # CRITICAL: Only return verified evidence if keywords matched
        if matched_keywords:
            keyword_coverage = len(matched_keywords) / max(1, len(rule.keywords[:10]))
            return EvidenceResult.verified(
                keywords=matched_keywords,
                snippet=best_snippet,
                score=keyword_coverage
            )

        # NO FABRICATION - return explicitly unverified result
        logger.debug(f"No keyword match for rule {rule.rule_id} in story text")
        return EvidenceResult.unverified(
            reason=f"No keyword overlap for rule {rule.rule_id}"
        )

    def _extract_relevant_snippet(self, story_text: str, rule: Rule) -> str:
        """Extract the most relevant snippet from story for this rule."""
        evidence_result = self._find_evidence(story_text, rule)
        if evidence_result.is_verified and evidence_result.matched_snippet:
            return evidence_result.matched_snippet[:200]
        return ""  # Don't return fabricated snippets

    def _determine_test_type(self, rule: Rule) -> str:
        """Determine the test type based on rule characteristics."""
        rule_content = (rule.description + " " + rule.validation).lower()

        if any(w in rule_content for w in ['error', 'invalid', 'fail', 'reject', 'block']):
            return "negative"
        if any(w in rule_content for w in ['edge', 'boundary', 'limit', 'maximum', 'minimum']):
            return "edge"
        if any(w in rule_content for w in ['security', 'auth', 'permission', 'access']):
            return "security"

        return "positive"

    def _extract_test_implications(
        self,
        reasoning_context: ReasoningContext,
        required_rules: RequiredRuleSet
    ) -> List[Dict[str, Any]]:
        """Extract test case implications from reasoning chains."""
        implications: List[Dict[str, Any]] = []

        for chain in reasoning_context.chains:
            for link in chain.links:
                if link.step_type == ReasoningStepType.TEST_IMPLICATION:
                    implications.append({
                        "type": chain.test_type or "positive",
                        "description": link.description,
                        "rule_id": chain.primary_rule_id,
                        "affected_modules": chain.affected_modules,
                    })

            # Add implications from expected behaviors
            for link in chain.links:
                if link.step_type == ReasoningStepType.EXPECTED_BEHAVIOR:
                    implications.append({
                        "type": chain.test_type or "positive",
                        "description": f"Verify: {link.description}",
                        "rule_id": link.rule.rule_id if link.rule else "",
                        "affected_modules": chain.affected_modules,
                    })

        # Deduplicate
        seen: Set[str] = set()
        unique_implications: List[Dict[str, Any]] = []
        for impl in implications:
            key = f"{impl['type']}:{impl['description']}"
            if key not in seen:
                unique_implications.append(impl)
                seen.add(key)

        return unique_implications

    def _collect_impacted_modules(
        self,
        required_rules: RequiredRuleSet
    ) -> List[str]:
        """Collect all modules impacted by the rule set."""
        modules: Set[str] = set()

        for cat_rule in required_rules.all_rules:
            rule = cat_rule.rule
            modules.update(rule.impacts)
            if rule.module:
                modules.add(rule.module)
            if rule.domain:
                modules.add(rule.domain)

        return sorted(list(modules))

    def _calculate_confidence(
        self,
        coverage_result: CoverageResult,
        reasoning_context: ReasoningContext
    ) -> float:
        """
        Calculate confidence score based on:
        - Coverage percentage
        - Number of reasoning chains with full evidence
        - Critical rule coverage
        - INTEGRITY FIX: Penalize unverified evidence

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base score from coverage
        base_score = coverage_result.coverage_percentage

        # Adjust for critical coverage
        critical_factor = coverage_result.critical_coverage

        # Adjust for reasoning depth
        chains_with_evidence = sum(
            1 for chain in reasoning_context.chains
            if len(chain.links) >= 3  # At least 3 links
        )
        reasoning_factor = (
            chains_with_evidence / len(reasoning_context.chains)
            if reasoning_context.chains else 0.5
        )

        # Weighted combination
        confidence = (
            base_score * 0.4 +
            critical_factor * 0.4 +
            reasoning_factor * 0.2
        )

        # INTEGRITY FIX: Penalize unverified evidence
        # Detect chains with unverified evidence marker
        unverified_count = sum(
            1 for chain in reasoning_context.chains
            if chain.links and "[UNVERIFIED" in str(
                chain.links[0].evidence if hasattr(chain.links[0], 'evidence') else ""
            )
        )

        if unverified_count > 0:
            # Reduce confidence proportionally to unverified evidence
            total_chains = max(1, len(reasoning_context.chains))
            unverified_ratio = unverified_count / total_chains
            unverified_penalty = min(0.4, unverified_ratio * 0.5)  # Max 40% penalty
            confidence -= unverified_penalty
            logger.debug(
                f"Confidence reduced by {unverified_penalty:.0%} due to "
                f"{unverified_count} chains with unverified evidence"
            )

        return min(1.0, max(0.0, confidence))

    def _get_story_text(self, story: Dict[str, Any]) -> str:
        """Get combined story text for analysis."""
        parts = []

        if story.get('title'):
            parts.append(story['title'])
        if story.get('summary'):
            parts.append(story['summary'])
        if story.get('description'):
            parts.append(story['description'])
        if story.get('acceptance_criteria'):
            if isinstance(story['acceptance_criteria'], list):
                parts.extend(story['acceptance_criteria'])
            else:
                parts.append(str(story['acceptance_criteria']))

        return " ".join(parts)
