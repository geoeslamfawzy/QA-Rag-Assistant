---
dependency_type: cross_module
modules: [programs, users, groups, trips]
risk_level: high
---

# Cross Dependencies: Programs <-> Users <-> Groups

## Overview

The Programs, Users, and Groups modules form a tightly coupled permission and access control system. Users must be in groups, groups must be in programs, and programs define what users can do.

## Dependency Matrix

| User State | Group State | Program State | Trip Access |
|------------|-------------|---------------|-------------|
| Active | Assigned | Active | Allowed (per rules) |
| Active | Assigned | Inactive | Blocked |
| Active | Unassigned | - | Blocked |
| Pending | - | - | Blocked |
| Inactive | - | - | Blocked |

## Critical Dependencies

### DEP-PU-001: Group Membership Requirement
**Trigger:** User attempts program access
**Dependency:** User must belong to a group assigned to the program

```
IF user.group IS NULL:
    DENY access
    SHOW "You must be assigned to a group"
ELSE IF user.group.program != target_program:
    DENY access
    SHOW "Your group is not assigned to this program"
```

**Impact:** Access without group = unauthorized trips

### DEP-PU-002: Program Rules Cascade to Users
**Trigger:** Trip booking by user
**Dependency:** Program rules apply to all users in assigned groups

**Applied Rules:**
- Ride schedule (days, times)
- Ride limits (per day/week/month)
- Budget limits (per trip/day/week/month)
- Service restrictions
- Location restrictions (geofencing)
- Approval requirements

```
FOR rule IN user.group.program.rules:
    IF NOT validate(rule, trip_request):
        REJECT trip
        SHOW rule.error_message
```

**Impact:** Rules not applied = policy violations

### DEP-PU-003: Role-Based Access Control
**Trigger:** User action in portal
**Dependency:** Permissions determined by user role

| Role | Scope | Capabilities |
|------|-------|--------------|
| Super Admin | Enterprise-wide | All operations |
| Business Admin | Enterprise-wide | Most operations |
| Program Moderator | Assigned program | Program management |
| Rider | Self only | Book trips, view history |

```
IF user.role == PROGRAM_MODERATOR:
    allowed_programs = [user.assigned_program]
    IF action.target_program NOT IN allowed_programs:
        DENY action
```

**Impact:** Wrong permissions = security breach or blocked legitimate actions

### DEP-PU-004: Group Deletion Migration
**Trigger:** Delete group with members
**Dependency:** Members must be migrated first

```
IF group.members.count > 0:
    BLOCK deletion
    SHOW "Migrate X members before deletion"
    OFFER migration_modal
ON migration_complete:
    ALLOW deletion
```

**Impact:** Deletion without migration = orphaned users

### DEP-PU-005: Program Deactivation Group Transfer
**Trigger:** Deactivate program with groups
**Dependency:** Groups must be transferred to another program

```
IF program.groups.count > 0:
    BLOCK deactivation
    SHOW "Transfer X groups before deactivation"
    OFFER transfer_modal
ON transfer_complete:
    ALLOW deactivation
```

**Impact:** Deactivation without transfer = orphaned groups

### DEP-PU-006: Single Super Admin Constraint
**Trigger:** Promote user to Super Admin
**Dependency:** Existing Super Admin auto-demoted

```
IF enterprise.super_admin EXISTS:
    existing_admin = enterprise.super_admin
    existing_admin.role = BUSINESS_ADMIN
    LOG "Super Admin demoted: {existing_admin}"
new_user.role = SUPER_ADMIN
LOG "New Super Admin: {new_user}"
```

**Impact:** Multiple Super Admins = ambiguous authority

### DEP-PU-007: Approval Workflow Routing
**Trigger:** Trip requires approval
**Dependency:** Routes to correct approvers based on user's program

```
IF user.group.program.auto_approval == FALSE:
    trip.status = PENDING_APPROVAL
    approvers = get_approvers(user.group.program)
    NOTIFY approvers
```

**Impact:** Wrong routing = delayed or missed approvals

## State Transition Dependencies

### User Invitation Accepted
**When:** User accepts invitation
**Triggers:**
- User status: PENDING -> ACTIVE
- User added to specified group
- User inherits program rules

### User Role Change
**When:** Role updated (e.g., Rider -> Moderator)
**Triggers:**
- Permission scope changes
- If promoted to Super Admin: Previous Super Admin demoted
- Audit log entry

### Group Assignment Change
**When:** User moved to different group
**Triggers:**
- Program rules change (if different program)
- Ride limits reset (if different program)
- Budget tracking reset (if different program)

### Program Deactivation
**When:** Program status -> INACTIVE
**Triggers:**
- All users in program groups blocked from booking
- Dashboard shows "Program inactive" message
- Moderators lose management access

## Data Flow

```
[User Invitation]
      |
      v
[Group Assignment] --> [Program Rules]
      |                      |
      v                      v
[User Active]          [Rule Enforcement]
      |                      |
      v                      v
[Trip Booking] <-------- [Validation]
```

## Regression Risk Areas

When modifying Programs, Users, or Groups:

1. **Group membership** - Verify access blocked without group
2. **Program rules** - Test each rule type (schedule, limits, etc.)
3. **Role permissions** - Test each role's capabilities
4. **Bulk operations** - Test CSV invite, group migration
5. **Deletion flows** - Test migration requirements
6. **Deactivation flows** - Test transfer requirements
7. **Role promotion** - Test Super Admin demotion cascade

## Test Scenarios

### Scenario 1: User Without Group
```
Given: User (Active), group = NULL
When: Attempt to book trip
Then: Booking blocked
And: Show "Assign to a group first"
```

### Scenario 2: Program Schedule Enforcement
```
Given: User in Program (Working Days: Sun-Thu)
When: Book trip on Friday
Then: Booking blocked
And: Show "Trips not allowed on this day"
```

### Scenario 3: Ride Limit Enforcement
```
Given: User in Program (Limit: 5 rides/week)
And: User has 5 rides this week
When: Book 6th ride
Then: Booking blocked
And: Show "Weekly ride limit reached"
```

### Scenario 4: Moderator Scope
```
Given: User (Program Moderator), assigned_program = "Sales Team"
When: Attempt to edit "Marketing Team" program
Then: Action blocked
And: Show "Access denied"
```

### Scenario 5: Group Deletion with Members
```
Given: Group with 10 members
When: Attempt to delete group
Then: Deletion blocked
And: Show "Migrate 10 members first"
And: Offer migration modal
```

### Scenario 6: Super Admin Promotion
```
Given: Enterprise with Super Admin (user_a)
When: Promote user_b to Super Admin
Then: user_b.role = SUPER_ADMIN
And: user_a.role = BUSINESS_ADMIN
And: Audit log updated
```
