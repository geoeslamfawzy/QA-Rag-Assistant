---
state_machine: enterprise
module: enterprises
version: 1.0
---

# State Machine: Enterprise Lifecycle

## States

| State | Description | Can Book Trips | Can Delete |
|-------|-------------|----------------|------------|
| PENDING | Awaiting approval after registration | No | Yes |
| ACTIVE | Approved and operational | Yes | No |
| INACTIVE | Deactivated by admin | No | Yes |

## Valid Transitions

| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| PENDING | ACTIVE | admin_approve | Legal info reviewed, documents valid |
| PENDING | INACTIVE | admin_reject | Rejection reason required |
| ACTIVE | INACTIVE | admin_deactivate | No ongoing trips |
| INACTIVE | ACTIVE | admin_reactivate | Budget available (Prepaid: balance > 0) |

## Invalid Transitions

| From | To | Reason |
|------|-----|--------|
| PENDING | (deleted) | Must be INACTIVE first |
| ACTIVE | (deleted) | Must be INACTIVE first |
| ACTIVE | PENDING | Cannot revert to pending |
| INACTIVE | PENDING | Cannot revert to pending |

## Deletion Rules

- Only INACTIVE enterprises can be deleted
- Deletion requires confirmation
- Deleted enterprises retain audit trail for compliance
- User data anonymized after 90 days

## State Rules

### PENDING State
**Entry Conditions:**
- New enterprise registration completed
- Email and phone verified
- Company profile submitted

**Restrictions:**
- Dashboard access blocked
- No trip booking allowed
- Limited to profile viewing

**Exit Conditions:**
- Admin reviews and approves/rejects
- Legal documents validated (for approval)

**Notifications:**
- Admin Panel: New enterprise notification
- Enterprise: "Account under review" message

### ACTIVE State
**Entry Conditions:**
- Admin approval
- Legal info approved (for invoice-enabled)
- OR reactivation from INACTIVE

**Capabilities:**
- Full dashboard access
- Trip booking enabled
- All features available

**Exit Conditions:**
- Manual deactivation by admin
- No ongoing trips required for deactivation

**Restrictions:**
- Cannot be deleted directly

### INACTIVE State
**Entry Conditions:**
- Admin deactivation
- OR rejection from PENDING

**Restrictions:**
- Dashboard access blocked (or read-only)
- No new trip booking
- Existing trips must be completed/cancelled

**Exit Conditions:**
- Admin reactivation
- Budget verification (Prepaid)

**Capabilities:**
- Can be deleted
- Can view historical data

## Reactivation Requirements

### Prepaid Enterprise
1. Wallet balance must be positive
2. Payment method on file (optional)
3. Legal info still valid

### Postpaid Enterprise
1. No outstanding overdue invoices
2. Budget limit configured
3. Legal info still valid

## Diagram

```
          [Registration]
                |
                v
            [PENDING]
           /         \
    Approve           Reject
         /             \
        v               v
    [ACTIVE] --------> [INACTIVE]
        ^                  |
        |    Reactivate    |
        +------------------+
                           |
                      Can Delete
```

## Financial Impact by State

| State | Wallet/Budget | Invoicing | Trips |
|-------|---------------|-----------|-------|
| PENDING | Viewable only | Not available | Blocked |
| ACTIVE | Full access | Available | Enabled |
| INACTIVE | Frozen | Historical only | Blocked |

## Audit Trail

### Logged Events
| Event | Data Captured |
|-------|---------------|
| Registration | Timestamp, user details, company info |
| Approval | Timestamp, admin ID, legal status |
| Rejection | Timestamp, admin ID, reason |
| Deactivation | Timestamp, admin ID, reason |
| Reactivation | Timestamp, admin ID, conditions verified |
| Deletion | Timestamp, admin ID, data retention notice |

## Notifications

| Transition | Recipient | Message Type |
|------------|-----------|--------------|
| PENDING created | Admin Panel | New enterprise alert |
| PENDING -> ACTIVE | Super Admin | Approval confirmation |
| PENDING -> INACTIVE (reject) | Super Admin | Rejection notification |
| ACTIVE -> INACTIVE | Super Admin | Deactivation notice |
| INACTIVE -> ACTIVE | Super Admin | Reactivation confirmation |
