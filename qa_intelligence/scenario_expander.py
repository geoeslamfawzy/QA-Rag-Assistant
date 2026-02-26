"""
Scenario Expander for Deterministic QA Brain v2.0

Generates test scenarios through:
1. Rule-based scenario derivation
2. Risk-level prioritization
3. State transition enumeration
4. Boundary condition generation

All generation is deterministic - no randomness or probabilistic sampling.
"""

from typing import List, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

from models.rule import Rule, RiskLevel

if TYPE_CHECKING:
    from models.required_rule_set import RequiredRuleSet
    from core.rule_graph import RuleDependencyGraph


class ScenarioType(Enum):
    """Types of test scenarios."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    BOUNDARY = "boundary"
    STATE_TRANSITION = "state_transition"
    ROLE_BASED = "role_based"
    INTEGRATION = "integration"
    SECURITY = "security"
    DATA_VALIDATION = "data_validation"


@dataclass
class TestScenario:
    """A generated test scenario."""
    id: str
    title: str
    description: str
    scenario_type: ScenarioType
    risk_level: RiskLevel
    priority: str                        # P0-P3, deterministic from risk_level
    preconditions: List[str] = field(default_factory=list)
    trigger: str = ""
    expected_outcome: str = ""
    linked_rule_ids: List[str] = field(default_factory=list)
    affected_modules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "scenario_type": self.scenario_type.value,
            "risk_level": self.risk_level.value,
            "priority": self.priority,
            "preconditions": self.preconditions,
            "trigger": self.trigger,
            "expected_outcome": self.expected_outcome,
            "linked_rule_ids": self.linked_rule_ids,
            "affected_modules": self.affected_modules,
        }


class ScenarioExpander:
    """
    Deterministic scenario expansion engine.

    Generates scenarios based on:
    1. Rule validation requirements
    2. Error message conditions
    3. State transition triggers
    4. Boundary conditions

    Expansion by risk level:
    - CRITICAL/HIGH: positive, negative, boundary, state, role, integration, security, data
    - MEDIUM: positive, negative, boundary, state
    - LOW: positive, negative only

    NO randomness - every rule produces the same scenarios every time.
    """

    # Deterministic priority mapping
    PRIORITY_MAP = {
        RiskLevel.CRITICAL: "P0",
        RiskLevel.HIGH: "P1",
        RiskLevel.MEDIUM: "P2",
        RiskLevel.LOW: "P3",
    }

    # Boundary keywords for detection
    BOUNDARY_KEYWORDS = ["limit", "maximum", "minimum", "threshold", "cap", "<=", ">=", "<", ">"]

    # Security keywords for detection
    SECURITY_KEYWORDS = ["permission", "access", "admin", "authorize", "role", "privilege"]

    def __init__(self, rule_graph: Optional["RuleDependencyGraph"] = None):
        """
        Initialize the scenario expander.

        Args:
            rule_graph: Optional rule dependency graph
        """
        self.graph = rule_graph
        self._scenario_counter = 0

    def expand(
        self,
        required_rules: "RequiredRuleSet",
        story_key: str
    ) -> List[TestScenario]:
        """
        Expand required rules into test scenarios.

        Generates deterministic scenarios for each rule based on risk level:
        - CRITICAL/HIGH: 8 scenario types
        - MEDIUM: 4 scenario types
        - LOW: 2 scenario types

        Args:
            required_rules: The required rule set
            story_key: Story key for ID generation

        Returns:
            List of TestScenario objects, sorted by priority
        """
        self._scenario_counter = 0
        scenarios: List[TestScenario] = []

        # Process rules in deterministic order (by risk level descending, then rule_id)
        sorted_rules = sorted(
            required_rules.all_rules,
            key=lambda cr: (-self._risk_order(cr.rule.risk_level), cr.rule.rule_id)
        )

        for cat_rule in sorted_rules:
            rule = cat_rule.rule
            rule_scenarios = self._expand_rule(rule, story_key)
            scenarios.extend(rule_scenarios)

        # Sort by priority (P0 first)
        scenarios.sort(key=lambda s: s.priority)

        return scenarios

    def _risk_order(self, risk_level: RiskLevel) -> int:
        """Get numeric order for risk level (higher = more critical)."""
        return {
            RiskLevel.CRITICAL: 4,
            RiskLevel.HIGH: 3,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 1,
        }.get(risk_level, 0)

    def _expand_rule(self, rule: Rule, story_key: str) -> List[TestScenario]:
        """Expand a single rule into scenarios based on risk level."""
        scenarios = []

        # Always generate positive scenario
        scenarios.append(self._create_positive_scenario(rule, story_key))

        # Always generate negative scenario (if rule has error_message)
        if rule.error_message:
            scenarios.append(self._create_negative_scenario(rule, story_key))

        # CRITICAL and HIGH get full expansion
        if rule.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            # Boundary scenarios
            if self._has_boundary_conditions(rule):
                scenarios.extend(self._create_boundary_scenarios(rule, story_key))

            # State transition scenarios
            if rule.lifecycle_states:
                scenarios.append(self._create_state_scenario(rule, story_key))

            # Role-based scenarios
            if self._is_role_based(rule):
                scenarios.append(self._create_role_scenario(rule, story_key))

            # Integration scenarios
            if rule.impacts and len(rule.impacts) >= 2:
                scenarios.append(self._create_integration_scenario(rule, story_key))

            # Security scenarios
            if self._is_security_rule(rule):
                scenarios.append(self._create_security_scenario(rule, story_key))

            # Data validation scenarios
            scenarios.append(self._create_data_validation_scenario(rule, story_key))

        # MEDIUM gets partial expansion
        elif rule.risk_level == RiskLevel.MEDIUM:
            # Boundary scenarios
            if self._has_boundary_conditions(rule):
                scenarios.extend(self._create_boundary_scenarios(rule, story_key))

            # State transition scenarios
            if rule.lifecycle_states:
                scenarios.append(self._create_state_scenario(rule, story_key))

        # LOW gets only positive and negative (already added above)

        return scenarios

    def _next_id(self, story_key: str, prefix: str) -> str:
        """Generate deterministic scenario ID."""
        self._scenario_counter += 1
        return f"TS-{story_key}-{prefix}-{self._scenario_counter:03d}"

    def _create_positive_scenario(self, rule: Rule, story_key: str) -> TestScenario:
        """Create positive (happy path) scenario."""
        return TestScenario(
            id=self._next_id(story_key, "POS"),
            title=f"Verify {rule.rule_id}: {rule.description[:50]}",
            description=f"Positive test for rule {rule.rule_id}",
            scenario_type=ScenarioType.POSITIVE,
            risk_level=rule.risk_level,
            priority=self.PRIORITY_MAP[rule.risk_level],
            preconditions=self._derive_preconditions(rule),
            trigger=rule.condition[:100] if rule.condition else "Execute the action",
            expected_outcome=rule.validation[:100] if rule.validation else "System behaves correctly",
            linked_rule_ids=[rule.rule_id] + rule.depends_on[:3],
            affected_modules=rule.impacts[:5] if rule.impacts else [],
        )

    def _create_negative_scenario(self, rule: Rule, story_key: str) -> TestScenario:
        """Create negative (error handling) scenario."""
        return TestScenario(
            id=self._next_id(story_key, "NEG"),
            title=f"Verify error handling for {rule.rule_id}",
            description=f"Negative test: trigger error for {rule.rule_id}",
            scenario_type=ScenarioType.NEGATIVE,
            risk_level=rule.risk_level,
            priority=self.PRIORITY_MAP[rule.risk_level],
            preconditions=self._derive_negative_preconditions(rule),
            trigger=f"Attempt to violate: {rule.condition[:80] if rule.condition else 'rule condition'}",
            expected_outcome=f"Error: {rule.error_message[:100] if rule.error_message else 'Validation error'}",
            linked_rule_ids=[rule.rule_id],
            affected_modules=rule.impacts[:5] if rule.impacts else [],
        )

    def _create_boundary_scenarios(self, rule: Rule, story_key: str) -> List[TestScenario]:
        """Create boundary test scenarios."""
        scenarios = []
        rule_text = (rule.validation + " " + rule.condition).lower()

        for term in self.BOUNDARY_KEYWORDS:
            if term in rule_text:
                scenarios.append(TestScenario(
                    id=self._next_id(story_key, "BND"),
                    title=f"Boundary: {term} for {rule.rule_id}",
                    description=f"Test at {term} boundary for {rule.rule_id}",
                    scenario_type=ScenarioType.BOUNDARY,
                    risk_level=rule.risk_level,
                    priority=self.PRIORITY_MAP[rule.risk_level],
                    preconditions=[f"Set value at exactly {term}"],
                    trigger=f"Execute with value at {term}",
                    expected_outcome="System handles boundary correctly",
                    linked_rule_ids=[rule.rule_id],
                    affected_modules=rule.impacts[:3] if rule.impacts else [],
                ))
                break  # One boundary scenario per rule

        return scenarios

    def _create_state_scenario(self, rule: Rule, story_key: str) -> TestScenario:
        """Create state transition scenario."""
        states = rule.lifecycle_states[:3] if rule.lifecycle_states else ["ACTIVE"]
        return TestScenario(
            id=self._next_id(story_key, "STA"),
            title=f"State transition: {rule.rule_id}",
            description=f"Test state transitions for {rule.rule_id}",
            scenario_type=ScenarioType.STATE_TRANSITION,
            risk_level=rule.risk_level,
            priority=self.PRIORITY_MAP[rule.risk_level],
            preconditions=[f"Entity in state: {', '.join(states)}"],
            trigger="Trigger state transition",
            expected_outcome="State changes correctly per rule",
            linked_rule_ids=[rule.rule_id],
            affected_modules=["state_machine"] + (rule.impacts[:2] if rule.impacts else []),
        )

    def _create_role_scenario(self, rule: Rule, story_key: str) -> TestScenario:
        """Create role-based access scenario."""
        return TestScenario(
            id=self._next_id(story_key, "ROL"),
            title=f"Role-based: {rule.rule_id}",
            description=f"Test role-based access for {rule.rule_id}",
            scenario_type=ScenarioType.ROLE_BASED,
            risk_level=rule.risk_level,
            priority=self.PRIORITY_MAP[rule.risk_level],
            preconditions=["User with specific role"],
            trigger="Attempt action with different roles",
            expected_outcome="Access granted/denied per role",
            linked_rule_ids=[rule.rule_id],
            affected_modules=["roles", "permissions"],
        )

    def _create_integration_scenario(self, rule: Rule, story_key: str) -> TestScenario:
        """Create integration test scenario."""
        modules = rule.impacts[:3] if rule.impacts else ["module_a", "module_b"]
        return TestScenario(
            id=self._next_id(story_key, "INT"),
            title=f"Integration: {rule.rule_id}",
            description=f"Integration test across {', '.join(modules)}",
            scenario_type=ScenarioType.INTEGRATION,
            risk_level=rule.risk_level,
            priority=self.PRIORITY_MAP[rule.risk_level],
            preconditions=[f"Systems connected: {', '.join(modules)}"],
            trigger="Trigger cross-module action",
            expected_outcome="All modules update correctly",
            linked_rule_ids=[rule.rule_id] + rule.depends_on[:2],
            affected_modules=list(modules),
        )

    def _create_security_scenario(self, rule: Rule, story_key: str) -> TestScenario:
        """Create security test scenario."""
        return TestScenario(
            id=self._next_id(story_key, "SEC"),
            title=f"Security: unauthorized access for {rule.rule_id}",
            description=f"Verify unauthorized user cannot execute {rule.rule_id}",
            scenario_type=ScenarioType.SECURITY,
            risk_level=RiskLevel.CRITICAL,  # Security always critical
            priority="P0",
            preconditions=["User without required permissions"],
            trigger=f"Attempt: {rule.condition[:50] if rule.condition else 'protected action'}",
            expected_outcome="Access denied / Permission error",
            linked_rule_ids=[rule.rule_id],
            affected_modules=["security", "authentication"],
        )

    def _create_data_validation_scenario(self, rule: Rule, story_key: str) -> TestScenario:
        """Create data validation scenario."""
        return TestScenario(
            id=self._next_id(story_key, "DAT"),
            title=f"Data validation: {rule.rule_id}",
            description=f"Test data validation for {rule.rule_id}",
            scenario_type=ScenarioType.DATA_VALIDATION,
            risk_level=rule.risk_level,
            priority=self.PRIORITY_MAP[rule.risk_level],
            preconditions=["Test data prepared"],
            trigger="Submit various data inputs",
            expected_outcome="Valid data accepted, invalid rejected",
            linked_rule_ids=[rule.rule_id],
            affected_modules=rule.impacts[:2] if rule.impacts else [],
        )

    def _derive_preconditions(self, rule: Rule) -> List[str]:
        """Derive preconditions from rule content."""
        preconditions = []

        if rule.lifecycle_states:
            preconditions.append(f"Entity in state: {', '.join(rule.lifecycle_states[:3])}")

        if rule.depends_on:
            preconditions.append(f"Prerequisites satisfied for: {', '.join(rule.depends_on[:3])}")

        return preconditions or ["Standard test environment"]

    def _derive_negative_preconditions(self, rule: Rule) -> List[str]:
        """Derive preconditions for negative test."""
        return [
            "Setup conditions to violate rule",
            f"Prepare invalid data for: {rule.condition[:50] if rule.condition else 'rule condition'}..."
        ]

    def _has_boundary_conditions(self, rule: Rule) -> bool:
        """Check if rule involves boundary conditions."""
        rule_text = (rule.validation + " " + rule.condition + " " + rule.description).lower()
        return any(kw in rule_text for kw in self.BOUNDARY_KEYWORDS)

    def _is_security_rule(self, rule: Rule) -> bool:
        """Check if rule is security-related."""
        rule_text = (rule.description + " " + rule.validation).lower()
        return any(kw in rule_text for kw in self.SECURITY_KEYWORDS)

    def _is_role_based(self, rule: Rule) -> bool:
        """Check if rule involves roles."""
        role_keywords = ["role", "admin", "user", "manager", "permission"]
        rule_text = (rule.description + " " + rule.validation).lower()
        return any(kw in rule_text for kw in role_keywords)
