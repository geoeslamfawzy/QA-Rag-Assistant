"""
Risk-Based Test Designer for Deterministic QA Brain v2.0

Creates structured test cases with:
1. Deterministic priority from rule risk_level
2. Full traceability to rules
3. BDD-formatted steps
4. Test data suggestions

All generation is deterministic - no randomness or probabilistic sampling.
"""

from typing import List, Dict, Any, Optional

from models.test_case import TestCase, PRIORITY_FROM_RISK
from models.rule import RiskLevel
from qa_intelligence.scenario_expander import TestScenario, ScenarioType


class RiskBasedTestDesigner:
    """
    Converts scenarios to structured test cases.

    Deterministic mappings:
    - CRITICAL risk -> P0 priority
    - HIGH risk -> P1 priority
    - MEDIUM risk -> P2 priority
    - LOW risk -> P3 priority

    No randomness in any test case generation.
    """

    PRIORITY_MAP = {
        RiskLevel.CRITICAL: "P0",
        RiskLevel.HIGH: "P1",
        RiskLevel.MEDIUM: "P2",
        RiskLevel.LOW: "P3",
    }

    RISK_LEVEL_MAP = {
        RiskLevel.CRITICAL: "CRITICAL",
        RiskLevel.HIGH: "HIGH",
        RiskLevel.MEDIUM: "MEDIUM",
        RiskLevel.LOW: "LOW",
    }

    TEST_TYPE_MAP = {
        ScenarioType.POSITIVE: "Positive",
        ScenarioType.NEGATIVE: "Negative",
        ScenarioType.BOUNDARY: "Edge",
        ScenarioType.STATE_TRANSITION: "State",
        ScenarioType.ROLE_BASED: "Role",
        ScenarioType.INTEGRATION: "Integration",
        ScenarioType.SECURITY: "Security",
        ScenarioType.DATA_VALIDATION: "Data",
    }

    def __init__(self):
        """Initialize the test designer."""
        self._tc_counter = 0

    def design_test_cases(
        self,
        scenarios: List[TestScenario],
        story_key: str
    ) -> List[TestCase]:
        """
        Convert scenarios to test cases with full structure.

        Args:
            scenarios: Test scenarios from ScenarioExpander
            story_key: Story key for ID generation

        Returns:
            List of TestCase objects with BDD steps
        """
        self._tc_counter = 0
        test_cases: List[TestCase] = []

        for scenario in scenarios:
            tc = self._scenario_to_test_case(scenario, story_key)
            test_cases.append(tc)

        return test_cases

    def _scenario_to_test_case(
        self,
        scenario: TestScenario,
        story_key: str
    ) -> TestCase:
        """Convert a single scenario to a test case."""
        self._tc_counter += 1
        tc_id = f"TC-{story_key}-{self._tc_counter:03d}"

        # Build BDD steps
        steps = self._build_bdd_steps(scenario)

        # Build expected results
        expected = self._build_expected_results(scenario)

        # Build test data suggestions
        test_data = self._suggest_test_data(scenario)

        # Get risk level string
        risk_level = self.RISK_LEVEL_MAP.get(scenario.risk_level, "MEDIUM")

        # Get test type
        test_type = self.TEST_TYPE_MAP.get(scenario.scenario_type, "Positive")

        return TestCase(
            id=tc_id,
            title=scenario.title,
            summary=scenario.title,
            preconditions=scenario.preconditions,
            steps=steps,
            test_data=test_data,
            expected_result=expected,
            expected=expected,  # Backward compatibility
            test_type=test_type,
            priority=scenario.priority,
            risk_level=risk_level,
            linked_rule_id=scenario.linked_rule_ids[0] if scenario.linked_rule_ids else "",
            linked_rule_ids=scenario.linked_rule_ids,
        )

    def _build_bdd_steps(self, scenario: TestScenario) -> List[str]:
        """Build BDD-formatted steps (Given/When/Then)."""
        steps = []

        # Given (preconditions)
        for i, precond in enumerate(scenario.preconditions):
            prefix = "Given" if i == 0 else "And"
            steps.append(f"{prefix} {precond}")

        # When (trigger)
        if scenario.trigger:
            steps.append(f"When {scenario.trigger}")

        # Then (expected)
        if scenario.expected_outcome:
            steps.append(f"Then {scenario.expected_outcome}")

        return steps

    def _build_expected_results(self, scenario: TestScenario) -> List[str]:
        """Build expected results list."""
        results = []

        if scenario.expected_outcome:
            results.append(scenario.expected_outcome)

        # Add type-specific expectations
        if scenario.scenario_type == ScenarioType.SECURITY:
            results.append("Verify unauthorized access is blocked")
            results.append("Verify appropriate error message displayed")

        elif scenario.scenario_type == ScenarioType.BOUNDARY:
            results.append("Verify boundary value is handled correctly")
            results.append("Verify no data corruption at boundary")

        elif scenario.scenario_type == ScenarioType.STATE_TRANSITION:
            results.append("Verify state changes as expected")
            results.append("Verify audit log records transition")

        elif scenario.scenario_type == ScenarioType.INTEGRATION:
            for module in scenario.affected_modules[:3]:
                results.append(f"Verify {module} module updated correctly")

        elif scenario.scenario_type == ScenarioType.NEGATIVE:
            results.append("Verify error message is clear and actionable")
            results.append("Verify system remains in valid state")

        return results

    def _suggest_test_data(self, scenario: TestScenario) -> Dict[str, Any]:
        """Suggest test data based on scenario type."""
        data: Dict[str, Any] = {
            "linked_rules": scenario.linked_rule_ids,
            "affected_modules": scenario.affected_modules,
            "scenario_type": scenario.scenario_type.value,
        }

        if scenario.scenario_type == ScenarioType.BOUNDARY:
            data["boundary_values"] = {
                "minimum": "test with minimum allowed value",
                "maximum": "test with maximum allowed value",
                "just_below_min": "test with value just below minimum",
                "just_above_max": "test with value just above maximum",
                "at_boundary": "test with exact boundary value",
            }

        elif scenario.scenario_type == ScenarioType.NEGATIVE:
            data["invalid_inputs"] = {
                "null": "test with null/empty value",
                "invalid_format": "test with wrong format",
                "out_of_range": "test with out of range value",
                "special_chars": "test with special characters",
                "sql_injection": "test with SQL injection patterns",
                "xss": "test with XSS patterns",
            }

        elif scenario.scenario_type == ScenarioType.SECURITY:
            data["security_scenarios"] = {
                "no_auth": "test without authentication",
                "invalid_token": "test with invalid token",
                "expired_token": "test with expired token",
                "wrong_role": "test with incorrect role",
                "privilege_escalation": "test privilege escalation attempt",
            }

        elif scenario.scenario_type == ScenarioType.STATE_TRANSITION:
            data["state_data"] = {
                "valid_transitions": "test all valid state transitions",
                "invalid_transitions": "test invalid state transition attempts",
                "concurrent_transitions": "test concurrent state changes",
            }

        elif scenario.scenario_type == ScenarioType.DATA_VALIDATION:
            data["validation_data"] = {
                "valid_data": "test with all valid data",
                "partial_data": "test with partial/incomplete data",
                "edge_case_data": "test with edge case values",
                "unicode_data": "test with unicode characters",
            }

        return data

    def design_from_rules(
        self,
        rules: List[Any],
        story_key: str
    ) -> List[TestCase]:
        """
        Design test cases directly from rules (simplified path).

        Args:
            rules: List of Rule objects
            story_key: Story key for ID generation

        Returns:
            List of TestCase objects
        """
        self._tc_counter = 0
        test_cases: List[TestCase] = []

        for rule in rules:
            # Create positive test case
            self._tc_counter += 1
            tc = TestCase(
                id=f"TC-{story_key}-{self._tc_counter:03d}",
                title=f"Verify {rule.rule_id}: {rule.description[:50]}",
                summary=f"Verify {rule.rule_id}: {rule.description[:50]}",
                preconditions=self._derive_preconditions_from_rule(rule),
                steps=self._derive_steps_from_rule(rule),
                expected=[rule.validation[:100] if rule.validation else "System behaves correctly"],
                test_type="Positive",
                risk_level=rule.risk_level.value.upper(),
                linked_rule_id=rule.rule_id,
                linked_rule_ids=[rule.rule_id] + rule.depends_on[:3],
            )
            test_cases.append(tc)

            # Create negative test case if rule has error_message
            if rule.error_message:
                self._tc_counter += 1
                tc_neg = TestCase(
                    id=f"TC-{story_key}-{self._tc_counter:03d}",
                    title=f"Verify error handling for {rule.rule_id}",
                    summary=f"Verify error handling for {rule.rule_id}",
                    preconditions=["Setup conditions to violate rule"],
                    steps=[
                        f"Given conditions that violate {rule.rule_id}",
                        f"When {rule.condition[:50] if rule.condition else 'action is attempted'}",
                        f"Then error is displayed: {rule.error_message[:50]}",
                    ],
                    expected=[rule.error_message[:100]],
                    test_type="Negative",
                    risk_level=rule.risk_level.value.upper(),
                    linked_rule_id=rule.rule_id,
                    linked_rule_ids=[rule.rule_id],
                )
                test_cases.append(tc_neg)

        return test_cases

    def _derive_preconditions_from_rule(self, rule: Any) -> List[str]:
        """Derive preconditions from rule."""
        preconditions = []

        if hasattr(rule, 'lifecycle_states') and rule.lifecycle_states:
            preconditions.append(f"Entity in state: {', '.join(rule.lifecycle_states[:3])}")

        if hasattr(rule, 'depends_on') and rule.depends_on:
            preconditions.append(f"Prerequisites: {', '.join(rule.depends_on[:3])}")

        return preconditions or ["Standard test environment"]

    def _derive_steps_from_rule(self, rule: Any) -> List[str]:
        """Derive BDD steps from rule."""
        steps = []

        # Given
        if hasattr(rule, 'lifecycle_states') and rule.lifecycle_states:
            steps.append(f"Given entity in state {rule.lifecycle_states[0]}")
        else:
            steps.append("Given standard test environment")

        # When
        if hasattr(rule, 'condition') and rule.condition:
            steps.append(f"When {rule.condition[:80]}")
        else:
            steps.append("When action is performed")

        # Then
        if hasattr(rule, 'validation') and rule.validation:
            steps.append(f"Then {rule.validation[:80]}")
        else:
            steps.append("Then system behaves correctly")

        return steps
