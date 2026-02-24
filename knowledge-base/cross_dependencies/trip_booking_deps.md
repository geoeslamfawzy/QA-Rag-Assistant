---
dependency_type: cross_module
modules: [trips, programs, payments, users, enterprises]
risk_level: critical
---

# Cross Dependencies: Trip Booking

## Overview

Trip booking is the most complex cross-module operation in Yassir Mobility B2B. It requires validation across enterprise status, payment plan, program rules, user permissions, and service availability.

## Validation Chain

Trip booking must pass ALL validation stages in order:

```
1. Enterprise Validation
       |
       v
2. User Validation
       |
       v
3. Program Validation
       |
       v
4. Financial Validation
       |
       v
5. Service Validation
       |
       v
6. Booking Execution
```

## Critical Dependencies

### DEP-TB-001: Enterprise Status Check
**Stage:** 1
**Trigger:** Any trip booking attempt
**Dependency:** Enterprise must be ACTIVE

```
IF enterprise.status != ACTIVE:
    REJECT booking
    IF status == PENDING:
        SHOW "Account pending activation"
    ELSE IF status == INACTIVE:
        SHOW "Account deactivated. Contact support"
```

**Impact:** Trips on inactive enterprise = service without payment

### DEP-TB-002: User Status and Group Check
**Stage:** 2
**Trigger:** Booking continues past enterprise check
**Dependency:** User must be active and in a group

```
IF user.status != ACTIVE:
    REJECT booking
    SHOW "Your account is inactive"

IF user.group IS NULL:
    REJECT booking
    SHOW "You must be assigned to a group"
```

**Impact:** Unauthorized user trips = policy violation

### DEP-TB-003: Program Rules Validation
**Stage:** 3
**Trigger:** Booking continues past user check
**Dependencies:** Multiple program rule checks

**3a. Schedule Check:**
```
IF NOT booking_time IN program.allowed_schedule:
    REJECT booking
    SHOW "Trips not allowed at this time"
```

**3b. Ride Limit Check:**
```
current_count = user.trips_in_period(program.limit_period)
IF current_count >= program.ride_limit:
    REJECT booking
    SHOW "Ride limit reached for this [day/week/month]"
```

**3c. Budget Limit Check:**
```
current_spend = user.spend_in_period(program.budget_period)
IF (current_spend + trip_cost) > program.budget_limit:
    REJECT booking
    SHOW "Budget limit exceeded for this [trip/day/week/month]"
```

**3d. Location Check (Geofencing):**
```
IF program.pickup_restriction:
    IF pickup NOT IN program.allowed_pickups:
        REJECT booking
        SHOW "Pickup location not allowed"

IF program.dropoff_restriction:
    IF dropoff NOT IN program.allowed_dropoffs:
        REJECT booking
        SHOW "Dropoff location not allowed"
```

**3e. Service Check:**
```
IF selected_service NOT IN program.allowed_services:
    REJECT booking
    SHOW "Service not available for your program"
```

**Impact:** Program rules bypassed = policy violations, overspending

### DEP-TB-004: Financial Validation
**Stage:** 4
**Trigger:** Booking continues past program check
**Dependency:** Varies by payment plan

**Prepaid:**
```
IF enterprise.wallet_balance < estimated_trip_cost:
    REJECT booking
    SHOW "Insufficient balance. Top up to continue"
```

**Postpaid:**
```
IF (enterprise.used_budget + estimated_trip_cost) > enterprise.budget_limit:
    REJECT booking
    SHOW "Budget limit exceeded. Contact admin"
```

**Impact:** Financial validation bypassed = debt accumulation

### DEP-TB-005: Service Availability
**Stage:** 5
**Trigger:** Booking continues past financial check
**Dependency:** Service enabled at enterprise and region level

```
IF selected_service NOT IN enterprise.enabled_services:
    REJECT booking
    SHOW "Service not available for your company"

IF selected_service NOT IN region.enabled_services:
    REJECT booking
    SHOW "Service not available in this area"
```

**Impact:** Unavailable service booked = failed trip

### DEP-TB-006: Approval Workflow
**Stage:** 6 (if applicable)
**Trigger:** Booking passes all checks but program requires approval
**Dependency:** Routes to approval queue

```
IF program.auto_approval == FALSE:
    trip.status = PENDING_APPROVAL
    ROUTE to Ride Requests tab
    NOTIFY approvers
ELSE:
    trip.status = PENDING
    ROUTE to driver matching
```

