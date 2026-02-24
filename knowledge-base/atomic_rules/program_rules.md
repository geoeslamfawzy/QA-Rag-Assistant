---
rule_type: atomic_rule
module: programs
risk_level: medium
---

# Atomic Rules: Programs & Groups

## Program Lifecycle Rules

### RULE-PROG-001: Group Requirement for Access
**Condition:** User attempts program access
**Validation:** User must belong to a group assigned to the program
**Error:** "You must be assigned to a group to access this program."
**Priority:** High

### RULE-PROG-002: Deactivation Group Transfer
**Condition:** Program deactivation request
**Validation:** If program has assigned groups, must transfer before deactivation
**Error:** "Transfer groups to another program before deactivation."
**Priority:** High

### RULE-PROG-003: Inactive Deletion Only
**Condition:** Program deletion request
**Validation:** Program must be INACTIVE to delete
**Error:** "Cannot delete active program. Deactivate first."
**Priority:** High

### RULE-PROG-004: No Duplicate Program Names
**Condition:** Program creation or rename
**Validation:** Program name must be unique within enterprise
**Error:** "Program name already exists."
**Priority:** Medium

## Group Rules

### RULE-PROG-005: Member Migration for Deletion
**Condition:** Group deletion request
**Validation:** All members must be migrated to another group first
**Error:** "Migrate all members before deleting group."
**Priority:** High

### RULE-PROG-006: Default Group Existence
**Condition:** Enterprise setup
**Validation:** At least one default group must exist
**Error:** "Cannot delete the last group."
**Priority:** High

### RULE-PROG-007: Program Assignment Required
**Condition:** Group creation
**Validation:** Group must be assigned to a program
**Error:** "Select a program for this group."
**Priority:** Medium

## User Assignment Rules

### RULE-PROG-008: Single Group Membership
**Condition:** User group assignment
**Validation:** User can only belong to one group at a time
**Error:** "User already assigned to another group."
**Priority:** Medium

### RULE-PROG-009: Moderator Role Restriction
**Condition:** User role = Program Moderator
**Validation:** Moderator can only manage their assigned program
**Error:** "Access denied. You can only manage your assigned program."
**Priority:** High

### RULE-PROG-010: Bulk Invite Limit
**Condition:** CSV bulk invite
**Validation:** Maximum 500 users per CSV upload
**Error:** "Bulk invite limited to 500 users."
**Priority:** Low

## Schedule Rules

### RULE-PROG-011: Working Days Definition
**Condition:** Schedule type = Working Days
**Validation:** Valid days: Sunday, Monday, Tuesday, Wednesday, Thursday
**Error:** N/A (UI constraint)
**Priority:** Medium

### RULE-PROG-012: Weekend Definition
**Condition:** Schedule type = Weekend
**Validation:** Valid days: Friday, Saturday
**Error:** N/A (UI constraint)
**Priority:** Medium

### RULE-PROG-013: Time Range Validation
**Condition:** Custom time range set
**Validation:** Start time must be before end time
**Error:** "Invalid time range."
**Priority:** Low

## Permission Rules

### RULE-PROG-014: Ride Limit Types
**Condition:** Ride limit configuration
**Validation:** Must specify: per Day, per Week, or per Month
**Error:** "Select ride limit period."
**Priority:** Medium

### RULE-PROG-015: Budget Limit Types
**Condition:** Budget limit configuration
**Validation:** Must specify: per Trip, per Day, per Week, or per Month
**Error:** "Select budget limit period."
**Priority:** Medium

### RULE-PROG-016: Unlimited Override
**Condition:** Unlimited checkbox selected
**Validation:** Numeric limit fields disabled when unlimited
**Error:** N/A (UI behavior)
**Priority:** Low

### RULE-PROG-017: Auto-Approval Default
**Condition:** New program creation
**Validation:** Auto-approval defaults to ON
**Error:** N/A (default setting)
**Priority:** Low

## Service Rules

### RULE-PROG-018: At Least One Service
**Condition:** Program service configuration
**Validation:** Program must have at least one enabled service
**Error:** "Enable at least one service for this program."
**Priority:** High

### RULE-PROG-019: Service Inheritance
**Condition:** Enterprise service disabled
**Validation:** If enterprise-level service disabled, program cannot enable it
**Error:** "Service not available at enterprise level."
**Priority:** Medium

### RULE-PROG-020: Cargo Service Restrictions
**Condition:** Cargo service selection
**Validation:** Cargo services may have additional restrictions (weight, size)
**Error:** "Cargo service restrictions apply."
**Priority:** Low

## Geofencing Rules

### RULE-PROG-021: Location Format
**Condition:** Address restriction set
**Validation:** Must be valid address within operating country
**Error:** "Invalid location format."
**Priority:** Medium

### RULE-PROG-022: Round Trip Logic
**Condition:** Round trips enabled
**Validation:** Destination automatically set to departure
**Error:** N/A (automatic)
**Priority:** Low

### RULE-PROG-023: Country Boundary
**Condition:** Any location set
**Validation:** Location must be within enterprise's operating country
**Error:** "Location outside operating area."
**Priority:** High

## Invitation Rules

### RULE-PROG-024: Email or Phone Required
**Condition:** User invitation
**Validation:** Must provide email OR phone number
**Error:** "Provide email or phone number."
**Priority:** High

### RULE-PROG-025: Phone Format Validation
**Condition:** Phone number entry
**Validation:** Must match country phone format
**Error:** "Invalid phone number format."
**Priority:** Medium

### RULE-PROG-026: Duplicate Invitation Check
**Condition:** Send invitation
**Validation:** Cannot invite already-registered user
**Error:** "User already registered."
**Priority:** Medium

### RULE-PROG-027: Invitation Link Expiry
**Condition:** Invitation link generated
**Validation:** Link expires after 30 days
**Error:** "Invitation link expired."
**Priority:** Low
