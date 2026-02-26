# Test Case Review: CMB-32860

**[ADMINPANEL] Payment Section**

*Generated: 2026-02-25 23:44:50*

---

## Story Details

- **Key:** CMB-32860
- **Status:** In Progress
- **Priority:** P2 - Medium
- **Type:** Story

### Description

As an admin on Admin Panel I need to manage all business-related payments in a centralized and dedicated Payment Management section that allows me to track online payments and bank/cheque transfers efficiently.

Acceptance Criteria

Scenario 01: Payment Section Structure

* As an admin
* When I access the Admin Panel
* Then I should see a new centralized section called Payments
* And the Payments section should contain two sub-sections:
** Online Payments
** Cheque / Bank Transfers

Scenario 02: Common table Online and Bank / Cheque Payments Screen

* As an admin
* When I open the Online Payments section
* Then I should see a list/table displaying the following columns:
** Month (displayed in letters)
** Transfer Date (Online payment Date when the business does an online payment, for bank transfers it should be the date of uploading bank payment receipt on webApp)
** Amount (Amount topped up by the business)
** Business Name (Name of the business that made the top-up)
** Budget Top-up Status, with the following states:
*** In progress
*** Done
** Action Column
*** Create pre-payment invoice
*** See all details

Scenario 03: Accessing Online payment details screen

* As an admin
* When I open the Online Payments section
* Then I should see a list/table displaying the following columns:
** Month (displayed in letters)
** Transfer Date
** *Value Date (Date when the company receives the funds should be filled manually by the admins)*
** Amount (Amount topped up by the business)
** Code 1 (Reference code identifying the payment source – e.g. YC3539332)
** Code 2 (Secondary reference code identifying the payment source – e.g. 21f98b20425d76e5c81f)
** Business Name (Name of the business that made the top-up)
** Budget Top-up Status, with the following states:
*** In progress
*** Done
** Attachments, including:
*** *Pre-payment invoice (Facture d’avance)*
*** *Payment receipt*
** Create Pre-payment Invoice button (should be disabled in case a pre-payment invoice is attached to the payment)

Scenario 03: Accessing Bank / Cheque Transfers Details Screen

* As an admin
* When I open the Online Payments section
* Then I should see a list/table displaying the following columns:
** Month (displayed in letters)
** Transfer Date
** Amount (Amount topped up by the business)
** Code 1 (Reference code identifying the payment source – e.g. YC3539332)
** Code 2 (Secondary reference code identifying the payment source – e.g. 21f98b20425d76e5c81f)
** Business Name (Name of the business that made the top-up)
** Budget Top-up Status, with the following states:
*** In progress
*** Done
** Attachments, including:
*** *Pre-payment invoice (Facture d’avance)*
** Create Pre-payment Invoice button (should be disabled in case a pre-payment invoice is attached to the payment)

Scenario 04: File Upload on Attachments

* As an admin
* When I visit a payment details screen (either online or bank/cheque transfers)
* Then I should be able to upload files in the Attachments section if they were empty
* And uploaded files should be linked to the corresponding payment entry

Scenario 05: Admin Comments

* As an admin
* When I visit a payment details screen (either online or bank/cheque transfers)
* Then I should be able to add comments
* And comments should be added to the activity log
* And each comment should include:
** Date
** Editor
** Value

Scenario 06: Notification on File Upload by Business

* As an admin
* When a business uploads a cheque or payment receipt (on bank transfers section on webApp)
* Then a notification should be sent to admins
* And the notification message should indicate: “Business X has uploaded a cheque / payment receipt for a completed bank Transfer”
* And when I click on the notification I should be redirected to the corresponding bank transfer details screen

Scenario 07: Notification on Pre-payment Invoice Creation

* As an admin
* When a pre-payment invoice is created
* Then a notification should be sent to relevant admins
* And the notification message should indicate: “Admin A has created a pre-payment invoice for Business X”
* Once the notification is clicked, admin is redirected to the details screen of the corresponding payment

Scenario 08: Notification on Admin Comment

* As an admin
* When another admin adds a comment on a pre-payment invoice
* Then a notification should be sent to relevant admins
* And the notification message should indicate: “Admin A has added a comment on Business X’s pre-payment invoice”
* and when the notification is clicked I should be redirected to the payment details screen for the corresponding comment

Scenario 09: Admin Permissions & Access Control

* As a superAdmin on adminPanel 
* When I access the Admin Permissions / Accesses screen
* Then I should be able to enable or disable access to the Payments section

