# Story Analysis Report – {{story_key}}

---

## 0. Story Overview

### Extracted Information

**Summary:**  
{{summary}}

**Description:**  
{{description}}

**Acceptance Criteria:**  
{{acceptance_criteria}}

**Dependencies:**  
{{dependencies}}

---

# 1. Functional Understanding

## 1.1 Business Goal
- What is the real business objective behind this story?
- What problem is being solved?
- What value does it bring?

## 1.2 Actor
- Who is the primary user / system actor?
- Are there secondary actors?

## 1.3 Trigger
- What initiates this flow?
- Is it manual, scheduled, event-driven, or API-based?

## 1.4 Functional Flow
- Main happy path
- Alternative flows
- Failure flows
- System interactions

---

# 2. Business Gaps

## 2.1 Missing Flows
- Are there alternative scenarios not covered?
- Are cancellation / retry flows defined?

## 2.2 Missing Validations
- Input validation rules?
- Mandatory vs optional fields?
- Format restrictions?

## 2.3 Undefined States
- Loading state?
- Partial success?
- Draft state?
- Archived / disabled state?

## 2.4 Completeness Review
- Is any required business logic missing?
- Is data persistence clearly defined?
- Are system boundaries clear?

---

# 3. Ambiguities

## 3.1 Undefined Limits
- Max/min values?
- Character limits?
- File size limits?
- Rate limits?

## 3.2 Undefined Error Behavior
- What happens on backend failure?
- Error message format?
- Retry behavior?
- Timeout handling?

## 3.3 Undefined Permissions
- Role-based access?
- Who can view/edit/delete?
- Cross-environment restrictions?

## 3.4 Clarity Issues
- Vague wording?
- Conflicting statements?
- Assumptions not explicitly stated?

---

# 4. Edge Cases

## 4.1 Input Edge Cases
- Empty input
- Null values
- Invalid format
- Special characters
- SQL injection patterns

## 4.2 Boundary Testing
- Min value
- Max value
- Over-limit values

## 4.3 Large Data Scenarios
- Large payloads
- Bulk operations
- High concurrency

## 4.4 Concurrency
- Multiple users updating simultaneously
- Race conditions
- Idempotency behavior

## 4.5 Environment Scenarios
- Different browsers
- Mobile vs desktop
- Network interruption

---

# 5. Risks & Impact

## 5.1 Functional Risks
- What existing modules may break?
- Backward compatibility risks?

## 5.2 Regression Impact
- Affected services?
- Affected APIs?
- Data migration risks?

## 5.3 Security Risks
- Authorization bypass?
- Data exposure?
- Injection risks?
- Sensitive data handling?

## 5.4 Performance Risks
- Response time expectations?
- Load impact?
- Database performance impact?

## 5.5 System Consistency
- Does it conflict with existing logic?
- Does it introduce technical debt?

---

# 6. Testability Review

## 6.1 Testable Criteria
- Are all acceptance criteria measurable?
- Are expected outputs clearly defined?

## 6.2 Non-Testable Areas
- Vague terms (e.g., "fast", "user-friendly")
- Undefined expected results
- Missing negative scenarios

## 6.3 Automation Feasibility
- API testable?
- UI automation feasible?
- Performance testable?
- Security testable?

---

# 7. Questions for Product / Business Team

### Business Clarifications
- {{question_1}}
- {{question_2}}
- {{question_3}}

### Validation & Rules
- {{question_4}}
- {{question_5}}

### Error Handling
- {{question_6}}
- {{question_7}}

### Permissions & Roles
- {{question_8}}
- {{question_9}}

### Edge & Risk Scenarios
- {{question_10}}
- {{question_11}}

---

# 8. Final QA Assessment

**Story Readiness Level:**  
- ☐ Ready  
- ☐ Needs Clarification  
- ☐ Blocked  

**Overall Risk Level:**  
- ☐ Low  
- ☐ Medium  
- ☐ High  

**QA Recommendation:**  
{{final_recommendation}}

---
