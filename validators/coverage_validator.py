"""
Coverage Validator for Deterministic QA Brain

Validates that retrieved rules cover the required rule set.
Implements strict mode that blocks generation when critical rules are missing.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Set, Dict, Any, Optional
from enum import Enum

from models.rule import Rule, RiskLevel
from models.required_rule_set import RequiredRuleSet, CategorizedRule, RuleCategory
from .base_validator import BaseValidator, ValidationResult, Severity

logger = logging.getLogger(__name__)


class CoverageStatus(Enum):
    """Overall coverage status."""
    FULL = "full"              # All required rules covered
    PARTIAL = "partial"        # Some rules missing but no critical gaps
    INSUFFICIENT = "insufficient"  # Missing high-risk rules
    BLOCKED = "blocked"        # Missing critical rules, cannot generate
    UNKNOWN = "unknown"        # No applicable rules found for domain (INTEGRITY FIX)


@dataclass
class CoverageResult:
    """
    Result of coverage validation.

    This is the key data structure for deterministic reasoning.
    If can_generate is False, the system must not produce confident output.
    """

    # Rule coverage
    required_rules: List[str]      # All required rule IDs
    retrieved_rules: List[str]     # Rules found in retrieved context
    missing_rules: List[str]       # Required but not retrieved

    # Coverage metrics
    coverage_percentage: float     # Overall coverage (0-1)
    critical_coverage: float       # Critical rules coverage (0-1)
    high_risk_coverage: float      # High+Critical coverage (0-1)

    # Critical gaps
    missing_critical: List[str]    # CRITICAL rules not covered
    missing_high_risk: List[str]   # HIGH risk rules not covered

    # Generation decision
    can_generate: bool             # False if missing_critical not empty (in strict mode)
    status: CoverageStatus

    # Detailed breakdown
    coverage_by_category: Dict[str, float] = field(default_factory=dict)
    coverage_by_domain: Dict[str, float] = field(default_factory=dict)

    # Warnings
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Export for reporting."""
        return {
            "required_rules": self.required_rules,
            "retrieved_rules": self.retrieved_rules,
            "missing_rules": self.missing_rules,
            "coverage_percentage": self.coverage_percentage,
            "critical_coverage": self.critical_coverage,
            "high_risk_coverage": self.high_risk_coverage,
            "missing_critical": self.missing_critical,
            "missing_high_risk": self.missing_high_risk,
            "can_generate": self.can_generate,
            "status": self.status.value,
            "coverage_by_category": self.coverage_by_category,
            "coverage_by_domain": self.coverage_by_domain,
            "warnings": self.warnings,
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Coverage Status: {self.status.value.upper()}",
            f"Overall Coverage: {self.coverage_percentage:.0%}",
            f"Critical Coverage: {self.critical_coverage:.0%}",
            f"High-Risk Coverage: {self.high_risk_coverage:.0%}",
            f"Can Generate: {'YES' if self.can_generate else 'NO - BLOCKED'}",
            "",
            f"Required Rules: {len(self.required_rules)}",
            f"Retrieved Rules: {len(self.retrieved_rules)}",
            f"Missing Rules: {len(self.missing_rules)}",
        ]

        if self.missing_critical:
            lines.append("")
            lines.append("CRITICAL MISSING (blocks generation):")
            for rule_id in self.missing_critical:
                lines.append(f"  - {rule_id}")

        if self.missing_high_risk:
            lines.append("")
            lines.append("HIGH-RISK MISSING:")
            for rule_id in self.missing_high_risk:
                lines.append(f"  - {rule_id}")

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


