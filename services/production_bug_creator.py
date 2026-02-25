"""
Production Bug Creator

Creates standalone Bug issues in Jira for production issues (NO parent, optional labels, optional prefix).
Used for production issues found in live environment.

Rules:
- Issue Type: Bug
- NO parent field (validated - fails if parent provided)
- Labels optional
- Summary prefix optional
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from config.jira_fields_config import JIRA_FIELDS, JiraFieldsConfig
from jira_client import JiraClient
from services.defect_field_generator import DefectFieldGenerator, GeneratedDefectFields

logger = logging.getLogger(__name__)


@dataclass
class ProductionBugResult:
    """Result of production bug creation."""
    success: bool
    issue_key: Optional[str] = None
    error: Optional[str] = None


class ProductionBugCreator:
    """
    Creates Production Bug (standalone Bug) in Jira.

    Used for production issues found in live environment.

    Rules:
    - Issue Type: Bug
    - NO parent field
    - Labels optional (not required)
    - Summary prefix optional (not required)

    Validates:
    - Parent must NOT be provided (fails if parent given)
    """

    ISSUE_TYPE = "Bug"  # Production issues use "Bug" type

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
        env: str = "prod",
        platform: str = "WebApp",
        priority: Optional[str] = None,
        parent_key: Optional[str] = None,  # Must be None for production bugs
    ) -> ProductionBugResult:
        """
        Create a production bug in Jira.

        Args:
            user_description: User's informal bug description (used as seed)
            module: Module name (e.g., "GiftCard", "Login", "Payment")
            env: Environment (default: prod for production bugs)
            platform: Platform (WebApp, iOS, Android, SuperApp)
            priority: Priority (p0-p3)
            parent_key: MUST be None - production bugs have no parent

        Returns:
            ProductionBugResult with issue key or error
        """
        # VALIDATION: Production bugs CANNOT have parent
        if parent_key is not None:
            return ProductionBugResult(
                success=False,
                error="Production bugs cannot have a parent."
            )

        # Generate fields from user description (using Production environment)
        fields = self._generator.generate(
            user_seed=user_description,
            module=module,
            defect_type="production",  # Uses Production environment
        )

        # Detect app context from user description for title prefix
        app_context = self._generator.detect_app_context(user_description)

        # Build Jira payload
        payload = self._build_payload(
            generated=fields,
            module=module,
            env=env,
            platform=platform,
            priority=priority,
            app_context=app_context,
        )

        # Create issue
        issue_key, error = self._client.create_issue_with_error(payload)

        if not issue_key:
            logger.error("Failed to create production bug: %s", error)
            return ProductionBugResult(success=False, error=error)

        logger.info("Created production bug: %s", issue_key)
        return ProductionBugResult(success=True, issue_key=issue_key)

    def _build_payload(
        self,
        generated: GeneratedDefectFields,
        module: str,
        env: str,
        platform: str,
        priority: Optional[str],
        app_context: str = "WebApp",
    ) -> Dict[str, Any]:
        """Build Jira payload for production bug."""
        cfg = self._config

        # Summary WITH prefix: [ALG] - {AppContext} - PROD : {title}
        summary = f"[ALG] - {app_context} - PROD : {generated.summary}"

        payload: Dict[str, Any] = {
            "project": {"key": cfg.PROJECT_KEY},
            "issuetype": {"name": self.ISSUE_TYPE},
            "summary": summary,
            "components": [{"name": c} for c in cfg.DEFAULT_COMPONENTS],
            cfg.SQUAD: {"value": cfg.DEFAULT_SQUAD},
            # NO labels required for production bugs
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
        assert "parent" not in payload, "Production bugs must not have parent"

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
