---
rule_type: atomic_rule
module: users
risk_level: high
---

# Atomic Rules: User Management

## Registration Rules

### RULE-USER-001: Email Uniqueness
**Condition:** User registration or email update
**Validation:** Email must be unique across the platform
**Error:** "Email already registered."
**Priority:** High

### RULE-USER-002: Email Format
**Condition:** Email input
**Validation:** Must match valid email format (RFC 5322)
**Error:** "Invalid email format."
**Priority:** Medium

### RULE-USER-003: Email Verification Required
**Condition:** Registration flow
**Validation:** Email must be verified via magic link before proceeding
**Error:** "Please verify your email to continue."
**Priority:** High

### RULE-USER-004: Phone Uniqueness per Business
**Condition:** Phone number entry
**Validation:** Phone unique within same business account
**Error:** "Phone number already registered to this business."
**Priority:** High

### RULE-USER-005: Phone Format by Country
**Condition:** Phone number input
**Validation:** Must match country-specific format based on prefix
| Prefix | Country | Format |
|--------|---------|--------|
| +213 | Algeria | +213 XXX XX XX XX |
| +216 | Tunisia | +216 XX XXX XXX |
| +212 | Morocco | +212 X XX XX XX XX |
| +221 | Senegal | +221 XX XXX XX XX |
**Error:** "Invalid phone number format for selected country."
**Priority:** Medium

### RULE-USER-006: OTP Verification Required
**Condition:** Phone number registration
**Validation:** OTP must be verified before account creation
**Error:** "Please verify your phone number."
**Priority:** High

### RULE-USER-007: Password Requirements
**Condition:** Password creation
**Validation:**
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
**Error:** "Password does not meet requirements."
**Priority:** High

### RULE-USER-008: Password Confirmation Match
**Condition:** Password creation
**Validation:** Password and confirmation must match
**Error:** "Passwords do not match."
**Priority:** High

## Role Rules

### RULE-USER-009: Valid Roles
**Condition:** Role assignment
**Validation:** Role must be one of: Super Admin, Business Admin, Program Moderator, Rider
**Error:** "Invalid role."
**Priority:** High

### RULE-USER-010: Single Super Admin
**Condition:** Super Admin assignment
**Validation:** Only one Super Admin per enterprise
**Error:** "Enterprise already has a Super Admin."
**Priority:** Critical

### RULE-USER-011: Auto-Demotion
**Condition:** New Super Admin assigned
**Validation:** Previous Super Admin automatically demoted to Business Admin
**Error:** N/A (automatic)
**Priority:** High

### RULE-USER-012: Moderator Scope
**Condition:** Program Moderator actions
**Validation:** Moderator can only manage assigned program and its groups
**Error:** "Access denied. Not your assigned program."
**Priority:** High

### RULE-USER-013: Rider Permissions
**Condition:** Rider actions
**Validation:** Rider can only: book trips, view own trips, view profile
**Error:** "Access denied."
**Priority:** High

## Status Rules

### RULE-USER-014: User Status Values
**Condition:** User status change
**Validation:** Status must be: Active, Pending, or Inactive
**Error:** "Invalid status."
**Priority:** Medium

### RULE-USER-015: Pending to Active
**Condition:** User accepts invitation
**Validation:** Status changes from Pending to Active
**Error:** N/A (automatic)
**Priority:** Medium

### RULE-USER-016: Manual Verification Override
**Condition:** Admin verifies user manually
**Validation:** Status set to Active, bypassing invitation
**Error:** N/A (admin action)
**Priority:** Low

### RULE-USER-017: Inactive User Access
**Condition:** Inactive user attempts login
**Validation:** Access denied
**Error:** "Account inactive. Contact administrator."
**Priority:** High

## Profile Rules

### RULE-USER-018: Required Profile Fields
**Condition:** Profile creation
**Validation:** Required: First Name, Last Name, Phone, Email
**Error:** "Please complete all required fields."
**Priority:** Medium

### RULE-USER-019: Name Format
**Condition:** Name input
**Validation:** Only letters, spaces, and hyphens allowed
**Error:** "Invalid characters in name."
**Priority:** Low

### RULE-USER-020: Job Position Optional
**Condition:** Profile completion
**Validation:** Job position is optional
**Error:** N/A
**Priority:** Low

## Session Rules

### RULE-USER-021: Session Timeout
**Condition:** User inactivity
**Validation:** Session expires after 30 minutes of inactivity
**Error:** "Session expired. Please log in again."
**Priority:** Medium

### RULE-USER-022: Concurrent Session Limit
**Condition:** Multiple device login
**Validation:** Maximum 3 concurrent sessions per user
**Error:** "Maximum sessions reached. Log out from another device."
**Priority:** Low

### RULE-USER-023: Logout Cascade
**Condition:** Password change
**Validation:** All existing sessions terminated
**Error:** N/A (security feature)
**Priority:** High

## Admin Rules

### RULE-USER-024: Admin Self-Edit Block
**Condition:** Admin attempts self-modification in Admin Panel
**Validation:** Cannot edit or delete own profile
**Error:** "Cannot modify your own profile."
**Priority:** Medium

### RULE-USER-025: Admin Country Access
**Condition:** Admin accesses data
**Validation:** Admin can only see data for assigned countries
**Error:** "Access denied for this country."
**Priority:** High

### RULE-USER-026: Super Admin Override
**Condition:** Super Admin actions
**Validation:** Super Admin bypasses all permission checks within enterprise
**Error:** N/A
**Priority:** High

## Deletion Rules

### RULE-USER-027: User Deletion Audit
**Condition:** User deleted
**Validation:** Deletion logged with timestamp and actor
**Error:** N/A (audit trail)
**Priority:** Medium

### RULE-USER-028: Active Trip Block
**Condition:** Delete user with active trips
**Validation:** Cannot delete user with ongoing trips
**Error:** "User has active trips. Complete or cancel before deletion."
**Priority:** High

### RULE-USER-029: Data Retention
**Condition:** User deleted
**Validation:** User data anonymized but retained for 90 days
**Error:** N/A (compliance)
**Priority:** Medium
