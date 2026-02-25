"""
Regression Defect Creator

Creates standalone Defect issues in Jira (NO parent, HAS labels, HAS prefix).
Used for regression testing findings.

Rules:
- Issue Type: Defect
- NO parent field (validated - fails if parent provided)
- HAS labels (required)
- Summary MUST include prefix: "{TestType} - {ENV} - {PLATFORM} - {Title}"
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from config.jira_fields_config import JIRA_FIELDS, JiraFieldsConfig
from jira_client import JiraClient
from services.defect_field_generator import DefectFieldGenerator, GeneratedDefectFields

logger = logging.getLogger(__name__)


@dataclass
class RegressionDefectResult:
    """Result of regression defect creation."""
    success: bool
    issue_key: Optional[str] = None
    error: Optional[str] = None


class RegressionDefectCreator:
    """
    Creates Regression Defect (standalone Defect) in Jira.

    Used for regression testing findings.

    Rules:
    - Issue Type: Defect
    - NO parent field
    - HAS labels (required)
    - Summary MUST include prefix: "Regression - {ENV} - {PLATFORM} - {Title}"

    Validates:
    - Parent must NOT be provided (fails if parent given)
    - Labels are required
    """

    ISSUE_TYPE = "Defect"  # Regression issues use "Defect" type

    # Default labels for regression defects
    DEFAULT_LABELS = ["regression-testing", "Regression-testing"]

    PRIORITY_MAP = {
        "p0": "P0 - Critical",
        "p1": "P1 - High",
        "p2": "P2 - Medium",
        "p3": "P3 - Low",
    }

    def __init__(
        self,
        jira_client: JiraClient,
        field_generator: Optional[DefectFieldGenerator] = None,
        config: Optional[JiraFieldsConfig] = None,
    ):
        self._client = jira_client
        self._generator = field_generator or DefectFieldGenerator()
        self._config = config or JIRA_FIELDS

    def create(
        self,
        user_description: str,
        module: str,
        env: str = "preprod",
        platform: str = "WebApp",
        test_type: str = "Regression",
        priority: Optional[str] = None,
        parent_key: Optional[str] = None,  # Must be None for regression defects
    ) -> RegressionDefectResult:
        """
        Create a regression defect in Jira.

        Args:
            user_description: User's informal bug description (used as seed)
            module: Module name (e.g., "GiftCard", "Login", "Payment")
            env: Environment (preprod, staging, prod)
            platform: Platform (WebApp, iOS, Android, SuperApp)
            test_type: Test type for prefix (Regression, Smoke, etc.)
            priority: Priority (p0-p3)
            parent_key: MUST be None - regression defects have no parent

        Returns:
            RegressionDefectResult with issue key or error
        """
        # VALIDATION: Regression defects CANNOT have parent
        if parent_key is not None:
            return RegressionDefectResult(
                success=False,
                error="Regression defects cannot have a parent. Use Story Defect instead."
            )

        # Generate fields from user description
        fields = self._generator.generate(
            user_seed=user_description,
            module=module,
        )

        # Build Jira payload
        payload = self._build_payload(
            generated=fields,
            module=module,
            env=env,
            platform=platform,
            test_type=test_type,
            priority=priority,
        )

        # Create issue
        issue_key, error = self._client.create_issue_with_error(payload)

        if not issue_key:
            logger.error("Failed to create regression defect: %s", error)
            return RegressionDefectResult(success=False, error=error)

        logger.info("Created regression defect: %s", issue_key)
        return RegressionDefectResult(success=True, issue_key=issue_key)

    def _build_payload(
        self,
        generated: GeneratedDefectFields,
        module: str,
        env: str,
        platform: str,
        test_type: str,
        priority: Optional[str],
    ) -> Dict[str, Any]:
        """Build Jira payload for regression defect."""
        cfg = self._config

        # Build summary WITH prefix
        env_display = env.upper() if env else "PREPROD"
        prefix = f"{test_type} - {env_display} - {platform} - "
        summary = f"{prefix}{generated.summary}"

        payload: Dict[str, Any] = {
            "project": {"key": cfg.PROJECT_KEY},
            "issuetype": {"name": self.ISSUE_TYPE},
            "summary": summary,
            "components": [{"name": c} for c in cfg.DEFAULT_COMPONENTS],
            cfg.SQUAD: {"value": cfg.DEFAULT_SQUAD},
            "labels": self.DEFAULT_LABELS,  # REQUIRED for regression defects
        }

        # Add priority
        if priority:
            payload["priority"] = {"name": self.PRIORITY_MAP.get(priority, "P1 - High")}

        # Add custom fields with ADF
        if cfg.PRECONDITION:
            payload[cfg.PRECONDITION] = self._to_adf(generated.preconditions)
        if cfg.STEPS_TO_REPRODUCE:
            steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(generated.steps_to_reproduce))
            payload[cfg.STEPS_TO_REPRODUCE] = self._to_adf(steps_text)
        if cfg.EXPECTED_RESULTS:
            payload[cfg.EXPECTED_RESULTS] = self._to_adf(generated.expected_results)
        if cfg.ACTUAL_RESULTS:
            payload[cfg.ACTUAL_RESULTS] = self._to_adf(generated.actual_results)
        if cfg.ENVIRONMENT:
            payload[cfg.ENVIRONMENT] = self._to_adf(generated.environment)

        # Description - always ADF
        payload["description"] = self._to_adf(generated.description)

        # VALIDATION: Ensure NO parent field
        assert "parent" not in payload, "Regression defects must not have parent"

        return payload

    @staticmethod
    def _to_adf(text: str) -> Dict[str, Any]:
        """Convert text to Atlassian Document Format."""
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text or ""}]
                }
            ]
        }
