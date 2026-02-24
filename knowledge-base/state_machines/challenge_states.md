---
state_machine: challenge
module: challenges
version: 1.0
---

# State Machine: Challenge Lifecycle

## States

| State | Description | Editable | Deletable |
|-------|-------------|----------|-----------|
| UPCOMING | Challenge created, not yet started | Yes | Yes |
| ONGOING | Challenge currently active | No | No |
| COMPLETED | All tiers achieved by enterprise | No | No |
| EXPIRED | End date passed without completion | No | No |
| DISABLED | Deactivated by admin (before start) | No | Yes |

## Valid Transitions

| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| UPCOMING | ONGOING | start_date_reached | Current date >= start_date |
| UPCOMING | DISABLED | admin_deactivate | Admin action before start |
| ONGOING | COMPLETED | all_tiers_achieved | Enterprise completes all tiers |
| ONGOING | EXPIRED | end_date_passed | Current date > end_date, not all tiers |
| DISABLED | (deleted) | admin_delete | Admin confirmation |

## Invalid Transitions

| From | To | Reason |
|------|-----|--------|
| ONGOING | UPCOMING | Cannot reverse started challenge |
| ONGOING | DISABLED | Cannot deactivate ongoing challenge |
| COMPLETED | Any | Terminal state - challenge won |
| EXPIRED | Any | Terminal state - challenge ended |
| ONGOING | (deleted) | Cannot delete ongoing challenge |

## State Rules

### UPCOMING State
**Entry Conditions:**
- Challenge created via Admin Panel
- Start date in future
- Valid tier configuration

**Capabilities:**
- Full editing allowed
- Can be deactivated
- Can be deleted
- Visible in challenge list

**Exit Conditions:**
- Start date reached (-> ONGOING)
- Admin deactivates (-> DISABLED)

**Validations:**
- Cannot overlap with existing challenges for same enterprises
- Tier configuration must be sequential
- Cumulative discount <= 100%

### ONGOING State
**Entry Conditions:**
- Current date >= start_date
- Challenge not disabled

**Capabilities:**
- View progress only
- No editing allowed
- No deletion allowed
- Tier tracking active

**Exit Conditions:**
- All tiers completed (-> COMPLETED)
- End date passed (-> EXPIRED)

**Processing:**
- Real-time ride counting
- Tier unlocking on criteria met
- Discount accumulation

### COMPLETED State
**Entry Conditions:**
- Enterprise achieves all tiers
- Before end date

**Capabilities:**
- View final results
- Historical reporting
- Discount applied to invoice

**Financial:**
- Total discount = sum of all tier discounts
- Applied at next billing cycle

### EXPIRED State
**Entry Conditions:**
- End date passed
- Not all tiers completed

**Capabilities:**
- View partial results
- Historical reporting
- Earned discounts still apply

**Financial:**
- Discount = sum of completed tier discounts
- Applied at next billing cycle

### DISABLED State
**Entry Conditions:**
- Admin deactivates before start
- Only from UPCOMING

**Capabilities:**
- Can be deleted
- View configuration
- Not visible to enterprises

## Diagram

```
    [Create Challenge]
           |
           v
       [UPCOMING]
       /    |    \
      /     |     \
     v      v      v
[ONGOING] [DISABLED] -> [DELETE]
    |
    +----------+
    |          |
    v          v
[COMPLETED] [EXPIRED]
```

## Tier States

### Tier Badge States
| State | Description |
|-------|-------------|
| LOCKED | Criteria not yet met |
| UNLOCKED | Criteria met, badge earned |

### Tier Transition
```
For each tier:
  IF enterprise_rides >= tier.min_rides:
    tier.state = UNLOCKED
    enterprise.discount += tier.discount_percent
```

## Discount Calculation

### During Challenge
```
earned_discount = SUM(
  tier.discount_percent
  FOR tier IN challenge.tiers
  WHERE tier.state == UNLOCKED
)
```

### At Challenge End
```
final_discount = MIN(earned_discount, 100%)
```

### Application
```
IF enterprise.payment_plan == POSTPAID:
  invoice_total -= invoice_total * final_discount
```

## Example: December Sprint

### Configuration
| Tier | Badge | Rides | Discount |
|------|-------|-------|----------|
| 1 | Copper 1 | 1-5 | 5% |
| 2 | Copper 2 | 6-10 | 10% |
| 3 | Bronze | 11-20 | 15% |
| 4 | Silver | 21-30 | 25% |
| 5 | Gold | 31-50 | 30% |
| 6 | Platinum | 51+ | 15% |
| **Total** | | | **100%** |

### Scenario: Enterprise completes 35 rides
- Tier 1: UNLOCKED (5%)
- Tier 2: UNLOCKED (10%)
- Tier 3: UNLOCKED (15%)
- Tier 4: UNLOCKED (25%)
- Tier 5: UNLOCKED (30%)
- Tier 6: LOCKED (not reached)
- **Total discount: 85%**

## Notifications

| Transition | Recipient | Message |
|------------|-----------|---------|
| UPCOMING created | Targeted enterprises | "New challenge available" |
| UPCOMING -> ONGOING | Targeted enterprises | "Challenge started" |
| Tier unlocked | Enterprise | "You unlocked [Badge]!" |
| ONGOING -> COMPLETED | Enterprise | "Challenge completed! X% discount earned" |
| ONGOING -> EXPIRED | Enterprise | "Challenge ended. X% discount earned" |

## Audit Trail

| Event | Data Captured |
|-------|---------------|
| Creation | Timestamp, admin_id, config |
| Edit | Timestamp, admin_id, changes |
| Deactivation | Timestamp, admin_id |
| Deletion | Timestamp, admin_id |
| Tier Unlock | Timestamp, enterprise_id, tier_id |
| Completion | Timestamp, enterprise_id, final_discount |
| Expiry | Timestamp, enterprise_id, partial_discount |
