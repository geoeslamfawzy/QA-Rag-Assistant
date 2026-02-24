---
module: payments
version: 1.0
last_updated: 2024-02-24
dependencies:
  - enterprises
  - trips
  - b2b_portal
  - admin_panel
---

# Payments Module

## Overview

The Payments module manages all financial transactions for B2B clients, including prepaid wallet management, postpaid billing cycles, invoice generation, and payment reconciliation.

## B2B Portal: Payments

### Payment Plan Display

**Prepaid Account View:**
- Remaining Budget prominently displayed (e.g., "307.85K DZD")
- "Budget top-up" button
- Payment Plan label: "Prepaid"
- Monthly invoices access: "View all"

**Postpaid Account View:**
- Budget field (current usage)
- Monthly budget field
- No top-up option
- Payment Plan label: "Pay Later"
- Monthly invoices access: "View all"

### Dashboard Financial Widget

**Prepaid:**
- Current Wallet Balance
- "Top Up Budget" action

**Postpaid:**
- Budget usage vs Budget limit
- "Pay Due Budget" action

## Admin Panel: Payments Tab

### Invoice Management

**Invoice History Dashboard:**
- Monthly cards (November 2025, October 2025, etc.)
- Status: Paid (Green), Unpaid (Red)
- Payment Date display
- Filter: All/Paid/Unpaid invoices

**Manual Invoice Generation:**
- "Generate an invoice" button
- Triggers email to registered Super Admin
- Email subject: "Yassir Business Invoice"
- Attachment: Standardized PDF invoice

**Invoice PDF Contents:**
- Client Info: Company Name, Address, RC/NIF/NIS/AI numbers
- Service Breakdown: Platform fees vs Driver service fees
- Totals: HT (Excl. Tax), TVA (Tax), TTC (Incl. Tax)
- Banking Details: Yassir bank account for wire transfers

**Payment Status Updates:**
- Manual reconciliation for off-platform payments
- Input: Amount Paid, Date of Payment
- Proof upload: PDF/Docx (bank slip)
- Result: Invoice status -> Paid

### Wallet & Budget Management

**Prepaid Workflow (Top-Up):**
1. Click "Top up Balance"
2. Enter amount
3. Attach payment document or transaction link
4. Click "Top-up Balance"
5. Amount credited immediately

**Postpaid Workflow (Credit Limit):**
- Widget shows "Enterprise Budget Limit"
- "Update Budget" adjusts credit ceiling
- Ceiling = maximum debt allowed

### Payment Plan Switching

**Prepaid to Postpaid:**
- Warning: Existing balance deducted from first bill
- Step 1: Confirm switch
- Step 2: Set Budget Limit immediately

**Postpaid to Prepaid:**
- Outstanding balance must be settled
- Wallet starts at zero

## Commission & Pricing

### B2B Commission Structure
- Default Commission: 19%
- Formula: `B2B_Price = Base_Trip_Price * (1 + Commission%)`
- Example: 1000 DZD trip = 1190 DZD B2B price
- Commission configurable per enterprise

### Discount & Rebates

**Configuration Steps:**
1. Define trigger condition (Spending amount or Ride count)
2. Define threshold (e.g., Monthly amount > 20,000 DZD)
3. Define refund percentage (e.g., 20%)

**Display:** Shows active rule (e.g., "20% - 20000 DZD")

## Business Rules

### General Payment Rules
- RULE-PAY-001: All amounts stored in local currency
- RULE-PAY-002: Commission calculated on base fare
- RULE-PAY-003: Tax (TVA) calculated on post-discount amount

### Prepaid Rules
- RULE-PAY-004: Trip blocked if wallet balance < trip cost
- RULE-PAY-005: Balance deducted immediately on trip completion
- RULE-PAY-006: Top-up requires payment proof
- RULE-PAY-007: Refunds credit wallet immediately

### Postpaid Rules
- RULE-PAY-008: Trip blocked if budget limit exceeded
- RULE-PAY-009: Charges accrued throughout month
- RULE-PAY-010: Invoice generated at month end
- RULE-PAY-011: Refunds reduce invoice amount

### Plan Switching Rules
- RULE-PAY-012: Prepaid -> Postpaid: Balance deducted from first invoice
- RULE-PAY-013: Postpaid -> Prepaid: Outstanding must be settled first
- RULE-PAY-014: Referral rewards expire on plan switch

### Invoice Rules
- RULE-PAY-015: Legal info required for invoice generation
- RULE-PAY-016: Invoice includes tax breakdown (HT, TVA, TTC)
- RULE-PAY-017: Manual payment updates require proof

### Commission Rules
- RULE-PAY-018: Default commission 19%
- RULE-PAY-019: Commission can be overridden per enterprise
- RULE-PAY-020: Commission displayed separately on invoice

## Financial Calculations

### Trip Cost Calculation
```
Base_Price = Driver fare
B2B_Price = Base_Price * (1 + Commission_Rate)
Tax = B2B_Price * Tax_Rate
Total = B2B_Price + Tax
```

### Discount Application
```
Eligible = (Condition met: spending > threshold OR rides > count)
Discount = Eligible_Amount * Discount_Percentage
Net_Invoice = Total_Invoice - Discount
```

### Refund Calculation
```
Prepaid: Wallet += Refund_Amount
Postpaid: Invoice_Due -= Refund_Amount
```

## Currency Support

| Country | Currency | Code |
|---------|----------|------|
| Algeria | Algerian Dinar | DZD |
| Tunisia | Tunisian Dinar | TND |
| Morocco | Moroccan Dirham | MAD |
| Senegal | West African CFA | XOF |

## API Endpoints

### B2B Portal
- `GET /api/payments/balance` - Get wallet balance
- `POST /api/payments/topup` - Top up wallet
- `GET /api/payments/invoices` - List invoices
- `GET /api/payments/invoices/{id}` - Invoice details
- `GET /api/payments/plan` - Current payment plan

### Admin Panel
- `GET /api/admin/enterprises/{id}/payments` - Payment info
- `POST /api/admin/enterprises/{id}/payments/topup` - Admin top-up
- `PUT /api/admin/enterprises/{id}/payments/budget` - Update budget
- `POST /api/admin/enterprises/{id}/payments/switch-plan` - Switch plan
- `GET /api/admin/enterprises/{id}/invoices` - All invoices
- `POST /api/admin/enterprises/{id}/invoices/generate` - Generate invoice
- `PUT /api/admin/enterprises/{id}/invoices/{id}/status` - Update status
- `PUT /api/admin/enterprises/{id}/commission` - Set commission
- `PUT /api/admin/enterprises/{id}/discount` - Set discount rules
