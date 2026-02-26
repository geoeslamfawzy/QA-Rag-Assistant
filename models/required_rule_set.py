"""
Required Rule Set Model for Deterministic QA Brain

Represents the complete set of rules required for a story analysis,
categorized by how they were determined to be required.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Set
from enum import Enum

from .rule import Rule, RiskLevel


class RuleCategory(Enum):
    """
    Category indicating why a rule is required.

    Used for traceability in deterministic reasoning.
    """
    DIRECT = "direct"              # Directly matched from story content
    DEPENDENCY = "dependency"      # Required by a direct rule (transitive)
    CROSS_MODULE = "cross_module"  # Required for cross-module operations
    STATE = "state"                # Required for detected lifecycle states
    KEYWORD = "keyword"            # Forced by KEYWORD_RULE_MAPPING


@dataclass
class CategorizedRule:
    """
    A rule with its category and reason for inclusion.

    Provides traceability for why each rule is required.
    """
    rule: Rule
    category: RuleCategory
    reason: str  # Human-readable reason for inclusion

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule.rule_id,
            "category": self.category.value,
            "reason": self.reason,
            "risk_level": self.rule.risk_level.value,
            "rule": self.rule.to_dict(),
        }

    def __hash__(self) -> int:
        """Hash by rule_id and category."""
        return hash((self.rule.rule_id, self.category))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CategorizedRule):
            return False
        return self.rule.rule_id == other.rule.rule_id and self.category == other.category


@dataclass
class RequiredRuleSet:
    """
    Complete set of rules required for a story analysis.

    Organizes rules by category for traceability and provides
    convenient accessors for coverage validation.

    Attributes:
        direct_rules: Rules directly matched from story content
        dependency_rules: Rules required by direct rules (transitive deps)
        cross_module_rules: Rules for cross-module operations
        state_rules: Rules applicable to detected lifecycle states
        keyword_rules: Rules forced by KEYWORD_RULE_MAPPING

        story_key: Jira story key this set is for
        detected_domains: Domains detected in the story
        detected_intents: Intents detected in the story
        detected_states: Lifecycle states detected in the story
    """

    # Categorized rules
    direct_rules: List[CategorizedRule] = field(default_factory=list)
    dependency_rules: List[CategorizedRule] = field(default_factory=list)
    cross_module_rules: List[CategorizedRule] = field(default_factory=list)
    state_rules: List[CategorizedRule] = field(default_factory=list)
    keyword_rules: List[CategorizedRule] = field(default_factory=list)

    # Context metadata
    story_key: str = ""
    detected_domains: List[str] = field(default_factory=list)
    detected_intents: List[str] = field(default_factory=list)
    detected_states: List[str] = field(default_factory=list)

    @property
    def all_rules(self) -> List[CategorizedRule]:
        """Get all required rules (deduplicated by rule_id)."""
        seen_ids: Set[str] = set()
        result: List[CategorizedRule] = []

        # Process in priority order: keyword, direct, dependency, cross_module, state
        for cat_rule in (
            self.keyword_rules +
            self.direct_rules +
            self.dependency_rules +
            self.cross_module_rules +
            self.state_rules
        ):
            if cat_rule.rule.rule_id not in seen_ids:
                result.append(cat_rule)
                seen_ids.add(cat_rule.rule.rule_id)

        return result

    @property
    def all_rule_ids(self) -> Set[str]:
        """Get all required rule IDs."""
        return {cr.rule.rule_id for cr in self.all_rules}

    @property
    def critical_rules(self) -> List[CategorizedRule]:
        """Get critical-risk rules only."""
        return [
            cr for cr in self.all_rules
            if cr.rule.risk_level == RiskLevel.CRITICAL
        ]

    @property
    def critical_rule_ids(self) -> Set[str]:
        """Get critical rule IDs."""
        return {cr.rule.rule_id for cr in self.critical_rules}

    @property
    def high_risk_rules(self) -> List[CategorizedRule]:
        """Get high or critical risk rules."""
        return [
            cr for cr in self.all_rules
            if cr.rule.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        ]

    @property
    def high_risk_rule_ids(self) -> Set[str]:
        """Get high-risk rule IDs."""
        return {cr.rule.rule_id for cr in self.high_risk_rules}

    def get_rules_by_category(self, category: RuleCategory) -> List[CategorizedRule]:
        """Get rules by category."""
        category_map = {
            RuleCategory.DIRECT: self.direct_rules,
            RuleCategory.DEPENDENCY: self.dependency_rules,
            RuleCategory.CROSS_MODULE: self.cross_module_rules,
            RuleCategory.STATE: self.state_rules,
            RuleCategory.KEYWORD: self.keyword_rules,
        }
        return category_map.get(category, [])

    def get_rules_by_domain(self, domain: str) -> List[CategorizedRule]:
        """Get rules for a specific domain."""
        return [
            cr for cr in self.all_rules
            if cr.rule.domain.lower() == domain.lower()
        ]

    def get_rules_by_module(self, module: str) -> List[CategorizedRule]:
        """Get rules from a specific module."""
        return [
            cr for cr in self.all_rules
            if cr.rule.module.lower() == module.lower()
        ]

    def get_impacted_modules(self) -> Set[str]:
        """Get all modules impacted by the rules."""
        modules: Set[str] = set()
        for cr in self.all_rules:
            modules.update(cr.rule.impacts)
            if cr.rule.module:
                modules.add(cr.rule.module)
        return modules

    def count_by_category(self) -> Dict[str, int]:
        """Count rules by category."""
        return {
            "direct": len(self.direct_rules),
            "dependency": len(self.dependency_rules),
            "cross_module": len(self.cross_module_rules),
            "state": len(self.state_rules),
            "keyword": len(self.keyword_rules),
            "total": len(self.all_rules),
        }

    def count_by_risk(self) -> Dict[str, int]:
        """Count rules by risk level."""
        counts: Dict[str, int] = {level.value: 0 for level in RiskLevel}
        for cr in self.all_rules:
            counts[cr.rule.risk_level.value] += 1
        return counts

    def is_empty(self) -> bool:
        """Check if no rules are required."""
        return len(self.all_rules) == 0

    def has_critical_rules(self) -> bool:
        """Check if there are any critical rules."""
        return len(self.critical_rules) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Export for debugging/serialization."""
        return {
            "story_key": self.story_key,
            "detected_domains": self.detected_domains,
            "detected_intents": self.detected_intents,
            "detected_states": self.detected_states,
            "counts": {
                "by_category": self.count_by_category(),
                "by_risk": self.count_by_risk(),
            },
            "rules": {
                "direct": [cr.to_dict() for cr in self.direct_rules],
                "dependency": [cr.to_dict() for cr in self.dependency_rules],
                "cross_module": [cr.to_dict() for cr in self.cross_module_rules],
                "state": [cr.to_dict() for cr in self.state_rules],
                "keyword": [cr.to_dict() for cr in self.keyword_rules],
            },
            "all_rule_ids": list(self.all_rule_ids),
            "critical_rule_ids": list(self.critical_rule_ids),
            "high_risk_rule_ids": list(self.high_risk_rule_ids),
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Required Rule Set for {self.story_key or 'Unknown Story'}",
            f"  Domains: {', '.join(self.detected_domains) or 'None'}",
            f"  Intents: {', '.join(self.detected_intents) or 'None'}",
            f"  States: {', '.join(self.detected_states) or 'None'}",
            "",
            "Rule Counts:",
        ]

        counts = self.count_by_category()
        for cat, count in counts.items():
            if cat != "total":
                lines.append(f"  {cat}: {count}")
        lines.append(f"  TOTAL: {counts['total']}")

        risk_counts = self.count_by_risk()
        lines.append("")
        lines.append("By Risk Level:")
        for level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            count = risk_counts.get(level.value, 0)
            if count > 0:
                lines.append(f"  {level.value.upper()}: {count}")

        if self.critical_rules:
            lines.append("")
            lines.append("Critical Rules (MUST be covered):")
            for cr in self.critical_rules:
                lines.append(f"  - {cr.rule.rule_id}: {cr.reason}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        counts = self.count_by_category()
        return (
            f"RequiredRuleSet(story={self.story_key}, "
            f"total={counts['total']}, critical={len(self.critical_rules)})"
        )
