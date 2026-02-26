"""
Defect Data Model for Deterministic QA Brain v2.0

Structured defect representation for multi-format export.
Supports both violation defects and story quality defects.
Extended with v2.0 fields for defect intelligence.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


# Risk level to Jira priority mapping (deterministic)
PRIORITY_MAP: Dict[str, str] = {
    "CRITICAL": "Highest",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
}

# Severity mapping from rule risk_level (v2.0 deterministic)
SEVERITY_FROM_RISK: Dict[str, str] = {
    "CRITICAL": "Highest",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
}

# Domain to Jira component mapping
COMPONENT_MAP: Dict[str, str] = {
    "b2b": "B2B",
    "payments": "Payments",
    "webapp": "WebApp",
    "admin_panel": "WebApp",
    "trips": "WebApp",
    "programs": "B2B",
    "referrals": "WebApp",
    "gift_cards": "Payments",
    "superapp": "SuperApp",
}


class DefectType(Enum):
    """Types of defects (v2.0)."""
    RULE_VIOLATION = "rule_violation"
    STATE_VIOLATION = "state_violation"
    FINANCIAL_VIOLATION = "financial_violation"
    CROSS_DEP_VIOLATION = "cross_dep_violation"
    AMBIGUITY_DEFECT = "ambiguity_defect"
    COVERAGE_GAP = "coverage_gap"
    MISSING_AC = "missing_ac"
    UNCLEAR_REQUIREMENT = "unclear_requirement"
    INCOMPLETE_STORY = "incomplete_story"


class Reproducibility(Enum):
    """Defect reproducibility levels (v2.0)."""
    ALWAYS = "Always"
    SOMETIMES = "Sometimes"
    RARELY = "Rarely"
    UNABLE = "Unable to reproduce"


@dataclass
class Defect:
    """
    Structured defect for multi-format export.

    Supports both violation defects (rule/state/financial/cross_dep)
    and story quality defects (missing_ac/unclear/incomplete).

    Extended in v2.0 with:
    - title: Short title
    - violated_rule_id: Primary violated rule
    - violated_rule_ids: All violated rules
    - defect_type_enum: DefectType enum
    - impacted_module: Primary affected module
    - reproducibility: Reproducibility level
    - root_cause_hypothesis: Hypothesis for root cause
    - confidence_score: Confidence in defect validity

    Attributes:
        summary: Short business-focused title
        preconditions: Context for reproducing the defect
        description: Detailed description of the issue
        steps_to_reproduce: Numbered steps to reproduce
        expected_results: What should happen
        actual_results: What actually happens (or violation)
        environment: Environment information
        risk_level: Risk level (CRITICAL, HIGH, MEDIUM, LOW)
        component: Derived from detected domain
        defect_type: "violation" or "story_quality" (legacy)
        violation_type: rule, state, financial, cross_dep (for violation defects)
        issue_type: missing_ac, unclear_requirement, incomplete_story (for story defects)
        rule_ids: Referenced rule IDs from validators
    """
    summary: str
    preconditions: str = ""
    description: str = ""
    user_description: str = ""  # User-provided description, preserved exactly
    steps_to_reproduce: List[str] = field(default_factory=list)
    expected_results: str = ""
    actual_results: str = ""
    environment: str = "Yassir Mobility B2B Platform"
    risk_level: str = "MEDIUM"
    component: str = "WebApp"
    defect_type: str = "violation"
    violation_type: Optional[str] = None
    issue_type: Optional[str] = None
    rule_ids: List[str] = field(default_factory=list)
    parent_key: Optional[str] = None  # Parent story key for story defects

    # v2.0 fields
    title: str = ""
    violated_rule_id: str = ""
    violated_rule_ids: List[str] = field(default_factory=list)
    impacted_module: str = ""
    reproducibility: str = "Always"
    root_cause_hypothesis: str = ""
    confidence_score: float = 1.0  # 0-1 confidence in defect validity

    def __post_init__(self):
        """Post-initialization to ensure deterministic mappings and backward compatibility."""
        # Sync title with summary
        if not self.title and self.summary:
            self.title = self.summary
        elif self.title and not self.summary:
            self.summary = self.title

        # Sync violated_rule_ids with rule_ids
        if self.rule_ids and not self.violated_rule_ids:
            self.violated_rule_ids = self.rule_ids.copy()
        elif self.violated_rule_ids and not self.rule_ids:
            self.rule_ids = self.violated_rule_ids.copy()

        # Set primary violated_rule_id
        if not self.violated_rule_id and self.violated_rule_ids:
            self.violated_rule_id = self.violated_rule_ids[0]
        elif not self.violated_rule_id and self.rule_ids:
            self.violated_rule_id = self.rule_ids[0]

        # Set impacted_module from component if not set
        if not self.impacted_module and self.component:
            self.impacted_module = self.component

    def get_severity(self) -> str:
        """Get deterministic severity from risk_level."""
        return SEVERITY_FROM_RISK.get(self.risk_level.upper(), "Medium")

    def get_priority(self) -> str:
        """Get deterministic Jira priority from risk_level."""
        return PRIORITY_MAP.get(self.risk_level.upper(), "Medium")

    def to_jira_description(self) -> str:
        """
        Format as Jira-compatible description.

        Returns:
            Formatted multi-line description for CSV export.
        """
        lines = []

        if self.preconditions:
            lines.append("Preconditions:")
            lines.append(self.preconditions)
            lines.append("")

        if self.description:
            lines.append("Description:")
            lines.append(self.description)
            lines.append("")

        if self.steps_to_reproduce:
            lines.append("Steps to Reproduce:")
            for i, step in enumerate(self.steps_to_reproduce, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if self.expected_results:
            lines.append("Expected Results:")
            lines.append(self.expected_results)
            lines.append("")

        if self.actual_results:
            lines.append("Actual Results:")
            lines.append(self.actual_results)
            lines.append("")

        if self.environment:
            lines.append("Environment:")
            lines.append(self.environment)

        # v2.0: Add rule references
        all_rules = self.violated_rule_ids or self.rule_ids
        if all_rules:
            lines.append("")
            lines.append("Related Rules:")
            for rule_id in all_rules:
                lines.append(f"- {rule_id}")

        # v2.0: Add root cause hypothesis if present
        if self.root_cause_hypothesis:
            lines.append("")
            lines.append("Root Cause Hypothesis:")
            lines.append(self.root_cause_hypothesis)

        # v2.0: Add confidence score
        if self.confidence_score < 1.0:
            lines.append("")
            lines.append(f"Confidence: {self.confidence_score:.0%}")

        return "\n".join(lines)

    def to_story_defect_description(self) -> str:
        """
        Format as Jira-compatible description for story defects.

        Includes user-provided description preserved exactly,
        enriched with RAG context (rule IDs, preconditions, etc.).

        Returns:
            Formatted multi-line description for story defect CSV export.
        """
        lines = []

        # 1. Preconditions (from RAG context)
        if self.preconditions:
            lines.append("Preconditions:")
            lines.append(self.preconditions)
            lines.append("")

        # 2. Defect Description (User Provided) - preserved exactly
        if self.user_description:
            lines.append("Defect Description (User Provided):")
            lines.append(self.user_description)
            lines.append("")

        # 3. Business Rule Reference (from RAG validators)
        all_rules = self.violated_rule_ids or self.rule_ids
        if all_rules:
            lines.append("Business Rule Reference:")
            for rule_id in all_rules:
                lines.append(f"- {rule_id}")
            lines.append("")

        # 4. Steps to Reproduce
        if self.steps_to_reproduce:
            lines.append("Steps to Reproduce:")
            for i, step in enumerate(self.steps_to_reproduce, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        # 5. Expected Results
        if self.expected_results:
            lines.append("Expected Results:")
            lines.append(self.expected_results)
            lines.append("")

        # 6. Actual Results
        if self.actual_results:
            lines.append("Actual Results:")
            lines.append(self.actual_results)
            lines.append("")

        # 7. Environment
        if self.environment:
            lines.append("Environment:")
            lines.append(self.environment)

        # v2.0: Root cause hypothesis
        if self.root_cause_hypothesis:
            lines.append("")
            lines.append("Root Cause Hypothesis:")
            lines.append(self.root_cause_hypothesis)

        return "\n".join(lines)

    def to_story_defect_csv_row(self) -> Dict[str, str]:
        """
        Convert Defect to Jira CSV import row for story defects.

        Uses Issue Type "Story Defect".

        Returns:
            Dictionary with CSV column values matching Jira import format.
        """
        return {
            "Summary": self.title or self.summary,
            "Description": self.to_story_defect_description(),
            "Issue Type": "Story Defect",
            "Priority": self.get_priority(),
            "Components": self._resolve_component(),
            "Labels": "Regression-testing,regression-testing",
            "Sprint": "Defects/Bugs/Imp",
            "Parent": self.parent_key or "",
        }

    def to_csv_row(self) -> Dict[str, str]:
        """
        Convert Defect to Jira CSV import row.

        Returns:
            Dictionary with CSV column values matching Jira import format.
            Headers: Summary, Description, Issue Type, Priority, Components, Labels, Sprint
        """
        return {
            "Summary": self.title or self.summary,
            "Description": self.to_jira_description(),
            "Issue Type": "Defect",
            "Priority": self.get_priority(),
            "Components": self._resolve_component(),
            "Labels": "Regression-testing,regression-testing",
            "Sprint": "Defects/Bugs/Imp",
            "Parent": self.parent_key or "",
        }

    def _resolve_component(self) -> str:
        """
        Resolve Jira component from domain/component field.

        Returns:
            Jira-compatible component name.
        """
        # Try impacted_module first (v2.0), then component
        module = self.impacted_module or self.component
        component_key = module.lower().replace(" ", "_")
        return COMPONENT_MAP.get(component_key, "WebApp")

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization."""
        return {
            "summary": self.summary,
            "title": self.title or self.summary,
            "preconditions": self.preconditions,
            "description": self.description,
            "user_description": self.user_description,
            "steps_to_reproduce": self.steps_to_reproduce,
            "expected_results": self.expected_results,
            "actual_results": self.actual_results,
            "environment": self.environment,
            "risk_level": self.risk_level,
            "severity": self.get_severity(),
            "priority": self.get_priority(),
            "component": self.component,
            "defect_type": self.defect_type,
            "violation_type": self.violation_type,
            "issue_type": self.issue_type,
            "rule_ids": self.rule_ids,
            "parent_key": self.parent_key,
            # v2.0 fields
            "violated_rule_id": self.violated_rule_id,
            "violated_rule_ids": self.violated_rule_ids,
            "impacted_module": self.impacted_module,
            "reproducibility": self.reproducibility,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "confidence_score": self.confidence_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> "Defect":
        """Create Defect from dictionary."""
        return cls(
            summary=data.get("summary", ""),
            preconditions=data.get("preconditions", ""),
            description=data.get("description", ""),
            user_description=data.get("user_description", ""),
            steps_to_reproduce=data.get("steps_to_reproduce", []),
            expected_results=data.get("expected_results", ""),
            actual_results=data.get("actual_results", ""),
            environment=data.get("environment", "Yassir Mobility B2B Platform"),
            risk_level=data.get("risk_level", "MEDIUM"),
            component=data.get("component", "WebApp"),
            defect_type=data.get("defect_type", "violation"),
            violation_type=data.get("violation_type"),
            issue_type=data.get("issue_type"),
            rule_ids=data.get("rule_ids", []),
            parent_key=data.get("parent_key"),
            title=data.get("title", data.get("summary", "")),
            violated_rule_id=data.get("violated_rule_id", ""),
            violated_rule_ids=data.get("violated_rule_ids", []),
            impacted_module=data.get("impacted_module", ""),
            reproducibility=data.get("reproducibility", "Always"),
            root_cause_hypothesis=data.get("root_cause_hypothesis", ""),
            confidence_score=data.get("confidence_score", 1.0),
        )