**Impact:** Approval bypass = unauthorized trips

## Data Flow

```
[Booking Request]
      |
      v
[Enterprise Module] -- status check --> ACTIVE?
      |
      v
[User Module] -- status, group check --> Valid?
      |
      v
[Programs Module] -- rules validation --> Pass?
      |
      v
[Payments Module] -- balance/budget check --> Sufficient?
      |
      v
[Services Config] -- availability check --> Available?
      |
      v
[Approval Check] -- auto_approval? --> Route accordingly
      |
      v
[Driver Matching] or [Ride Requests]
```

## Trip Placement Matrix

| Booking Type | Approval Required | Placement |
|--------------|-------------------|-----------|
| Instant | No | Ongoing Rides (PENDING) |
| Instant | Yes | Ride Requests |
| Scheduled | No | Upcoming Rides |
| Scheduled | Yes | Ride Requests |

## Regression Risk Areas

When modifying any related module:

1. **Enterprise status** - Verify ACTIVE check
2. **User group membership** - Verify group requirement
3. **Program schedules** - Test day and time restrictions
4. **Ride limits** - Test all period types
5. **Budget limits** - Test all period types
6. **Geofencing** - Test pickup and dropoff restrictions
7. **Service restrictions** - Test allowed services
8. **Financial validation** - Test both payment plans
9. **Approval workflow** - Test routing
10. **Service availability** - Test enterprise and region levels

## Test Scenarios

### Scenario 1: Complete Happy Path (Prepaid)
```
Given: Enterprise (ACTIVE, Prepaid, balance = 10000)
And: User (ACTIVE, in group, program allows all)
When: Book instant trip (cost = 500)
Then: Booking accepted
And: Trip status = PENDING
And: Placed in Ongoing Rides
```

### Scenario 2: Inactive Enterprise
```
Given: Enterprise (INACTIVE)
When: Book trip
Then: Booking rejected at stage 1
And: Show "Account deactivated"
```

### Scenario 3: User Without Group
```
Given: Enterprise (ACTIVE)
And: User (ACTIVE, group = NULL)
When: Book trip
Then: Booking rejected at stage 2
And: Show "You must be assigned to a group"
```

### Scenario 4: Outside Schedule
```
Given: Enterprise (ACTIVE)
And: User in Program (Working Days only)
When: Book trip on Friday
Then: Booking rejected at stage 3a
And: Show "Trips not allowed at this time"
```

### Scenario 5: Ride Limit Reached
```
Given: Program (Limit: 3 rides/day)
And: User has 3 rides today
When: Book 4th ride
Then: Booking rejected at stage 3b
And: Show "Daily ride limit reached"
```

### Scenario 6: Insufficient Balance (Prepaid)
```
Given: Enterprise (Prepaid, balance = 100)
When: Book trip (cost = 500)
Then: Booking rejected at stage 4
And: Show "Insufficient balance"
```

### Scenario 7: Budget Exceeded (Postpaid)
```
Given: Enterprise (Postpaid, used = 9500, limit = 10000)
When: Book trip (cost = 1000)
Then: Booking rejected at stage 4
And: Show "Budget limit exceeded"
```

### Scenario 8: Approval Required
```
Given: Program (auto_approval = FALSE)
When: Book trip passing all checks
Then: Trip status = PENDING_APPROVAL
And: Placed in Ride Requests
And: Approvers notified
```

## Error Message Reference

| Stage | Condition | Message |
|-------|-----------|---------|
| 1 | Enterprise pending | "Account pending activation" |
| 1 | Enterprise inactive | "Account deactivated. Contact support" |
| 2 | User inactive | "Your account is inactive" |
| 2 | No group | "You must be assigned to a group" |
| 3a | Schedule violation | "Trips not allowed at this time" |
| 3b | Ride limit | "Ride limit reached for this [period]" |
| 3c | Budget limit | "Budget limit exceeded for this [period]" |
| 3d | Pickup restricted | "Pickup location not allowed" |
| 3d | Dropoff restricted | "Dropoff location not allowed" |
| 3e | Service restricted | "Service not available for your program" |
| 4 | Prepaid insufficient | "Insufficient balance. Top up to continue" |
| 4 | Postpaid exceeded | "Budget limit exceeded. Contact admin" |
| 5 | Enterprise service off | "Service not available for your company" |
| 5 | Region service off | "Service not available in this area" |
