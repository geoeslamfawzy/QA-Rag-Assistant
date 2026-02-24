---
rule_type: atomic_rule
module: trips
risk_level: high
---

# Atomic Rules: Trip Booking & Management

## Booking Rules

### RULE-TRIP-001: Guest Booking Restriction
**Condition:** Guest user attempts direct booking
**Validation:** Guests cannot self-book business trips
**Error:** "Guests cannot book trips directly. Admin must book on your behalf."
**Priority:** High

### RULE-TRIP-002: Program Service Filter
**Condition:** Service selection during booking
**Validation:** Available services determined by assigned program
**Error:** "Service not available for your program."
**Priority:** Medium

### RULE-TRIP-003: Scheduled Trip Repeat
**Condition:** Enable repeat booking
**Validation:** Only available for scheduled (future) trips
**Error:** "Repeat booking only available for scheduled trips."
**Priority:** Low

### RULE-TRIP-004: Approval Workflow Trigger
**Condition:** Ride request submission
**Validation:** If program auto-approval OFF, trip goes to Ride Requests
**Error:** N/A (workflow routing)
**Priority:** Medium

### RULE-TRIP-005: Budget Check Before Booking
**Condition:** Trip booking request
**Validation:**
- Prepaid: Wallet balance >= estimated trip cost
- Postpaid: Used budget + trip cost <= budget limit
**Error:** "Insufficient budget for this trip."
**Priority:** Critical

## Status Rules

### RULE-TRIP-006: Initial Status
**Condition:** Instant trip booking confirmed
**Validation:** Trip status = PENDING
**Error:** N/A (system default)
**Priority:** High

### RULE-TRIP-007: Valid Status Progression
**Condition:** Trip status update
**Validation:**
- PENDING -> ACCEPTED
- ACCEPTED -> DRIVER_ARRIVED
- DRIVER_ARRIVED -> STARTED
- STARTED -> FINISHED
**Error:** "Invalid status transition."
**Priority:** Critical

### RULE-TRIP-008: Terminal Status Enforcement
**Condition:** Attempt to change terminal status
**Validation:** Cannot change from: FINISHED, *_CANCELED, NO_DRIVER_AVAILABLE
**Error:** "Trip is in terminal state. No changes allowed."
**Priority:** Critical

### RULE-TRIP-009: Cancellation Policy
**Condition:** Cancel trip request
**Validation:** Cancellation allowed in: PENDING, ACCEPTED, DRIVER_ARRIVED
**Error:** "Cannot cancel trip in current status."
**Priority:** High

## Financial Rules

### RULE-TRIP-010: Prepaid Deduction
**Condition:** Trip completed (FINISHED)
**Validation:** Trip cost deducted from enterprise wallet
**Error:** N/A (automatic deduction)
**Priority:** Critical

### RULE-TRIP-011: Postpaid Accrual
**Condition:** Trip completed (FINISHED)
**Validation:** Trip cost added to monthly accrual
**Error:** N/A (automatic accrual)
**Priority:** Critical

### RULE-TRIP-012: Refund to Wallet
**Condition:** Refund approved (Prepaid)
**Validation:** Refund amount credited to wallet immediately
**Error:** N/A (automatic credit)
**Priority:** High

### RULE-TRIP-013: Invoice Adjustment
**Condition:** Refund approved (Postpaid)
**Validation:** Refund amount reduces invoice total
**Error:** N/A (automatic adjustment)
**Priority:** High

### RULE-TRIP-014: Commission Calculation
**Condition:** Trip cost display/calculation
**Validation:** B2B price = base fare * (1 + commission %)
**Error:** N/A (calculation)
**Priority:** High

## Schedule Rules

### RULE-TRIP-015: Program Schedule Enforcement
**Condition:** Trip booking request
**Validation:** Booking time must be within program's allowed schedule
**Error:** "Trip not allowed at this time. Check program schedule."
**Priority:** Medium

### RULE-TRIP-016: Working Days Definition
**Condition:** Program schedule = Working Days
**Validation:** Sunday to Thursday only
**Error:** "Trips not available on Friday/Saturday for this program."
**Priority:** Medium

### RULE-TRIP-017: Weekend Definition
**Condition:** Program schedule = Weekend
**Validation:** Friday and Saturday only
**Error:** "Trips only available on weekends for this program."
**Priority:** Medium

## Location Rules

### RULE-TRIP-018: Geofencing Enforcement
**Condition:** Trip with geo-restricted program
**Validation:** Pickup/dropoff must be within allowed locations
**Error:** "Location not allowed for this program."
**Priority:** Medium

### RULE-TRIP-019: Round Trip Restriction
**Condition:** Program allows round trips only
**Validation:** Destination must equal departure
**Error:** "Only round trips allowed for this program."
**Priority:** Medium

## Limit Rules

### RULE-TRIP-020: Ride Limit per Member
**Condition:** Trip booking
**Validation:** Member's trip count within period <= program limit
**Error:** "Ride limit reached for this period."
**Priority:** High

### RULE-TRIP-021: Budget per Member
**Condition:** Trip booking
**Validation:** Member's spending within period <= program budget limit
**Error:** "Budget limit reached for this period."
**Priority:** High

## Export Rules

### RULE-TRIP-022: Export Range Limit
**Condition:** Trip export request
**Validation:** Date range <= 31 days
**Error:** "Export date range cannot exceed 31 days."
**Priority:** Low

### RULE-TRIP-023: Async Export Delivery
**Condition:** Large export request
**Validation:** Export delivered via email asynchronously
**Error:** N/A (email delivery)
**Priority:** Low
