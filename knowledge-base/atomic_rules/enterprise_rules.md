---
rule_type: atomic_rule
module: enterprises
risk_level: high
---

# Atomic Rules: Enterprise Management

## Account Lifecycle Rules

### RULE-ENT-001: Single Super Admin Policy
**Condition:** Enterprise account registration or admin promotion
**Validation:** Only ONE user can hold Super Admin role per enterprise
**Error:** "Enterprise already has a Super Admin. Demote existing before promotion."
**Priority:** Critical

### RULE-ENT-002: Account Activation Requirement
**Condition:** User attempts dashboard access
**Validation:** Enterprise status must be ACTIVE
**Error:** "Account pending activation. Contact support."
**Priority:** Critical

### RULE-ENT-003: Inactive Deletion Only
**Condition:** Delete enterprise request
**Validation:** Enterprise status must be INACTIVE
**Error:** "Cannot delete active enterprise. Deactivate first."
**Priority:** High

### RULE-ENT-004: Phone Number Uniqueness
**Condition:** User registration or phone update
**Validation:** Phone number unique per business account
**Error:** "Phone number already registered to another account."
**Priority:** High

### RULE-ENT-005: Country Lock by Phone Prefix
**Condition:** Registration phone entry
**Validation:** Country auto-detected and locked based on phone prefix
**Error:** N/A (auto-selection)
**Priority:** Medium

## User Management Rules

### RULE-ENT-006: Super Admin Demotion Protection
**Condition:** Attempt to demote current Super Admin
**Validation:** Cannot directly demote; must promote another user first
**Error:** "Promote another user to Super Admin to demote current admin."
**Priority:** High

### RULE-ENT-007: Auto-Demotion on Promotion
**Condition:** Rider promoted to Super Admin
**Validation:** Existing Super Admin automatically demoted to Business Admin
**Error:** N/A (automatic transition)
**Priority:** High

### RULE-ENT-008: Self-Edit Restriction
**Condition:** Admin attempts self-modification
**Validation:** Cannot edit or delete own profile
**Error:** "Cannot modify your own profile. Contact another admin."
**Priority:** Medium

### RULE-ENT-009: Group Migration Required
**Condition:** Delete group with members
**Validation:** All members must be migrated to another group first
**Error:** "Migrate members before deleting group."
**Priority:** High

## Legal Compliance Rules

### RULE-ENT-010: Legal Info for Invoice
**Condition:** Invoice generation request
**Validation:** Legal information must be approved
**Error:** "Legal information pending. Cannot generate invoice."
**Priority:** Critical

### RULE-ENT-011: Required Legal Documents
**Condition:** Legal info submission
**Validation:** NIF, NIS, RC, AI documents required
**Error:** "Missing required legal documents."
**Priority:** High

### RULE-ENT-012: Legal Info Review Queue
**Condition:** Legal documents submitted
**Validation:** Documents go to Admin Panel review queue
**Error:** N/A (queue processing)
**Priority:** Medium

## Status Transition Rules

### RULE-ENT-013: Valid Status Transitions
**Condition:** Enterprise status change
**Validation:**
- PENDING -> ACTIVE (approval)
- ACTIVE -> INACTIVE (deactivation)
- INACTIVE -> ACTIVE (reactivation)
**Error:** "Invalid status transition."
**Priority:** High

### RULE-ENT-014: No Active Trips for Deactivation
**Condition:** Enterprise deactivation request
**Validation:** No ongoing trips allowed
**Error:** "Complete or cancel ongoing trips before deactivation."
**Priority:** High

### RULE-ENT-015: Budget for Reactivation
**Condition:** Enterprise reactivation (Prepaid)
**Validation:** Wallet balance must be positive
**Error:** "Top up wallet before reactivation."
**Priority:** Medium

## Transaction Rules

### RULE-ENT-016: Transaction Logging
**Condition:** Any administrative or financial action
**Validation:** All actions must be logged with timestamp and actor
**Error:** N/A (system enforcement)
**Priority:** High

### RULE-ENT-017: Export Date Range Limit
**Condition:** Trip export request
**Validation:** Date range cannot exceed 31 days
**Error:** "Export range limited to 31 days."
**Priority:** Low

## Assignment Rules

### RULE-ENT-018: Sales Rep Reassignment on Delete
**Condition:** Delete Sales Representative
**Validation:** Assigned enterprises must be reassigned first
**Error:** "Reassign enterprises before deleting Sales Rep."
**Priority:** Medium

### RULE-ENT-019: Inside Sales Restriction
**Condition:** Inside Sales role access
**Validation:** Limited to Leads Management only
**Error:** "Access denied. Inside Sales restricted to Leads."
**Priority:** High
