"""
CSV Exporter for Jira Import

Exports test cases to Jira-compatible CSV format with fixed business rules.
"""
import csv
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.test_case import TestCase


class CSVExporter:
    """
    Exports test cases to Jira-compatible CSV format.

    Fixed Business Rules:
    - Issue Type: "Test"
    - Squad: "B2B"
    - Components: "SuperApp"
    - Priority: Derived from risk level
    """

    # Fixed Jira field values
    ISSUE_TYPE = "Test"
    SQUAD = "B2B"
    COMPONENTS = "SuperApp"

    # Risk level to Jira priority mapping
    PRIORITY_MAP = {
        "CRITICAL": "Critical",
        "HIGH": "High",
        "MEDIUM": "Medium",
        "LOW": "Low",
    }

    # CSV headers matching Jira import format
    HEADERS = ["Summary", "Description", "Issue Type", "Priority", "Squad", "Components"]

    def __init__(self, output_dir: Path = None):
        """
        Initialize the CSV exporter.

        Args:
            output_dir: Output directory for CSV files. Defaults to output/test-cases/
        """
        self._output_dir = output_dir or Path("output/test-cases")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, test_cases: List[TestCase], issue_key: str) -> Path:
        """
        Export test cases to a Jira-compatible CSV file.

        Args:
            test_cases: List of TestCase objects to export.
            issue_key: Jira issue key (used for filename).

        Returns:
            Path to the generated CSV file.
        """
        output_path = self._output_dir / f"{issue_key}.csv"

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.HEADERS,
                quoting=csv.QUOTE_ALL
            )
            writer.writeheader()

            for tc in test_cases:
                writer.writerow(self._test_case_to_row(tc))

        return output_path

    def _test_case_to_row(self, tc: TestCase) -> dict:
        """
        Convert a TestCase to a CSV row dictionary.

        Args:
            tc: TestCase object to convert.

        Returns:
            Dictionary with CSV column values.
        """
        return {
            "Summary": tc.summary,
            "Description": tc.to_bdd_description(),
            "Issue Type": self.ISSUE_TYPE,
            "Priority": self.PRIORITY_MAP.get(tc.risk_level.upper(), "Medium"),
            "Squad": self.SQUAD,
            "Components": self.COMPONENTS,
        }
