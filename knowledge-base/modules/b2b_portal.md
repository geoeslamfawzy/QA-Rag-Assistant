---
module: b2b_portal
version: 1.0
last_updated: 2024-02-24
dependencies:
  - programs
  - trips
  - payments
  - users
---

# B2B Corporate Portal Module

## Overview

The B2B Corporate Portal is a dedicated platform for external businesses and corporate partners to manage transportation for their employees and clients. It enables companies to allocate free rides, apply corporate discounts, and track usage.

## Authentication

### Login Methods
- Google SSO (Single Sign-On)
- Standard Email & Password
- Phone Number

### Registration Workflow

**Step 1: Email Verification**
- User enters business email
- System validates email uniqueness
- Magic Link sent for verification

**Step 2: Security & Contact Verification**
- Password creation (must confirm)
- Phone number entry
- Phone uniqueness check (per business account)
- OTP verification via SMS

**Step 3: Company Profiling**
- Admin Details: First Name, Last Name, Job Position
- Business Metadata: Company Name, Industry, Company Size, Expected Platform Users
- Location Logic:
  - Country auto-detected from phone prefix (+213 = Algeria)
  - City dropdown filtered by detected country

**Step 4: Account Submission & Approval**
- Account created with status: PENDING/INACTIVE
- Notification triggered in Admin Panel
- Operations Team reviews and Activates/Rejects
- User blocked from dashboard until status = ACTIVE
- Notification sent upon activation

## Dashboard (Home)

### Global Navigation

**Top Navigation Bar:**
- Company Context: Yassir logo (home link)
- Budget Status Pill: Current financial status with refresh icon
- Language Selector: English, Arabic, French
- Notification Bell
- User Profile:
  - Display: First Name, Last Name, Position
  - Actions: Switch Company, Add New Company, Logout

**Side Navigation Menu (Collapsible):**
- Dashboard
- Users And Groups
- Programs
- Account (Profile Details, Edit Profile, Password, Settings, Legal Info)
- Book Rides
- Payments
- Trips
- Referrals
- Business Challenge
- Support

### Dashboard Widgets

**1. Onboarding Section**
- Conditional: Appears when setup incomplete
- Progress indicator (e.g., "1/3 Steps completed")
- Action cards: Update details, Set up team, Sign contract

**2. Operational Quick-Stats Row**
- Member Quick View: Total members count, "Invite Members" button
- Cashback Status: Current percentage, eligibility text
- Rides Summary: Total rides count

**3. Quick Actions & Financials**
- Ongoing Rides: Active trip counter, "Request ride" / "Rebook last ride"
- Financial Overview:
  - Postpaid: Budget usage vs limit, "Pay Due Budget"
  - Prepaid: Wallet balance, "Top Up Budget"

**4. Rides Overview**
- Time-series chart (14 days)
- Segmentation: Instant Rides (Pink), Scheduled Rides (Purple)

**5. Members and Groups Section**
- Total Members: Donut chart (Active vs Pending)
- Total Groups: Count + "Create group"
- Total Programs: Count + "Create program"

**6. Referrals Section**
- Referred businesses count
- "Go to referrals" action

## Key Business Rules

### Account Management
- RULE-B2B-001: One Super Admin per Enterprise account
- RULE-B2B-002: Phone number must be unique per business account
- RULE-B2B-003: Country locked based on phone prefix
- RULE-B2B-004: Account access blocked until status = ACTIVE
- RULE-B2B-005: Multiple company management supported per user

### Dashboard
- RULE-B2B-006: Onboarding section hidden when setup complete
- RULE-B2B-007: Financial widget adapts to payment plan (Prepaid/Postpaid)
- RULE-B2B-008: Budget refresh requires explicit user action

## API Endpoints

- `POST /api/auth/login` - User login
- `POST /api/auth/register` - Start registration
- `POST /api/auth/verify-email` - Email verification
- `POST /api/auth/verify-phone` - Phone OTP verification
- `GET /api/dashboard` - Dashboard data
- `GET /api/dashboard/stats` - Quick stats
- `GET /api/dashboard/rides-overview` - Rides chart data
