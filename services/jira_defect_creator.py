"""
Jira Defect Creator Module

Creates Defect issues in Jira using separate custom fields.
Uses RAG-grounded Defect objects from DefectBuilder.

Design:
- Receives Defect object from DefectBuilder (already anti-hallucination grounded)
- Maps Defect fields to Jira custom fields using JiraFieldsConfig
- Falls back to Description for unconfigured custom fields
- Links to parent story if provided
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from config.jira_fields_config import JIRA_FIELDS, JiraFieldsConfig
from jira_client import JiraClient
from models.defect import Defect

logger = logging.getLogger(__name__)


@dataclass
class JiraDefectResult:
    """Result of defect creation in Jira."""
    success: bool
    issue_key: Optional[str] = None
    linked: bool = False
    error: Optional[str] = None


class JiraDefectCreator:
    """
    Creates Defect issues in Jira with separate custom fields.

    Design:
    - Receives Defect object from DefectBuilder (RAG-grounded)
    - Maps Defect fields to Jira custom fields
    - Falls back to Description for unconfigured fields
    - Links to parent story if provided

    Anti-Hallucination:
    - Content comes ONLY from DefectBuilder which extracts from RAGContext
    - No LLM inference - all content is grounded in:
      - Story metadata (from Jira API)
      - Retrieved knowledge chunks (from RAG)
      - Validator findings (from ValidatorPipeline)
    """

    # Link type for Defect -> Story relationship
    LINK_TYPE = "Defect"

    # Priority mapping (CLI arg -> Jira priority name)
    PRIORITY_MAP = {
        "p0": "P0 - Critical",
        "p1": "P1 - High",
        "p2": "P2 - Medium",
        "p3": "P3 - Low",
    }

    def __init__(
        self,
        jira_client: JiraClient,
        config: Optional[JiraFieldsConfig] = None,
    ):
        """
        Initialize JiraDefectCreator.

        Args:
            jira_client: JiraClient instance for API calls
            config: Optional custom field configuration (defaults to JIRA_FIELDS)
        """
        self._client = jira_client
        self._config = config or JIRA_FIELDS

    def create(
        self,
        defect: Defect,
        story_key: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> JiraDefectResult:
        """
        Create a defect in Jira from a Defect object.

        Args:
            defect: Defect object from DefectBuilder (RAG-grounded)
            story_key: Optional parent story to link to
            priority: Priority level (p0, p1, p2, p3)

        Returns:
            JiraDefectResult with issue key and status
        """
        # Build Jira fields from Defect object
        fields = self._build_fields(defect, priority)

        # Create the issue
        issue_key, error_msg = self._client.create_issue_with_error(fields)

        if not issue_key:
            logger.error("Failed to create defect: %s", error_msg)
            return JiraDefectResult(success=False, error=error_msg)

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
                logger.warning("Defect created but linking failed: %s", link_error)

        return JiraDefectResult(
            success=True,
            issue_key=issue_key,
            linked=linked,
            error=link_error if not linked and story_key else None,
        )

    def _build_fields(
        self,
        defect: Defect,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build Jira fields dict from Defect object.

        Uses JiraFieldsConfig to determine which fields go into custom fields
        vs flattened into Description.

        Args:
            defect: Defect object with all field values
            priority: Optional priority override (p0-p3)

        Returns:
            Dictionary of Jira fields ready for API call
        """
        cfg = self._config

        # Base fields (always present)
        fields: Dict[str, Any] = {
            "project": {"key": cfg.PROJECT_KEY},
            "summary": defect.summary,
            "issuetype": {"name": cfg.ISSUE_TYPE},
            "components": [{"name": c} for c in cfg.DEFAULT_COMPONENTS],
            cfg.SQUAD: {"value": cfg.DEFAULT_SQUAD},
            "labels": cfg.DEFAULT_LABELS,
        }

        # Add priority if provided
        if priority:
            priority_name = self.PRIORITY_MAP.get(priority, "P1 - High")
            fields["priority"] = {"name": priority_name}

        # Build description - either full or partial depending on custom fields
        description_parts: List[str] = []

        # Precondition - requires ADF in Jira Cloud API v3
        if cfg.has_custom_field("PRECONDITION") and cfg.PRECONDITION:
            fields[cfg.PRECONDITION] = self._to_adf(defect.preconditions)
        elif defect.preconditions:
            description_parts.append(f"*Precondition:*\n{defect.preconditions}")

        # Description (main description always goes to description field)
        if defect.description:
            description_parts.append(f"*Description:*\n{defect.description}")

        # User description (preserved exactly)
        if defect.user_description:
            description_parts.append(f"*User Report:*\n{defect.user_description}")

        # Steps to reproduce - requires ADF in Jira Cloud API v3
        steps_text = self._format_steps(defect.steps_to_reproduce)
        if cfg.has_custom_field("STEPS_TO_REPRODUCE") and cfg.STEPS_TO_REPRODUCE:
            fields[cfg.STEPS_TO_REPRODUCE] = self._to_adf(steps_text)
        elif steps_text:
            description_parts.append(f"*Steps to Reproduce:*\n{steps_text}")

        # Expected results - requires ADF in Jira Cloud API v3
        if cfg.has_custom_field("EXPECTED_RESULTS") and cfg.EXPECTED_RESULTS:
            fields[cfg.EXPECTED_RESULTS] = self._to_adf(defect.expected_results)
        elif defect.expected_results:
            description_parts.append(f"*Expected Results:*\n{defect.expected_results}")

        # Actual results - requires ADF in Jira Cloud API v3
        if cfg.has_custom_field("ACTUAL_RESULTS") and cfg.ACTUAL_RESULTS:
            fields[cfg.ACTUAL_RESULTS] = self._to_adf(defect.actual_results)
        elif defect.actual_results:
            description_parts.append(f"*Actual Results:*\n{defect.actual_results}")

        # Environment - SYSTEM FIELD REQUIRES ADF
        if cfg.has_custom_field("ENVIRONMENT") and cfg.ENVIRONMENT:
            fields[cfg.ENVIRONMENT] = self._to_adf(defect.environment)  # ADF required!
        elif defect.environment:
            description_parts.append(f"*Environment:*\n{defect.environment}")

        # Add rule IDs reference if present
        if defect.rule_ids:
            rule_refs = "\n".join(f"- {rule_id}" for rule_id in defect.rule_ids)
            description_parts.append(f"*Related Rules:*\n{rule_refs}")

        # Description field - SYSTEM FIELD REQUIRES ADF
        fields["description"] = self._to_adf("\n\n".join(description_parts))

        return fields

    @staticmethod
    def _format_steps(steps: List[str]) -> str:
        """Format steps list as numbered text."""
        if not steps:
            return ""
        return "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))

    @staticmethod
    def _to_adf(text: str) -> Dict[str, Any]:
        """
        Convert plain text to Atlassian Document Format (ADF).

        Required for system fields like 'description' and 'environment'.
        Custom textarea fields should use plain text instead.
        """
        if not text:
            text = ""
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                }
            ]
        }
