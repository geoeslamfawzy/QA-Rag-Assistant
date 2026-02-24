---
rule_type: atomic_rule
module: subscription
risk_level: high
---

# Atomic Rules: Subscription Management

## SUB-001: Single Active Subscription
**Condition:** User attempts to create a new subscription
**Validation:** User must not have an existing active subscription
**Error:** "User already has an active subscription. Cancel existing subscription first."
**Priority:** critical

## SUB-002: Valid Payment Method Required
**Condition:** User creates or upgrades subscription
**Validation:** User must have at least one valid payment method on file
**Error:** "A valid payment method is required for subscription changes."
**Priority:** high

## SUB-003: Upgrade Proration Calculation
**Condition:** User upgrades subscription mid-cycle
**Validation:** Prorated amount = (NewPrice - OldPrice) * (RemainingDays / TotalDays)
**Error:** N/A (calculation rule)
**Priority:** high

## SUB-004: Downgrade Timing
**Condition:** User downgrades subscription
**Validation:** Downgrade takes effect at the end of current billing period
**Error:** N/A (business rule)
**Priority:** medium

## SUB-005: Cancellation Access Period
**Condition:** User cancels subscription
**Validation:** User retains access until end of paid period
**Error:** N/A (business rule)
**Priority:** high

## SUB-006: Grace Period for Failed Payments
**Condition:** Subscription payment fails
**Validation:** 3-day grace period before suspension
**Error:** "Payment failed. You have 3 days to update payment method."
**Priority:** critical

## SUB-007: No Reactivation of Cancelled Subscriptions
**Condition:** User attempts to reactivate cancelled subscription
**Validation:** Cancelled subscriptions cannot be reactivated
**Error:** "This subscription has been cancelled. Please create a new subscription."
**Priority:** medium

## SUB-008: Trial Period Limits
**Condition:** User starts trial subscription
**Validation:** User can only have one trial per plan type
**Error:** "You have already used your trial for this plan."
**Priority:** medium

## SUB-009: Enterprise Plan Approval
**Condition:** User selects enterprise plan
**Validation:** Enterprise plans require sales approval
**Error:** "Enterprise plans require approval. Sales team will contact you."
**Priority:** high

## SUB-010: Billing Cycle Consistency
**Condition:** User changes billing cycle
**Validation:** Changes apply at next renewal, not mid-cycle
**Error:** N/A (business rule)
**Priority:** medium
