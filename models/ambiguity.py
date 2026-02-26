"""
Ambiguity Data Models for Deterministic QA Brain v2.0

Structured representations for ambiguity detection results.
All models are deterministic with no random elements.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class AmbiguityCategory(Enum):
    """Categories of ambiguity in user stories."""
    MISSING_BOUNDARY = "missing_boundary"          # No min/max specified
    VAGUE_QUANTIFIER = "vague_quantifier"          # "some", "many", "few"
    UNDEFINED_BEHAVIOR = "undefined_behavior"      # Missing error handling
    IMPLICIT_ASSUMPTION = "implicit_assumption"    # Assumed context not stated
    CONFLICTING_REQUIREMENT = "conflicting_req"    # Contradictory ACs
    MISSING_STATE = "missing_state"                # Lifecycle state not specified
    INCOMPLETE_FLOW = "incomplete_flow"            # Missing steps in flow
    UNDEFINED_ACTOR = "undefined_actor"            # Actor not specified
    MISSING_VALIDATION = "missing_validation"      # No validation criteria
    MISSING_ERROR_HANDLING = "missing_error_handling"  # No error case defined
    MISSING_NEGATIVE_FLOW = "missing_negative_flow"    # No negative scenario


class AmbiguitySeverity(Enum):
    """Severity of ambiguity impact."""
    CRITICAL = "critical"   # Blocks implementation
    HIGH = "high"           # Major risk of misinterpretation
    MEDIUM = "medium"       # Moderate risk
    LOW = "low"             # Minor clarification needed

    @classmethod
    def from_string(cls, value: str) -> "AmbiguitySeverity":
        """Parse severity from string (case-insensitive)."""
        value_lower = value.lower().strip()
        for level in cls:
            if level.value == value_lower:
                return level
        return cls.MEDIUM  # Default

    def __lt__(self, other: "AmbiguitySeverity") -> bool:
        """Compare severity levels (CRITICAL > HIGH > MEDIUM > LOW)."""
        order = {
            AmbiguitySeverity.CRITICAL: 4,
            AmbiguitySeverity.HIGH: 3,
            AmbiguitySeverity.MEDIUM: 2,
            AmbiguitySeverity.LOW: 1
        }
        return order[self] < order[other]

    def __le__(self, other: "AmbiguitySeverity") -> bool:
        return self == other or self < other

    def __gt__(self, other: "AmbiguitySeverity") -> bool:
        return not self <= other

    def __ge__(self, other: "AmbiguitySeverity") -> bool:
        return not self < other


@dataclass
class AmbiguityItem:
    """A single detected ambiguity."""
    category: AmbiguityCategory
    severity: AmbiguitySeverity
    description: str
    location: str                        # Where in story found
    clarification_question: str          # Question to ask
    violated_rule_ids: List[str] = field(default_factory=list)
    suggested_resolution: Optional[str] = None
    confidence: float = 1.0              # 0-1 confidence in detection

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "clarification_question": self.clarification_question,
            "violated_rule_ids": self.violated_rule_ids,
            "suggested_resolution": self.suggested_resolution,
            "confidence": self.confidence,
        }

    def to_markdown(self) -> str:
        """Format as markdown for output."""
        lines = [
            f"### {self.category.value.replace('_', ' ').title()}",
            f"**Severity:** {self.severity.value.upper()}",
            f"**Description:** {self.description}",
            f"**Location:** {self.location}",
            f"**Question:** {self.clarification_question}",
        ]
        if self.violated_rule_ids:
            lines.append(f"**Related Rules:** {', '.join(self.violated_rule_ids)}")
        if self.suggested_resolution:
            lines.append(f"**Suggested Resolution:** {self.suggested_resolution}")
        return "\n".join(lines)


@dataclass
class AmbiguityReport:
    """Complete ambiguity analysis report."""
    ambiguity_score: float               # 0-1, where 0 = no ambiguity, 1 = fully ambiguous
    items: List[AmbiguityItem] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    categories_detected: List[AmbiguityCategory] = field(default_factory=list)
    overall_severity: AmbiguitySeverity = AmbiguitySeverity.LOW

    def is_clear(self) -> bool:
        """Check if story has no significant ambiguities."""
        return self.ambiguity_score < 0.2 and self.overall_severity == AmbiguitySeverity.LOW

    def has_blocking_ambiguities(self) -> bool:
        """Check if any ambiguity is critical (blocks implementation)."""
        return any(item.severity == AmbiguitySeverity.CRITICAL for item in self.items)

    def get_critical_items(self) -> List[AmbiguityItem]:
        """Get all critical severity items."""
        return [item for item in self.items if item.severity == AmbiguitySeverity.CRITICAL]

    def get_high_items(self) -> List[AmbiguityItem]:
        """Get all high severity items."""
        return [item for item in self.items if item.severity == AmbiguitySeverity.HIGH]

    def count_by_category(self) -> Dict[str, int]:
        """Count ambiguities by category."""
        counts: Dict[str, int] = {}
        for item in self.items:
            category_name = item.category.value
            counts[category_name] = counts.get(category_name, 0) + 1
        return counts

    def count_by_severity(self) -> Dict[str, int]:
        """Count ambiguities by severity."""
        counts: Dict[str, int] = {}
        for item in self.items:
            severity_name = item.severity.value
            counts[severity_name] = counts.get(severity_name, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "ambiguity_score": self.ambiguity_score,
            "items": [item.to_dict() for item in self.items],
            "clarification_questions": self.clarification_questions,
            "categories_detected": [cat.value for cat in self.categories_detected],
            "overall_severity": self.overall_severity.value,
            "is_clear": self.is_clear(),
            "has_blocking": self.has_blocking_ambiguities(),
            "count_by_category": self.count_by_category(),
            "count_by_severity": self.count_by_severity(),
        }

    def to_markdown(self) -> str:
        """Format as markdown for output."""
        lines = [
            "# Ambiguity Analysis Report",
            "",
            f"**Ambiguity Score:** {self.ambiguity_score:.2f}",
            f"**Overall Severity:** {self.overall_severity.value.upper()}",
            f"**Total Issues:** {len(self.items)}",
            "",
        ]

        if self.has_blocking_ambiguities():
            lines.append("**WARNING: BLOCKING AMBIGUITIES DETECTED**")
            lines.append("")

        # Summary by severity
        by_severity = self.count_by_severity()
        if by_severity:
            lines.append("## Summary by Severity")
            for severity, count in sorted(by_severity.items(), key=lambda x: -count):
                lines.append(f"- {severity.upper()}: {count}")
            lines.append("")

        # Clarification questions
        if self.clarification_questions:
            lines.append("## Clarification Questions")
            for i, q in enumerate(self.clarification_questions, 1):
                lines.append(f"{i}. {q}")
            lines.append("")

        # Detailed items
        if self.items:
            lines.append("## Detailed Findings")
            for item in self.items:
                lines.append("")
                lines.append(item.to_markdown())

        return "\n".join(lines)

    @classmethod
    def empty(cls) -> "AmbiguityReport":
        """Create an empty report (no ambiguities)."""
        return cls(
            ambiguity_score=0.0,
            items=[],
            clarification_questions=[],
            categories_detected=[],
            overall_severity=AmbiguitySeverity.LOW,
        )
