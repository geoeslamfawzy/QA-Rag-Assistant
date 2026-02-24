---
rule_type: financial_logic
module: subscription
risk_level: high
---

# Financial Logic: Pricing & Calculations

## Plan Pricing

| Plan | Monthly | Annual | Savings |
|------|---------|--------|---------|
| Basic | $10.00 | $100.00 | 17% |
| Premium | $25.00 | $250.00 | 17% |
| Enterprise | Custom | Custom | Negotiated |

## Proration Calculations

### Upgrade Proration Formula

When upgrading mid-cycle:

```
prorated_charge = (new_plan_price - old_plan_price) * (remaining_days / total_days_in_cycle)
```

**Example:**
- Current: Basic ($10/month)
- New: Premium ($25/month)
- Day 15 of 30-day cycle
- Remaining: 15 days

```
prorated_charge = ($25 - $10) * (15 / 30) = $15 * 0.5 = $7.50
```

### Downgrade Credit

Downgrades do NOT generate credits or refunds:
- Access to higher tier continues until cycle end
- New (lower) price applies at next renewal

## Discount Rules

### Coupon Types
- **Percentage**: 10%, 20%, 50% off
- **Fixed Amount**: $5, $10, $25 off
- **Free Trial Extension**: +7, +14 days

### Discount Constraints

FIN-001: Discount cannot exceed 100% of charge
FIN-002: Maximum one coupon per transaction
FIN-003: Coupons cannot be stacked
FIN-004: Minimum order after discount: $0.50

### Discount Application Order

1. Apply percentage discount first
2. Apply fixed amount discount second
3. Apply any credits last

## Tax Calculations

### Tax Rates by Region

| Region | Tax Type | Rate |
|--------|----------|------|
| US (most states) | Sales Tax | 0-10% |
| EU | VAT | 20-25% |
| UK | VAT | 20% |
| UAE | VAT | 5% |
| Saudi Arabia | VAT | 15% |

### Tax Calculation Rules

FIN-005: Tax is calculated on post-discount amount
FIN-006: Tax-exempt users must have valid exemption certificate
FIN-007: B2B transactions may be reverse-charged (EU VAT)

### Display Rules

- Prices shown are exclusive of tax by default
- Tax amount shown separately at checkout
- Final amount = subtotal + tax

## Refund Calculations

### Full Refund
```
refund_amount = original_charge - any_used_credits
```

### Partial Refund (Service Issue)
```
refund_amount = original_charge * (unused_days / total_days)
```

### Partial Refund (Discretionary)
```
refund_amount = MIN(requested_amount, eligible_amount)
```

## Currency Handling

### Supported Currencies
- USD (default)
- EUR
- GBP
- AED
- SAR

### Conversion Rules

FIN-008: Store all amounts in base currency (USD) internally
FIN-009: Display in user's preferred currency
FIN-010: Lock exchange rate at time of transaction
FIN-011: Conversion fees apply (2.5%)

### Rounding Rules

- Always round UP to nearest cent for charges
- Always round DOWN to nearest cent for refunds
- Use banker's rounding for display purposes
