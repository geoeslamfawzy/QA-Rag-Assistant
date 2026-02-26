"""
Enhanced Rule Model for Deterministic QA Brain

This module defines the core Rule dataclass with full dependency tracking,
lifecycle state awareness, and risk classification for deterministic reasoning.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class RiskLevel(Enum):
    """Risk level classification for rules."""
    CRITICAL = "critical"  # Must be covered, blocks generation if missing
    HIGH = "high"          # Should be covered, lowers confidence if missing
    MEDIUM = "medium"      # Good to have, minor impact if missing
    LOW = "low"            # Optional, no impact if missing

    @classmethod
    def from_string(cls, value: str) -> "RiskLevel":
        """Parse risk level from string (case-insensitive)."""
        value_lower = value.lower().strip()
        for level in cls:
            if level.value == value_lower:
                return level
        # Default mappings for common variations
        if value_lower in ["crit", "blocker", "p0"]:
            return cls.CRITICAL
        if value_lower in ["important", "major", "p1"]:
            return cls.HIGH
        if value_lower in ["moderate", "normal", "p2"]:
            return cls.MEDIUM
        if value_lower in ["minor", "trivial", "p3", "p4"]:
            return cls.LOW
        return cls.MEDIUM  # Default

    def __lt__(self, other: "RiskLevel") -> bool:
        """Compare risk levels for sorting (CRITICAL > HIGH > MEDIUM > LOW)."""
        order = {
            RiskLevel.CRITICAL: 4,
            RiskLevel.HIGH: 3,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 1
        }
        return order[self] < order[other]

    def __le__(self, other: "RiskLevel") -> bool:
        return self == other or self < other

    def __gt__(self, other: "RiskLevel") -> bool:
        return not self <= other

    def __ge__(self, other: "RiskLevel") -> bool:
        return not self < other


@dataclass
class Rule:
    """
    Enhanced rule model with full dependency and lifecycle tracking.

    This is the foundation of the Deterministic QA Brain, enabling:
    - Transitive dependency resolution
    - Cross-domain impact analysis
    - Lifecycle state awareness
    - Strict risk-based coverage requirements

    Attributes:
        rule_id: Unique identifier (e.g., FIN-REF-012, RULE-ENT-001, DEP-EP-007)
        domain: Business domain (e.g., referrals, enterprises, payments)
        module: Knowledge base module type (e.g., financial_logic, atomic_rule)
        risk_level: Risk classification affecting coverage requirements
        lifecycle_states: States where this rule applies (empty = all states)
        depends_on: Rule IDs this rule depends on (for transitive expansion)
        impacts: Modules/entities affected when this rule triggers
        description: Human-readable rule description
        condition: When the rule applies
        validation: What the rule validates/enforces
        error_message: Error message when rule is violated
        keywords: Keywords for rule matching
        source_file: Source file in knowledge base
        source_chunk_id: Chunk ID for traceability
    """

    # Core identification
    rule_id: str
    domain: str = ""
    module: str = ""

    # Risk classification
    risk_level: RiskLevel = RiskLevel.MEDIUM

    # State applicability (empty list = applies to all states)
    lifecycle_states: List[str] = field(default_factory=list)

    # Dependency chain
    depends_on: List[str] = field(default_factory=list)
    impacts: List[str] = field(default_factory=list)

    # Rule content
    description: str = ""
    condition: str = ""
    validation: str = ""
    error_message: str = ""

    # Matching
    keywords: List[str] = field(default_factory=list)

    # Source tracking
    source_file: str = ""
    source_chunk_id: str = ""

    def is_critical(self) -> bool:
        """Check if rule is critical risk level (must be covered)."""
        return self.risk_level == RiskLevel.CRITICAL

    def is_high_risk(self) -> bool:
        """Check if rule is high risk or critical."""
        return self.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]

    def applies_to_state(self, state: str) -> bool:
        """
        Check if rule applies to given lifecycle state.

        Args:
            state: The state to check (case-insensitive)

        Returns:
            True if rule applies to state, False otherwise.
            If lifecycle_states is empty, rule applies to all states.
        """
        if not self.lifecycle_states:
            return True  # No state restriction = applies to all
        state_upper = state.upper().strip()
        return state_upper in [s.upper().strip() for s in self.lifecycle_states]

    def applies_to_any_state(self, states: List[str]) -> bool:
        """
        Check if rule applies to any of the given states.

        Args:
            states: List of states to check

        Returns:
            True if rule applies to at least one of the states
        """
        if not self.lifecycle_states:
            return True  # No state restriction
        if not states:
            return True  # No states specified = don't filter
        return any(self.applies_to_state(s) for s in states)

    def has_dependencies(self) -> bool:
        """Check if rule has any dependencies."""
        return len(self.depends_on) > 0

    def has_impacts(self) -> bool:
        """Check if rule has any documented impacts."""
        return len(self.impacts) > 0

    def matches_keywords(self, text: str, min_matches: int = 1) -> bool:
        """
        Check if rule keywords match in text.

        Args:
            text: Text to search in
            min_matches: Minimum keyword matches required

        Returns:
            True if at least min_matches keywords found in text
        """
        if not self.keywords:
            return False
        text_lower = text.lower()
        match_count = sum(1 for kw in self.keywords if kw.lower() in text_lower)
        return match_count >= min_matches

    def get_semantics(self) -> str:
        """
        Get rule semantics for output generation.

        Returns a formatted string containing the rule's semantic content
        for inclusion in deterministic output.
        """
        parts = []
        if self.description:
            parts.append(f"**{self.rule_id}**: {self.description}")
        if self.condition:
            parts.append(f"  - Condition: {self.condition}")
        if self.validation:
            parts.append(f"  - Validation: {self.validation}")
        if self.error_message:
            parts.append(f"  - Error: {self.error_message}")
        if self.impacts:
            parts.append(f"  - Impacts: {', '.join(self.impacts)}")
        return "\n".join(parts) if parts else f"**{self.rule_id}**"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rule_id": self.rule_id,
            "domain": self.domain,
            "module": self.module,
            "risk_level": self.risk_level.value,
            "lifecycle_states": self.lifecycle_states,
            "depends_on": self.depends_on,
            "impacts": self.impacts,
            "description": self.description,
            "condition": self.condition,
            "validation": self.validation,
            "error_message": self.error_message,
            "keywords": self.keywords,
            "source_file": self.source_file,
            "source_chunk_id": self.source_chunk_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """Create Rule from dictionary."""
        risk_level = data.get("risk_level", "medium")
        if isinstance(risk_level, str):
            risk_level = RiskLevel.from_string(risk_level)
        elif isinstance(risk_level, RiskLevel):
            pass
        else:
            risk_level = RiskLevel.MEDIUM

        return cls(
            rule_id=data.get("rule_id", ""),
            domain=data.get("domain", ""),
            module=data.get("module", ""),
            risk_level=risk_level,
            lifecycle_states=data.get("lifecycle_states", []),
            depends_on=data.get("depends_on", []),
            impacts=data.get("impacts", []),
            description=data.get("description", ""),
            condition=data.get("condition", ""),
            validation=data.get("validation", ""),
            error_message=data.get("error_message", ""),
            keywords=data.get("keywords", []),
            source_file=data.get("source_file", ""),
            source_chunk_id=data.get("source_chunk_id", ""),
        )

    def __hash__(self) -> int:
        """Hash by rule_id for set/dict usage."""
        return hash(self.rule_id)

    def __eq__(self, other: object) -> bool:
        """Equality by rule_id."""
        if not isinstance(other, Rule):
            return False
        return self.rule_id == other.rule_id

    def __repr__(self) -> str:
        return f"Rule(id={self.rule_id}, risk={self.risk_level.value}, deps={len(self.depends_on)})"
