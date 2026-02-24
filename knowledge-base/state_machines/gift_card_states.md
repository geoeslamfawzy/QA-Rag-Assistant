---
state_machine: gift_card
module: gift_cards
version: 1.0
---

# State Machine: Gift Card Lifecycle

## States

| State | Description | Usable | Revertable |
|-------|-------------|--------|------------|
| ACTIVE | Card purchased and ready for use | Yes | Yes |
| EXPIRED | Validity period ended | No | Yes |
| DEACTIVATED | Manually deactivated by admin | No | Yes |
| REVERTED | Balance refunded to enterprise | No | No |
| EXHAUSTED | Balance fully used | No | No |

## Valid Transitions

| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| ACTIVE | EXPIRED | validity_end_reached | Current date > validity end |
| ACTIVE | DEACTIVATED | manual_deactivation | Admin action |
| ACTIVE | REVERTED | balance_refund | remaining_balance > 0 |
| ACTIVE | EXHAUSTED | balance_depleted | remaining_balance = 0 |
| EXPIRED | REVERTED | balance_refund | remaining_balance > 0 |
| DEACTIVATED | REVERTED | balance_refund | remaining_balance > 0 |

## Invalid Transitions

| From | To | Reason |
|------|-----|--------|
| REVERTED | Any | Terminal state - balance refunded |
| EXHAUSTED | Any | Terminal state - no balance |
| EXPIRED | ACTIVE | Cannot reactivate expired card |
| DEACTIVATED | ACTIVE | Cannot reactivate deactivated card |

## State Rules

### ACTIVE State
**Entry Conditions:**
- Enterprise purchases gift card
- Wallet has sufficient balance
- Purchase confirmed

**Capabilities:**
- Can be used for trips
- Can be reverted
- Can be deactivated
- Can view usage history

**Exit Conditions:**
- Validity period ends (-> EXPIRED)
- Balance reaches zero (-> EXHAUSTED)
- Manual deactivation (-> DEACTIVATED)
- Balance refund (-> REVERTED)

**Financial:**
- Holds value on behalf of enterprise
- Value decreases with each eligible trip

### EXPIRED State
**Entry Conditions:**
- Current date > validity_end_date
- Automatic transition (system job)

**Capabilities:**
- Cannot be used for trips
- Can be reverted (if balance > 0)
- Can view usage history

**Financial:**
- Remaining balance frozen
- Can be recovered via revert

### DEACTIVATED State
**Entry Conditions:**
- Admin manually deactivates
- No trip in progress using card

**Capabilities:**
- Cannot be used for trips
- Can be reverted (if balance > 0)
- Can view usage history

**Financial:**
- Remaining balance frozen
- Can be recovered via revert

### REVERTED State
**Entry Conditions:**
- Enterprise requests balance refund
- remaining_balance > 0

**On Entry:**
- enterprise_wallet += remaining_balance
- card.remaining_balance = 0
- voucher_code = INVALID

**Capabilities:**
- None - permanently unusable
- Historical view only

**Financial:**
- Balance returned to enterprise wallet
- No further financial impact

### EXHAUSTED State
**Entry Conditions:**
- remaining_balance reaches 0 via usage

**Capabilities:**
- None - balance depleted
- Historical view only

**Financial:**
- No balance to revert
- No further financial impact

## Diagram

```
    [Purchase]
        |
        v
    [ACTIVE]
        |
    +---+---+---+---+
    |   |   |       |
    v   v   v       v
[EXPIRED] [DEACTIVATED] [EXHAUSTED]
    |       |               |
    |   +---+               |
    |   |                   |
    v   v                   |
[REVERTED] <----------------+
                        (if balance > 0)
```

## Balance Tracking Through States

| State | Balance Status | Wallet Impact |
|-------|----------------|---------------|
| ACTIVE | Decreasing | None during use |
| EXPIRED | Frozen | None |
| DEACTIVATED | Frozen | None |
| REVERTED | Zero | +remaining returned |
| EXHAUSTED | Zero | None |

## Voucher Code Validity

| State | Code Valid |
|-------|------------|
| ACTIVE | Yes |
| EXPIRED | No |
| DEACTIVATED | No |
| REVERTED | No |
| EXHAUSTED | No |

## Notifications

| Transition | Recipient | Message |
|------------|-----------|---------|
| Purchase | Super Admin | "Gift card purchased" |
| ACTIVE -> EXPIRED | Super Admin | "Gift card expired with balance X" |
| ACTIVE -> DEACTIVATED | Super Admin | "Gift card deactivated" |
| Any -> REVERTED | Super Admin | "Gift card balance X refunded" |
| ACTIVE -> EXHAUSTED | Super Admin | "Gift card fully used" |

## Audit Trail

| Event | Data Captured |
|-------|---------------|
| Purchase | Timestamp, buyer, amount, voucher_code |
| Usage | Timestamp, rider, trip_id, amount_deducted |
| Expiry | Timestamp, remaining_balance |
| Deactivation | Timestamp, admin_id, reason |
| Revert | Timestamp, admin_id, amount_refunded |
| Exhaustion | Timestamp, final_trip_id |
