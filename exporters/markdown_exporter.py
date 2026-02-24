"""
Markdown Exporter for Test Cases

Exports test cases to markdown table format.
"""
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.test_case import TestCase


class MarkdownExporter:
    """
    Exports test cases to markdown table format.

    Output format matches the existing test-suite markdown structure.
    """

    def __init__(self, output_dir: Path = None):
        """
        Initialize the Markdown exporter.

        Args:
            output_dir: Output directory for markdown files. Defaults to output/test-suite/
        """
        self._output_dir = output_dir or Path("output/test-suite")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, test_cases: List[TestCase], issue_key: str, title: str = "") -> Path:
        """
        Export test cases to a markdown file.

        Args:
            test_cases: List of TestCase objects to export.
            issue_key: Jira issue key (used for filename).
            title: Story title for header.

        Returns:
            Path to the generated markdown file.
        """
        output_path = self._output_dir / f"test-cases-{issue_key}.md"

        # Build header
        escaped_title = self._escape_cell(title) if title else "Untitled"
        header = f"# Test Cases – {issue_key}\n**{escaped_title}**\n\n---\n\n"

        # Build table header
        table_header = (
            "| TC ID | Title | Precondition | Steps (BDD) | Test Data | "
            "Expected Result | Type | Priority |\n"
            "|-------|--------|--------------|-------------|-----------|"
            "-----------------|------|----------|\n"
        )

        # Build table rows
        rows = []
        for tc in test_cases:
            rows.append(tc.to_markdown_row())

        table_rows = "\n".join(rows)

        # Build summary
        type_counts = self._count_types(test_cases)
        types_str = ", ".join(type_counts.keys()) if type_counts else "N/A"
        summary = (
            f"\n\n---\n\n"
            f"**Summary**\n"
            f"- **Total test cases:** {len(test_cases)}\n"
            f"- **Types:** {types_str}\n"
            f"- **Priorities:** P0, P1, P2, P3\n"
        )

        # Write to file
        content = header + table_header + table_rows + summary
        output_path.write_text(content, encoding="utf-8")

        return output_path

    def _escape_cell(self, s: str) -> str:
        """Escape pipe and newlines for markdown table."""
        if not s:
            return "—"
        return s.replace("|", "\\|").replace("\n", " ").strip()[:500]

    def _count_types(self, test_cases: List[TestCase]) -> dict:
        """Count test cases by type."""
        counts = {}
        for tc in test_cases:
            if tc.test_type not in counts:
                counts[tc.test_type] = 0
            counts[tc.test_type] += 1
        return counts
