"""
Integrity Validator for Deterministic QA Brain

Validates the integrity of generated output by:
1. Extracting cited rule IDs from output
2. Comparing with required rules
3. Scoring reasoning depth and evidence quality
4. Computing Grounded Reasoning Score (0-5)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Optional

from models.required_rule_set import RequiredRuleSet
from .base_validator import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class IntegrityReport:
    """
    Report from integrity validation.

    Contains the Grounded Reasoning Score and component scores.
    """

    # Rule citation analysis
    required_rule_ids: Set[str]
    cited_rule_ids: Set[str]
    missing_citations: Set[str]
    unexpected_citations: Set[str]  # Cited but not required

    # Grounded Reasoning Score (0-5 scale)
    grounded_reasoning_score: float

    # Component scores (each 0-1)
    citation_completeness: float    # Required rules cited
    reasoning_depth: float          # Chains have full depth
    evidence_quality: float         # Citations include context/evidence
    consistency: float              # No contradictions

    # Issues found
    integrity_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Export for reporting."""
        return {
            "required_rule_ids": list(self.required_rule_ids),
            "cited_rule_ids": list(self.cited_rule_ids),
            "missing_citations": list(self.missing_citations),
            "unexpected_citations": list(self.unexpected_citations),
            "grounded_reasoning_score": self.grounded_reasoning_score,
            "citation_completeness": self.citation_completeness,
            "reasoning_depth": self.reasoning_depth,
            "evidence_quality": self.evidence_quality,
            "consistency": self.consistency,
            "integrity_issues": self.integrity_issues,
            "warnings": self.warnings,
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        # Map score to description
        score_desc = self._score_description(self.grounded_reasoning_score)

        lines = [
            f"Grounded Reasoning Score: {self.grounded_reasoning_score:.1f}/5.0 ({score_desc})",
            "",
            "Component Scores:",
            f"  Citation Completeness: {self.citation_completeness:.0%}",
            f"  Reasoning Depth: {self.reasoning_depth:.0%}",
            f"  Evidence Quality: {self.evidence_quality:.0%}",
            f"  Consistency: {self.consistency:.0%}",
            "",
            f"Rules Cited: {len(self.cited_rule_ids)}",
            f"Rules Required: {len(self.required_rule_ids)}",
            f"Missing Citations: {len(self.missing_citations)}",
        ]

        if self.missing_citations:
            lines.append("")
            lines.append("Missing Rule Citations:")
            for rule_id in list(self.missing_citations)[:10]:
                lines.append(f"  - {rule_id}")

        if self.integrity_issues:
            lines.append("")
            lines.append("Integrity Issues:")
            for issue in self.integrity_issues[:5]:
                lines.append(f"  - {issue}")

        return "\n".join(lines)

    def _score_description(self, score: float) -> str:
        """Get description for grounding score."""
        if score >= 4.5:
            return "Excellent"
        elif score >= 4.0:
            return "Good"
        elif score >= 3.0:
            return "Acceptable"
        elif score >= 2.0:
            return "Weak"
        elif score >= 1.0:
            return "Poor"
        else:
            return "Ungrounded"


class IntegrityValidator(BaseValidator):
    """
    Validates integrity of generated output.

    Checks:
    1. All required rules are cited
    2. Citations include proper context/evidence
    3. Reasoning chains are complete
    4. No contradictory statements

    Grounded Reasoning Score (0-5):
    - 5: All rules cited with full evidence and reasoning chains
    - 4: All critical rules cited, minor gaps in evidence
    - 3: Most rules cited, some reasoning gaps
    - 2: Significant citation gaps, weak reasoning
    - 1: Few rules cited, no clear reasoning
    - 0: No rule grounding detected
    """

    # Score weights for calculating final score
    CITATION_WEIGHT = 0.4
    REASONING_WEIGHT = 0.3
    EVIDENCE_WEIGHT = 0.2
    CONSISTENCY_WEIGHT = 0.1

    # Patterns for analysis
    RULE_ID_PATTERNS = [
        r'(FIN-[A-Z]{1,5}-\d{3})',
        r'(RULE-[A-Z]{1,5}-\d{3})',
        r'(DEP-[A-Z]{1,5}-\d{3})',
    ]

    # Evidence indicators
    EVIDENCE_INDICATORS = [
        r'based on',
        r'according to',
        r'as defined in',
        r'per rule',
        r'rule states',
        r'validation:',
        r'condition:',
        r'because',
        r'therefore',
        r'this means',
    ]

    # Reasoning indicators
    REASONING_INDICATORS = [
        r'implies',
        r'consequently',
        r'thus',
        r'hence',
        r'as a result',
        r'leads to',
        r'causes',
        r'triggers',
        r'results in',
        r'must verify',
        r'should test',
        r'expected behavior',
    ]

    def __init__(self):
        super().__init__("IntegrityValidator")

    def validate_integrity(
        self,
        generated_output: str,
        required_rules: RequiredRuleSet
    ) -> IntegrityReport:
        """
        Validate integrity of generated output.

        Args:
            generated_output: The generated text/markdown
            required_rules: The required rule set

        Returns:
            IntegrityReport with scores and issues
        """
        # Extract cited rules from output
        cited_ids = self._extract_cited_rules(generated_output)

        # Get required rule IDs
        required_ids = required_rules.all_rule_ids

        # Calculate missing and unexpected citations
        missing_citations = required_ids - cited_ids
        unexpected_citations = cited_ids - required_ids

        # Calculate component scores
        citation_completeness = self._calculate_citation_completeness(
            required_ids, cited_ids
        )

        reasoning_depth = self._calculate_reasoning_depth(
            generated_output, required_rules
        )

        evidence_quality = self._calculate_evidence_quality(
            generated_output, required_rules
        )

        consistency = self._check_consistency(generated_output)

        # Calculate final grounded reasoning score (0-5)
        grounded_score = self._calculate_grounded_score(
            citation_completeness,
            reasoning_depth,
            evidence_quality,
            consistency
        )

        # Generate issues and warnings
        issues, warnings = self._analyze_issues(
            cited_ids,
            required_ids,
            missing_citations,
            generated_output
        )

        return IntegrityReport(
            required_rule_ids=required_ids,
            cited_rule_ids=cited_ids,
            missing_citations=missing_citations,
            unexpected_citations=unexpected_citations,
            grounded_reasoning_score=grounded_score,
            citation_completeness=citation_completeness,
            reasoning_depth=reasoning_depth,
            evidence_quality=evidence_quality,
            consistency=consistency,
            integrity_issues=issues,
            warnings=warnings,
        )

    def validate(
        self,
        story: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]]
    ) -> ValidationResult:
        """Standard validator interface."""
        result = self._create_result(
            passed=True,
            summary="Integrity validation completed"
        )

        # Get generated output from story
        generated_output = story.get('generated_output', '')
        required_rules = story.get('required_rules')

        if not generated_output:
            result.add_warning(
                "No generated output provided for integrity validation"
            )
            return result

        if not required_rules:
            result.add_warning(
                "No required rules provided, cannot validate integrity"
            )
            return result

        # Validate integrity
        report = self.validate_integrity(generated_output, required_rules)

        # Populate result
        result.details['integrity'] = report.to_dict()
        result.score = report.grounded_reasoning_score / 5.0  # Normalize to 0-1

        # Determine pass/fail based on score
        MIN_SCORE = 3.0  # Minimum acceptable score
        result.passed = report.grounded_reasoning_score >= MIN_SCORE

        # Add findings
        for issue in report.integrity_issues:
            result.add_error(issue)

        for warning in report.warnings:
            result.add_warning(warning)

        if report.missing_citations:
            for rule_id in list(report.missing_citations)[:5]:
                result.add_warning(
                    f"Required rule not cited: {rule_id}",
                    rule_id=rule_id
                )

        result.summary = (
            f"Grounded Reasoning Score: {report.grounded_reasoning_score:.1f}/5.0. "
            f"Cited {len(report.cited_rule_ids)}/{len(report.required_rule_ids)} rules."
        )

        return result

    def _extract_cited_rules(self, output: str) -> Set[str]:
        """Extract all rule IDs mentioned in output."""
        rule_ids: Set[str] = set()
        output_upper = output.upper()

        for pattern in self.RULE_ID_PATTERNS:
            matches = re.findall(pattern, output_upper)
            rule_ids.update(matches)

        return rule_ids

    def _calculate_citation_completeness(
        self,
        required_ids: Set[str],
        cited_ids: Set[str]
    ) -> float:
        """
        Calculate citation completeness score.

        Returns percentage of required rules that are cited.
        """
        if not required_ids:
            return 1.0

        cited_required = required_ids.intersection(cited_ids)
        return len(cited_required) / len(required_ids)

    def _calculate_reasoning_depth(
        self,
        output: str,
        required_rules: RequiredRuleSet
    ) -> float:
        """
        Score reasoning depth.

        Checks:
        - Does output explain WHY rules apply?
        - Are state transitions explained?
        - Are impacts documented?
        """
        output_lower = output.lower()

        # Count reasoning indicators
        reasoning_count = sum(
            len(re.findall(pattern, output_lower))
            for pattern in self.REASONING_INDICATORS
        )

        # Expected: at least 1 reasoning indicator per 3 rules
        expected_reasoning = max(1, len(required_rules.all_rule_ids) / 3)

        # Score based on ratio (capped at 1.0)
        score = min(1.0, reasoning_count / expected_reasoning)

        # Bonus for state transition explanations
        if 'state' in output_lower and ('transition' in output_lower or '->' in output):
            score = min(1.0, score + 0.1)

        # Bonus for impact explanations
        if 'impact' in output_lower or 'affects' in output_lower:
            score = min(1.0, score + 0.1)

        return score

    def _calculate_evidence_quality(
        self,
        output: str,
        required_rules: RequiredRuleSet
    ) -> float:
        """
        Score evidence quality.

        Checks:
        - Are rule conditions quoted?
        - Are validation criteria included?
        - Is there story-to-rule mapping?
        """
        output_lower = output.lower()

        # Count evidence indicators
        evidence_count = sum(
            len(re.findall(pattern, output_lower))
            for pattern in self.EVIDENCE_INDICATORS
        )

        # Check for quoted content (evidence)
        quote_count = len(re.findall(r'[""][^""]+[""]', output))
        evidence_count += quote_count * 0.5

        # Expected: at least 1 evidence indicator per 2 rules
        expected_evidence = max(1, len(required_rules.all_rule_ids) / 2)

        # Score based on ratio (capped at 1.0)
        score = min(1.0, evidence_count / expected_evidence)

        # Bonus for structured evidence
        if 'condition:' in output_lower or 'validation:' in output_lower:
            score = min(1.0, score + 0.1)

        return score

    def _check_consistency(self, output: str) -> float:
        """
        Check for contradictory statements.

        Returns 1.0 for fully consistent, lower for contradictions found.
        """
        output_lower = output.lower()

        # Simple contradiction detection
        contradictions = 0

        # Check for "should" vs "should not" on same topics
        should_patterns = re.findall(r'should (\w+)', output_lower)
        should_not_patterns = re.findall(r'should not (\w+)', output_lower)

        common_verbs = set(should_patterns).intersection(set(should_not_patterns))
        contradictions += len(common_verbs)

        # Check for "must" vs "must not" on same topics
        must_patterns = re.findall(r'must (\w+)', output_lower)
        must_not_patterns = re.findall(r'must not (\w+)', output_lower)

        common_must = set(must_patterns).intersection(set(must_not_patterns))
        contradictions += len(common_must)

        # Score: 1.0 for no contradictions, decreases with each
        if contradictions == 0:
            return 1.0
        elif contradictions <= 2:
            return 0.8
        elif contradictions <= 5:
            return 0.5
        else:
            return 0.2

    def _calculate_grounded_score(
        self,
        citation: float,
        reasoning: float,
        evidence: float,
        consistency: float
    ) -> float:
        """
        Calculate final Grounded Reasoning Score (0-5).

        Weighted combination of component scores.
        """
        weighted_score = (
            citation * self.CITATION_WEIGHT +
            reasoning * self.REASONING_WEIGHT +
            evidence * self.EVIDENCE_WEIGHT +
            consistency * self.CONSISTENCY_WEIGHT
        )

        # Convert 0-1 score to 0-5 scale
        return weighted_score * 5.0

    def _analyze_issues(
        self,
        cited_ids: Set[str],
        required_ids: Set[str],
        missing_citations: Set[str],
        output: str
    ) -> tuple[List[str], List[str]]:
        """Analyze and categorize issues found."""
        issues: List[str] = []
        warnings: List[str] = []

        # Critical: No rules cited at all
        if not cited_ids:
            issues.append("No rule IDs cited in output - output is ungrounded")

        # Critical: More than 50% missing
        if missing_citations and len(missing_citations) > len(required_ids) * 0.5:
            issues.append(
                f"Majority of required rules not cited "
                f"({len(missing_citations)}/{len(required_ids)})"
            )

        # Warning: Some rules missing
        elif missing_citations:
            warnings.append(
                f"{len(missing_citations)} required rule(s) not cited"
            )

        # Warning: Output too short for thorough reasoning
        word_count = len(output.split())
        if word_count < 100:
            warnings.append(
                f"Output very short ({word_count} words) - "
                "may lack sufficient reasoning depth"
            )

        # Warning: No evidence patterns found
        output_lower = output.lower()
        has_evidence = any(
            pattern in output_lower
            for pattern in ['based on', 'according to', 'as defined', 'rule states']
        )
        if not has_evidence:
            warnings.append(
                "No evidence indicators found - "
                "output may lack proper rule grounding"
            )

        return issues, warnings

    def quick_check(self, output: str, required_rule_ids: Set[str]) -> bool:
        """
        Quick check if output cites required rules.

        Returns True if all critical rules are cited.
        """
        cited = self._extract_cited_rules(output)
        return required_rule_ids.issubset(cited)
