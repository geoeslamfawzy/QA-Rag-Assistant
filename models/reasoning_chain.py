"""
Reasoning Chain Model for Deterministic QA Brain

Provides traceable reasoning chains that connect:
Rule -> State -> Impact -> Expected Behavior

Used for deterministic output generation with full justification.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from .rule import Rule


class ReasoningStepType(Enum):
    """Type of step in a reasoning chain."""
    RULE_MATCH = "rule_match"           # Rule matched to story content
    STATE_TRANSITION = "state"          # State change detected
    IMPACT_CHAIN = "impact"             # Impact on other modules
    EXPECTED_BEHAVIOR = "expected"      # Expected system behavior
    TEST_IMPLICATION = "test"           # Implied test case
    DEPENDENCY = "dependency"           # Dependent rule triggered
    VALIDATION = "validation"           # Validation requirement


@dataclass
class ReasoningLink:
    """
    A single link in the reasoning chain.

    Represents one step of deterministic reasoning with evidence.
    """
    step_type: ReasoningStepType
    description: str
    evidence: str                       # Quote from story/rule supporting this
    rule: Optional[Rule] = None         # Associated rule if applicable
    implications: List[str] = field(default_factory=list)

    # For state transitions
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    trigger: Optional[str] = None

    # For impacts
    impacted_module: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "step_type": self.step_type.value,
            "description": self.description,
            "evidence": self.evidence,
            "implications": self.implications,
        }
        if self.rule:
            result["rule_id"] = self.rule.rule_id
        if self.from_state:
            result["from_state"] = self.from_state
        if self.to_state:
            result["to_state"] = self.to_state
        if self.trigger:
            result["trigger"] = self.trigger
        if self.impacted_module:
            result["impacted_module"] = self.impacted_module
        return result

    def to_markdown(self) -> str:
        """Format link as markdown."""
        parts = []

        # Step type indicator
        type_labels = {
            ReasoningStepType.RULE_MATCH: "Rule Match",
            ReasoningStepType.STATE_TRANSITION: "State Transition",
            ReasoningStepType.IMPACT_CHAIN: "Impact",
            ReasoningStepType.EXPECTED_BEHAVIOR: "Expected Behavior",
            ReasoningStepType.TEST_IMPLICATION: "Test Implication",
            ReasoningStepType.DEPENDENCY: "Dependency",
            ReasoningStepType.VALIDATION: "Validation",
        }
        label = type_labels.get(self.step_type, self.step_type.value)
        parts.append(f"**{label}**")

        # Main description
        if self.rule:
            parts.append(f"  - Rule: `{self.rule.rule_id}`")
        parts.append(f"  - {self.description}")

        # State transition details
        if self.step_type == ReasoningStepType.STATE_TRANSITION:
            if self.from_state and self.to_state:
                parts.append(f"  - Transition: {self.from_state} -> {self.to_state}")
            if self.trigger:
                parts.append(f"  - Trigger: {self.trigger}")

        # Impact details
        if self.impacted_module:
            parts.append(f"  - Impacted Module: {self.impacted_module}")

        # Evidence
        if self.evidence:
            parts.append(f"  - Evidence: \"{self.evidence}\"")

        # Implications
        if self.implications:
            parts.append("  - Implications:")
            for impl in self.implications:
                parts.append(f"    - {impl}")

        return "\n".join(parts)


@dataclass
class ReasoningChain:
    """
    Complete reasoning chain for a test case or finding.

    Provides traceable justification from:
    Rule -> State -> Impact -> Expected Behavior

    This is the core structure for deterministic output generation.
    """

    links: List[ReasoningLink] = field(default_factory=list)

    # Summary metadata
    primary_rule_id: str = ""
    primary_rule: Optional[Rule] = None
    affected_modules: List[str] = field(default_factory=list)
    test_type: str = ""                 # positive, negative, edge, security
    confidence: float = 1.0             # 0-1, based on evidence quality

    # Chain context
    story_key: str = ""
    story_snippet: str = ""             # Relevant story excerpt

    def add_rule_match(
        self,
        rule: Rule,
        evidence: str,
        description: Optional[str] = None
    ) -> "ReasoningChain":
        """
        Add rule match step.

        Args:
            rule: The matched rule
            evidence: Quote from story that triggered the match
            description: Optional custom description

        Returns:
            self for chaining
        """
        desc = description or f"Story content triggers rule {rule.rule_id}"
        self.links.append(ReasoningLink(
            step_type=ReasoningStepType.RULE_MATCH,
            description=desc,
            evidence=evidence,
            rule=rule,
            implications=[f"Must verify: {rule.validation}"] if rule.validation else []
        ))

        # Update primary rule if not set
        if not self.primary_rule_id:
            self.primary_rule_id = rule.rule_id
            self.primary_rule = rule

        return self

    def add_state_transition(
        self,
        from_state: str,
        to_state: str,
        trigger: str,
        rule: Optional[Rule] = None,
        evidence: str = ""
    ) -> "ReasoningChain":
        """
        Add state transition step.

        Args:
            from_state: Starting state
            to_state: Ending state
            trigger: What causes the transition
            rule: Optional associated rule
            evidence: Supporting evidence

        Returns:
            self for chaining
        """
        desc = f"State transition from {from_state} to {to_state}"
        implications = [
            f"System must validate transition is allowed",
            f"Pre-conditions for {to_state} must be checked",
        ]

        self.links.append(ReasoningLink(
            step_type=ReasoningStepType.STATE_TRANSITION,
            description=desc,
            evidence=evidence,
            rule=rule,
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            implications=implications
        ))

        return self

    def add_impact(
        self,
        impacted_module: str,
        impact_description: str,
        source_rule: Optional[Rule] = None,
        evidence: str = ""
    ) -> "ReasoningChain":
        """
        Add impact chain step.

        Args:
            impacted_module: The module affected
            impact_description: What happens to the module
            source_rule: Rule that causes the impact
            evidence: Supporting evidence

        Returns:
            self for chaining
        """
        self.links.append(ReasoningLink(
            step_type=ReasoningStepType.IMPACT_CHAIN,
            description=impact_description,
            evidence=evidence,
            rule=source_rule,
            impacted_module=impacted_module,
            implications=[f"Test {impacted_module} module for side effects"]
        ))

        # Track affected modules
        if impacted_module not in self.affected_modules:
            self.affected_modules.append(impacted_module)

        return self

    def add_expected_behavior(
        self,
        expected: str,
        based_on_rule: Optional[Rule] = None,
        evidence: str = ""
    ) -> "ReasoningChain":
        """
        Add expected behavior step.

        Args:
            expected: The expected system behavior
            based_on_rule: Rule this expectation is based on
            evidence: Supporting evidence

        Returns:
            self for chaining
        """
        implications = ["Create test case to verify this behavior"]
        if based_on_rule and based_on_rule.error_message:
            implications.append(f"Verify error message: \"{based_on_rule.error_message}\"")

        self.links.append(ReasoningLink(
            step_type=ReasoningStepType.EXPECTED_BEHAVIOR,
            description=expected,
            evidence=evidence,
            rule=based_on_rule,
            implications=implications
        ))

        return self

    def add_dependency(
        self,
        dependent_rule: Rule,
        parent_rule_id: str,
        evidence: str = ""
    ) -> "ReasoningChain":
        """
        Add dependency step.

        Args:
            dependent_rule: The dependent rule that must also be considered
            parent_rule_id: The rule that triggers this dependency
            evidence: Supporting evidence

        Returns:
            self for chaining
        """
        desc = f"Rule {dependent_rule.rule_id} is required by {parent_rule_id}"
        self.links.append(ReasoningLink(
            step_type=ReasoningStepType.DEPENDENCY,
            description=desc,
            evidence=evidence,
            rule=dependent_rule,
            implications=[
                f"Must also verify: {dependent_rule.validation}" if dependent_rule.validation else
                f"Must also verify rule {dependent_rule.rule_id}"
            ]
        ))

        return self

    def add_test_implication(
        self,
        test_description: str,
        test_type: str,
        based_on_rule: Optional[Rule] = None
    ) -> "ReasoningChain":
        """
        Add test implication step.

        Args:
            test_description: Description of implied test
            test_type: Type of test (positive, negative, edge, security)
            based_on_rule: Rule this test is based on

        Returns:
            self for chaining
        """
        self.links.append(ReasoningLink(
            step_type=ReasoningStepType.TEST_IMPLICATION,
            description=test_description,
            evidence="",
            rule=based_on_rule,
            implications=[]
        ))

        # Update chain test type if not set
        if not self.test_type:
            self.test_type = test_type

        return self

    def get_all_rule_ids(self) -> List[str]:
        """Get all rule IDs referenced in this chain."""
        rule_ids = []
        for link in self.links:
            if link.rule and link.rule.rule_id not in rule_ids:
                rule_ids.append(link.rule.rule_id)
        return rule_ids

    def get_all_implications(self) -> List[str]:
        """Get all implications from all links."""
        implications = []
        for link in self.links:
            implications.extend(link.implications)
        return implications

    def to_markdown(self) -> str:
        """Format chain as readable markdown."""
        lines = []

        # Header
        if self.primary_rule_id:
            lines.append(f"### Reasoning Chain: {self.primary_rule_id}")
        else:
            lines.append("### Reasoning Chain")

        if self.test_type:
            lines.append(f"*Test Type: {self.test_type}*")

        if self.affected_modules:
            lines.append(f"*Affected Modules: {', '.join(self.affected_modules)}*")

        lines.append("")

        # Story context
        if self.story_snippet:
            lines.append("**Story Context:**")
            lines.append(f"> {self.story_snippet}")
            lines.append("")

        # Chain links
        lines.append("**Reasoning Steps:**")
        lines.append("")

        for i, link in enumerate(self.links, 1):
            lines.append(f"{i}. {link.to_markdown()}")
            lines.append("")

        # Summary implications
        all_implications = self.get_all_implications()
        if all_implications:
            lines.append("**Summary - Test Implications:**")
            for impl in all_implications[:5]:  # Top 5
                lines.append(f"- {impl}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Export for serialization."""
        return {
            "primary_rule_id": self.primary_rule_id,
            "affected_modules": self.affected_modules,
            "test_type": self.test_type,
            "confidence": self.confidence,
            "story_key": self.story_key,
            "story_snippet": self.story_snippet,
            "links": [link.to_dict() for link in self.links],
            "all_rule_ids": self.get_all_rule_ids(),
            "all_implications": self.get_all_implications(),
        }

    def __repr__(self) -> str:
        return (
            f"ReasoningChain(rule={self.primary_rule_id}, "
            f"steps={len(self.links)}, modules={self.affected_modules})"
        )


