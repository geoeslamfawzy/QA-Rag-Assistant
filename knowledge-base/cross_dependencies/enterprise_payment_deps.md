---
dependency_type: cross_module
modules: [enterprises, payments, trips]
risk_level: critical
---

# Cross Dependencies: Enterprise <-> Payments

## Overview

The relationship between Enterprise and Payments modules is fundamental to the Yassir Mobility B2B system. Payment plan selection affects nearly every aspect of enterprise operations, from dashboard display to trip processing and invoicing.

## Dependency Matrix

| Enterprise State | Payment Impact | Trip Impact |
|------------------|----------------|-------------|
| PENDING | No payments | No trips |
| ACTIVE (Prepaid) | Wallet active | Trip if balance > cost |
| ACTIVE (Postpaid) | Accrual active | Trip if used < limit |
| INACTIVE | Payments frozen | Trips blocked |

## Critical Dependencies

### DEP-EP-001: Dashboard Widget Adaptation
**Trigger:** Enterprise payment plan setting
**Dependency:** Dashboard displays different widgets based on plan

| Plan | Widget Display |
|------|----------------|
| Prepaid | Wallet Balance, Top-Up Button |
| Postpaid | Budget Used/Limit, Pay Due Button |

**Impact:** Wrong widget = user confusion, potential errors

### DEP-EP-002: Trip Booking Validation
**Trigger:** Trip booking attempt
**Dependency:** Validation logic varies by payment plan

**Prepaid:**
```
IF wallet_balance < estimated_trip_cost:
    BLOCK booking
    SHOW "Insufficient balance"
```

**Postpaid:**
```
IF (used_budget + estimated_trip_cost) > budget_limit:
    BLOCK booking
    SHOW "Budget limit exceeded"
```

**Impact:** Incorrect validation = over-spending or blocked legitimate trips

### DEP-EP-003: Trip Completion Financial Processing
**Trigger:** Trip status = FINISHED
**Dependency:** Settlement differs by plan

**Prepaid:**
```
wallet_balance -= trip_cost
LOG transaction: DEBIT
```

**Postpaid:**
```
used_budget += trip_cost
LOG accrual
```

**Impact:** Wrong processing = financial discrepancy

### DEP-EP-004: Refund Processing
**Trigger:** Refund approved
**Dependency:** Credit destination varies

**Prepaid:**
```
wallet_balance += refund_amount
IMMEDIATE effect
```

**Postpaid:**
```
used_budget -= refund_amount
(OR) invoice_total -= refund_amount
```

**Impact:** Wrong credit = balance errors

### DEP-EP-005: Invoice Generation Prerequisite
**Trigger:** Invoice generation request
**Dependency:** Legal info must be approved

```
IF enterprise.legal_info_status != APPROVED:
    BLOCK invoice generation
    SHOW "Legal info pending"
```

**Impact:** Invoice without legal info = compliance violation

### DEP-EP-006: Plan Switching Financial Settlement
**Trigger:** Payment plan change

**Prepaid -> Postpaid:**
```
existing_balance = wallet_balance
wallet_balance = 0
first_invoice_credit = existing_balance
```

**Postpaid -> Prepaid:**
```
IF outstanding_balance > 0:
    BLOCK switch
    SHOW "Settle outstanding balance first"
ELSE:
    wallet_balance = 0
```

**Impact:** Unsettled balance = financial loss

### DEP-EP-007: Referral Reward Invalidation
**Trigger:** Payment plan change
**Dependency:** All referral rewards expire

```
ON plan_switch:
    FOR reward IN enterprise.referral_rewards:
        reward.status = VOIDED
        LOG "Reward voided due to plan switch"
```

**Impact:** Rewards survive switch = incorrect entitlements

## State Transition Dependencies

### Enterprise Activation
**When:** PENDING -> ACTIVE
**Requires:**
- Legal info approved (for invoice-enabled)
- Payment plan selected
- (Prepaid) Initial balance OR (Postpaid) Budget limit set

### Enterprise Deactivation
**When:** ACTIVE -> INACTIVE
**Triggers:**
- Trip booking blocked
- Wallet/Budget frozen
- Ongoing trips must complete first

### Enterprise Reactivation
**When:** INACTIVE -> ACTIVE
**Requires:**
- (Prepaid) wallet_balance > 0
- (Postpaid) No overdue invoices

## Data Flow

```
[Enterprise Module]
      |
      | status, legal_info, payment_plan
      v
[Payments Module]
      |
      | balance, budget_limit, used_budget
      v
[Trips Module]
      |
      | booking_allowed, trip_cost
      v
[Financial Settlement]
```

## Regression Risk Areas

When modifying Enterprise or Payments:

1. **Dashboard widgets** - Verify correct display per plan
2. **Trip booking validation** - Test both plan types
3. **Trip completion processing** - Verify correct deduction/accrual
4. **Refund flow** - Test credit to correct destination
5. **Invoice generation** - Verify legal info check
6. **Plan switching** - Test balance handling
7. **Referral rewards** - Verify voiding on switch

## Test Scenarios

### Scenario 1: Prepaid Trip Booking
```
Given: Enterprise (Prepaid), wallet = 500 DZD
When: Book trip (estimated 300 DZD)
Then: Booking allowed
And: Wallet unchanged until completion
```

### Scenario 2: Prepaid Insufficient Balance
```
Given: Enterprise (Prepaid), wallet = 100 DZD
When: Book trip (estimated 300 DZD)
Then: Booking blocked
And: Show "Insufficient balance"
```

### Scenario 3: Postpaid Budget Limit
```
Given: Enterprise (Postpaid), used = 900, limit = 1000
When: Book trip (estimated 200 DZD)
Then: Booking blocked
And: Show "Budget limit exceeded"
```

### Scenario 4: Plan Switch with Balance
```
Given: Enterprise (Prepaid), wallet = 5000 DZD
When: Switch to Postpaid
Then: Wallet = 0
And: First invoice credit = 5000 DZD
And: Referral rewards voided
```

### Scenario 5: Invoice without Legal Info
```
Given: Enterprise, legal_info_status = PENDING
When: Request invoice generation
Then: Generation blocked
And: Show "Legal info pending"
```
