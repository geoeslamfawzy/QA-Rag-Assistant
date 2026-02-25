"""
Jira Custom Field Configuration

Maps logical field names to Jira custom field IDs.
Set field ID to None to flatten into Description field.

To find your custom field IDs:
1. Via Jira Admin:
   - Go to Jira Settings > Issues > Custom Fields
   - Click on each field to see its ID in the URL

2. Via API:
   curl -u email:token "https://your-jira.atlassian.net/rest/api/3/field" \
     | jq '.[] | select(.custom == true) | {id, name}'

3. Update the field IDs below with your Jira instance values.
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class JiraFieldsConfig:
    """
    Configuration for Jira custom fields used in defect creation.

    Fields set to None will be flattened into the Description field.
    This provides graceful fallback when custom fields are not available.
    """

    # Project and issue type
    PROJECT_KEY: str = "CMB"
    ISSUE_TYPE: str = "Defect"

    # Custom fields - DISCOVERED FROM DEBUG (CMB Project, Bug/Defect)
    # Textarea fields accept plain text, system fields require ADF
    PRECONDITION: Optional[str] = "customfield_10391"       # textarea, plain text
    STEPS_TO_REPRODUCE: Optional[str] = "customfield_10389"  # textarea, plain text
    EXPECTED_RESULTS: Optional[str] = "customfield_10390"   # textarea, plain text
    ACTUAL_RESULTS: Optional[str] = "customfield_10388"     # textarea, plain text
    ENVIRONMENT: Optional[str] = "environment"              # system field, ADF required

    # Known custom fields
    SQUAD: str = "customfield_10513"

    # Default values for Defect creation
    DEFAULT_COMPONENTS: List[str] = field(
        default_factory=lambda: ["B2B", "B2C WebApp"]
    )
    DEFAULT_LABELS: List[str] = field(
        default_factory=lambda: ["regression-testing", "Regression-testing"]
    )
    DEFAULT_SQUAD: str = "B2B & B2C WebApp"

    def has_custom_field(self, name: str) -> bool:
        """
        Check if a custom field is configured (not None).

        Args:
            name: Field name (e.g., "PRECONDITION", "STEPS_TO_REPRODUCE")

        Returns:
            True if the field has a custom field ID configured
        """
        return getattr(self, name.upper(), None) is not None

    def get_custom_field(self, name: str) -> Optional[str]:
        """
        Get the custom field ID for a given field name.

        Args:
            name: Field name (e.g., "PRECONDITION", "STEPS_TO_REPRODUCE")

        Returns:
            Custom field ID or None if not configured
        """
        return getattr(self, name.upper(), None)


# Default configuration instance
# Import this in your code: from config.jira_fields_config import JIRA_FIELDS
JIRA_FIELDS = JiraFieldsConfig()
