---
rule_type: atomic_rule
module: payment_processing
risk_level: critical
---

# Atomic Rules: Payment Processing

## PAY-001: Idempotency Required
**Condition:** Any payment transaction is initiated
**Validation:** Transaction must include unique idempotency key
**Error:** "Idempotency key is required for all transactions."
**Priority:** critical

## PAY-002: Minimum Charge Amount
**Condition:** Charge transaction is created
**Validation:** Amount must be >= $0.50 (50 cents)
**Error:** "Minimum charge amount is $0.50."
**Priority:** high

## PAY-003: Maximum Charge Amount
**Condition:** Charge transaction is created
**Validation:** Amount must be <= $50,000
**Error:** "Maximum single charge is $50,000. Contact support for larger amounts."
**Priority:** high

## PAY-004: Refund Amount Limit
**Condition:** Refund is requested
**Validation:** Refund amount <= original charge amount
**Error:** "Refund amount cannot exceed original charge."
**Priority:** critical

## PAY-005: Refund Window (Full)
**Condition:** Full refund is requested
**Validation:** Request within 30 days of original charge
**Error:** "Full refunds are only available within 30 days of charge."
**Priority:** high

## PAY-006: Refund Window (Partial)
**Condition:** Partial refund is requested
**Validation:** Request within 90 days of original charge
**Error:** "Partial refunds are only available within 90 days of charge."
**Priority:** high

## PAY-007: Currency Consistency
**Condition:** Transaction involves currency
**Validation:** Currency must match original transaction currency
**Error:** "Currency mismatch. Transaction currency: {expected}."
**Priority:** critical

## PAY-008: Valid Card Expiry
**Condition:** Card payment is processed
**Validation:** Card expiry date must be in the future
**Error:** "Card has expired. Please use a valid card."
**Priority:** high

## PAY-009: Retry on Processing Error
**Condition:** Transaction fails with processing error
**Validation:** Retry up to 3 times with exponential backoff
**Error:** "Payment processing failed. Retrying..."
**Priority:** medium

## PAY-010: No Retry on Validation Error
**Condition:** Transaction fails with validation error
**Validation:** Do not retry, return error immediately
**Error:** "{validation_error_message}"
**Priority:** high

## PAY-011: Fraud Detection Block
**Condition:** Fraud detection triggers
**Validation:** Block transaction and flag for review
**Error:** "Transaction blocked for security review."
**Priority:** critical

## PAY-012: Daily Transaction Limit
**Condition:** User initiates charge
**Validation:** Daily total charges <= $100,000
**Error:** "Daily transaction limit reached."
**Priority:** high
