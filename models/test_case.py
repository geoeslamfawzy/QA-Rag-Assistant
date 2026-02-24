"""
Test Case Data Model

Structured test case representation for multi-format export.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class TestCase:
    """
    Structured test case for multi-format export.

    Attributes:
        id: Test case identifier (e.g., TC-01, TC-02)
        summary: Test case title/summary
        preconditions: List of precondition statements
        steps: BDD steps (Given/When/Then format)
        expected: Expected results
        test_type: Type of test (Positive, Negative, Edge, Security)
        risk_level: Risk level for priority mapping (CRITICAL, HIGH, MEDIUM, LOW)
    """
    id: str
    summary: str
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    expected: List[str] = field(default_factory=list)
    test_type: str = "Positive"
    risk_level: str = "MEDIUM"

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
        if self.expected:
            lines.append("")
            lines.append("Expected:")
            for exp in self.expected:
                lines.append(f"- {exp}")

        return "\n".join(lines)

    def to_markdown_row(self) -> str:
        """
        Format as markdown table row.

        Returns:
            Pipe-separated markdown table row.
        """
        precond = "; ".join(self.preconditions) if self.preconditions else "—"
        steps_str = "<br>".join(self.steps) if self.steps else "—"
        expected_str = "; ".join(self.expected) if self.expected else "Behaviour matches acceptance criteria."

        # Escape pipe characters
        precond = precond.replace("|", "\\|")[:200]
        steps_str = steps_str.replace("|", "\\|")[:500]
        expected_str = expected_str.replace("|", "\\|")[:200]
        summary = self.summary.replace("|", "\\|")[:100]

        # Priority mapping
        priority_map = {
            "CRITICAL": "P0",
            "HIGH": "P1",
            "MEDIUM": "P2",
            "LOW": "P3",
        }
        priority = priority_map.get(self.risk_level.upper(), "P2")

        return f"| {self.id} | {summary} | {precond} | {steps_str} | — | {expected_str} | {self.test_type} | {priority} |"
