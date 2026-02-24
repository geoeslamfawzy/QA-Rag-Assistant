"""
Jira Client Module

Pure data-access layer for the Jira API.
No display or formatting logic lives here — see display/issue_display.py.
"""
import logging
import os
import re
from typing import List, Dict, Optional, Any
from jira import JIRA
from jira.exceptions import JIRAError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class JiraClient:
    """Data-access client for the Jira REST API."""

    def __init__(self):
        """Initialise from environment variables; raises ValueError if credentials are missing."""
        self.server = os.getenv('JIRA_SERVER')
        self.email = os.getenv('JIRA_EMAIL')
        self.api_token = os.getenv('JIRA_API_TOKEN')
        self.project_key = os.getenv('JIRA_PROJECT_KEY', '')

        if not all([self.server, self.email, self.api_token]):
            raise ValueError(
                "Missing required Jira credentials. "
                "Set JIRA_SERVER, JIRA_EMAIL, and JIRA_API_TOKEN in your .env file."
            )

        self.jira = JIRA(server=self.server, basic_auth=(self.email, self.api_token))
        logger.info("Connected to Jira: %s", self.server)

    def get_issues(
        self,
        jql: str = None,
        project_key: str = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch issues matching a JQL query. Returns empty list on error."""
        if jql is None:
            if project_key:
                jql = f"project = {project_key}"
            elif self.project_key:
                jql = f"project = {self.project_key}"
            else:
                jql = "ORDER BY updated DESC"

        try:
            issues = self.jira.search_issues(jql, maxResults=max_results)
            logger.info("Found %d issue(s)", len(issues))
            return [self._issue_to_dict(issue) for issue in issues]
        except JIRAError as e:
            logger.error("Error fetching issues: %s", e)
            return []

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Fetch a single issue by key. Returns None on error."""
        try:
            return self._issue_to_dict(self.jira.issue(issue_key))
        except JIRAError as e:
            logger.error("Error fetching issue %s: %s", issue_key, e)
            return None

    def add_comment(self, issue_key: str, comment: str) -> bool:
        """Add a comment to an issue. Returns True on success."""
        try:
            self.jira.add_comment(self.jira.issue(issue_key), comment)
            logger.info("Comment added to %s", issue_key)
            return True
        except JIRAError as e:
            logger.error("Error adding comment: %s", e)
            return False

    def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> bool:
        """Update issue fields. Returns True on success."""
        try:
            self.jira.issue(issue_key).update(fields=fields)
            logger.info("Issue %s updated", issue_key)
            return True
        except JIRAError as e:
            logger.error("Error updating issue: %s", e)
            return False

    def get_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Return all comments for an issue. Returns empty list on error."""
        try:
            issue = self.jira.issue(issue_key, expand='comments')
            if not (hasattr(issue.fields, 'comment') and issue.fields.comment.comments):
                return []
            return [
                {
                    'author': c.author.displayName,
                    'body': c.body,
                    'created': c.created,
                    'updated': c.updated,
                }
                for c in issue.fields.comment.comments
            ]
        except JIRAError as e:
            logger.error("Error fetching comments: %s", e)
            return []

    def _issue_to_dict(self, issue) -> Dict[str, Any]:
        """Convert a Jira issue object to a plain dictionary."""
        description = issue.fields.description or ''
        return {
            'key': issue.key,
            'summary': issue.fields.summary,
            'status': issue.fields.status.name,
            'assignee': issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned',
            'reporter': issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown',
            'priority': issue.fields.priority.name if issue.fields.priority else 'None',
            'issue_type': issue.fields.issuetype.name,
            'created': issue.fields.created,
            'updated': issue.fields.updated,
            'description': description or 'No description',
            'acceptance_criteria': self._extract_acceptance_criteria(issue, description),
            'url': f"{self.server}/browse/{issue.key}",
        }

    @staticmethod
    def _extract_acceptance_criteria(issue, description: str) -> Optional[str]:
        """Extract acceptance criteria from custom fields or description text."""
        for field_name in ['acceptance criteria', 'acceptance', 'criteria', 'customfield_10026']:
            try:
                field = getattr(issue.fields, field_name, None)
                if field:
                    return str(field)
            except AttributeError:
                pass

        if description:
            return JiraClient._extract_ac_from_description(description)
        return None

    @staticmethod
    def _extract_ac_from_description(description: str) -> Optional[str]:
        """Search description text for acceptance criteria patterns."""
        patterns = [
            r'Acceptance Criteria[:\s]*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'AC[:\s]*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'Acceptance[:\s]*(.*?)(?=\n\n|\n[A-Z]|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return None
