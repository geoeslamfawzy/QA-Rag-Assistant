"""
Test Case Service Module

Orchestrates the test case generation workflow: fetch → RAG → build → export.
Generates both CSV (Jira-ready) and Markdown output formats.
"""
from pathlib import Path
from typing import Optional, Dict, Any, List

from jira_client import JiraClient
from tc_builder import TestCaseBuilder, generate_test_cases
from services.output_writer import OutputWriter
from services.rag_context_builder import RAGContextBuilder
from exporters import CSVExporter, MarkdownExporter
from models.test_case import TestCase


class TestCaseService:
    """
    Coordinates Jira fetch, RAG context, test case building, and export.

    Workflow:
    1. Fetch Jira issue
    2. Build RAG context (for risk level)
    3. Build structured TestCase objects
    4. Export to CSV (Jira-ready) and Markdown
    """

    def __init__(
        self,
        client: JiraClient,
        writer: OutputWriter,
        rag_builder: Optional[RAGContextBuilder] = None,
    ):
        """
        Initialize the Test Case Service.

        Args:
            client: JiraClient for fetching issues.
            writer: OutputWriter (kept for backward compatibility).
            rag_builder: Optional RAGContextBuilder for risk level detection.
        """
        self._client = client
        self._writer = writer
        self._rag_builder = rag_builder
        self._tc_builder = TestCaseBuilder()
        self._csv_exporter = CSVExporter()
        self._md_exporter = MarkdownExporter()

    def generate(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Generate test cases for a Jira issue.

        Fetches the issue, determines risk level via RAG, builds test cases,
        and exports to both CSV and Markdown formats.

        Args:
            issue_key: Jira issue key (e.g., CMB-32860).

        Returns:
            Dictionary with issue, test_cases, csv_path, md_path, or None if not found.
        """
        # Step 1: Fetch Jira issue
        issue = self._client.get_issue(issue_key)
        if not issue:
            return None

        # Step 2: Get risk level from RAG context (if available)
        risk_level = "MEDIUM"  # Default
        if self._rag_builder:
            try:
                rag_context = self._rag_builder.build(issue_key)
                if rag_context and rag_context.pre_analysis:
                    risk_level = rag_context.pre_analysis.risk_level.upper()
            except Exception:
                # If RAG fails, continue with default risk level
                pass

        # Step 3: Build test cases
        test_cases = self._tc_builder.build(issue, risk_level)

        # Step 4: Export to both formats
        csv_path = self._csv_exporter.export(test_cases, issue_key)
        md_path = self._md_exporter.export(
            test_cases,
            issue_key,
            issue.get("summary", "")
        )

        return {
            "issue": issue,
            "test_cases": test_cases,
            "csv_path": csv_path,
            "md_path": md_path,
            "risk_level": risk_level,
        }

    def generate_legacy(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Legacy method for backward compatibility.

        Uses the original markdown-only generation.

        Args:
            issue_key: Jira issue key.

        Returns:
            Dictionary with issue and saved_path, or None if not found.
        """
        issue = self._client.get_issue(issue_key)
        if not issue:
            return None

        markdown = generate_test_cases(issue)
        saved_path = self._writer.write_test_cases(issue_key, markdown)

        return {"issue": issue, "saved_path": saved_path}
