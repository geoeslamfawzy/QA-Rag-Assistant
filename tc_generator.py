#!/usr/bin/env python3
"""
Test case generator for Jira stories.
Produces BDD-style test cases in the QA table format from story description and AC.
"""
import re
from typing import Dict, Any, List, Tuple


def _escape_table_cell(s: str) -> str:
    """Escape pipe and newlines for markdown table."""
    if not s:
        return "—"
    return s.replace("|", "\\|").replace("\n", " ").strip()[:500]


def _extract_scenarios(description: str) -> List[Tuple[str, str]]:
    """Extract scenario title and body from description. Returns list of (title, body)."""
    if not description:
        return []
    scenarios = []
    # Match "Scenario 01: Title" or "Scenario : Title" or "Scenario 12 : Title"
    pattern = re.compile(
        r"Scenario\s*(\d*)\s*[:\-]\s*([^\n*]+)\s*\n(.*?)(?=Scenario\s|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(description):
        num, title, body = m.group(1), m.group(2).strip(), m.group(3).strip()
        body = re.sub(r"\*+", "", body).strip()
        body = " ".join(body.split())[:800]
        scenarios.append((f"Scenario {num}: {title}" if num else title, body))
    return scenarios


def _steps_from_scenario(body: str) -> str:
    """Build Given/When/Then steps from scenario body."""
    lines = [l.strip() for l in body.split(".") if l.strip()]
    given = []
    when = []
    then = []
    for line in lines:
        line_lower = line.lower()
        if line_lower.startswith("as "):
            given.append(line)
        elif line_lower.startswith("when "):
            when.append(line)
        elif line_lower.startswith("then ") or line_lower.startswith("and "):
            then.append(line)
        else:
            then.append(line)
    parts = []
    if given:
        parts.append("Given " + "; ".join(given[:2]))
    if when:
        parts.append("When " + when[0])
    if then:
        parts.append("Then " + then[0])
    return "<br>".join(parts) if parts else body[:300]


def generate_test_cases(issue: Dict[str, Any]) -> str:
    """
    Generate test cases markdown for a Jira issue.
    Uses description and acceptance criteria to build BDD-style TC table.
    """
    key = issue.get("key", "UNKNOWN")
    title = issue.get("summary", "")
    description = issue.get("description", "") or ""
    full_text = description + "\n\n" + (issue.get("acceptance_criteria") or "")

    scenarios = _extract_scenarios(full_text)
    rows = []

    # One or two TCs per scenario
    tc_id = 1
    for sc_title, sc_body in scenarios:
        steps = _steps_from_scenario(sc_body)
        short_title = sc_title[:80] if len(sc_title) > 80 else sc_title
        title_verb = "Verify" if "verify" not in short_title.lower() and "validate" not in short_title.lower() else ""
        tc_title = f"Verify {short_title}" if title_verb == "Verify" else short_title
        if not tc_title.startswith(("Verify", "Validate", "Test")):
            tc_title = "Verify " + tc_title
        rows.append(
            (
                f"TC-{tc_id:02d}",
                _escape_table_cell(tc_title),
                "User has required role and access.",
                _escape_table_cell(steps),
                "—",
                "Behaviour matches acceptance criteria.",
                "Positive",
                "P1",
            )
        )
        tc_id += 1

    # Standard negative/security/edge TCs
    standard = [
        (
            "Validate non-admin or user without permission cannot access the feature",
            "Given I am not an admin / do not have access.<br>When I try to open the feature.<br>Then access is denied.",
            "Security",
            "P1",
        ),
        (
            "Verify invalid or unsupported file type is rejected on upload",
            "Given I am on a screen that allows file upload.<br>When I upload an invalid file type.<br>Then upload is rejected with a clear message.",
            "Negative",
            "P2",
        ),
        (
            "Verify oversized file is rejected on upload",
            "Given I am on a screen that allows file upload.<br>When I upload a file over the max size.<br>Then upload is rejected with a clear message.",
            "Negative",
            "P2",
        ),
        (
            "Verify empty list or no data shows correct empty state",
            "Given there is no data for the current view.<br>When I open the list/screen.<br>Then an empty state message is shown, not a broken layout.",
            "Edge",
            "P2",
        ),
    ]
    for st_title, st_steps, st_type, st_prio in standard:
        rows.append(
            (
                f"TC-{tc_id:02d}",
                st_title,
                "Feature is available.",
                st_steps,
                "—",
                "System behaves as described in steps.",
                st_type,
                st_prio,
            )
        )
        tc_id += 1

    # Build markdown table
    header = f"# Test Cases – {key}  \n**{_escape_table_cell(title)}**\n\n---\n\n"
    table_header = "| TC ID | Title | Precondition | Steps (BDD) | Test Data | Expected Result | Type | Priority |\n|-------|--------|--------------|-------------|-----------|-----------------|------|----------|\n"
    table_rows = "\n".join(
        "| " + " | ".join(r) + " |" for r in rows
    )
    summary = f"\n\n---\n\n**Summary**  \n- **Total test cases:** {len(rows)}  \n- **Types:** Positive, Negative, Edge, Security.  \n- **Priorities:** P1, P2.\n"
    return header + table_header + table_rows + summary
