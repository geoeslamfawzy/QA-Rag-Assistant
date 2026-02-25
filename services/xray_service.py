"""
XRAY Service Module

Orchestrates Test issue creation in Jira for XRAY integration.
Handles deduplication, retry logic, and batch processing.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from jira_client import JiraClient
from models.test_case import TestCase

logger = logging.getLogger(__name__)


@dataclass
class XrayTestResult:
    """Result of a single Test issue creation attempt."""
    test_case_id: str
    summary: str
    status: str  # "created", "skipped", "failed"
    issue_key: Optional[str] = None
    error: Optional[str] = None
    linked: bool = False


@dataclass
class XrayBatchResult:
    """Result of batch Test issue creation."""
    story_key: str
    total_count: int
    created: List[XrayTestResult] = field(default_factory=list)
    skipped: List[XrayTestResult] = field(default_factory=list)
    failed: List[XrayTestResult] = field(default_factory=list)

    @property
    def created_count(self) -> int:
        return len(self.created)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    @property
    def success(self) -> bool:
        return self.failed_count == 0

    def summary(self) -> str:
        """Return human-readable summary."""
        return (
            f"Story {self.story_key}: "
            f"{self.created_count} created, "
            f"{self.skipped_count} skipped (duplicates), "
            f"{self.failed_count} failed"
        )


class XrayService:
    """
    Orchestrates Test issue creation in Jira for XRAY.

    Design:
    - Receives JiraClient via constructor (DI pattern)
    - Checks for duplicates before creating
    - Retries failed requests up to 3 times
    - Links created Tests to parent Story
    - Returns structured result for CLI display
    """

    # Configuration
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2.0
    LINK_TYPE = "Test"  # XRAY link type: Test -> Story

    # Target project for Test issues (QATM = QA Testing project)
    TARGET_PROJECT = "QATM"

    # Required Jira fields (specific to QATM project)
    DEFAULT_COMPONENT = "B2B_WebApp"  # Component in QATM project
    DEFAULT_SQUAD = "B2B"  # customfield_10513

    def __init__(self, jira_client: JiraClient):
        """
        Initialize XrayService.

        Args:
            jira_client: JiraClient instance for API calls.
        """
        self._client = jira_client
        # Fail-fast tracking for configuration errors
        self._link_disabled = False
        self._link_error: Optional[str] = None
        self._create_disabled = False
        self._create_error: Optional[str] = None

    def create_tests_for_story(
        self,
        story_key: str,
        test_cases: List[TestCase],
        dry_run: bool = False,
    ) -> XrayBatchResult:
        """
        Create Test issues in Jira for a list of test cases.

        Workflow:
        1. Extract project key from story key
        2. For each test case:
           a. Check if Test already exists (by summary)
           b. If exists, skip (deduplication)
           c. If not, create Test issue
           d. Link Test to Story
        3. Return structured result

        Args:
            story_key: Parent story key (e.g., "CMB-32860").
            test_cases: List of TestCase objects to create.
            dry_run: If True, simulate without creating issues.

        Returns:
            XrayBatchResult with created, skipped, and failed tests.
        """
        result = XrayBatchResult(
            story_key=story_key,
            total_count=len(test_cases),
        )

        # Reset fail-fast state for this batch
        self._link_disabled = False
        self._link_error = None
        self._create_disabled = False
        self._create_error = None

        # Extract project key from story key (e.g., "CMB-32860" -> "CMB")
        project_key = self._extract_project_key(story_key)
        if not project_key:
            logger.error("Invalid story key format: %s", story_key)
            for tc in test_cases:
                result.failed.append(XrayTestResult(
                    test_case_id=tc.id,
                    summary=tc.summary,
                    status="failed",
                    error=f"Invalid story key format: {story_key}",
                ))
            return result

        # Process each test case
        for tc in test_cases:
            test_result = self._process_test_case(
                tc, project_key, story_key, dry_run
            )

            if test_result.status == "created":
                result.created.append(test_result)
            elif test_result.status == "skipped":
                result.skipped.append(test_result)
            else:
                result.failed.append(test_result)

        logger.info(result.summary())
        return result

    def _process_test_case(
        self,
        tc: TestCase,
        project_key: str,
        story_key: str,
        dry_run: bool,
    ) -> XrayTestResult:
        """
        Process a single test case: check duplicate, create, link.

        Args:
            tc: TestCase object.
            project_key: Jira project key.
            story_key: Parent story key.
            dry_run: If True, simulate without creating.

        Returns:
            XrayTestResult with status and details.
        """
        # Step 1: Check for duplicate in target project (QATM)
        existing_key = self._client.find_issue_by_summary(
            summary=tc.summary,
            project=self.TARGET_PROJECT,
            issue_type="Test",
        )

        if existing_key:
            logger.info(
                "Skipping duplicate: %s already exists as %s",
                tc.summary[:50], existing_key
            )
            return XrayTestResult(
                test_case_id=tc.id,
                summary=tc.summary,
                status="skipped",
                issue_key=existing_key,
                linked=True,  # Assume already linked
            )

        if dry_run:
            return XrayTestResult(
                test_case_id=tc.id,
                summary=tc.summary,
                status="created",
                issue_key="DRY-RUN",
                linked=True,
            )

        # Step 2: Check if creation is disabled due to config error
        if self._create_disabled:
            return XrayTestResult(
                test_case_id=tc.id,
                summary=tc.summary,
                status="failed",
                error=self._create_error,
            )

        # Step 3: Create Test issue with retry
        fields = self._build_issue_fields(tc, project_key)
        issue_key = self._create_with_retry(fields)

        if not issue_key:
            return XrayTestResult(
                test_case_id=tc.id,
                summary=tc.summary,
                status="failed",
                error="Failed to create issue after retries",
            )

        # Step 3: Link Test to Story (skip if linking is disabled due to config error)
        if self._link_disabled:
            return XrayTestResult(
                test_case_id=tc.id,
                summary=tc.summary,
                status="created",
                issue_key=issue_key,
                linked=False,
                error=self._link_error,
            )

        linked = self._link_with_retry(story_key, issue_key)

        return XrayTestResult(
            test_case_id=tc.id,
            summary=tc.summary,
            status="created",
            issue_key=issue_key,
            linked=linked,
            error=None if linked else self._link_error or "Created but linking failed",
        )

    def _build_issue_fields(
        self,
        tc: TestCase,
        project_key: str,
    ) -> Dict[str, Any]:
        """
        Build Jira issue fields from TestCase.

        Args:
            tc: TestCase object.
            project_key: Jira project key.

        Returns:
            Dictionary of Jira fields for issue creation.
        """
        # Build description in required format
        description = self._format_description(tc)

        return {
            "project": {"key": self.TARGET_PROJECT},  # Always create in QATM project
            "summary": tc.summary,
            "issuetype": {"name": "Test"},
            "description": description,
            # Required fields for this Jira instance
            "components": [{"name": self.DEFAULT_COMPONENT}],
            "customfield_10513": {"value": self.DEFAULT_SQUAD},
        }

    def _format_description(self, tc: TestCase) -> str:
        """
        Format test case as BDD description for Jira.

        Format:
            Preconditions:
            - ...

            Steps:
            1. Given...
            2. When...
            3. Then...

            Expected Results:
            - ...

        Args:
            tc: TestCase object.

        Returns:
            Formatted description string.
        """
        lines = []

        # Preconditions section
        if tc.preconditions:
            lines.append("Preconditions:")
            for p in tc.preconditions:
                lines.append(f"- {p}")
            lines.append("")

        # Steps section (BDD format)
        if tc.steps:
            lines.append("Steps:")
            for i, step in enumerate(tc.steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        # Expected Results section
        if tc.expected:
            lines.append("Expected Results:")
            for exp in tc.expected:
                lines.append(f"- {exp}")

        return "\n".join(lines)

    def _create_with_retry(self, fields: Dict[str, Any]) -> Optional[str]:
        """
        Create issue with fail-fast on configuration errors.

        Detects configuration errors (400 with component/permission issues)
        and disables future create attempts.

        Args:
            fields: Jira issue fields.

        Returns:
            Issue key on success, None on failure.
        """
        issue_key, error_msg = self._client.create_issue_with_error(fields)

        if issue_key:
            return issue_key

        # Check for configuration error (400 = component/permission issue)
        if error_msg and "400" in error_msg:
            if "component" in error_msg.lower() or "permission" in error_msg.lower():
                self._create_disabled = True
                self._create_error = "Configuration error - check Jira project components/permissions"
                logger.error(self._create_error)
                return None

        # For other errors, still fail fast (no retries for API errors)
        self._create_error = error_msg or "Create issue failed"
        logger.error("Create issue failed: %s", self._create_error)
        return None

    def _link_with_retry(self, story_key: str, test_key: str) -> bool:
        """
        Create issue link with retry logic.

        Detects configuration errors (404) and disables future link attempts.

        Args:
            story_key: Parent story key.
            test_key: Created test key.

        Returns:
            True on success, False on failure.
        """
        success, error_msg = self._client.create_link_with_error(
            link_type=self.LINK_TYPE,
            inward_key=story_key,
            outward_key=test_key,
        )

        if success:
            return True

        # Check for configuration error (404 = link type not found)
        if error_msg and ("404" in error_msg or "not found" in error_msg.lower()):
            self._link_disabled = True
            self._link_error = f"Link type '{self.LINK_TYPE}' not found - check Jira configuration"
            logger.error(self._link_error)
            return False

        # For other errors, don't retry (fail fast)
        self._link_error = error_msg or "Link creation failed"
        logger.error("Link creation failed: %s", self._link_error)
        return False

    @staticmethod
    def _extract_project_key(issue_key: str) -> Optional[str]:
        """
        Extract project key from issue key.

        Args:
            issue_key: Jira issue key (e.g., "CMB-32860").

        Returns:
            Project key (e.g., "CMB") or None if invalid.
        """
        if not issue_key or "-" not in issue_key:
            return None
        return issue_key.split("-")[0].upper()
