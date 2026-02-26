"""
Defect Engine for Deterministic QA Brain v2.0

Generates defects from:
1. Ambiguity findings
2. Rule violations
3. Coverage gaps
4. State transition failures

All generation is deterministic - severity strictly maps from rule risk_level.
No probabilistic assignment or guessing.
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING

from models.defect import Defect, DefectType, SEVERITY_FROM_RISK, PRIORITY_MAP
from models.ambiguity import AmbiguityReport, AmbiguityItem, AmbiguitySeverity
from models.gap import GapReport, GapItem

if TYPE_CHECKING:
    from validators.base_validator import ValidationResult


class DefectEngine:
    """
    Deterministic defect generation engine.

    Severity mapping (strict from rule risk_level):
    - CRITICAL rule -> Highest severity
    - HIGH rule -> High severity
    - MEDIUM rule -> Medium severity
    - LOW rule -> Low severity

    No probabilistic assignment.
    """

    SEVERITY_MAP = {
        "critical": "Highest",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    }

    AMBIGUITY_SEVERITY_MAP = {
        AmbiguitySeverity.CRITICAL: "CRITICAL",
        AmbiguitySeverity.HIGH: "HIGH",
        AmbiguitySeverity.MEDIUM: "MEDIUM",
        AmbiguitySeverity.LOW: "LOW",
    }

    def __init__(self):
        """Initialize the defect engine."""
        self._defect_counter = 0

    def generate_from_ambiguity(
        self,
        ambiguity_report: AmbiguityReport,
        story_key: str
    ) -> List[Defect]:
        """
        Generate defects from ambiguity findings.

        Only generates defects for CRITICAL and HIGH severity ambiguities.

        Args:
            ambiguity_report: The ambiguity analysis report
            story_key: Parent story key

        Returns:
            List of Defect objects
        """
        defects: List[Defect] = []

        for item in ambiguity_report.items:
            # Only create defects for high-severity ambiguities
            if item.severity in [AmbiguitySeverity.CRITICAL, AmbiguitySeverity.HIGH]:
                defect = self._create_ambiguity_defect(item, story_key)
                defects.append(defect)

        return defects

    def generate_from_gaps(
        self,
        gap_report: GapReport,
        story_key: str
    ) -> List[Defect]:
        """
        Generate defects from coverage gaps.

        Only generates defects for critical and high risk gaps.

        Args:
            gap_report: The gap analysis report
            story_key: Parent story key

        Returns:
            List of Defect objects
        """
        defects: List[Defect] = []

        for item in gap_report.items:
            # Only create defects for high-severity gaps
            if item.risk_level.lower() in ["critical", "high"]:
                defect = self._create_gap_defect(item, story_key)
                defects.append(defect)

        return defects

    def generate_from_validation(
        self,
        validation_results: Dict[str, Any],
        story_key: str
    ) -> List[Defect]:
        """
        Generate defects from validation failures.

        Args:
            validation_results: Dictionary of validator name -> result
            story_key: Parent story key

        Returns:
            List of Defect objects
        """
        defects: List[Defect] = []

        for validator_name, result in validation_results.items():
            # Check if result has passed attribute and findings
            if hasattr(result, 'passed') and not result.passed:
                if hasattr(result, 'findings'):
                    for finding in result.findings:
                        # Check severity
                        severity = getattr(finding, 'severity', None)
                        if severity and hasattr(severity, 'value'):
                            if severity.value in ["error", "critical"]:
                                defect = self._create_validation_defect(
                                    finding, validator_name, story_key
                                )
                                defects.append(defect)

        return defects

    def generate_from_rule_violation(
        self,
        rule_id: str,
        rule_description: str,
        violation_description: str,
        risk_level: str,
        story_key: str,
        impacted_modules: Optional[List[str]] = None
    ) -> Defect:
        """
        Generate a defect from a specific rule violation.

        Args:
            rule_id: The violated rule ID
            rule_description: Rule description
            violation_description: Description of the violation
            risk_level: Rule's risk level (CRITICAL, HIGH, MEDIUM, LOW)
            story_key: Parent story key
            impacted_modules: List of impacted modules

        Returns:
            Defect object
        """
        self._defect_counter += 1

        severity = self.SEVERITY_MAP.get(risk_level.lower(), "Medium")
        priority = PRIORITY_MAP.get(risk_level.upper(), "Medium")

        return Defect(
            summary=f"[{story_key}] Rule Violation: {rule_id}",
            title=f"Rule {rule_id} violated: {rule_description[:50]}",
            description=violation_description,
            preconditions=f"Rule {rule_id}: {rule_description[:100]}",
            steps_to_reproduce=[
                f"1. Review story {story_key}",
                f"2. Check rule {rule_id} requirements",
                f"3. Observe violation: {violation_description[:50]}",
            ],
            expected_results=f"Story should comply with rule {rule_id}",
            actual_results=f"Violation detected: {violation_description[:100]}",
            risk_level=risk_level.upper(),
            defect_type="violation",
            violation_type="rule",
            violated_rule_id=rule_id,
            violated_rule_ids=[rule_id],
            rule_ids=[rule_id],
            impacted_module=impacted_modules[0] if impacted_modules else "WebApp",
            confidence_score=0.95,
            parent_key=story_key,
        )

    def generate_story_defect(
        self,
        story_key: str,
        defect_description: str,
        issue_type: str,
        risk_level: str = "MEDIUM",
        rule_ids: Optional[List[str]] = None
    ) -> Defect:
        """
        Generate a story-level defect (missing AC, unclear requirement, etc.).

        Args:
            story_key: Parent story key
            defect_description: User-provided description
            issue_type: Type of issue (missing_ac, unclear_requirement, incomplete_story)
            risk_level: Risk level
            rule_ids: Related rule IDs

        Returns:
            Defect object
        """
        self._defect_counter += 1

        return Defect(
            summary=f"[{story_key}] Story Quality: {issue_type.replace('_', ' ').title()}",
            title=f"Story Quality Issue: {issue_type.replace('_', ' ').title()}",
            user_description=defect_description,
            description=f"Story quality issue detected in {story_key}",
            preconditions="Story review",
            steps_to_reproduce=[
                f"1. Review story {story_key}",
                f"2. Observe issue: {issue_type.replace('_', ' ')}",
            ],
            expected_results="Story should be complete and clear",
            actual_results=defect_description[:200],
            risk_level=risk_level.upper(),
            defect_type="story_quality",
            issue_type=issue_type,
            rule_ids=rule_ids or [],
            violated_rule_ids=rule_ids or [],
            confidence_score=0.9,
            parent_key=story_key,
        )

    def _create_ambiguity_defect(
        self,
        item: AmbiguityItem,
        story_key: str
    ) -> Defect:
        """Create defect from ambiguity item."""
        self._defect_counter += 1

        risk_level = self.AMBIGUITY_SEVERITY_MAP.get(item.severity, "MEDIUM")

        return Defect(
            summary=f"[{story_key}] Ambiguity: {item.description[:60]}",
            title=f"Ambiguity in {story_key}: {item.category.value.replace('_', ' ').title()}",
            description=f"Detected ambiguity in story {story_key}",
            preconditions=f"Story location: {item.location[:100]}",
            steps_to_reproduce=[
                f"1. Review story {story_key}",
                f"2. Locate: {item.location[:80]}",
                f"3. Observe ambiguity: {item.description[:80]}",
            ],
            expected_results=f"Story should clearly specify: {item.clarification_question[:100]}",
            actual_results=f"Ambiguous: {item.description[:100]}",
            risk_level=risk_level,
            defect_type="ambiguity_defect",
            issue_type=item.category.value,
            violated_rule_id=item.violated_rule_ids[0] if item.violated_rule_ids else "",
            violated_rule_ids=item.violated_rule_ids,
            rule_ids=item.violated_rule_ids,
            confidence_score=item.confidence,
            parent_key=story_key,
            root_cause_hypothesis=f"Story contains {item.category.value.replace('_', ' ')} that needs clarification",
        )

    def _create_gap_defect(
        self,
        item: GapItem,
        story_key: str
    ) -> Defect:
        """Create defect from gap item."""
        self._defect_counter += 1

        risk_level = item.risk_level.upper()

        return Defect(
            summary=f"[{story_key}] Coverage Gap: {item.description[:60]}",
            title=f"Missing coverage for {', '.join(item.missing_rule_ids[:3]) if item.missing_rule_ids else 'rules'}",
            description=f"Test coverage gap detected in story {story_key}",
            preconditions="Test suite review",
            steps_to_reproduce=[
                f"1. Review test coverage for {story_key}",
                f"2. Check coverage of: {', '.join(item.missing_rule_ids[:5]) if item.missing_rule_ids else 'related rules'}",
                f"3. Observe gap: {item.description[:80]}",
            ],
            expected_results="All rules should have test coverage",
            actual_results=f"Gap: {item.description[:100]}",
            risk_level=risk_level,
            defect_type="coverage_gap",
            violation_type=item.category.value,
            violated_rule_id=item.missing_rule_ids[0] if item.missing_rule_ids else "",
            violated_rule_ids=item.missing_rule_ids,
            rule_ids=item.missing_rule_ids,
            impacted_module=item.affected_modules[0] if item.affected_modules else "WebApp",
            confidence_score=item.confidence,
            parent_key=story_key,
            root_cause_hypothesis=f"Test coverage does not include {item.category.value.replace('_', ' ')}",
        )

    def _create_validation_defect(
        self,
        finding: Any,
        validator_name: str,
        story_key: str
    ) -> Defect:
        """Create defect from validation finding."""
        self._defect_counter += 1

        # Map validator name to defect type
        defect_type_map = {
            "StateValidator": "state_violation",
            "FinancialValidator": "financial_violation",
            "RuleEngine": "rule_violation",
            "CrossDepChecker": "cross_dep_violation",
        }

        defect_type = defect_type_map.get(validator_name, "rule_violation")

        # Get severity from finding
        severity = "MEDIUM"
        if hasattr(finding, 'severity') and hasattr(finding.severity, 'value'):
            severity_value = finding.severity.value.lower()
            if severity_value in ["critical", "error"]:
                severity = "CRITICAL"
            elif severity_value == "warning":
                severity = "HIGH"

        # Get message
        message = getattr(finding, 'message', str(finding))[:200]

        # Get rule ID
        rule_id = getattr(finding, 'rule_id', "") or ""

        return Defect(
            summary=f"[{story_key}] {validator_name}: {message[:50]}",
            title=f"Validation failure from {validator_name}",
            description=message,
            preconditions=f"Validation by {validator_name}",
            steps_to_reproduce=[
                f"1. Run {validator_name} on {story_key}",
                f"2. Observe failure: {message[:80]}",
            ],
            expected_results="Validation should pass",
            actual_results=f"Validation failed: {message[:100]}",
            risk_level=severity,
            defect_type=defect_type,
            violation_type=validator_name.lower().replace("validator", "").replace("checker", ""),
            violated_rule_id=rule_id,
            violated_rule_ids=[rule_id] if rule_id else [],
            rule_ids=[rule_id] if rule_id else [],
            confidence_score=0.95,
            parent_key=story_key,
        )
