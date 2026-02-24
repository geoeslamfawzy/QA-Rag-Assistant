---
state_machine: subscription
module: subscription
version: 1.0
---

# State Machine: Subscription Lifecycle

## States

| State | Description | Entry Conditions |
|-------|-------------|------------------|
| TRIAL | Free trial period | New subscription with trial |
| ACTIVE | Paid and active | Payment successful |
| PENDING_PAYMENT | Awaiting payment | After failed payment |
| SUSPENDED | Temporarily suspended | Grace period expired |
| CANCELLED | User cancelled | User requested cancellation |
| EXPIRED | Subscription ended | Term completed without renewal |

## Valid Transitions

| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| TRIAL | ACTIVE | trial_convert | Payment method valid, charge successful |
| TRIAL | CANCELLED | trial_cancel | None |
| TRIAL | EXPIRED | trial_expire | Trial period ended, no conversion |
| ACTIVE | ACTIVE | renew | Payment successful |
| ACTIVE | PENDING_PAYMENT | payment_failed | Payment attempt failed |
| ACTIVE | CANCELLED | user_cancel | None |
| PENDING_PAYMENT | ACTIVE | payment_retry_success | Retry payment successful |
| PENDING_PAYMENT | SUSPENDED | grace_period_expired | 3 days elapsed without payment |
| SUSPENDED | ACTIVE | payment_received | Payment successful |
| SUSPENDED | CANCELLED | admin_cancel | Admin action |

## Invalid Transitions

The following transitions are NOT allowed:

- CANCELLED -> ACTIVE: "Cancelled subscriptions cannot be reactivated. Create new subscription."
- CANCELLED -> TRIAL: "Cannot restart trial after cancellation."
- EXPIRED -> ACTIVE: "Expired subscriptions cannot be reactivated. Create new subscription."
- EXPIRED -> TRIAL: "Cannot restart trial after expiration."
- SUSPENDED -> TRIAL: "Cannot revert to trial from suspended state."

## Terminal States

Terminal states (no outgoing transitions except to CANCELLED):
- CANCELLED
- EXPIRED

## State Rules

### TRIAL State
- Duration: 14 days (configurable)
- Features: Full access to plan features
- Notifications: Day 7 reminder, Day 12 warning, Day 14 expiry
- Auto-transition: EXPIRED if no conversion

### ACTIVE State
- Features: Full plan access
- Billing: Recurring charges per billing cycle
- Notifications: Renewal confirmation, payment receipt

### PENDING_PAYMENT State
- Duration: 3 days (grace period)
- Features: Full access maintained
- Notifications: Day 1 warning, Day 2 urgent, Day 3 final
- Auto-transition: SUSPENDED after grace period

### SUSPENDED State
- Features: Read-only access (no new actions)
- Duration: 30 days before data archival
- Notifications: Immediate notification, weekly reminders
- Recovery: Payment required to return to ACTIVE

### CANCELLED State
- Features: Access until end of paid period
- Data: Retained for 90 days
- Notifications: Cancellation confirmation, data deletion warning

### EXPIRED State
- Features: No access
- Data: Retained for 30 days then archived
- Notifications: Expiry notification, resubscription offer

## Diagram

```
    [TRIAL] ──────────────┬──────────────> [ACTIVE]
       │                  │                    │
       │                  v                    │
       │            [EXPIRED]                  │
       │                                       │
       └─────────────────────────────────> [CANCELLED]
                                               ^
                                               │
    [ACTIVE] ───> [PENDING_PAYMENT] ───> [SUSPENDED]
       │                │                      │
       │                │                      │
       └────────────────┴──────────────────────┘
```
