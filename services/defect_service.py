"""
Defect Service Module

Creates Defect/Bug issues in Jira and links them to parent stories.
"""
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict

from jira_client import JiraClient

logger = logging.getLogger(__name__)


@dataclass
class DefectResult:
    """Result of defect creation."""
    success: bool
    issue_key: Optional[str] = None
    linked: bool = False
    error: Optional[str] = None


class DefectFormatter:
    """Formats user input into professional defect summary and description."""

    @staticmethod
    def format_summary(
        user_summary: str,
        module: str,
        env: str = "preprod",
        browser: str = "chrome",
    ) -> str:
        """
        Generate professional summary with prefix format.

        Example: [Regression][Preprod][Chrome][GiftCard] User cannot login
        """
        env_display = "Preprod" if env == "preprod" else "Staging"
        browser_display = "Chrome" if browser == "chrome" else "Super App"

        # Capitalize first letter of summary
        summary_clean = user_summary.strip()
        if summary_clean:
            summary_clean = summary_clean[0].upper() + summary_clean[1:]

        return f"[Regression][{env_display}][{browser_display}][{module}] {summary_clean}"

    @staticmethod
    def format_description(
        user_description: str,
        module: str,
        env: str = "preprod",
        browser: str = "chrome",
    ) -> str:
        """
        Generate structured description with all required sections.

        Sections:
        - Precondition
        - Description
        - Steps to reproduce
        - Expected Results
        - Actual Results
        - Environment
        """
        env_display = "Preprod" if env == "preprod" else "Staging"
        browser_display = "Chrome" if browser == "chrome" else "Super App"

        return f"""*Precondition:*
User is logged in and on the {module} page

*Description:*
{user_description}

*Steps to reproduce:*
1. Navigate to {module}
2. Perform the action described above
3. Observe the issue

*Expected Results:*
[To be filled]

*Actual Results:*
{user_description}

*Environment:*
{env_display} | {browser_display}"""

    @staticmethod
    def format_summary_with_ai(
        generator,  # OllamaGenerator instance
        user_input: str,
        module: str,
        env: str = "preprod",
        browser: str = "chrome",
    ) -> str:
        """
        Use AI to generate professional summary.

        Args:
            generator: OllamaGenerator instance
            user_input: Raw user description of the bug
            module: Module name
            env: Environment (preprod/staging)
            browser: Browser (chrome/superapp)

        Returns:
            Professional summary with prefix format
        """
        env_display = "Preprod" if env == "preprod" else "Staging"
        browser_display = "Chrome" if browser == "chrome" else "Super App"

        prompt = f"""Rewrite this bug description as a professional, concise defect summary.
Keep it under 80 characters.
Be specific and technical.
Do not include any prefix or brackets.

User's bug report: "{user_input}"
Module: {module}

Output ONLY the summary text (no prefix, no quotes, no explanation):"""

        ai_summary = generator.generate(prompt, temperature=0.3, max_tokens=100)

        # Fallback to template if AI fails
        if not ai_summary or len(ai_summary) < 5:
            summary_clean = user_input.strip()
            if summary_clean:
                ai_summary = summary_clean[0].upper() + summary_clean[1:]
            else:
                ai_summary = user_input

        # Clean up AI response (remove quotes if present)
        ai_summary = ai_summary.strip().strip('"\'')

        return f"[Regression][{env_display}][{browser_display}][{module}] {ai_summary}"

    @staticmethod
    def format_description_with_ai(
        generator,  # OllamaGenerator instance
        user_input: str,
        module: str,
        env: str = "preprod",
        browser: str = "chrome",
    ) -> str:
        """
        Use AI to generate professional structured description.

        Args:
            generator: OllamaGenerator instance
            user_input: Raw user description of the bug
            module: Module name
            env: Environment (preprod/staging)
            browser: Browser (chrome/superapp)

        Returns:
            Professional structured description with all sections
        """
        env_display = "Preprod" if env == "preprod" else "Staging"
        browser_display = "Chrome" if browser == "chrome" else "Super App"

        prompt = f"""Based on this bug report, generate a professional defect description.

User's bug report: "{user_input}"
Module: {module}
Environment: {env_display}
Browser: {browser_display}

Generate content for each section below. Be specific and professional.
Infer reasonable steps and expected behavior from the context.

*Precondition:*
(List 2-3 bullet points of conditions that must be true before testing)

*Description:*
(Professional rewrite of the bug, 2-3 sentences)

*Steps to reproduce:*
(Numbered steps, be specific, 4-6 steps)

*Expected Results:*
(What should happen normally, 1-2 sentences)

*Actual Results:*
(What actually happens - the bug behavior, 1-2 sentences)

*Environment:*
{env_display} | {browser_display}

Output the complete formatted description with all sections:"""

        ai_description = generator.generate(prompt, temperature=0.5, max_tokens=800)

        # Fallback to template if AI fails
        if not ai_description or len(ai_description) < 100:
            return DefectFormatter.format_description(user_input, module, env, browser)

        return ai_description


