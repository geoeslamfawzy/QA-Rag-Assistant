"""
Defect Data Model

Structured defect representation for multi-format export.
Supports both violation defects and story quality defects.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Risk level to Jira priority mapping
PRIORITY_MAP: Dict[str, str] = {
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


@dataclass
class Defect:
    """
    Structured defect for multi-format export.

    Supports both violation defects (rule/state/financial/cross_dep)
    and story quality defects (missing_ac/unclear/incomplete).

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
        defect_type: "violation" or "story_quality"
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

        if self.rule_ids:
            lines.append("")
            lines.append("Related Rules:")
            for rule_id in self.rule_ids:
                lines.append(f"- {rule_id}")

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
        if self.rule_ids:
            lines.append("Business Rule Reference:")
            for rule_id in self.rule_ids:
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

        return "\n".join(lines)

    def to_story_defect_csv_row(self) -> Dict[str, str]:
        """
        Convert Defect to Jira CSV import row for story defects.

        Uses Issue Type "Story Defect".

        Returns:
            Dictionary with CSV column values matching Jira import format.
        """
        return {
            "Summary": self.summary,
            "Description": self.to_story_defect_description(),
            "Issue Type": "Story Defect",
            "Priority": PRIORITY_MAP.get(self.risk_level.upper(), "Medium"),
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
            "Summary": self.summary,
            "Description": self.to_jira_description(),
            "Issue Type": "Defect",
            "Priority": PRIORITY_MAP.get(self.risk_level.upper(), "Medium"),
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
        component_key = self.component.lower().replace(" ", "_")
        return COMPONENT_MAP.get(component_key, "WebApp")
