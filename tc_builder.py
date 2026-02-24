#!/usr/bin/env python3
"""
Test Case Builder Module

Builds structured TestCase objects from Jira story data.
Extracts scenarios from description and acceptance criteria to create BDD-style test cases.
"""
import re
from typing import Dict, Any, List, Tuple

from models.test_case import TestCase


class TestCaseBuilder:
    """
    Builds structured test cases from Jira issue data.

    Extracts scenarios from issue description and acceptance criteria,
    then creates TestCase objects with BDD steps.
    """

    # Standard test cases that are added to every story
    STANDARD_TEST_CASES = [
        {
            "title": "Validate non-admin or user without permission cannot access the feature",
            "steps": [
                "Given: I am not an admin / do not have access",
                "When: I try to open the feature",
                "Then: Access is denied with appropriate error message"
            ],
            "preconditions": ["User is logged in without required permissions"],
            "expected": ["Access denied", "Error message displayed"],
            "type": "Security",
        },
        {
            "title": "Verify invalid or unsupported file type is rejected on upload",
            "steps": [
                "Given: I am on a screen that allows file upload",
                "When: I upload an invalid file type",
                "Then: Upload is rejected with a clear message"
            ],
            "preconditions": ["File upload feature is available"],
            "expected": ["Upload rejected", "Clear error message shown"],
            "type": "Negative",
        },
        {
            "title": "Verify oversized file is rejected on upload",
            "steps": [
                "Given: I am on a screen that allows file upload",
                "When: I upload a file over the max size",
                "Then: Upload is rejected with a clear message"
            ],
            "preconditions": ["File upload feature is available"],
            "expected": ["Upload rejected", "Size limit error shown"],
            "type": "Negative",
        },
        {
            "title": "Verify empty list or no data shows correct empty state",
            "steps": [
                "Given: There is no data for the current view",
                "When: I open the list/screen",
                "Then: An empty state message is shown, not a broken layout"
            ],
            "preconditions": ["Feature is available"],
            "expected": ["Empty state message displayed", "Layout remains intact"],
            "type": "Edge",
        },
    ]

    def build(self, issue: Dict[str, Any], risk_level: str = "MEDIUM") -> List[TestCase]:
        """
        Build test cases from a Jira issue.

        Args:
            issue: Jira issue dictionary with key, summary, description, acceptance_criteria.
            risk_level: Risk level from RAG pre-analysis (CRITICAL, HIGH, MEDIUM, LOW).

        Returns:
            List of TestCase objects.
        """
        description = issue.get("description", "") or ""
        acceptance_criteria = issue.get("acceptance_criteria", "") or ""
        full_text = f"{description}\n\n{acceptance_criteria}"

        # Extract scenarios from the full text
        scenarios = self._extract_scenarios(full_text)

        test_cases = []
        tc_id = 1

        # Build test cases from extracted scenarios
        for sc_title, sc_body in scenarios:
            steps = self._build_bdd_steps(sc_body)
            summary = self._build_summary(sc_title)

            tc = TestCase(
                id=f"TC-{tc_id:02d}",
                summary=summary,
                preconditions=["User has required role and access"],
                steps=steps,
                expected=["Behaviour matches acceptance criteria"],
                test_type="Positive",
                risk_level=risk_level,
            )
            test_cases.append(tc)
            tc_id += 1

        # Add standard test cases
        for std_tc in self.STANDARD_TEST_CASES:
            tc = TestCase(
                id=f"TC-{tc_id:02d}",
                summary=std_tc["title"],
                preconditions=std_tc["preconditions"],
                steps=std_tc["steps"],
                expected=std_tc["expected"],
                test_type=std_tc["type"],
                risk_level=risk_level,
            )
            test_cases.append(tc)
            tc_id += 1

        return test_cases

    def _extract_scenarios(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract scenario title and body from text.

        Args:
            text: Full text from description and acceptance criteria.

        Returns:
            List of (title, body) tuples.
        """
        if not text:
            return []

        scenarios = []

        # Match patterns like:
        # "Scenario 01: Title" or "Scenario : Title" or "Scenario 12 : Title"
        pattern = re.compile(
            r"Scenario\s*(\d*)\s*[:\-]\s*([^\n*]+)\s*\n(.*?)(?=Scenario\s|\Z)",
            re.IGNORECASE | re.DOTALL,
        )

        for m in pattern.finditer(text):
            num, title, body = m.group(1), m.group(2).strip(), m.group(3).strip()

            # Clean up body text
            body = re.sub(r"\*+", "", body).strip()
            body = " ".join(body.split())[:800]

            # Format title
            if num:
                scenarios.append((f"Scenario {num}: {title}", body))
            else:
                scenarios.append((title, body))

        return scenarios

    def _build_bdd_steps(self, body: str) -> List[str]:
        """
        Build Given/When/Then steps from scenario body.

        Args:
            body: Scenario body text.

        Returns:
            List of BDD step strings.
        """
        lines = [l.strip() for l in body.split(".") if l.strip()]

        given = []
        when = []
        then = []

        for line in lines:
            line_lower = line.lower()
            if line_lower.startswith("as "):
                given.append(line)
            elif line_lower.startswith("given "):
                given.append(line)
            elif line_lower.startswith("when "):
                when.append(line)
            elif line_lower.startswith("then "):
                then.append(line)
            elif line_lower.startswith("and "):
                # Add to the last non-empty category
                if then:
                    then.append(line)
                elif when:
                    when.append(line)
                else:
                    given.append(line)
            else:
                # Default to expected behavior
                then.append(line)

        steps = []

        if given:
            steps.append(f"Given: {'; '.join(given[:2])}")

        if when:
            steps.append(f"When: {when[0]}")
            for additional in when[1:3]:
                steps.append(f"And: {additional}")

        if then:
            steps.append(f"Then: {then[0]}")
            for additional in then[1:3]:
                steps.append(f"And: {additional}")

        # If no structured steps found, use body as a single step
        if not steps:
            steps = [f"Given: User is on the feature", f"When: User performs the action", f"Then: {body[:200]}"]

        return steps

    def _build_summary(self, sc_title: str) -> str:
        """
        Build test case summary from scenario title.

        Ensures the summary starts with a verification verb.

        Args:
            sc_title: Scenario title from extraction.

        Returns:
            Formatted summary string.
        """
        short_title = sc_title[:80] if len(sc_title) > 80 else sc_title

        # Check if title already has a verification verb
        title_lower = short_title.lower()
        has_verb = any(title_lower.startswith(v) for v in ["verify", "validate", "test", "check", "ensure"])

        if has_verb:
            return short_title
        else:
            return f"Verify {short_title}"


# Backward compatibility function
def generate_test_cases(issue: Dict[str, Any]) -> str:
    """
    Legacy function for backward compatibility.

    Generates markdown string for test cases (original behavior).
    Use TestCaseBuilder.build() for structured output.
    """
    from exporters.markdown_exporter import MarkdownExporter

    builder = TestCaseBuilder()
    test_cases = builder.build(issue)

    # Build markdown manually for backward compatibility
    key = issue.get("key", "UNKNOWN")
    title = issue.get("summary", "")

    def escape_cell(s: str) -> str:
        if not s:
            return "—"
        return s.replace("|", "\\|").replace("\n", " ").strip()[:500]

    header = f"# Test Cases – {key}\n**{escape_cell(title)}**\n\n---\n\n"
    table_header = (
        "| TC ID | Title | Precondition | Steps (BDD) | Test Data | "
        "Expected Result | Type | Priority |\n"
        "|-------|--------|--------------|-------------|-----------|"
        "-----------------|------|----------|\n"
    )

    rows = [tc.to_markdown_row() for tc in test_cases]
    table_rows = "\n".join(rows)

    summary = (
        f"\n\n---\n\n**Summary**\n"
        f"- **Total test cases:** {len(test_cases)}\n"
        f"- **Types:** Positive, Negative, Edge, Security.\n"
        f"- **Priorities:** P1, P2.\n"
    )

    return header + table_header + table_rows + summary
