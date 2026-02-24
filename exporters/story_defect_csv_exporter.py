"""
Story Defect CSV Exporter for Jira Import

Exports story defects to Jira-compatible CSV format with Bug issue type.
Separate from DefectCSVExporter to handle story-specific requirements.
"""
import csv
from pathlib import Path
from typing import List, Optional

from models.defect import Defect


class StoryDefectCSVExporter:
    """
    Exports story defects to Jira-compatible CSV format.

    Fixed Business Rules:
    - Issue Type: "Bug" (NOT "Defect")
    - Labels: "Regression-testing,regression-testing"
    - Sprint: "Defects/Bugs/Imp"
    - Parent: Set to parent story key
    - Priority: Mapped from risk level (Highest, High, Medium, Low)
    """

    # Fixed Jira field values for story defects
    ISSUE_TYPE = "Story Defect"
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
        "Parent",
    ]

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the Story Defect CSV exporter.

        Args:
            output_dir: Output directory for CSV files. Defaults to output/story-defects/
        """
        self._output_dir = output_dir or Path("output/story-defects")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, defect: Defect, parent_key: str) -> Path:
        """
        Export a story defect to a Jira-compatible CSV file.

        Args:
            defect: Defect object to export.
            parent_key: Parent story key (e.g., CMB-35293).

        Returns:
            Path to the generated CSV file.
        """
        # Filename: <PARENT_KEY>-defect.csv
        output_path = self._output_dir / f"{parent_key}-defect.csv"

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.HEADERS,
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
            writer.writerow(self._defect_to_row(defect, parent_key))

        return output_path

    def export_multiple(self, defects: List[Defect], parent_key: str) -> Path:
        """
        Export multiple story defects to a single CSV file.

        Args:
            defects: List of Defect objects to export.
            parent_key: Parent story key.

        Returns:
            Path to the generated CSV file.
        """
        output_path = self._output_dir / f"{parent_key}-defect.csv"

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.HEADERS,
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()

            for defect in defects:
                writer.writerow(self._defect_to_row(defect, parent_key))

        return output_path

    def _defect_to_row(self, defect: Defect, parent_key: str) -> dict:
        """
        Convert a Defect to a CSV row dictionary.

        Uses Defect.to_story_defect_csv_row() and ensures fixed business rules.

        Args:
            defect: Defect object to convert.
            parent_key: Parent story key.

        Returns:
            Dictionary with CSV column values.
        """
        row = defect.to_story_defect_csv_row()

        # Ensure fixed values are applied (override any defaults)
        row["Issue Type"] = self.ISSUE_TYPE
        row["Labels"] = self.LABELS
        row["Sprint"] = self.SPRINT
        row["Parent"] = parent_key

        return row
