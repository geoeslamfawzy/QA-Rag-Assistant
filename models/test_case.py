"""
Test Case Data Model for Deterministic QA Brain v2.0

Structured test case representation for multi-format export.
Extended with v2.0 fields for risk-based test design.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# Deterministic priority mapping from risk level
PRIORITY_FROM_RISK: Dict[str, str] = {
    "CRITICAL": "P0",
    "HIGH": "P1",
    "MEDIUM": "P2",
    "LOW": "P3",
}


@dataclass
class TestCase:
    """
    Structured test case for multi-format export.

    Extended in v2.0 with:
    - title: Distinct title field
    - test_data: Structured test data
    - expected_result: Alias for expected
    - priority: Deterministic from risk_level
    - linked_rule_id: Primary linked rule
    - linked_rule_ids: All linked rules

    Attributes:
        id: Test case identifier (e.g., TC-01, TC-02)
        title: Test case title (v2.0)
        summary: Test case title/summary (backward compatibility)
        preconditions: List of precondition statements
        steps: BDD steps (Given/When/Then format)
        test_data: Structured test data (v2.0)
        expected: Expected results (original field)
        expected_result: Expected results (v2.0 alias)
        test_type: Type of test (Positive, Negative, Edge, Security)
        priority: Test priority P0-P3 (v2.0, deterministic from risk_level)
        risk_level: Risk level for priority mapping (CRITICAL, HIGH, MEDIUM, LOW)
        linked_rule_id: Primary rule that generated this test (v2.0)
        linked_rule_ids: All rules linked to this test (v2.0)
    """
    id: str
    summary: str
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    expected: List[str] = field(default_factory=list)
    test_type: str = "Positive"
    risk_level: str = "MEDIUM"

    # v2.0 fields
    title: str = ""
    test_data: Dict[str, Any] = field(default_factory=dict)
    expected_result: List[str] = field(default_factory=list)
    priority: str = ""
    linked_rule_id: str = ""
    linked_rule_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Post-initialization to ensure deterministic mappings."""
        # Sync title with summary for backward compatibility
        if not self.title and self.summary:
            self.title = self.summary
        elif self.title and not self.summary:
            self.summary = self.title

        # Sync expected and expected_result
        if self.expected and not self.expected_result:
            self.expected_result = self.expected.copy()
        elif self.expected_result and not self.expected:
            self.expected = self.expected_result.copy()

        # Deterministic priority assignment from risk_level
        if not self.priority:
            self.priority = PRIORITY_FROM_RISK.get(self.risk_level.upper(), "P2")

    def get_priority(self) -> str:
        """Get deterministic priority from risk_level."""
        return PRIORITY_FROM_RISK.get(self.risk_level.upper(), "P2")

    def to_bdd_description(self) -> str:
        """
        Format as BDD description for Jira.

        Returns:
            Formatted string with preconditions and BDD steps.
        """
        lines = []

        # Add preconditions section
        if self.preconditions:
            lines.append("Preconditions:")
            for p in self.preconditions:
                lines.append(f"- {p}")
            lines.append("")

        # Add BDD steps
        for step in self.steps:
            lines.append(step)

        # Add expected results if present
        expected = self.expected_result or self.expected
        if expected:
            lines.append("")
            lines.append("Expected:")
            for exp in expected:
                lines.append(f"- {exp}")

        return "\n".join(lines)

    def to_markdown_row(self) -> str:
        """
        Format as markdown table row.

        Returns:
            Pipe-separated markdown table row.
        """
        precond = "; ".join(self.preconditions) if self.preconditions else "-"
        steps_str = "<br>".join(self.steps) if self.steps else "-"
        expected = self.expected_result or self.expected
        expected_str = "; ".join(expected) if expected else "Behaviour matches acceptance criteria."

        # Escape pipe characters
        precond = precond.replace("|", "\\|")[:200]
        steps_str = steps_str.replace("|", "\\|")[:500]
        expected_str = expected_str.replace("|", "\\|")[:200]
        title = (self.title or self.summary).replace("|", "\\|")[:100]

        # Use stored or calculated priority
        priority = self.priority or self.get_priority()

        return f"| {self.id} | {title} | {precond} | {steps_str} | - | {expected_str} | {self.test_type} | {priority} |"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title or self.summary,
            "summary": self.summary,
            "preconditions": self.preconditions,
            "steps": self.steps,
            "test_data": self.test_data,
            "expected": self.expected,
            "expected_result": self.expected_result or self.expected,
            "test_type": self.test_type,
            "priority": self.priority or self.get_priority(),
            "risk_level": self.risk_level,
            "linked_rule_id": self.linked_rule_id,
            "linked_rule_ids": self.linked_rule_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        """Create TestCase from dictionary."""
        return cls(
            id=data.get("id", ""),
            summary=data.get("summary", data.get("title", "")),
            preconditions=data.get("preconditions", []),
            steps=data.get("steps", []),
            expected=data.get("expected", data.get("expected_result", [])),
            test_type=data.get("test_type", "Positive"),
            risk_level=data.get("risk_level", "MEDIUM"),
            title=data.get("title", data.get("summary", "")),
            test_data=data.get("test_data", {}),
            expected_result=data.get("expected_result", data.get("expected", [])),
            priority=data.get("priority", ""),
            linked_rule_id=data.get("linked_rule_id", ""),
            linked_rule_ids=data.get("linked_rule_ids", []),
        )
