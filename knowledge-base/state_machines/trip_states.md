---
state_machine: trip
module: trips
version: 1.0
---

# State Machine: Trip Lifecycle

## States

| State | Description | Terminal |
|-------|-------------|----------|
| PENDING | Awaiting driver acceptance | No |
| ACCEPTED | Driver accepted, en route to pickup | No |
| DRIVER_ARRIVED | Driver at pickup location | No |
| STARTED | Trip in progress | No |
| FINISHED | Trip completed successfully | Yes |
| DRIVER_CANCELED | Driver cancelled the trip | Yes |
| RIDER_CANCELED | Rider cancelled the trip | Yes |
| DRIVER_COMING_CANCELED | Driver cancelled while en route | Yes |
| DRIVER_COMING_RIDER_CANCELED | Rider cancelled while driver en route | Yes |
| NO_DRIVER_AVAILABLE | No driver found for request | Yes |
| DRIVER_ABANDONED | Driver abandoned during trip | Yes |
| RIDER_ABANDONED | Rider abandoned during trip | Yes |
| ADJUSTED | Fare adjustment applied | Yes |
| TRIP_REQUEST_EXPIRED | Scheduled request expired | Yes |
| TRIP_REQUEST_DECLINED | Request declined by approver | Yes |
| BOOK_ASSIGNED | Book assigned to specific driver | No |

## Valid Transitions

### Happy Path
| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| PENDING | ACCEPTED | driver_accept | Driver available, not on another trip |
| ACCEPTED | DRIVER_ARRIVED | driver_at_pickup | GPS within pickup radius |
| DRIVER_ARRIVED | STARTED | trip_start | Rider confirmation or timer |
| STARTED | FINISHED | trip_end | Fare calculated, destination reached |

### Cancellation Paths
| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| PENDING | RIDER_CANCELED | rider_cancel | Within cancellation window |
| PENDING | NO_DRIVER_AVAILABLE | timeout | No driver accepted within limit |
| ACCEPTED | DRIVER_CANCELED | driver_cancel | Cancellation reason required |
| ACCEPTED | RIDER_CANCELED | rider_cancel | Cancellation fee may apply |
| ACCEPTED | DRIVER_COMING_CANCELED | driver_cancel_enroute | Driver en route cancelled |
| ACCEPTED | DRIVER_COMING_RIDER_CANCELED | rider_cancel_enroute | Rider cancelled during approach |
| DRIVER_ARRIVED | DRIVER_CANCELED | driver_cancel | Rider no-show |
| DRIVER_ARRIVED | RIDER_CANCELED | rider_cancel | Cancellation fee applies |

### Abandonment Paths
| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| STARTED | DRIVER_ABANDONED | driver_abandon | Emergency, safety issue |
| STARTED | RIDER_ABANDONED | rider_abandon | Rider exited unexpectedly |

### Adjustment Path
| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| FINISHED | ADJUSTED | fare_adjustment | Admin override, dispute resolution |

### Scheduled Trip Paths
| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| PENDING | TRIP_REQUEST_EXPIRED | scheduled_timeout | Scheduled time passed, no driver |
| PENDING | TRIP_REQUEST_DECLINED | approver_decline | Manual decline by approver |

## Invalid Transitions

The following transitions are NOT allowed:

| From | To | Reason |
|------|-----|--------|
| FINISHED | Any | Terminal state - trip completed |
| *_CANCELED | Any | Terminal state - trip cancelled |
| NO_DRIVER_AVAILABLE | Any | Terminal state - no driver found |
| STARTED | PENDING | Cannot revert started trip |
| DRIVER_ARRIVED | PENDING | Cannot revert arrival |
| ACCEPTED | PENDING | Cannot unaccept trip |
| FINISHED | STARTED | Cannot restart completed trip |

## State Rules

### PENDING State
- Duration: Max 5 minutes for instant, varies for scheduled
- Auto-transition: NO_DRIVER_AVAILABLE if timeout
- Financial: No charges yet

### ACCEPTED State
- Duration: Until driver arrives at pickup
- Notifications: ETA updates to rider
- Financial: Cancellation fee may apply if cancelled

### DRIVER_ARRIVED State
- Duration: Max 5 minutes wait time
- Notifications: "Driver arrived" push notification
- Financial: Waiting charges may start after threshold

### STARTED State
- Duration: Until trip completion
- Tracking: Real-time GPS tracking active
- Financial: Fare meter running

### FINISHED State
- Trigger: Rider dropped at destination
- Financial: Final fare calculated and charged
- Notifications: Receipt sent

### Terminal States
All *_CANCELED, NO_DRIVER_AVAILABLE, *_ABANDONED, EXPIRED, DECLINED:
- No further transitions allowed
- Financial settlement triggered
- Notifications sent to relevant parties

## Diagram

```
                              [PENDING]
                                  |
              +--------+----------+----------+--------+
              |        |          |          |        |
              v        v          v          v        v
        [ACCEPTED]  [RIDER_     [NO_DRIVER  [EXPIRED] [DECLINED]
              |      CANCELED]   AVAILABLE]
              |
    +---------+---------+
    |         |         |
    v         v         v
[DRIVER_   [DRIVER_  [RIDER_
ARRIVED]   CANCELED] CANCELED]
    |
    |
    v
[STARTED]
    |
    +---------+---------+
    |         |         |
    v         v         v
[FINISHED] [DRIVER_  [RIDER_
    |      ABANDONED] ABANDONED]
    v
[ADJUSTED]
```

## Financial Impact by State

| State | Prepaid Impact | Postpaid Impact |
|-------|----------------|-----------------|
| PENDING | No impact | No impact |
| ACCEPTED | No impact | No impact |
| DRIVER_ARRIVED | No impact | No impact |
| STARTED | No impact (charging) | No impact (accruing) |
| FINISHED | Wallet -= fare | Budget += fare |
| *_CANCELED | May deduct cancellation fee | May accrue cancellation fee |
| ADJUSTED | Recalculate charge/refund | Recalculate accrual |
