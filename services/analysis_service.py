"""
Analysis Service Module

Orchestrates the story analysis workflow: fetch → analyze → write.
Receives all dependencies via constructor (Dependency Inversion Principle).
"""
from pathlib import Path
from typing import Optional, Dict, Any

from jira_client import JiraClient
from analyzer import IssueAnalyzer
from services.output_writer import OutputWriter


class AnalysisService:
    """
    Coordinates JiraClient, IssueAnalyzer, and OutputWriter
    so that CLI handlers contain no orchestration logic.
    """

    def __init__(self, client: JiraClient, analyzer: IssueAnalyzer, writer: OutputWriter):
        self._client = client
        self._analyzer = analyzer
        self._writer = writer

    def analyze_story(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Fetch, analyze, and save a story. Returns result dict or None if not found."""
        issue = self._client.get_issue(issue_key)
        if not issue:
            return None
        analysis = self._analyzer.analyze_story(issue)
        content = self._analyzer.format_story_analysis_md(issue, analysis, issue_key)
        saved_path = self._writer.write_analysis(issue_key, content)
        return {"issue": issue, "analysis": analysis, "saved_path": saved_path}

    def analyze_bulk(self, jql: Optional[str], limit: int) -> Optional[Dict[str, Any]]:
        """Fetch multiple issues and run bulk analysis. Returns result dict or None."""
        issues = self._client.get_issues(jql=jql, max_results=limit)
        if not issues:
            return None
        return {"issues": issues, "analysis": self._analyzer.analyze_issues(issues)}

    def get_single_insights(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Fetch a single issue and produce quick insights. Returns result dict or None."""
        issue = self._client.get_issue(issue_key)
        if not issue:
            return None
        return {"issue": issue, "insights": self._analyzer.analyze_single_issue(issue)}
