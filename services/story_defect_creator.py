"""
Story Defect Creator

Creates Story Defect issues as sub-tasks under User Stories (HAS parent, NO labels, NO prefix).

Rules:
- Issue Type: Story Defect (sub-task type)
- MUST have parent field (required for sub-tasks)
- NO labels
- NO prefix in summary - clean professional title only
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from config.jira_fields_config import JIRA_FIELDS, JiraFieldsConfig
from jira_client import JiraClient
from services.defect_field_generator import DefectFieldGenerator, GeneratedDefectFields

logger = logging.getLogger(__name__)


@dataclass
class StoryDefectResult:
    """Result of story defect creation."""
    success: bool
    issue_key: Optional[str] = None
    parent_key: Optional[str] = None
    linked: bool = False
    error: Optional[str] = None


class StoryDefectCreator:
    """
    Creates Story Defect (sub-task under User Story) in Jira.

    Rules:
    - Issue Type: Story Defect (sub-task type)
    - MUST have parent field (required for sub-tasks)
    - NO labels
    - NO prefix in summary - clean professional title only

    Validates:
    - Parent key is REQUIRED (fails if missing)
    - Labels must NOT be included
    - Summary must NOT have prefix
    """

    ISSUE_TYPE = "Story Defect"  # Story defects use "Story Defect" type (sub-task)

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
        parent_key: str,  # REQUIRED for story defects
        module: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> StoryDefectResult:
        """
        Create a story defect in Jira.

        Args:
            user_description: User's informal bug description (used as seed)
            parent_key: Parent story key - REQUIRED
            module: Optional module name for context
            priority: Priority (p0-p3)

        Returns:
            StoryDefectResult with issue key and parent info
        """
        # VALIDATION: Story defects MUST have parent
        if not parent_key:
            return StoryDefectResult(
                success=False,
                error="Story defects require a parent story key. Use Regular Defect instead."
            )

        # Fetch parent story context for enrichment
        story_context = self._fetch_story_context(parent_key)
        if story_context is None:
            return StoryDefectResult(
                success=False,
                error=f"Parent story {parent_key} not found"
            )

        # Derive module from story if not provided
        effective_module = module or self._extract_module_from_story(story_context)

        # Generate fields from user description (using Staging environment for story defects)
        fields = self._generator.generate(
            user_seed=user_description,
            story_context=story_context,
            module=effective_module,
            defect_type="story",  # Uses Staging environment
        )

        # Build Jira payload (WITH parent field - Story Defect is a sub-task)
        payload = self._build_payload(
            generated=fields,
            parent_key=parent_key,
            priority=priority,
        )

        # Create issue
        issue_key, error = self._client.create_issue_with_error(payload)

        if not issue_key:
            logger.error("Failed to create story defect: %s", error)
            return StoryDefectResult(success=False, error=error)

        # Story Defect is a sub-task type - parent relationship established via parent field
        # No need for separate linking
        logger.info("Created story defect %s under parent %s", issue_key, parent_key)
        return StoryDefectResult(
            success=True,
            issue_key=issue_key,
            parent_key=parent_key,
            linked=True,  # Parent relationship established via parent field
            error=None,
        )

    def _fetch_story_context(self, story_key: str) -> Optional[Dict]:
        """Fetch parent story for context enrichment."""
        try:
            return self._client.get_issue(story_key)
        except Exception as e:
            logger.warning("Failed to fetch story %s: %s", story_key, e)
            return None

    def _extract_module_from_story(self, story: Dict) -> Optional[str]:
        """Extract module from story components or labels."""
        fields = story.get("fields", {})

        # Try components
        components = fields.get("components", [])
        if components:
            return components[0].get("name")

        # Try labels
        labels = fields.get("labels", [])
        known_modules = ["giftcard", "payment", "login", "trips", "b2b", "b2c"]
        for label in labels:
            if label.lower() in known_modules:
                return label.title()

        return None

    def _build_payload(
        self,
        generated: GeneratedDefectFields,
        parent_key: str,
        priority: Optional[str],
    ) -> Dict[str, Any]:
        """Build Jira payload for story defect (WITH parent field - Story Defect is a sub-task)."""
        cfg = self._config

        # Summary WITHOUT prefix - clean professional title
        summary = generated.summary  # No prefix!

        payload: Dict[str, Any] = {
            "project": {"key": cfg.PROJECT_KEY},
            "issuetype": {"name": self.ISSUE_TYPE},
            "summary": summary,
            "parent": {"key": parent_key},  # REQUIRED - Story Defect is a sub-task type
            "components": [{"name": c} for c in cfg.DEFAULT_COMPONENTS],
            cfg.SQUAD: {"value": cfg.DEFAULT_SQUAD},
            # NO "labels" field - story defects don't have labels
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

        # VALIDATION: Ensure no labels
        assert "labels" not in payload, "Story defects must not have labels"

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
