---
rule_type: cross_dependency
modules:
  - subscription
  - payment_processing
risk_level: high
---

# Cross-Module Dependencies: Subscription & Payment

## Overview

The subscription module has critical dependencies on the payment processing module. All subscription state changes that involve billing require coordination with payment.

## Dependency Map

| From | To | Type | Description | Risk Level |
|------|-----|------|-------------|------------|
| subscription | payment_processing | sync | Subscription charges | critical |
| subscription | payment_processing | sync | Proration calculation | high |
| subscription | payment_processing | async | Refund processing | high |
| payment_processing | subscription | event | Payment success/failure | critical |
| payment_processing | subscription | event | Refund completion | medium |

## Critical Dependency Chains

### Chain 1: Subscription Creation

```
1. User selects plan
2. subscription.create() called
3. payment.charge() called synchronously
4. IF payment succeeds:
   - subscription.activate()
   - notification.send_confirmation()
5. IF payment fails:
   - subscription.mark_pending()
   - notification.send_failure()
```

**Risks:**
- Payment timeout leaves subscription in limbo
- Network failure between services
- Inconsistent state if partial failure

**Mitigations:**
- Use saga pattern with compensation
- Idempotent operations
- State reconciliation job

### Chain 2: Subscription Upgrade

```
1. User requests upgrade
2. subscription.calculate_proration()
3. payment.charge(prorated_amount)
4. IF payment succeeds:
   - subscription.apply_upgrade()
   - notification.send_upgrade_confirmation()
5. IF payment fails:
   - subscription.revert_upgrade()
   - notification.send_failure()
```

**Risks:**
- Proration calculation inconsistency
- User charged but upgrade not applied
- Race condition with concurrent requests

**Mitigations:**
- Lock subscription during upgrade
- Atomic upgrade transaction
- Compensation on failure

### Chain 3: Payment Failure Recovery

```
1. payment.failed event received
2. subscription.mark_pending_payment()
3. notification.send_payment_failed()
4. Start grace period timer (3 days)
5. IF payment retry succeeds within grace:
   - subscription.reactivate()
6. IF grace period expires:
   - subscription.suspend()
```

**Risks:**
- Missed webhook delivery
- Timer inconsistency
- User access during pending state

**Mitigations:**
- Webhook retry with idempotency
- Distributed timer service
- Cache subscription state

## Integration Points

### APIs Called

| Source | Target API | Purpose | Timeout |
|--------|-----------|---------|---------|
| subscription | POST /payments/charge | New subscription | 30s |
| subscription | POST /payments/refund | Cancellation refund | 30s |
| subscription | GET /payments/{id} | Status check | 10s |

### Events Published

| Module | Event | Subscribers |
|--------|-------|-------------|
| payment | payment.completed | subscription, notification, audit |
| payment | payment.failed | subscription, notification |
| subscription | subscription.created | notification, analytics |
| subscription | subscription.cancelled | notification, analytics, user |

### Webhooks

| Source | Webhook | Handler |
|--------|---------|---------|
| Stripe | charge.succeeded | payment.handle_charge_success |
| Stripe | charge.failed | payment.handle_charge_failure |
| Stripe | refund.created | payment.handle_refund |

## Failure Scenarios

### Scenario 1: Payment Gateway Down

**Detection:** Connection timeout or 5xx responses
**Impact:** Cannot create/upgrade subscriptions
**Recovery:**
1. Retry with exponential backoff
2. Switch to backup gateway
3. Queue failed transactions
4. Alert operations team

### Scenario 2: Webhook Delivery Failure

**Detection:** Missing expected events
**Impact:** Subscription state drift
**Recovery:**
1. Implement webhook retry
2. Run reconciliation job hourly
3. Manual intervention for critical issues

### Scenario 3: Inconsistent State

**Detection:** Reconciliation finds mismatches
**Impact:** User access issues, billing problems
**Recovery:**
1. Identify source of truth (payment gateway)
2. Sync subscription state
3. Issue credits if user overcharged
4. Restore access if incorrectly suspended

## Testing Requirements

1. **Integration Tests:**
   - Happy path: successful payment flow
   - Payment failure and recovery
   - Webhook handling
   - Timeout handling

2. **Chaos Tests:**
   - Gateway unavailability
   - Network partitions
   - Slow responses

3. **Contract Tests:**
   - API contract between modules
   - Event schema validation