Scenario 10: Pre-payment Invoice Template

* As an admin
* When I create a pre-payment invoice
* Then the invoice should follow the following template : [Factures d'avance sur consommation 2025 - Google Sheets|https://docs.google.com/spreadsheets/d/1nTlne6nA2zitIbsl7-hqLb_eDf-8BudOSaMGl32Ecjw/edit?gid=1823161240#gid=1823161240]

Scenario 11 : Budget topup status update 

* As an admin
* When I click on the status of the topup on 'budget topup' column
* Then I should be able to change the status manually from in progress to done or vice versa

Scenario 12 : Activity logs Records

* As an admin
* When I access the activity log section 
* Then the following records should be listed there
** updating status of the budget topup, 
** creation of a pre-payment invoice, 
** the date when was the line added to the table (the date of the online topup or the date of uploading the bank payment receipt on webApp

Scenario : Viewing Comments

* As an admin
* When I access the payment details screen and I click on a comment
* Then I should be able to see an overlay screen displaying the comment and it should not be an editable field

Scenario : Online Payment Notification Redirection

* As an admin
* When A user have done a successful online topup for their budget
* Then I should receive a notification that the business have done a successfull online payment (which we already have implemented) *and* Once the notification is clicked then I should be redirected to the payment details screen for the corresponding online payment

*Design :* 
[https://www.figma.com/design/QAWLLHSrk08BZi3jaDCpv4/-B2B----Ops-Dashboard-Handoff?node-id=14646-21194&t=xJGxDlXJaw2eDGp7-1|https://www.figma.com/design/QAWLLHSrk08BZi3jaDCpv4/-B2B----Ops-Dashboard-Handoff?node-id=14646-21194&t=xJGxDlXJaw2eDGp7-1|smart-link] 

### Acceptance Criteria

8.0

---

## Coverage Analysis

### Risk Level: CRITICAL

### Intents Requiring Test Coverage

- **payment_flow** (confidence: 90%)

### Domains to Cover

payments, b2b_pricing, admin_panel, invoicing, notification

---

## Coverage Gaps Detected

### RuleEngine Gaps

- **[info]** Matched rule: RULE-PAY-010 - Invoice generated at month end
- **[info]** Matched rule: RULE-ADMIN-004 - Single Super Admin per enterprise
- **[info]** Matched rule: RULE-PAY-020 - Commission displayed separately on invoice
- **[info]** Matched rule: RULE-ENT-004 - Phone Number Uniqueness
- **[info]** Matched rule: RULE-ADMIN-003 - Legal info required for invoice generation
- **[warning]** Critical rule not covered: RULE-TRIP-014 - Commission Calculation
  - *Suggestion:* Ensure story covers: ** Trip cost display/calculation
- **[warning]** Low rule coverage: 26%
  - *Suggestion:* Story may be missing important business rules

---

## Relevant Test Patterns from Knowledge Base

### Module

**payments/admin_panel:_payments_tab_2** (relevance: 75%)
> ## Admin Panel: Payments Tab

### Invoice Management

**Invoice History Dashboard:**
- Monthly cards (November 2025, October 2025, etc.)
- Status: Paid (Green), Unpaid (Red)
- Payment Date display
- Filter: All/Paid/Unpaid invoices

**Manual Invoice Generation:**
- "Generate an invoice" button
- Tri...

**payments/api_endpoints_7** (relevance: 75%)
> ## API Endpoints

### B2B Portal
- `GET /api/payments/balance` - Get wallet balance
- `POST /api/payments/topup` - Top up wallet
- `GET /api/payments/invoices` - List invoices
- `GET /api/payments/invoices/{id}` - Invoice details
- `GET /api/payments/plan` - Current payment plan

### Admin Panel
- `...

**payments/overview_0** (relevance: 72%)
> ## Overview

The Payments module manages all financial transactions for B2B clients, including prepaid wallet management, postpaid billing cycles, invoice generation, and payment reconciliation.

### Financial Logic

**b2b_pricing/currency_support_5** (relevance: 51%)
> ## Currency Support

| Country | Currency | Code | Symbol |
|---------|----------|------|--------|
| Algeria | Algerian Dinar | DZD | د.ج |
| Tunisia | Tunisian Dinar | TND | د.ت |
| Morocco | Moroccan Dirham | MAD | د.م. |
| Senegal | West African CFA | XOF | CFA |

### Currency Rules
- FIN-B2B-021...

**referral_rewards/overview_0** (relevance: 51%)
> ## Overview

Referral rewards are financial incentives given to enterprises that successfully refer other businesses to the Yassir Mobility platform. Rewards differ based on the referrer's payment plan.

**gift_card_logic/card_lifecycle_financial_impact_6** (relevance: 51%)
> ## Card Lifecycle Financial Impact

### Active Card
- Holds value on behalf of enterprise
- Value decreases with each use
- No wallet impact during usage

### Deactivated Card
- Manual deactivation by admin
- Remaining balance frozen
- Can still be reverted

### Expired Card
- Automatic when validit...

### Cross Dependency

**trip_booking_deps/regression_risk_areas_6** (relevance: 49%)
> ## Regression Risk Areas

When modifying any related module:

1. **Enterprise status** - Verify ACTIVE check
2. **User group membership** - Verify group requirement
3. **Program schedules** - Test day and time restrictions
4. **Ride limits** - Test all period types
5. **Budget limits** - Test all pe...

### Atomic Rule

**enterprise_rules/account_lifecycle_rules_0** (relevance: 55%)
> ## Account Lifecycle Rules

### RULE-ENT-001: Single Super Admin Policy
**Condition:** Enterprise account registration or admin promotion
**Validation:** Only ONE user can hold Super Admin role per enterprise
**Error:** "Enterprise already has a Super Admin. Demote existing before promotion."
**Prio...

**program_rules/program_lifecycle_rules_0** (relevance: 55%)
> ## Program Lifecycle Rules

### RULE-PROG-001: Group Requirement for Access
**Condition:** User attempts program access
**Validation:** User must belong to a group assigned to the program
**Error:** "You must be assigned to a group to access this program."
**Priority:** High

### RULE-PROG-002: Deac...

**trip_rules/financial_rules_2** (relevance: 53%)
> ## Financial Rules

### RULE-TRIP-010: Prepaid Deduction
**Condition:** Trip completed (FINISHED)
**Validation:** Trip cost deducted from enterprise wallet
**Error:** N/A (automatic deduction)
**Priority:** Critical

### RULE-TRIP-011: Postpaid Accrual
**Condition:** Trip completed (FINISHED)
**Vali...

### State Machine

**enterprise_states/valid_transitions_1** (relevance: 55%)
> ## Valid Transitions

| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| PENDING | ACTIVE | admin_approve | Legal info reviewed, documents valid |
| PENDING | INACTIVE | admin_reject | Rejection reason required |
| ACTIVE | INACTIVE | admin_deactivate | No ongoing trips |...

**challenge_states/audit_trail_9** (relevance: 55%)
> ## Audit Trail

| Event | Data Captured |
|-------|---------------|
| Creation | Timestamp, admin_id, config |
| Edit | Timestamp, admin_id, changes |
| Deactivation | Timestamp, admin_id |
| Deletion | Timestamp, admin_id |
| Tier Unlock | Timestamp, enterprise_id, tier_id |
| Completion | Timestam...

**challenge_states/valid_transitions_1** (relevance: 51%)
> ## Valid Transitions

| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| UPCOMING | ONGOING | start_date_reached | Current date >= start_date |
| UPCOMING | DISABLED | admin_deactivate | Admin action before start |
| ONGOING | COMPLETED | all_tiers_achieved | Enterprise c...

---

## Test Coverage Recommendations

### Priority Testing Areas

1. Financial Logic
1. State Machine

### Risk Areas Requiring Tests

- financial_impact
- state_transition
- data_integrity
- security
- high_risk_intent:payment_flow

### Suggested Test Types

- [ ] Happy path scenarios
- [ ] Edge cases and boundaries
- [ ] Error handling scenarios
- [ ] State transition tests
- [ ] Integration tests with dependent modules

---

## Analysis Metadata

**IMPORTANT:** This analysis is based ONLY on:
- Retrieved knowledge chunks from local knowledge base
- Validator findings (state, financial, rule, cross-dep)
- Story pre-analysis results

**Rules:**
1. Use ONLY the provided RAG context - do NOT invent information
2. If context is insufficient, clearly state "Insufficient Context"
3. Reference rule IDs when available (e.g., RULE-B2B-001)
4. Stay business-focused - avoid generic software advice
5. Do NOT suggest features not mentioned in the story

---

*Generated by QA RAG System*
*Timestamp: 2026-02-25 23:44:50*