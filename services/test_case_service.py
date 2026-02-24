"""
Test Case Service Module

Orchestrates the test case generation workflow: fetch → generate → write.
Receives all dependencies via constructor (Dependency Inversion Principle).
"""
from pathlib import Path
from typing import Optional, Dict, Any

from jira_client import JiraClient
from tc_generator import generate_test_cases
from services.output_writer import OutputWriter


class TestCaseService:
    """
    Coordinates JiraClient, generate_test_cases, and OutputWriter
    so that CLI handlers contain no orchestration logic.
    """

    def __init__(self, client: JiraClient, writer: OutputWriter):
        self._client = client
        self._writer = writer

    def generate(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Fetch issue, generate test cases, write file. Returns result dict or None."""
        issue = self._client.get_issue(issue_key)
        if not issue:
            return None
        markdown = generate_test_cases(issue)
        saved_path = self._writer.write_test_cases(issue_key, markdown)
        return {"issue": issue, "saved_path": saved_path}