class CoverageValidator(BaseValidator):
    """
    Validates rule coverage against required rule set.

    Enforces strict coverage thresholds and blocks generation
    when critical rules are missing.

    Thresholds:
    - CRITICAL_COVERAGE_THRESHOLD: 1.0 (all critical rules required)
    - HIGH_RISK_COVERAGE_THRESHOLD: 0.9 (90% of high-risk rules)
    - OVERALL_COVERAGE_THRESHOLD: 0.7 (70% overall coverage)
    """

    # Default thresholds (can be overridden from config)
    CRITICAL_COVERAGE_THRESHOLD = 1.0   # All critical rules required
    HIGH_RISK_COVERAGE_THRESHOLD = 0.9  # 90% of high-risk rules
    OVERALL_COVERAGE_THRESHOLD = 0.7    # 70% overall coverage

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the coverage validator.

        Args:
            strict_mode: If True, blocks generation when critical rules missing
        """
        super().__init__("CoverageValidator")
        self.strict_mode = strict_mode

    def validate_coverage(
        self,
        required_rules: RequiredRuleSet,
        retrieved_rule_ids: Set[str]
    ) -> CoverageResult:
        """
        Validate that retrieved rules cover requirements.

        Args:
            required_rules: Complete required rule set
            retrieved_rule_ids: Rule IDs found in retrieved context

        Returns:
            CoverageResult with detailed coverage metrics
        """
        # Get all required rule IDs
        all_required_ids = required_rules.all_rule_ids
        critical_ids = required_rules.critical_rule_ids
        high_risk_ids = required_rules.high_risk_rule_ids

        # INTEGRITY FIX: Handle empty rule set as UNKNOWN, not FULL
        # Empty rule set means we don't know how to validate this domain
        if not all_required_ids:
            logger.warning(
                "QA Brain blocked: No applicable rules found for detected domains. "
                "Cannot verify compliance."
            )
            return CoverageResult(
                required_rules=[],
                retrieved_rules=[],
                missing_rules=[],
                coverage_percentage=0.0,  # NOT 1.0 - we have ZERO coverage
                critical_coverage=0.0,
                high_risk_coverage=0.0,
                missing_critical=[],
                missing_high_risk=[],
                can_generate=False,  # BLOCKED - unknown domain
                status=CoverageStatus.UNKNOWN,
                coverage_by_category={},
                coverage_by_domain={},
                warnings=[
                    "No applicable rules found for detected domains. "
                    "Cannot verify compliance. Generation blocked for safety."
                ]
            )

        # Calculate what's covered
        covered_ids = all_required_ids.intersection(retrieved_rule_ids)
        missing_ids = all_required_ids - retrieved_rule_ids

        # Critical analysis
        covered_critical = critical_ids.intersection(retrieved_rule_ids)
        missing_critical = list(critical_ids - retrieved_rule_ids)

        # High-risk analysis
        covered_high_risk = high_risk_ids.intersection(retrieved_rule_ids)
        missing_high_risk = list(high_risk_ids - retrieved_rule_ids - critical_ids)

        # Calculate coverage percentages (safe division - all_required_ids is non-empty here)
        coverage_percentage = len(covered_ids) / len(all_required_ids)

        critical_coverage = (
            len(covered_critical) / len(critical_ids)
            if critical_ids else 1.0
        )

        high_risk_coverage = (
            len(covered_high_risk) / len(high_risk_ids)
            if high_risk_ids else 1.0
        )

        # Calculate coverage by category
        coverage_by_category = self._calculate_coverage_by_category(
            required_rules, retrieved_rule_ids
        )

        # Calculate coverage by domain
        coverage_by_domain = self._calculate_coverage_by_domain(
            required_rules, retrieved_rule_ids
        )

        # Determine generation permission
        can_generate, status = self._determine_status(
            coverage_percentage,
            missing_critical,
            missing_high_risk
        )

        # Generate warnings
        warnings = self._generate_warnings(
            coverage_percentage,
            critical_coverage,
            high_risk_coverage,
            missing_critical,
            missing_high_risk
        )

        return CoverageResult(
            required_rules=list(all_required_ids),
            retrieved_rules=list(retrieved_rule_ids.intersection(all_required_ids)),
            missing_rules=list(missing_ids),
            coverage_percentage=coverage_percentage,
            critical_coverage=critical_coverage,
            high_risk_coverage=high_risk_coverage,
            missing_critical=missing_critical,
            missing_high_risk=missing_high_risk,
            can_generate=can_generate,
            status=status,
            coverage_by_category=coverage_by_category,
            coverage_by_domain=coverage_by_domain,
            warnings=warnings,
        )

    def validate(
        self,
        story: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Standard validator interface.

        Note: Requires 'required_rules' and 'retrieved_rule_ids' in story dict.
        """
        result = self._create_result(
            passed=True,
            summary="Coverage validation completed"
        )

        # Get required rules from story (must be pre-computed)
        required_rules = story.get('required_rules')
        if not required_rules:
            result.add_warning(
                "No required rules provided, cannot validate coverage",
                suggestion="Run RuleSetBuilder before coverage validation"
            )
            return result

        # Extract rule IDs from knowledge context
        retrieved_ids = self._extract_rule_ids_from_context(knowledge_context)

        # Validate coverage
        coverage = self.validate_coverage(required_rules, retrieved_ids)

        # Populate result
        result.details['coverage'] = coverage.to_dict()
        result.score = coverage.coverage_percentage
        result.passed = coverage.can_generate

        # Add findings
        if coverage.missing_critical:
            for rule_id in coverage.missing_critical:
                result.add_error(
                    f"CRITICAL rule not covered: {rule_id}",
                    rule_id=rule_id,
                    suggestion="Ensure this rule is in knowledge base and retrievable"
                )

        if coverage.missing_high_risk:
            for rule_id in coverage.missing_high_risk:
                result.add_warning(
                    f"HIGH-RISK rule not covered: {rule_id}",
                    rule_id=rule_id
                )

        if coverage.coverage_percentage < self.OVERALL_COVERAGE_THRESHOLD:
            result.add_warning(
                f"Low coverage: {coverage.coverage_percentage:.0%}",
                suggestion="Review knowledge base for missing rules"
            )

        result.summary = (
            f"Coverage: {coverage.coverage_percentage:.0%} "
            f"({len(coverage.retrieved_rules)}/{len(coverage.required_rules)} rules). "
            f"Status: {coverage.status.value}"
        )

        return result

    def _calculate_coverage_by_category(
        self,
        required_rules: RequiredRuleSet,
        retrieved_ids: Set[str]
    ) -> Dict[str, float]:
        """Calculate coverage percentage by rule category."""
        result = {}

        for category in RuleCategory:
            category_rules = required_rules.get_rules_by_category(category)
            if category_rules:
                category_ids = {cr.rule.rule_id for cr in category_rules}
                covered = len(category_ids.intersection(retrieved_ids))
                result[category.value] = covered / len(category_ids)
            else:
                result[category.value] = 1.0  # No rules = fully covered

        return result

    def _calculate_coverage_by_domain(
        self,
        required_rules: RequiredRuleSet,
        retrieved_ids: Set[str]
    ) -> Dict[str, float]:
        """Calculate coverage percentage by domain."""
        result = {}
        domain_rules: Dict[str, Set[str]] = {}

        # Group rules by domain
        for cr in required_rules.all_rules:
            domain = cr.rule.domain or 'unknown'
            if domain not in domain_rules:
                domain_rules[domain] = set()
            domain_rules[domain].add(cr.rule.rule_id)

        # Calculate coverage per domain
        for domain, rule_ids in domain_rules.items():
            covered = len(rule_ids.intersection(retrieved_ids))
            result[domain] = covered / len(rule_ids) if rule_ids else 1.0

        return result

    def _determine_status(
        self,
        coverage: float,
        missing_critical: List[str],
        missing_high_risk: List[str]
    ) -> tuple[bool, CoverageStatus]:
        """
        Determine overall coverage status and generation permission.

        INTEGRITY FIX: CRITICAL rules ALWAYS block generation, regardless of strict_mode.
        strict_mode only affects non-critical rule enforcement.

        Returns:
            Tuple of (can_generate, status)
        """
        # BLOCKED: ANY critical rule missing - ALWAYS, regardless of mode
        # This is a CRITICAL integrity fix - we NEVER allow generation
        # when critical rules are missing, even in loose mode
        if missing_critical:
            logger.warning(
                f"QA Brain blocked: Missing critical rules: {missing_critical}. "
                "Critical rules ALWAYS block generation."
            )
            return False, CoverageStatus.BLOCKED

        # FULL: Everything covered
        if coverage >= 1.0 and not missing_high_risk:
            return True, CoverageStatus.FULL

        # INSUFFICIENT: Too many high-risk rules missing (strict mode enforced)
        if self.strict_mode and len(missing_high_risk) > 2:
            return False, CoverageStatus.INSUFFICIENT

        # PARTIAL: Some rules missing but acceptable
        if coverage >= self.OVERALL_COVERAGE_THRESHOLD:
            return True, CoverageStatus.PARTIAL

        # INSUFFICIENT: Below threshold (strict mode enforced for non-critical)
        if self.strict_mode:
            return False, CoverageStatus.INSUFFICIENT

        # Loose mode allows low coverage for non-critical rules only
        return True, CoverageStatus.PARTIAL

    def _generate_warnings(
        self,
        coverage: float,
        critical_coverage: float,
        high_risk_coverage: float,
        missing_critical: List[str],
        missing_high_risk: List[str]
    ) -> List[str]:
        """Generate warnings based on coverage analysis."""
        warnings = []

        if missing_critical:
            warnings.append(
                f"CRITICAL: Missing {len(missing_critical)} critical rule(s): "
                f"{', '.join(missing_critical[:5])}"
            )

        if missing_high_risk:
            warnings.append(
                f"HIGH-RISK: Missing {len(missing_high_risk)} high-risk rule(s)"
            )

        if coverage < self.OVERALL_COVERAGE_THRESHOLD:
            warnings.append(
                f"Coverage {coverage:.0%} below threshold {self.OVERALL_COVERAGE_THRESHOLD:.0%}"
            )

        if high_risk_coverage < self.HIGH_RISK_COVERAGE_THRESHOLD:
            warnings.append(
                f"High-risk coverage {high_risk_coverage:.0%} "
                f"below threshold {self.HIGH_RISK_COVERAGE_THRESHOLD:.0%}"
            )

        return warnings

    def _extract_rule_ids_from_context(
        self,
        knowledge_context: List[Dict[str, Any]]
    ) -> Set[str]:
        """Extract all rule IDs from knowledge context chunks."""
        import re

        rule_ids = set()
        patterns = [
            r'(FIN-[A-Z]{1,5}-\d{3})',
            r'(RULE-[A-Z]{1,5}-\d{3})',
            r'(DEP-[A-Z]{1,5}-\d{3})',
        ]

        for chunk in knowledge_context:
            content = chunk.get('content', '').upper()
            for pattern in patterns:
                matches = re.findall(pattern, content)
                rule_ids.update(matches)

        return rule_ids