class DefectService:
    """
    Creates Defect issues in Jira.

    Design:
    - Receives JiraClient via constructor (DI pattern)
    - Creates Defect issues in CMB project
    - Optionally links to parent story
    - Adds priority and collaborators to defects
    """

    # Target project for Defect issues
    TARGET_PROJECT = "CMB"

    # Issue type
    ISSUE_TYPE = "Defect"

    # Required Jira fields
    DEFAULT_COMPONENTS = ["B2B", "B2C WebApp"]
    DEFAULT_SQUAD = "B2B & B2C WebApp"  # customfield_10513
    DEFAULT_LABELS = ["regression-testing", "Regression-testing"]

    # Link type for defect -> story
    LINK_TYPE = "Defect"

    # Priority mapping (CLI arg -> Jira priority name)
    PRIORITY_MAP = {
        "p0": "P0 - Critical",
        "p1": "P1 - High",
        "p2": "P2 - Medium",
        "p3": "P3 - Low",
    }
    DEFAULT_PRIORITY = "p1"
    PRIORITY_ENABLED = True

    # Collaborators to add to every defect (email addresses)
    COLLABORATOR_EMAILS = [
        "anastasia@yassir.com",
        "dalia.ihab@yassir.com",
        "nourelhouda.chouial@yassir.com",
        "wissem.dhaouadi@yassir.com",
    ]

    # Collaborators custom field ID (needs to be discovered)
    # Set to None to disable until correct field ID is found
    # To enable: find the field ID in Jira Admin > Custom Fields > Collaborators
    COLLABORATORS_FIELD = None  # Disabled - field not on Defect screen

    def __init__(self, jira_client: JiraClient):
        """
        Initialize DefectService.

        Args:
            jira_client: JiraClient instance for API calls.
        """
        self._client = jira_client
        # Cache for collaborator account IDs
        self._collaborator_ids: Optional[List[str]] = None

    def _get_collaborator_ids(self) -> List[str]:
        """
        Get account IDs for collaborators (cached).

        Returns:
            List of Jira account IDs.
        """
        if self._collaborator_ids is not None:
            return self._collaborator_ids

        self._collaborator_ids = []
        for email in self.COLLABORATOR_EMAILS:
            account_id = self._client.get_user_by_email(email)
            if account_id:
                self._collaborator_ids.append(account_id)
            else:
                logger.warning("Could not find collaborator: %s", email)

        return self._collaborator_ids

    def create_defect(
        self,
        summary: str,
        description: str,
        story_key: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> DefectResult:
        """
        Create a Defect/Bug issue in Jira.

        Args:
            summary: Defect summary/title.
            description: Detailed description of the defect.
            story_key: Optional parent story to link to.
            priority: Priority level (p0, p1, p2, p3). Defaults to p1.

        Returns:
            DefectResult with issue key and status.
        """
        # Build issue fields
        fields: Dict[str, any] = {
            "project": {"key": self.TARGET_PROJECT},
            "summary": summary,
            "issuetype": {"name": self.ISSUE_TYPE},
            "description": description,
            "components": [{"name": c} for c in self.DEFAULT_COMPONENTS],
            "customfield_10513": {"value": self.DEFAULT_SQUAD},
            "labels": self.DEFAULT_LABELS,
        }

        # Add priority (only if enabled)
        if self.PRIORITY_ENABLED:
            priority_key = priority or self.DEFAULT_PRIORITY
            priority_name = self.PRIORITY_MAP.get(priority_key, self.PRIORITY_MAP[self.DEFAULT_PRIORITY])
            fields["priority"] = {"name": priority_name}

        # Add collaborators (only if field is configured)
        if self.COLLABORATORS_FIELD:
            collaborator_ids = self._get_collaborator_ids()
            if collaborator_ids:
                fields[self.COLLABORATORS_FIELD] = [
                    {"accountId": aid} for aid in collaborator_ids
                ]

        # Create the defect
        issue_key, error_msg = self._client.create_issue_with_error(fields)

        if not issue_key:
            logger.error("Failed to create defect: %s", error_msg)
            return DefectResult(
                success=False,
                error=error_msg or "Failed to create defect",
            )

        logger.info("Created defect %s", issue_key)

        # Link to story if provided
        linked = False
        link_error = None
        if story_key:
            linked, link_error = self._client.create_link_with_error(
                link_type=self.LINK_TYPE,
                inward_key=story_key,
                outward_key=issue_key,
            )
            if not linked:
                logger.warning(
                    "Defect created but linking failed: %s", link_error
                )

        return DefectResult(
            success=True,
            issue_key=issue_key,
            linked=linked,
            error=link_error if not linked and story_key else None,
        )
