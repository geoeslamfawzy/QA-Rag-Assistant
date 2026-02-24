---
module: gift_cards
version: 1.0
last_updated: 2024-02-24
dependencies:
  - payments
  - b2b_portal
  - admin_panel
---

# Gift Cards Module

## Overview

Gift Cards provide a self-service marketplace where Business Admins can purchase digital vouchers to incentivize employees or guests. The module handles the full lifecycle: Purchase -> Configuration -> Distribution -> Tracking -> Reclamation.

## B2B Portal: Gift Cards

### Buy Gift Cards Tab

**Template Marketplace:**
- Grid of available templates (country-specific)
- Card metadata: Visual Theme, Monetary Value
- Actions: "Customize card" or "Add funds to buy"

**Budget Validation Logic:**
- System checks Wallet Balance vs Gift Card price
- Sufficient Funds: Purchase enabled
- Insufficient Funds: Button disabled
- On purchase: Cost immediately deducted from company budget

### Program Configuration (After Purchase)

**Customization Form:**
- Validity Period: Start Date, Expiry Date
- Monetary Limits: Minimum ride cost, Maximum ride cost
- Usage Frequency: Total uses (lifetime), Uses per ride (daily)
- Geofencing: Pick-up and Drop-off locations
- Discount Rate: Percentage covered (default 100%)

**Default Settings Option:**
- Skip configuration with "Use default settings"
- Defaults: Unlimited time, Anywhere-to-Anywhere, 100% discount

### My Cards Tab (Inventory)

**Dashboard View:**
- Card Status: Active or Expired
- Financial Tracking: Original Value, Remaining Balance
- Actions: View details, Download, Revert balance

**Card Details View:**
- Program rules summary (Validity, Restrictions)
- Current financial health

### Distribution

**Download as PDF:**
- Generates printable voucher
- Contains: Voucher Code (e.g., GRT-102956), QR code, Usage rules

### Usage History

**Data Points:**
- User Name & Phone
- Date & Time
- Itinerary (Start/End points)
- Ride Cost
- Card Value Used

**Empty State:** "No usage recorded yet"

### Financial Reversal (Revert to Budget)

**Revert Workflow:**
1. Available on cards with Remaining Balance > 0
2. Click "Refund remaining balance"
3. Confirmation modal: "Refund [Amount] to your balance?"
4. On confirm:
   - Funds credited to Company Wallet
   - Gift Card status = Deactivated/Reverted
   - Voucher code becomes invalid

## Admin Panel: Gift Cards

### Templates Dashboard

**Search & Filtering:**
- Search by Name
- Filter by Status: Active/Inactive

**Grid Columns:**
- Name
- Amount
- Theme
- No of purchases (click for usage report)
- Status
- Actions: Settings (Gear), Delete/Deactivate

### Create Giftcard Template

**Configuration Form:**
- Template Name (required)
- Monetary Amount
- Country (auto-locked to admin's region)
- Visual Theme selection (Classic, Midnight Noir, Pink, Birthday, etc.)

**Country Rule:** Templates are country-specific. Business Admins only see cards for their country.

### Lifecycle Management

**Deactivation (For Used Templates):**
- Condition: Purchases >= 1
- Action: Changes status to Inactive
- Impact: Removed from B2B WebApp, remains in Admin Panel for reporting
- Existing active cards remain valid

**Deletion (For Unused Templates):**
- Condition: Purchases = 0
- Action: Permanent removal from system

### Usage Reporting

**Purchased Instances List:**
- Business name
- Giftcard ID
- Total trips paid
- Remaining value

**Trip Log:**
- Granular history of rides
- User Phone Number for audit

**Activity Log:**
- All admin actions (Created, Deactivated)
- Editor ID and timestamps

## Business Rules

### Purchase Rules
- RULE-GC-001: Wallet balance must cover gift card price
- RULE-GC-002: Cost deducted immediately on purchase
- RULE-GC-003: Insufficient funds = purchase blocked

### Configuration Rules
- RULE-GC-004: Default settings apply if no customization
- RULE-GC-005: Validity period defines card lifespan
- RULE-GC-006: Usage caps enforced (lifetime and daily)

### Usage Rules
- RULE-GC-007: Card value deducted per trip
- RULE-GC-008: Trip cost within min/max limits
- RULE-GC-009: Geofencing restricts pickup/dropoff

### Reversal Rules
- RULE-GC-010: Only cards with remaining balance can be reverted
- RULE-GC-011: Revert credits company wallet immediately
- RULE-GC-012: Reverted card = permanently deactivated
- RULE-GC-013: Voucher code invalidated after revert

### Admin Rules
- RULE-GC-014: Templates are country-specific
- RULE-GC-015: Only unused templates (0 purchases) can be deleted
- RULE-GC-016: Used templates can only be deactivated

## State Machine

| State | Triggers | Next States |
|-------|----------|-------------|
| ACTIVE | Card in use | EXPIRED, DEACTIVATED, REVERTED |
| EXPIRED | Validity period ends | (Terminal) |
| DEACTIVATED | Manual deactivation | (Terminal) |
| REVERTED | Balance refund | (Terminal) |

## API Endpoints

### B2B Portal
- `GET /api/giftcards/templates` - Available templates
- `POST /api/giftcards/purchase` - Purchase card
- `GET /api/giftcards` - My cards
- `GET /api/giftcards/{id}` - Card details
- `GET /api/giftcards/{id}/usage` - Usage history
- `POST /api/giftcards/{id}/revert` - Revert balance
- `GET /api/giftcards/{id}/download` - Download PDF

### Admin Panel
- `GET /api/admin/giftcards/templates` - All templates
- `POST /api/admin/giftcards/templates` - Create template
- `PUT /api/admin/giftcards/templates/{id}` - Update template
- `DELETE /api/admin/giftcards/templates/{id}` - Delete template
- `POST /api/admin/giftcards/templates/{id}/deactivate` - Deactivate
- `GET /api/admin/giftcards/templates/{id}/purchases` - Purchase list
- `GET /api/admin/giftcards/{id}/trips` - Trip log
