---
rule_type: financial_logic
module: gift_cards
risk_level: high
---

# Financial Logic: Gift Cards

## Overview

Gift Cards are digital vouchers that enterprises purchase to incentivize employees or guests. They represent pre-paid ride credit with configurable usage restrictions.

## Purchase Flow

### Budget Validation
```
IF wallet_balance >= gift_card_price:
    purchase_enabled = TRUE
ELSE:
    purchase_enabled = FALSE
    show_message("Add funds to buy")
```

### Financial Rules
- FIN-GC-001: Wallet balance must cover gift card price
- FIN-GC-002: Cost deducted immediately on purchase
- FIN-GC-003: Purchase is non-refundable (except via revert)

### Purchase Transaction
| Step | Action | Effect |
|------|--------|--------|
| 1 | Select template | Price displayed |
| 2 | Confirm purchase | Wallet -= Price |
| 3 | Card created | Status = ACTIVE |

## Card Configuration

### Configurable Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| Validity Start | When card becomes usable | Purchase date |
| Validity End | When card expires | Unlimited |
| Min Ride Cost | Minimum trip value to use card | 0 |
| Max Ride Cost | Maximum trip value covered | Card value |
| Total Uses | Lifetime usage limit | Unlimited |
| Uses per Day | Daily usage limit | Unlimited |
| Discount Rate | Percentage of trip covered | 100% |
| Pickup Location | Geofence for pickup | Any |
| Dropoff Location | Geofence for dropoff | Any |

### Default Settings
- FIN-GC-004: "Use default settings" = Unlimited everything, 100% coverage

## Usage Logic

### Eligibility Check
```
card_eligible = (
    card.status == ACTIVE
    AND current_date BETWEEN card.validity_start AND card.validity_end
    AND trip_cost >= card.min_ride_cost
    AND trip_cost <= card.max_ride_cost
    AND card.uses_today < card.daily_limit
    AND card.total_uses < card.lifetime_limit
    AND pickup IN card.allowed_pickups
    AND dropoff IN card.allowed_dropoffs
)
```

### Deduction Calculation
```
IF card_eligible:
    covered_amount = trip_cost * (card.discount_rate / 100)
    actual_deduction = MIN(covered_amount, card.remaining_balance)
    rider_pays = trip_cost - actual_deduction

    card.remaining_balance -= actual_deduction
    card.total_uses += 1
    card.uses_today += 1
```

### Financial Rules
- FIN-GC-005: Card covers up to discount_rate % of trip
- FIN-GC-006: Never deduct more than remaining balance
- FIN-GC-007: Rider pays difference if card insufficient
- FIN-GC-008: Trip blocked if rider cannot pay difference

## Balance Tracking

### Balance States
| State | Description |
|-------|-------------|
| Full | remaining_balance == original_value |
| Partial | 0 < remaining_balance < original_value |
| Exhausted | remaining_balance == 0 |

### Balance Updates
| Event | Effect |
|-------|--------|
| Purchase | remaining = original_value |
| Trip usage | remaining -= deduction |
| Revert | remaining -> 0, wallet += remaining |

## Revert (Balance Refund)

### Eligibility
- FIN-GC-009: Only cards with remaining_balance > 0 can be reverted

### Revert Process
```
IF card.remaining_balance > 0:
    enterprise_wallet += card.remaining_balance
    card.remaining_balance = 0
    card.status = REVERTED
    card.voucher_code = INVALIDATED
```

### Financial Rules
- FIN-GC-010: Revert credits company wallet immediately
- FIN-GC-011: Reverted card is permanently deactivated
- FIN-GC-012: Voucher code becomes invalid
- FIN-GC-013: No partial revert (all or nothing)

## Card Lifecycle Financial Impact

### Active Card
- Holds value on behalf of enterprise
- Value decreases with each use
- No wallet impact during usage

### Deactivated Card
- Manual deactivation by admin
- Remaining balance frozen
- Can still be reverted

### Expired Card
- Automatic when validity_end passed
- Remaining balance frozen
- Can still be reverted

### Reverted Card
- Balance returned to enterprise
- Card permanently unusable

## Admin Template Management

### Template Pricing
- FIN-GC-014: Templates country-specific
- FIN-GC-015: Amount set at template creation
- FIN-GC-016: B2B sees fixed price per template

### Template Lifecycle
| State | Purchases | Deletable | Effect |
|-------|-----------|-----------|--------|
| Active | 0 | Yes | Available for purchase |
| Active | >=1 | No | Deactivate only |
| Inactive | Any | No | Hidden from B2B |

## Financial Reporting

### Per-Card Metrics
| Metric | Calculation |
|--------|-------------|
| Original Value | Template amount |
| Total Spent | original - remaining |
| Trips Paid | Count of usages |
| Avg per Trip | Total Spent / Trips Paid |
| Remaining | Current balance |

### Enterprise Summary
| Metric | Calculation |
|--------|-------------|
| Total Purchased | Sum of all card values |
| Total Active | Sum of remaining balances |
| Total Used | Sum of (original - remaining) |
| Revert Total | Sum of reverted amounts |

## Edge Cases

### Edge Case 1: Trip Exceeds Card Balance
```
trip_cost = 500 DZD
card_remaining = 200 DZD
card_deduction = 200 DZD
rider_pays = 300 DZD from wallet/budget
```

### Edge Case 2: Below Minimum Ride Cost
- Card not eligible
- Rider pays full trip cost from wallet/budget

### Edge Case 3: Exceeds Daily Limit
- Card not eligible for this trip
- Rider pays full trip cost from wallet/budget

### Edge Case 4: Expired Card with Balance
- Card unusable for trips
- Balance can be reverted to wallet

### Edge Case 5: Concurrent Usage Attempt
- First request processed
- Second request sees updated balance
- Race condition handled at database level
