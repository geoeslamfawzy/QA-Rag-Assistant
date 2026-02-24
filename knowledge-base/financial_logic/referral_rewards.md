---
rule_type: financial_logic
module: referrals
risk_level: high
---

# Financial Logic: Referral Rewards

## Overview

Referral rewards are financial incentives given to enterprises that successfully refer other businesses to the Yassir Mobility platform. Rewards differ based on the referrer's payment plan.

## Prepaid Rewards (Free Trips)

### How It Works
1. Referrer invites a business
2. Referee completes qualification criteria
3. Referrer receives free trips

### Reward Configuration
| Parameter | Description | Default |
|-----------|-------------|---------|
| Completion Threshold | Trigger condition target | Varies |
| Free Trips Count | Number of free trips | Up to 20 |
| Price Limit per Trip | Maximum trip value covered | e.g., 2,000 DZD |
| Validity Period | How long rewards last | 1 month |

### Trigger Conditions (Choose One)
1. **Budget Top-up:** Referee tops up wallet by X amount
2. **Rides Completion:** Referee completes X trips
3. **Members Onboarded:** Referee invites X members

### Financial Rules
- FIN-REF-001: Maximum 20 free trips per successful referral
- FIN-REF-002: Price limit is binary: trip eligible if cost <= limit
- FIN-REF-003: Trip cost exceeding limit = not covered, pay full price
- FIN-REF-004: Free trips valid for 1 month from issuance
- FIN-REF-005: Expired free trips are voided, no conversion

### Reward Stacking
- FIN-REF-006: Multiple referrals stack rewards
- Example: 5 successful referrals = 5 x 20 = 100 free trips available

### Free Trip Deduction Logic
```
IF trip_cost <= price_limit:
    deduct_from_free_trips(1)
    wallet_deduction = 0
ELSE:
    deduct_from_wallet(trip_cost)
    free_trips_unchanged()
```

## Postpaid Rewards (Invoice Discount)

### How It Works
1. Referrer invites a business
2. Referee completes qualification criteria
3. Referrer receives discount percentage on invoice

### Reward Configuration
| Parameter | Description | Default |
|-----------|-------------|---------|
| Completion Threshold | Trigger condition target | Varies |
| Discount Percentage | Invoice reduction rate | e.g., 10% |
| Reward Price Limit | Maximum discount value | Optional cap |
| Validity Date | Optional expiry | None |

### Trigger Conditions (Choose One)
1. **Amount Spent:** Referee spends X amount
2. **Rides Completion:** Referee completes X trips
3. **Members Onboarded:** Referee invites X members

### Financial Rules
- FIN-REF-007: Discount percentages accumulate
- FIN-REF-008: Maximum cumulative discount = 100%
- FIN-REF-009: Discount applied at invoice generation
- FIN-REF-010: Price limit caps maximum discount amount

### Reward Stacking
- FIN-REF-011: Multiple referrals stack percentages
- Example: 10 referrals x 10% each = 100% discount (max)

### Discount Calculation
```
total_discount_percent = MIN(sum(all_referral_percents), 100%)
discount_amount = invoice_total * total_discount_percent
IF price_limit_set:
    discount_amount = MIN(discount_amount, price_limit)
final_invoice = invoice_total - discount_amount
```

## Plan Switching Impact

### CRITICAL RULE: FIN-REF-012
**Payment plan change (Prepaid <-> Postpaid) = ALL rewards EXPIRE immediately**

### Conversion Rules
- FIN-REF-013: Free trips do NOT convert to invoice discounts
- FIN-REF-014: Invoice discounts do NOT convert to free trips
- FIN-REF-015: No partial conversion or proration

### Switch Scenarios
| From | To | Result |
|------|-----|--------|
| Prepaid (50 free trips) | Postpaid | 50 trips LOST |
| Postpaid (30% discount) | Prepaid | 30% discount LOST |

## Rule Hierarchy

### Priority Order
1. Enterprise-specific rule (highest priority)
2. Country-level rule (default)

### Rule Management
- FIN-REF-016: Enterprise rule overrides country rule completely
- FIN-REF-017: Deleting enterprise rule reverts to country rule
- FIN-REF-018: "Use country configuration" checkbox inherits defaults

## Reward Status Tracking

### Reward States
| State | Description |
|-------|-------------|
| AVAILABLE | Ready to use |
| USED | Consumed (free trip taken or discount applied) |
| EXPIRED | Validity period ended |
| VOIDED | Plan switched, reward invalidated |

### State Transitions
| From | To | Trigger |
|------|-----|---------|
| AVAILABLE | USED | Trip/Invoice processed |
| AVAILABLE | EXPIRED | Validity date passed |
| AVAILABLE | VOIDED | Payment plan changed |

## Financial Audit Trail

### Logged Events
- Referral completion
- Reward issuance
- Reward usage (each trip/invoice)
- Reward expiry
- Reward voiding (plan switch)

### Audit Data
| Field | Description |
|-------|-------------|
| Timestamp | Event time |
| Enterprise ID | Referrer |
| Referee ID | Referred business |
| Reward Type | Free trips / Discount % |
| Reward Value | Trips count or percentage |
| Status | Current state |

## Edge Cases

### Edge Case 1: Partial Referral
- Referee starts qualification but doesn't complete
- Status remains PENDING
- No reward issued

### Edge Case 2: Referee Deactivation
- Referee deactivated after referrer gets reward
- Reward remains valid (no clawback)

### Edge Case 3: Multiple Referrers
- Only first referrer gets credit (first-touch attribution)

### Edge Case 4: Self-Referral Attempt
- System blocks (same email domain detection)
- No reward issued
