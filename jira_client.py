"""
Jira Client Module

Pure data-access layer for the Jira API.
No display or formatting logic lives here — see display/issue_display.py.
"""
import logging
import os
import re
from typing import List, Dict, Optional, Any, Tuple

import requests
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

    def post_comment(self, issue_key: str, comment: str) -> bool:
        """
        Post a formatted comment to a Jira issue.

        Wrapper around add_comment with additional validation.
        Used by JiraCommentService for posting QA results.

        Args:
            issue_key: Jira issue key (e.g., CMB-123)
            comment: Comment text (supports Jira wiki markup)

        Returns:
            True if posted successfully, False otherwise
        """
        if not comment or not comment.strip():
            logger.warning("Attempted to post empty comment to %s", issue_key)
            return False

        if not issue_key or not issue_key.strip():
            logger.warning("Invalid issue key provided for comment posting")
            return False

        return self.add_comment(issue_key, comment)

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

    # -------------------------------------------------------------------------
    # Issue Creation and Linking (for XRAY integration)
    # -------------------------------------------------------------------------

    def create_issue(self, fields: Dict[str, Any]) -> Optional[str]:
        """
        Create a new issue in Jira using REST API v3.

        Args:
            fields: Dictionary of Jira fields for the new issue.
                Required keys: project, summary, issuetype
                Optional keys: description, priority, components, etc.

        Returns:
            Issue key (e.g., "CMB-12345") on success, None on failure.

        Example:
            fields = {
                "project": {"key": "CMB"},
                "summary": "Verify user login with valid credentials",
                "issuetype": {"name": "Test"},
                "priority": {"name": "Medium"},
                "description": "Preconditions:\\n- User exists..."
            }
            issue_key = client.create_issue(fields)
        """
        url = f"{self.server.rstrip('/')}/rest/api/3/issue"

        # Convert description to ADF (Atlassian Document Format) if it's a string
        if "description" in fields and isinstance(fields["description"], str):
            fields = fields.copy()
            fields["description"] = self._text_to_adf(fields["description"])

        payload = {"fields": fields}

        try:
            response = requests.post(
                url,
                json=payload,
                auth=(self.email, self.api_token),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )

            # If priority field causes error, retry without it
            if response.status_code == 400:
                error_data = response.json()
                if "priority" in str(error_data.get("errors", {})):
                    logger.warning("Priority field rejected, retrying without priority")
                    fields_no_priority = {k: v for k, v in fields.items() if k != "priority"}
                    payload = {"fields": fields_no_priority}
                    response = requests.post(
                        url,
                        json=payload,
                        auth=(self.email, self.api_token),
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                        },
                        timeout=30,
                    )

            response.raise_for_status()
            data = response.json()
            issue_key = data.get("key")
            logger.info("Created issue %s", issue_key)
            return issue_key

        except requests.RequestException as e:
            logger.error("Error creating issue: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Response: %s", e.response.text)
            return None

    def create_issue_with_error(self, fields: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Create a new issue in Jira, returning error details for fail-fast detection.

        Args:
            fields: Dictionary of Jira fields for the new issue.

        Returns:
            Tuple of (issue_key: Optional[str], error_message: Optional[str])
        """
        url = f"{self.server.rstrip('/')}/rest/api/3/issue"

        # Convert description to ADF if it's a string
        if "description" in fields and isinstance(fields["description"], str):
            fields = fields.copy()
            fields["description"] = self._text_to_adf(fields["description"])

        payload = {"fields": fields}

        try:
            response = requests.post(
                url,
                json=payload,
                auth=(self.email, self.api_token),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            issue_key = data.get("key")
            logger.info("Created issue %s", issue_key)
            return issue_key, None

        except requests.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_msg = f"{e.response.status_code}: {e.response.text}"
            logger.error("Error creating issue: %s", error_msg)
            return None, error_msg

    @staticmethod
    def _text_to_adf(text: str) -> Dict[str, Any]:
        """
        Convert plain text to Atlassian Document Format (ADF).

        ADF is required for description field in Jira REST API v3.

        Args:
            text: Plain text string.

        Returns:
            ADF document structure.
        """
        # Split text into paragraphs
        paragraphs = text.split("\n")
        content = []

        for para in paragraphs:
            if para.strip():
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": para}]
                })
            else:
                # Empty line = empty paragraph for spacing
                content.append({"type": "paragraph", "content": []})

        return {
            "type": "doc",
            "version": 1,
            "content": content
        }

    def create_link(
        self,
        link_type: str,
        inward_key: str,
        outward_key: str,
    ) -> bool:
        """
        Create a link between two issues using REST API v3.

        Args:
            link_type: Name of the link type (e.g., "Tests", "Blocks").
            inward_key: Key of the inward issue (e.g., Story key).
            outward_key: Key of the outward issue (e.g., Test key).

        Returns:
            True on success, False on failure.

        Example:
            # Link Test CMB-12345 to Story CMB-100
            client.create_link("Tests", "CMB-100", "CMB-12345")
        """
        url = f"{self.server.rstrip('/')}/rest/api/3/issueLink"
        payload = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key},
        }

        try:
            response = requests.post(
                url,
                json=payload,
                auth=(self.email, self.api_token),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            response.raise_for_status()
            logger.info("Linked %s -> %s (%s)", outward_key, inward_key, link_type)
            return True
        except requests.RequestException as e:
            logger.error("Error creating link: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Response: %s", e.response.text)
            return False

    def create_link_with_error(
        self,
        link_type: str,
        inward_key: str,
        outward_key: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Create a link between two issues, returning error details.

        Same as create_link but returns error message for fail-fast detection.

        Args:
            link_type: Name of the link type (e.g., "Test", "Blocks").
            inward_key: Key of the inward issue (e.g., Story key).
            outward_key: Key of the outward issue (e.g., Test key).

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        url = f"{self.server.rstrip('/')}/rest/api/3/issueLink"
        payload = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key},
        }

        try:
            response = requests.post(
                url,
                json=payload,
                auth=(self.email, self.api_token),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            response.raise_for_status()
            logger.info("Linked %s -> %s (%s)", outward_key, inward_key, link_type)
            return True, None
        except requests.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_msg = f"{e.response.status_code}: {e.response.text}"
            logger.error("Error creating link: %s", error_msg)
            return False, error_msg

    def find_issue_by_summary(
        self,
        summary: str,
        project: str,
        issue_type: str = "Test",
    ) -> Optional[str]:
        """
        Find an existing issue by exact summary match.

        Used for deduplication - prevents creating duplicate Test issues.
        Uses REST API v3 directly to avoid deprecated v2 search endpoint.

        Args:
            summary: Exact summary to search for.
            project: Project key to search in.
            issue_type: Issue type to filter by (default: "Test").

        Returns:
            Issue key if found, None if not found.

        Example:
            existing = client.find_issue_by_summary(
                summary="Verify login with valid credentials",
                project="CMB",
                issue_type="Test"
            )
            if existing:
                print(f"Test already exists: {existing}")
        """
        # Escape special JQL characters in summary
        escaped_summary = summary.replace('"', '\\"').replace("'", "\\'")
        jql = (
            f'project = {project} AND '
            f'issuetype = "{issue_type}" AND '
            f'summary ~ "{escaped_summary}"'
        )
        try:
            # Use REST API v3 directly (v2 is deprecated)
            url = f"{self.server.rstrip('/')}/rest/api/3/search/jql"
            response = requests.get(
                url,
                params={"jql": jql, "maxResults": 5, "fields": "summary"},
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            for issue in data.get("issues", []):
                issue_summary = issue.get("fields", {}).get("summary", "")
                # Exact match check (JQL ~ is fuzzy)
                if issue_summary.strip().lower() == summary.strip().lower():
                    issue_key = issue.get("key")
                    logger.info("Found existing issue: %s", issue_key)
                    return issue_key
            return None
        except requests.RequestException as e:
            logger.error("Error searching for issue: %s", e)
            return None

    def get_user_by_email(self, email: str) -> Optional[str]:
        """
        Get Jira account ID by email address.

        Uses the user search API to find a user by their email.

        Args:
            email: User's email address.

        Returns:
            Account ID if found, None if not found.

        Example:
            account_id = client.get_user_by_email("john@example.com")
        """
        url = f"{self.server.rstrip('/')}/rest/api/3/user/search"
        try:
            response = requests.get(
                url,
                params={"query": email},
                auth=(self.email, self.api_token),
                headers={"Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            users = response.json()

            # Find exact email match
            for user in users:
                if user.get("emailAddress", "").lower() == email.lower():
                    account_id = user.get("accountId")
                    logger.info("Found user %s: %s", email, account_id)
                    return account_id

            # If no exact match, return first result if available
            if users:
                account_id = users[0].get("accountId")
                logger.info("Found user (fuzzy) %s: %s", email, account_id)
                return account_id

            logger.warning("User not found: %s", email)
            return None
        except requests.RequestException as e:
            logger.error("Error searching for user %s: %s", email, e)
            return None
