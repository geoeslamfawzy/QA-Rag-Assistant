# Jira Test Case Generator Prompt

## Task
Generate detailed test cases for a given Jira story.

⚠️ Do NOT generate test cases before a specific user story is provided.

---

## Story Key:
{{story_key}}

---

## Instructions

Generate test cases based on the provided user story and all Acceptance Criteria (AC).

Cover the following:

- Positive scenarios
- Negative scenarios
- Boundary cases
- Role-based scenarios
- API validation
- Integration scenarios
- Error handling
- Security validations

Each Acceptance Criteria must be fully covered.

No duplicate test cases.

Use simple B1 English level.
Use short and clear sentences.
Avoid complex statements.

---

## Test Case Writing Rules

- Use BDD format (Given / When / Then).
- Title must start with:
  - Verify
  - Validate
  - Test
- Use professional QA language.
- Expected result must be clear and measurable.
- Prioritize based on risk.
- Keep statements short and direct.

---

## Output Format

# Test Cases – {{story_key}}

| TC ID | Title | Precondition | Steps (BDD) | Test Data | Expected Result | Type | Priority |

---

## Types

- Positive
- Negative
- Edge
- Security
- Integration
- Regression
