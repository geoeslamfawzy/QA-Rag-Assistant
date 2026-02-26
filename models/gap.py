"""
Gap Analysis Data Models for Deterministic QA Brain v2.0

Structured representations for gap analysis results.
All models are deterministic with no random elements.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class GapCategory(Enum):
    """Categories of gaps in test coverage."""
    MISSING_RULE = "missing_rule"              # Required rule not tested
    BOUNDARY_GAP = "boundary_gap"              # Boundary conditions untested
    STATE_GAP = "state_gap"                    # State transition untested
    CROSS_MODULE_GAP = "cross_module_gap"      # Integration point untested
    ERROR_HANDLING_GAP = "error_handling_gap"  # Error scenario missing
    REGRESSION_RISK = "regression_risk"        # Change affects existing behavior
    SECURITY_GAP = "security_gap"              # Security test missing
    DATA_VALIDATION_GAP = "data_validation_gap"  # Data validation untested
    PERFORMANCE_GAP = "performance_gap"        # Performance scenario missing


class RegressionRisk(Enum):
    """Regression risk levels."""
    CRITICAL = "critical"   # High probability of regression
    HIGH = "high"           # Moderate probability
    MEDIUM = "medium"       # Low probability
    LOW = "low"             # Minimal probability

    @classmethod
    def from_string(cls, value: str) -> "RegressionRisk":
        """Parse risk from string (case-insensitive)."""
        value_lower = value.lower().strip()
        for level in cls:
            if level.value == value_lower:
                return level
        return cls.MEDIUM  # Default


@dataclass
class GapItem:
    """A single detected gap."""
    category: GapCategory
    description: str
    missing_rule_ids: List[str] = field(default_factory=list)
    affected_modules: List[str] = field(default_factory=list)
    suggested_test: Optional[str] = None
    risk_level: str = "medium"  # Matches rule risk_level values
    confidence: float = 1.0     # 0-1 confidence in detection

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "description": self.description,
            "missing_rule_ids": self.missing_rule_ids,
            "affected_modules": self.affected_modules,
            "suggested_test": self.suggested_test,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
        }

    def to_markdown(self) -> str:
        """Format as markdown for output."""
        lines = [
            f"### {self.category.value.replace('_', ' ').title()}",
            f"**Description:** {self.description}",
            f"**Risk Level:** {self.risk_level.upper()}",
        ]
        if self.missing_rule_ids:
            lines.append(f"**Missing Rules:** {', '.join(self.missing_rule_ids)}")
        if self.affected_modules:
            lines.append(f"**Affected Modules:** {', '.join(self.affected_modules)}")
        if self.suggested_test:
            lines.append(f"**Suggested Test:** {self.suggested_test}")
        return "\n".join(lines)


@dataclass
class GapReport:
    """Complete gap analysis report."""
    gap_score: float                     # 0-1, where 1 = fully covered, 0 = no coverage
    items: List[GapItem] = field(default_factory=list)
    missing_rule_ids: List[str] = field(default_factory=list)
    regression_risk: RegressionRisk = RegressionRisk.LOW
    regression_risk_areas: List[str] = field(default_factory=list)
    cross_module_impacts: List[str] = field(default_factory=list)
    coverage_by_rule_type: Dict[str, float] = field(default_factory=dict)

    def is_fully_covered(self) -> bool:
        """Check if there are no significant gaps."""
        return self.gap_score >= 0.9 and not self.has_critical_gaps()

    def has_critical_gaps(self) -> bool:
        """Check if any gap has critical risk level."""
        return any(item.risk_level.lower() == "critical" for item in self.items)

    def has_high_gaps(self) -> bool:
        """Check if any gap has high risk level."""
        return any(item.risk_level.lower() in ["critical", "high"] for item in self.items)

    def get_critical_gaps(self) -> List[GapItem]:
        """Get all critical risk gaps."""
        return [item for item in self.items if item.risk_level.lower() == "critical"]

    def get_high_gaps(self) -> List[GapItem]:
        """Get all high risk gaps."""
        return [item for item in self.items if item.risk_level.lower() == "high"]

    def count_by_category(self) -> Dict[str, int]:
        """Count gaps by category."""
        counts: Dict[str, int] = {}
        for item in self.items:
            category_name = item.category.value
            counts[category_name] = counts.get(category_name, 0) + 1
        return counts

    def count_by_risk(self) -> Dict[str, int]:
        """Count gaps by risk level."""
        counts: Dict[str, int] = {}
        for item in self.items:
            risk = item.risk_level.lower()
            counts[risk] = counts.get(risk, 0) + 1
        return counts

    def get_all_missing_rules(self) -> List[str]:
        """Get deduplicated list of all missing rule IDs."""
        all_rules = set(self.missing_rule_ids)
        for item in self.items:
            all_rules.update(item.missing_rule_ids)
        return sorted(list(all_rules))

    def get_all_affected_modules(self) -> List[str]:
        """Get deduplicated list of all affected modules."""
        all_modules = set(self.cross_module_impacts)
        for item in self.items:
            all_modules.update(item.affected_modules)
        return sorted(list(all_modules))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "gap_score": self.gap_score,
            "items": [item.to_dict() for item in self.items],
            "missing_rule_ids": self.missing_rule_ids,
            "regression_risk": self.regression_risk.value,
            "regression_risk_areas": self.regression_risk_areas,
            "cross_module_impacts": self.cross_module_impacts,
            "coverage_by_rule_type": self.coverage_by_rule_type,
            "is_fully_covered": self.is_fully_covered(),
            "has_critical_gaps": self.has_critical_gaps(),
            "count_by_category": self.count_by_category(),
            "count_by_risk": self.count_by_risk(),
        }

    def to_markdown(self) -> str:
        """Format as markdown for output."""
        lines = [
            "# Gap Analysis Report",
            "",
            f"**Coverage Score:** {self.gap_score:.2f}",
            f"**Regression Risk:** {self.regression_risk.value.upper()}",
            f"**Total Gaps:** {len(self.items)}",
            "",
        ]

        if self.has_critical_gaps():
            lines.append("**WARNING: CRITICAL GAPS DETECTED**")
            lines.append("")

        # Missing rules summary
        all_missing = self.get_all_missing_rules()
        if all_missing:
            lines.append("## Missing Rule Coverage")
            for rule_id in all_missing[:20]:  # Limit to 20
                lines.append(f"- {rule_id}")
            if len(all_missing) > 20:
                lines.append(f"- ... and {len(all_missing) - 20} more")
            lines.append("")

        # Cross-module impacts
        all_modules = self.get_all_affected_modules()
        if all_modules:
            lines.append("## Cross-Module Impacts")
            for module in all_modules:
                lines.append(f"- {module}")
            lines.append("")

        # Regression risk areas
        if self.regression_risk_areas:
            lines.append("## Regression Risk Areas")
            for area in self.regression_risk_areas[:10]:
                lines.append(f"- {area}")
            lines.append("")

        # Summary by category
        by_category = self.count_by_category()
        if by_category:
            lines.append("## Summary by Category")
            for category, count in sorted(by_category.items(), key=lambda x: -x[1]):
                lines.append(f"- {category.replace('_', ' ').title()}: {count}")
            lines.append("")

        # Detailed items
        if self.items:
            lines.append("## Detailed Findings")
            for item in self.items:
                lines.append("")
                lines.append(item.to_markdown())

        return "\n".join(lines)

    @classmethod
    def full_coverage(cls) -> "GapReport":
        """Create a report indicating full coverage (no gaps)."""
        return cls(
            gap_score=1.0,
            items=[],
            missing_rule_ids=[],
            regression_risk=RegressionRisk.LOW,
            regression_risk_areas=[],
            cross_module_impacts=[],
            coverage_by_rule_type={},
        )
