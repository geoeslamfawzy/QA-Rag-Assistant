#!/usr/bin/env python3
"""
Jira Custom Field Debug Script

Investigates why custom fields are not being populated during Bug/Defect creation.

Steps:
1. Fetch all Jira fields and find custom field IDs
2. Check createmeta to see which fields are on Bug create screen
3. Test field creation with ADF format
4. Verify created issue
5. Report findings

Usage:
    python debug_jira_fields.py

Author: Debug script for custom field investigation
"""
import os
import json
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()


class JiraFieldDebugger:
    """Debug utility for Jira custom field issues."""

    def __init__(self):
        self.server = os.getenv('JIRA_SERVER')
        self.email = os.getenv('JIRA_EMAIL')
        self.api_token = os.getenv('JIRA_API_TOKEN')

        if not all([self.server, self.email, self.api_token]):
            raise ValueError("Missing JIRA_SERVER, JIRA_EMAIL, or JIRA_API_TOKEN")

        print(f"Initialized with server: {self.server}")

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request to Jira."""
        url = f"{self.server.rstrip('/')}{endpoint}"
        return requests.request(
            method,
            url,
            auth=(self.email, self.api_token),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30,
            **kwargs
        )

    # -------------------------------------------------------------------
    # STEP 1: Fetch Field Metadata
    # -------------------------------------------------------------------
    def get_all_fields(self) -> List[Dict]:
        """GET /rest/api/3/field - Fetch all Jira fields."""
        print("\n" + "="*60)
        print("STEP 1: FETCHING ALL JIRA FIELDS")
        print("="*60)

        response = self._request("GET", "/rest/api/3/field")

        if response.status_code != 200:
            print(f"ERROR: {response.status_code}")
            print(response.text)
            return []

        fields = response.json()
        print(f"Total fields: {len(fields)}")
        return fields

    def find_relevant_fields(self, fields: List[Dict]) -> Dict[str, Dict]:
        """Find fields matching our target names."""
        keywords = [
            "precondition",
            "steps",
            "expected",
            "actual",
            "environment",
            "reproduce",
        ]

        print("\n" + "-"*60)
        print("SEARCHING FOR RELEVANT CUSTOM FIELDS:")
        print("-"*60)

        found = {}
        for field in fields:
            name = field.get("name", "").lower()
            field_id = field.get("id", "")

            for keyword in keywords:
                if keyword in name:
                    schema = field.get("schema", {})
                    field_info = {
                        "id": field_id,
                        "name": field.get("name"),
                        "schema_type": schema.get("type"),
                        "schema_custom": schema.get("custom"),
                        "schema_system": schema.get("system"),
                        "custom": field.get("custom", False),
                    }
                    found[field_id] = field_info

                    print(f"\n[MATCH] {field.get('name')}")
                    print(f"  ID: {field_id}")
                    print(f"  Schema Type: {schema.get('type')}")
                    print(f"  Schema Custom: {schema.get('custom')}")
                    print(f"  Is Custom: {field.get('custom', False)}")
                    break

        if not found:
            print("\nNo matching fields found!")
            print("\nAvailable custom fields:")
            for f in fields:
                if f.get("custom"):
                    print(f"  - {f.get('id')}: {f.get('name')}")

        return found

    # -------------------------------------------------------------------
    # STEP 2: ADF Helper
    # -------------------------------------------------------------------
    @staticmethod
    def to_adf(text: str) -> Dict[str, Any]:
        """Convert plain text to Atlassian Document Format (ADF)."""
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

    # -------------------------------------------------------------------
    # STEP 3: Get Create Meta (Check Available Fields)
    # -------------------------------------------------------------------
    def get_create_meta(self, project: str, issue_type: str) -> Dict:
        """Get createmeta to see which fields are available on create screen."""
        print("\n" + "="*60)
        print(f"STEP 3: GET CREATE META FOR {project}/{issue_type}")
        print("="*60)

        # Try new endpoint first (Jira Cloud)
        endpoint = f"/rest/api/3/issue/createmeta/{project}/issuetypes"
        response = self._request("GET", endpoint)

        if response.status_code == 200:
            data = response.json()
            print(f"\nAvailable issue types in {project}:")

            # Find Bug issue type ID
            bug_id = None
            for it in data.get("issueTypes", data.get("values", [])):
                it_name = it.get("name", "")
                it_id = it.get("id", "")
                print(f"  - {it_name} (ID: {it_id})")
                if it_name.lower() in ["bug", "defect"]:
                    bug_id = it_id

            if bug_id:
                # Get fields for this issue type
                fields_endpoint = f"/rest/api/3/issue/createmeta/{project}/issuetypes/{bug_id}"
                fields_response = self._request("GET", fields_endpoint)

                if fields_response.status_code == 200:
                    fields_data = fields_response.json()
                    print(f"\nFields available for {issue_type} in {project}:")
                    available_fields = fields_data.get("fields", fields_data.get("values", {}))

                    if isinstance(available_fields, dict):
                        for fid, finfo in available_fields.items():
                            if fid.startswith("customfield_"):
                                print(f"  - {fid}: {finfo.get('name', 'Unknown')}")
                    elif isinstance(available_fields, list):
                        for f in available_fields:
                            fid = f.get("fieldId", f.get("id", ""))
                            if fid.startswith("customfield_"):
                                print(f"  - {fid}: {f.get('name', 'Unknown')}")

                    return fields_data

        # Try legacy endpoint
        print(f"New endpoint returned {response.status_code}, trying legacy...")
        endpoint = f"/rest/api/3/issue/createmeta?projectKeys={project}&issuetypeNames={issue_type}&expand=projects.issuetypes.fields"
        response = self._request("GET", endpoint)

        if response.status_code != 200:
            print(f"ERROR: {response.status_code}")
            print(response.text[:500])
            return {}

        data = response.json()
        print("\nCreatemeta response (first 1500 chars):")
        print(json.dumps(data, indent=2)[:1500])
        return data

    # -------------------------------------------------------------------
    # STEP 4: Create Minimal Test Issue
    # -------------------------------------------------------------------
    def create_debug_issue(
        self,
        project: str,
        field_id: Optional[str] = None,
        field_name: Optional[str] = None,
        use_adf: bool = True,
        issue_type: str = "Bug",
    ) -> Optional[str]:
        """Create a minimal test issue with ONE custom field."""
        print("\n" + "="*60)
        print(f"STEP 4: CREATE DEBUG ISSUE (ADF={use_adf})")
        print("="*60)

        payload = {
            "fields": {
                "project": {"key": project},
                "summary": f"[DEBUG] Field Test - {field_name or 'No custom field'}",
                "issuetype": {"name": issue_type},
                "description": self.to_adf("Debug issue to test custom field population."),
            }
        }

        # Add the custom field if specified
        if field_id and field_name:
            test_value = f"DEBUG TEST VALUE - {field_name}"
            if use_adf:
                payload["fields"][field_id] = self.to_adf(test_value)
                print(f"Using ADF format for {field_id}")
            else:
                payload["fields"][field_id] = test_value
                print(f"Using plain text for {field_id}")

        print("\nREQUEST PAYLOAD:")
        print(json.dumps(payload, indent=2))

        response = self._request("POST", "/rest/api/3/issue", json=payload)

        print(f"\nSTATUS CODE: {response.status_code}")
        print("RESPONSE:")

        try:
            resp_json = response.json()
            print(json.dumps(resp_json, indent=2))
        except Exception:
            print(response.text[:500])

        if response.status_code == 201:
            issue_key = response.json().get("key")
            print(f"\n[SUCCESS] CREATED: {issue_key}")
            return issue_key
        else:
            print(f"\n[FAILED]")
            return None

    # -------------------------------------------------------------------
    # STEP 5: Verify Created Issue
    # -------------------------------------------------------------------
    def verify_issue(self, issue_key: str, field_id: Optional[str] = None) -> None:
        """Verify the custom field value on the created issue."""
        print("\n" + "="*60)
        print(f"STEP 5: VERIFY ISSUE {issue_key}")
        print("="*60)

        response = self._request("GET", f"/rest/api/3/issue/{issue_key}")

        if response.status_code != 200:
            print(f"ERROR: {response.status_code}")
            print(response.text[:500])
            return

        data = response.json()
        fields = data.get("fields", {})

        if field_id:
            print(f"\nField {field_id} value:")
            field_value = fields.get(field_id)
            if field_value:
                print(json.dumps(field_value, indent=2))
            else:
                print("None / Not Found")

        # Check all custom fields
        print("\n--- ALL CUSTOMFIELD VALUES ---")
        custom_count = 0
        for key, value in sorted(fields.items()):
            if key.startswith("customfield_"):
                if value is not None:
                    custom_count += 1
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    print(f"{key}: {value_str}")

        if custom_count == 0:
            print("No custom fields with values found!")

    # -------------------------------------------------------------------
    # BONUS: List all custom fields in project
    # -------------------------------------------------------------------
    def list_all_custom_fields(self, fields: List[Dict]) -> None:
        """List all custom fields available in the system."""
        print("\n" + "="*60)
        print("ALL CUSTOM FIELDS IN JIRA INSTANCE")
        print("="*60)

        custom_fields = [f for f in fields if f.get("custom")]
        print(f"\nTotal custom fields: {len(custom_fields)}\n")

        for f in sorted(custom_fields, key=lambda x: x.get("name", "")):
            schema = f.get("schema", {})
            print(f"ID: {f.get('id')}")
            print(f"  Name: {f.get('name')}")
            print(f"  Type: {schema.get('type')}")
            print(f"  Custom Type: {schema.get('custom')}")
            print()

    # -------------------------------------------------------------------
    # MAIN DEBUG FLOW
    # -------------------------------------------------------------------
    def run_debug(self, project: str = "CMB", issue_type: str = "Bug"):
        """Run the complete debug flow."""
        print("\n" + "#"*60)
        print("JIRA CUSTOM FIELD DEBUG SCRIPT")
        print("#"*60)
        print(f"Server: {self.server}")
        print(f"Project: {project}")
        print(f"Issue Type: {issue_type}")

        # Step 1: Get all fields
        all_fields = self.get_all_fields()
        if not all_fields:
            return

        # Step 2: Find relevant fields
        relevant = self.find_relevant_fields(all_fields)

        # List ALL custom fields
        self.list_all_custom_fields(all_fields)

        # Step 3: Get create meta
        self.get_create_meta(project, issue_type)

        # Step 4 & 5: Test creating issue with first relevant field
        if relevant:
            print("\n" + "="*60)
            print("TESTING FIRST RELEVANT FIELD")
            print("="*60)

            field_id, field_info = list(relevant.items())[0]
            field_name = field_info["name"]

            # Try with ADF first
            issue_key = self.create_debug_issue(
                project, field_id, field_name,
                use_adf=True, issue_type=issue_type
            )

            if issue_key:
                self.verify_issue(issue_key, field_id)
            else:
                # Retry without ADF
                print("\n--- RETRYING WITHOUT ADF ---")
                issue_key = self.create_debug_issue(
                    project, field_id, field_name,
                    use_adf=False, issue_type=issue_type
                )
                if issue_key:
                    self.verify_issue(issue_key, field_id)
        else:
            # No relevant fields found, create basic issue to verify connectivity
            print("\n--- CREATING BASIC TEST ISSUE (no custom field) ---")
            issue_key = self.create_debug_issue(
                project, issue_type=issue_type
            )
            if issue_key:
                self.verify_issue(issue_key)

        print("\n" + "#"*60)
        print("DEBUG COMPLETE")
        print("#"*60)
        print("\nNEXT STEPS:")
        print("1. Check if expected custom fields appear in 'ALL CUSTOM FIELDS' list")
        print("2. Check if fields appear in createmeta (fields on create screen)")
        print("3. If field not in createmeta -> Add to Bug create screen in Jira Admin")
        print("4. If ADF fails but plain text works -> Field doesn't support rich text")
        print("5. If both fail -> Check field permissions or project scope")


if __name__ == "__main__":
    import sys

    project = "CMB"
    issue_type = "Bug"

    if len(sys.argv) > 1:
        project = sys.argv[1]
    if len(sys.argv) > 2:
        issue_type = sys.argv[2]

    print(f"Running debug for project={project}, issue_type={issue_type}")
    print("To customize: python debug_jira_fields.py <PROJECT> <ISSUE_TYPE>")

    debugger = JiraFieldDebugger()
    debugger.run_debug(project=project, issue_type=issue_type)
