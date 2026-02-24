---
rule_type: financial_logic
module: payments
risk_level: high
---

# Financial Logic: B2B Pricing & Commission

## Commission Structure

### Default Commission
- Rate: 19%
- Application: Applied to base trip price
- Configurable: Yes, per enterprise

### Commission Calculation Formula
```
B2B_Price = Base_Trip_Price * (1 + Commission_Rate)
```

**Example:**
- Base Trip Price: 1,000 DZD
- Commission Rate: 19%
- B2B Price: 1,000 * 1.19 = 1,190 DZD

### Commission Override
- Admin Panel allows custom commission per enterprise
- Display: Shows percentage in Enterprise Settings
- Audit: Changes logged in Transaction Log

## Payment Plans

### Prepaid (Wallet-Based)

**How It Works:**
1. Enterprise tops up wallet
2. Trip cost deducted immediately on completion
3. Balance must cover trip cost before booking

**Key Rules:**
- FIN-B2B-001: Trip blocked if wallet balance < estimated trip cost
- FIN-B2B-002: Deduction occurs at trip FINISHED status
- FIN-B2B-003: Refunds credit wallet immediately
- FIN-B2B-004: Top-up requires payment proof document

**Wallet Operations:**
| Operation | Trigger | Effect |
|-----------|---------|--------|
| Top-up | Manual | +Amount to balance |
| Trip Deduction | Trip completed | -Trip cost |
| Refund | Admin action | +Refund amount |
| Gift Card Revert | Card revert | +Remaining balance |

### Postpaid (Credit-Based)

**How It Works:**
1. Enterprise has budget limit (credit ceiling)
2. Trips accrue throughout month
3. Invoice generated at month end
4. Payment reconciled manually

**Key Rules:**
- FIN-B2B-005: Trip blocked if (used + trip cost) > budget limit
- FIN-B2B-006: Charges accrue without immediate deduction
- FIN-B2B-007: Refunds reduce invoice amount
- FIN-B2B-008: Invoice requires approved legal info

**Budget Operations:**
| Operation | Trigger | Effect |
|-----------|---------|--------|
| Set Limit | Admin action | Sets ceiling |
| Trip Accrual | Trip completed | +Trip cost to used |
| Refund | Admin action | -Refund from used |
| Invoice Paid | Payment confirmed | Used resets |

## Plan Switching

### Prepaid to Postpaid
**Rule:** FIN-B2B-009
1. Warning displayed: "Existing balance deducted from first bill"
2. Prepaid balance recorded
3. First Postpaid invoice reduced by prepaid balance
4. Budget limit must be set immediately

### Postpaid to Prepaid
**Rule:** FIN-B2B-010
1. Outstanding balance must be settled first
2. No switch allowed with unpaid invoices
3. Wallet starts at zero

### Plan Switch Impact on Features
**Rule:** FIN-B2B-011
- Referral rewards EXPIRE immediately
- Free trips (Prepaid) do NOT convert to discounts
- Discounts (Postpaid) do NOT convert to free trips

## Discount & Rebates

### Configuration Options
- **Trigger:** Spending amount OR Ride count
- **Threshold:** Minimum to qualify (e.g., 20,000 DZD monthly)
- **Refund Percentage:** Rebate rate (e.g., 20%)

### Discount Application
```
Eligible_Amount = Total_Spending (if spending > threshold)
                  OR Total_Rides * Avg_Fare (if rides > count)
Discount = Eligible_Amount * Rebate_Percentage
```

**Rules:**
- FIN-B2B-012: Discounts apply at invoice generation
- FIN-B2B-013: Discount cannot exceed total invoice
- FIN-B2B-014: Multiple discount rules stack

## Invoice Generation

### Invoice Components
| Component | Description |
|-----------|-------------|
| Service Fees | Platform commission portion |
| Driver Fees | Base fare to driver |
| Subtotal HT | Pre-tax total |
| TVA | Tax amount (rate varies by country) |
| Total TTC | Final amount due |

### Invoice Requirements
- FIN-B2B-015: Legal info must be approved
- FIN-B2B-016: All required documents: NIF, NIS, RC, AI
- FIN-B2B-017: Invoice sent via email to Super Admin

### Payment Reconciliation
- FIN-B2B-018: Manual payment update in Admin Panel
- FIN-B2B-019: Payment proof required (PDF/Docx)
- FIN-B2B-020: Status updates: Unpaid -> Paid

## Currency Support

| Country | Currency | Code | Symbol |
|---------|----------|------|--------|
| Algeria | Algerian Dinar | DZD | د.ج |
| Tunisia | Tunisian Dinar | TND | د.ت |
| Morocco | Moroccan Dirham | MAD | د.م. |
| Senegal | West African CFA | XOF | CFA |

### Currency Rules
- FIN-B2B-021: All amounts stored in local currency
- FIN-B2B-022: No cross-currency transactions
- FIN-B2B-023: Each enterprise operates in single currency

## Tax Calculations

### Tax by Region
| Country | Tax Type | Rate |
|---------|----------|------|
| Algeria | TVA | 19% |
| Tunisia | TVA | 19% |
| Morocco | TVA | 20% |
| Senegal | TVA | 18% |

### Tax Rules
- FIN-B2B-024: Tax calculated on post-discount amount
- FIN-B2B-025: Tax displayed separately on invoice
- FIN-B2B-026: Business-to-business transactions may have exemptions

## Rounding Rules

- FIN-B2B-027: All amounts rounded to 2 decimal places
- FIN-B2B-028: Round UP for charges
- FIN-B2B-029: Round DOWN for refunds
- FIN-B2B-030: Display in whole units for local currencies (DZD, XOF)
