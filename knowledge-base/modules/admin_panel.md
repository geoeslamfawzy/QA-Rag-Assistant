---
module: admin_panel
version: 1.0
last_updated: 2024-02-24
dependencies:
  - enterprises
  - payments
  - legal_info
  - leads
---

# Admin Panel Module

## Overview

The Admin Panel is the central command center for Yassir Operations, Sales, and Support teams. It manages corporate accounts (B2B), legal compliance, user roles, and system configurations across all operating regions.

## Global Navigation

### Top Navigation Bar
- System Identity: Yassir Logo (redirects to Enterprises)
- Country Selector: Data isolation by country (Algeria, Tunisia, Morocco, Senegal)
- Notification Icon
- Admin Profile: Name and email

### Side Navigation Menu
1. Enterprises
2. Review Legal Info
3. Manage Admins (All Administrators, Sales Representatives, Inside Sales)
4. Country Reports
5. Leads Management
6. Services Config
7. Notifications
8. Referral
9. Challenges
10. Enterprises V1 (Legacy)
11. Yassir's Legal Info
12. Gift Cards

## Enterprises Module

### Search & Filtering
- Search by: Enterprise Name, Rider Phone Number, Rider Email
- Filters: Date, Payment Plan (Prepaid/Postpaid), Status (Active/Inactive), Service Area, Sales Rep

### Data Grid Columns
- Enterprise Name (with source indicator icon for manual/lead conversion)
- Payment Plan
- Sales Rep (N/A if unassigned)
- Creation Date
- Status

### Management Actions
- Add New Enterprise
- Export Data (CSV/Excel)
- Delete Enterprise (INACTIVE only)

### Enterprise Details Tabs

**Tab 1: Enterprise Information**
- Account Manager assignment
- Enterprise metadata (Legal Name, Industry, Size, Location)
- Commission Percentage (default 19%)
- Discount & Rebates configuration
- Account Type toggle (Enterprise/Individual)
- Legal Information section

**Tab 2: User Management**
- Access Dashboard (Limited Access simulation)
- Re-Invite All pending users
- User grid: Name, Phone, Email, Role, Status
- Actions: Edit user, Verify user (manual override)
- Role rules: Single Super Admin policy, promotion/demotion logic

**Tab 3: Payments**
- Invoice History (Paid/Unpaid filter)
- Manual Invoice Generation
- Payment Status Updates
- Prepaid: Top-up Balance
- Postpaid: Update Budget Limit
- Payment Plan Switching

**Tab 4: Transactions**
- Audit log of all activities
- Filters: Date, Action Type
- Action Types: Top Up, Update Budget, Activation, Deactivation, Legal updates

**Tab 5: Trips**
- Export Rides (max 31-day range)
- Filters: Trip Status, Date
- Columns: Client, Locations, Date, Trip ID, Price, Budget Before/After, Status, Refund

**Tab 6: Settings**
- Support Admin assignment
- Sales Representative assignment
- Enterprise Lifecycle: Deactivate/Activate/Delete

**Tab 7: Referral**
- Referral performance metrics
- Enterprise-specific reward rules
- Configuration: Country config or Custom rule

## Review Legal Info

### Purpose
Centralized queue for validating regulatory documents.

### Filters
- Enterprise Name search
- Submission Date
- Status: Pending, Approved, Rejected

### Actions
- Review Submission (Pending only)

## Manage Admins

### All Administrators
- Search by Name/Email
- Filters: Country, Status (Active/Inactive)
- Self-management constraint: Cannot edit/delete own profile
- Edit permissions: Role toggles, Country access, Module permissions

### Sales Representatives
- Enterprise assignment (bulk update supported)
- Deletion requires enterprise reassignment

### Inside Sales
- Restricted to Leads Management view
- Deletion options: Remove from Inside Sales only, or Full deletion
- Orphaned leads revert to Unassigned

## Country Reports

### Monthly Invoices
- Bulk generation for all enterprises
- Output: CSV with company data and invoice links

### Monthly Finance Reports
- Async email delivery
- Columns: Company details, BAM info, Budget, Invoice details, Discounts, Free trips, Sales attribution

## Services Config

- Country-level service catalog
- Enterprise-level enable/disable per service
- Bulk actions: Enable/Disable for all

## Key Business Rules

### Enterprise Management
- RULE-ADMIN-001: Only INACTIVE enterprises can be deleted
- RULE-ADMIN-002: Payment plan switch: Prepaid balance deducted from first Postpaid invoice
- RULE-ADMIN-003: Legal info required for invoice generation
- RULE-ADMIN-004: Single Super Admin per enterprise

### User Management
- RULE-ADMIN-005: Promoting Rider to Super Admin demotes existing Super Admin
- RULE-ADMIN-006: Current Super Admin cannot be directly demoted

### Transactions
- RULE-ADMIN-007: All financial and administrative actions logged
- RULE-ADMIN-008: Export date range limited to 31 days

### Permissions
- RULE-ADMIN-009: Self-manipulation not allowed (cannot edit/delete own profile)
- RULE-ADMIN-010: Inside Sales restricted to Leads Management only