@dataclass
class ReasoningContext:
    """
    Collection of reasoning chains for a complete analysis.

    Used by DeterministicGenerator to produce full output.
    """
    chains: List[ReasoningChain] = field(default_factory=list)
    story_key: str = ""
    total_rules_referenced: int = 0
    total_modules_impacted: int = 0

    def add_chain(self, chain: ReasoningChain) -> None:
        """Add a reasoning chain."""
        self.chains.append(chain)
        self._update_totals()

    def _update_totals(self) -> None:
        """Update totals from chains."""
        all_rules: set = set()
        all_modules: set = set()

        for chain in self.chains:
            all_rules.update(chain.get_all_rule_ids())
            all_modules.update(chain.affected_modules)

        self.total_rules_referenced = len(all_rules)
        self.total_modules_impacted = len(all_modules)

    def get_all_rule_ids(self) -> List[str]:
        """Get all unique rule IDs across all chains."""
        rule_ids: set = set()
        for chain in self.chains:
            rule_ids.update(chain.get_all_rule_ids())
        return list(rule_ids)

    def get_all_affected_modules(self) -> List[str]:
        """Get all unique affected modules."""
        modules: set = set()
        for chain in self.chains:
            modules.update(chain.affected_modules)
        return list(modules)

    def to_markdown(self) -> str:
        """Format all chains as markdown."""
        lines = [
            f"## Deterministic Reasoning Output",
            f"**Story:** {self.story_key}",
            f"**Rules Referenced:** {self.total_rules_referenced}",
            f"**Modules Impacted:** {self.total_modules_impacted}",
            "",
            "---",
            "",
        ]

        for chain in self.chains:
            lines.append(chain.to_markdown())
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Export for serialization."""
        return {
            "story_key": self.story_key,
            "total_rules_referenced": self.total_rules_referenced,
            "total_modules_impacted": self.total_modules_impacted,
            "chains": [chain.to_dict() for chain in self.chains],
            "all_rule_ids": self.get_all_rule_ids(),
            "all_affected_modules": self.get_all_affected_modules(),
        }
