"""
Defect CSV Exporter for Jira Import

Exports defects to Jira-compatible CSV format with fixed business rules.
"""
import csv
from pathlib import Path
from typing import List, Optional

from models.defect import Defect


class DefectCSVExporter:
    """
    Exports defects to Jira-compatible CSV format.

    Fixed Business Rules:
    - Issue Type: "Bug"
    - Labels: "Regression-testing,regression-testing"
    - Sprint: "Defects/Bugs/Imp"
    - Priority: Mapped from risk level (Highest, High, Medium, Low)
    - Components: Derived from domain
    """

    # Fixed Jira field values
    ISSUE_TYPE = "Defect"
    LABELS = "Regression-testing,regression-testing"
    SPRINT = "Defects/Bugs/Imp"

    # CSV headers matching Jira import format
    HEADERS = [
        "Summary",
        "Description",
        "Issue Type",
        "Priority",
        "Components",
        "Labels",
        "Sprint",
    ]

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the Defect CSV exporter.

        Args:
            output_dir: Output directory for CSV files. Defaults to output/defects/
        """
        self._output_dir = output_dir or Path("output/defects")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, defect: Defect, issue_key: str) -> Path:
        """
        Export a single defect to a Jira-compatible CSV file.

        Args:
            defect: Defect object to export.
            issue_key: Jira issue key (used for filename).

        Returns:
            Path to the generated CSV file.
        """
        output_path = self._output_dir / f"{issue_key}.csv"

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.HEADERS,
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
            writer.writerow(self._defect_to_row(defect))

        return output_path

    def export_multiple(self, defects: List[Defect], issue_key: str) -> Path:
        """
        Export multiple defects to a single Jira-compatible CSV file.

        Args:
            defects: List of Defect objects to export.
            issue_key: Jira issue key (used for filename).

        Returns:
            Path to the generated CSV file.
        """
        output_path = self._output_dir / f"{issue_key}.csv"

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.HEADERS,
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()

            for defect in defects:
                writer.writerow(self._defect_to_row(defect))

        return output_path

    def _defect_to_row(self, defect: Defect) -> dict:
        """
        Convert a Defect to a CSV row dictionary.

        Uses Defect.to_csv_row() and ensures fixed business rules are applied.

        Args:
            defect: Defect object to convert.

        Returns:
            Dictionary with CSV column values.
        """
        row = defect.to_csv_row()

        # Ensure fixed values are applied (override any defaults)
        row["Issue Type"] = self.ISSUE_TYPE
        row["Labels"] = self.LABELS
        row["Sprint"] = self.SPRINT

        return row
