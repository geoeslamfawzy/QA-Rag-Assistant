---
module: referrals
version: 1.0
last_updated: 2024-02-24
dependencies:
  - enterprises
  - payments
  - b2b_portal
  - admin_panel
---

# Referrals Module

## Overview

The Referrals module is a growth-focused system designed to incentivize existing B2B clients to refer other businesses to the Yassir Mobility platform. It manages referral link distribution, tracking, and reward calculation based on payment plans.

## B2B Portal: Referrals

### Layout Structure
- **Left Column**: Functional tabs (Invites, Referrals Breakdown)
- **Right Column**: "How it works" guide

### Tab 1: Invites (Default View)

**Invite via Referral Link:**
- Pre-filled testimonial text with unique referral URL
- Actions: Share Link (native sharing), Copy Link

**Invite via Email:**
- Input field for email addresses
- "Send invite" button triggers automated email

### Tab 2: Referrals Breakdown

**Pending Referrals Card:**
- Count of invited businesses not yet qualified
- "Learn more" link (criteria explanation)

**Completed Referrals Card:**
- Count of successfully joined businesses
- "Learn more" link

### Information Sidebar ("How referrals work")

**Process Steps:**
1. Share unique link or invite via email
2. Referred business onboards and completes required task
3. Referrer receives reward

**Reward Definition:**
- Example: "3 free trips reward during ongoing month"
- Conditions: Monetary cap per trip (e.g., 2,000 DZD)

## Admin Panel: Referrals

### Enterprise-Level Referral Tab

**Referral Dashboard:**
- Completed Referrals count
- Unique Referral Link with Copy action
- Enterprises Referred list (Name, BAM Email, Status)

**Rewards Rule Configuration:**
- State 1: No Rule Set - "Create rule" button, "Use country configuration" checkbox
- State 2: Country Configuration - Inherits global rules
- State 3: Custom Rule - Edit/Delete options

**Hierarchy:** Enterprise Rule > Country Rule

### Global Referral Module (Country Level)

**Payment Plan Context:**
- Toggle between "Prepaid rule" and "Postpaid rule"

**Statistics Overview:**
- Total enterprises in country
- Total referrers
- Referred enterprises count

## Referral Rule Logic

### Prepaid Rules (Free Trips)

**Trigger Conditions (Select One):**
- Budget top-up: Referee tops up by X amount
- Rides completion: Referee completes X trips
- Members onboarded: Referee invites X members

**Reward Configuration:**
- Completion Threshold: Target value
- Reward: Number of free trips (max 20)
- Reward Price Limit: Max cost per free trip
- Validity: 1 month
- Reward Validity Date: Optional expiry

### Postpaid Rules (Invoice Discount)

**Trigger Conditions (Select One):**
- Amount Spent: Referee spends X amount
- Rides completion: Referee completes X trips
- Members onboarded: Referee invites X members

**Reward Configuration:**
- Completion Threshold: Target value
- Reward: Discount percentage on invoice
- Reward Price Limit: Cap on discount value
- Reward Validity Date: Optional expiry

## Business Rules

### General Rules
- RULE-REF-001: Each enterprise has unique referral link
- RULE-REF-002: Referrer must be active enterprise
- RULE-REF-003: Self-referral not allowed

### Reward Accumulation
- RULE-REF-004: Prepaid rewards stack (5 referrals x 20 trips = 100 free trips)
- RULE-REF-005: Postpaid percentages stack (10 referrals x 10% = 100% discount)
- RULE-REF-006: Maximum discount = 100% of invoice

### Payment Plan Switching
- RULE-REF-007: Plan switch (Prepaid <-> Postpaid) = ALL rewards expire immediately
- RULE-REF-008: Free trips do NOT convert to discounts
- RULE-REF-009: Discounts do NOT convert to free trips

### Rule Hierarchy
- RULE-REF-010: Enterprise Rule > Country Rule
- RULE-REF-011: Deleting Enterprise Rule reverts to Country Rule

### Prepaid-Specific
- RULE-REF-012: Free trips max 20 per referral
- RULE-REF-013: Price limit = binary eligibility (trip must be <= limit)
- RULE-REF-014: Rewards valid for 1 month

### Postpaid-Specific
- RULE-REF-015: Discount capped by Reward Price Limit
- RULE-REF-016: Discount applies to monthly invoice total

## State Machine

### Referral Status
| Status | Description |
|--------|-------------|
| PENDING | Invited but not qualified |
| COMPLETED | Qualified and reward issued |
| EXPIRED | Qualification period ended |

### Reward Status
| Status | Description |
|--------|-------------|
| AVAILABLE | Ready to use |
| USED | Consumed |
| EXPIRED | Validity period ended |
| VOIDED | Plan switched, reward invalidated |

## API Endpoints

### B2B Portal
- `GET /api/referrals/link` - Get referral link
- `POST /api/referrals/invite` - Send email invite
- `GET /api/referrals/pending` - Pending referrals
- `GET /api/referrals/completed` - Completed referrals
- `GET /api/referrals/rewards` - Available rewards

### Admin Panel
- `GET /api/admin/enterprises/{id}/referrals` - Enterprise referrals
- `GET /api/admin/referrals/country` - Country-level stats
- `POST /api/admin/referrals/rules` - Create rule
- `PUT /api/admin/referrals/rules/{id}` - Update rule
- `DELETE /api/admin/referrals/rules/{id}` - Delete rule
- `GET /api/admin/enterprises/{id}/referrals/rules` - Enterprise rules
