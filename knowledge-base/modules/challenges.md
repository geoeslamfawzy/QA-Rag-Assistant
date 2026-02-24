---
module: challenges
version: 1.0
last_updated: 2024-02-24
dependencies:
  - enterprises
  - trips
  - payments
  - admin_panel
---

# Business Challenges Module

## Overview

The Business Challenges module is a gamification and engagement system designed to incentivize corporate riders. It tracks usage against specific goals and rewards businesses with discounts based on ride volume and tier progression.

## B2B Portal: Challenges Dashboard

### Active Challenge Section (Top Banner)

**Visibility:** Only appears if there's an ONGOING challenge

**Display Elements:**
- Date Range (start - end)
- Status Indicator: "Ongoing"
- Performance Metrics: Earned Discount, Completed Rides
- Action: "View Details" button

### Challenge History Section

**Search & Filter:**
- Search by Challenge Name
- Date filter
- Status filter: Expired, Completed, Partially Completed

**Data Columns:**
- Challenge Name
- Date Range
- Reward (achieved)
- Status
- Actions: "View Details"

## Challenge Details Page

### Header & Context
- Back button
- Challenge Name
- Date Range
- Status Tag (Completed, Ongoing, Expired)

### Progression Map

**Progress Bar:** Linear bar showing overall completion

**Tier Grid (Badges):**
- Sequential milestones displayed in grid
- Badge Information:
  - Discount Label (e.g., 10% discount)
  - Badge Icon (Copper, Bronze, Silver, Gold, Platinum)
  - Tier Name (e.g., Copper 1, Gold 2)
  - Entry/Exit Criteria (e.g., 3-4 rides)
- State Logic: Badges light up when criteria met

### Performance Sidebar

**Overview Widget:**
- Rides Completed
- Discount Earned (e.g., 100%)

**"How it works" Widget:**
- Instruction 1: Unlock levels by taking professional rides
- Instruction 2: Accumulate discounts, receive at billing cycle end

## Admin Panel: Challenges

### Challenges Dashboard

**Search & Filtering:**
- Search by name
- Filters: Date, Status (Upcoming/Ongoing/Completed/Expired), Activation (Enabled/Disabled)

**Data Grid Columns:**
- Challenge Name
- Start/End Date
- Completed by (enterprise count)
- Activation status
- Status (lifecycle)
- Actions: "View details"

### Create Challenge Wizard

**Step 1: Basic Configuration**
- Challenge Name (max 30 characters)
- Duration: Start Date, End Date
- Constraints:
  - Cannot create challenge in the past
  - Cannot overlap with existing challenges for same companies

**Step 2: Eligibility (Targeting)**
- All enterprises
- Prepaid enterprises
- Postpaid enterprises
- Select from enterprises list (manual)

**Step 3: Tier Configuration (Criteria Logic)**

**Structure:** Up to 10 sequential criteria (levels)

**Sequential Logic Rule:**
- If Criterion (n) ends at X trips
- Then Criterion (n+1) must start at X+1 trips

**Reward Rules:**
- Input: Percentage per tier
- Cap: Cumulative reward cannot exceed 100%

## Business Rules

### Challenge Creation
- RULE-CHAL-001: Challenge name max 30 characters
- RULE-CHAL-002: Cannot create challenges in the past
- RULE-CHAL-003: Cannot overlap with existing challenges for same enterprises
- RULE-CHAL-004: Max 10 tiers per challenge

### Tier Logic
- RULE-CHAL-005: Tiers must be sequential (no gaps)
- RULE-CHAL-006: Tier n+1 starts at (Tier n end + 1)
- RULE-CHAL-007: Cumulative discount max 100%

### Lifecycle
- RULE-CHAL-008: Only UPCOMING challenges can be edited
- RULE-CHAL-009: Only UPCOMING challenges can be deactivated
- RULE-CHAL-010: Only UPCOMING challenges can be deleted
- RULE-CHAL-011: ONGOING/COMPLETED/EXPIRED challenges are locked

### Rewards
- RULE-CHAL-012: Discounts apply to invoice at billing cycle end
- RULE-CHAL-013: Discount earned = sum of completed tier percentages
- RULE-CHAL-014: Badge unlocks when ride count meets tier criteria

### Status Transitions
- RULE-CHAL-015: UPCOMING -> ONGOING when start date reached
- RULE-CHAL-016: ONGOING -> COMPLETED when all tiers completed
- RULE-CHAL-017: ONGOING -> EXPIRED when end date passed without completion

## State Machine

### Challenge States

| State | Description | Editable | Deletable |
|-------|-------------|----------|-----------|
| UPCOMING | Not yet started | Yes | Yes |
| ONGOING | Currently active | No | No |
| COMPLETED | All tiers achieved | No | No |
| EXPIRED | End date passed | No | No |

### State Transitions

| From | To | Trigger |
|------|-----|---------|
| UPCOMING | ONGOING | Start date reached |
| ONGOING | COMPLETED | All tiers completed |
| ONGOING | EXPIRED | End date passed |
| UPCOMING | (deleted) | Manual deletion |

### Badge/Tier States

| State | Description |
|-------|-------------|
| LOCKED | Criteria not met |
| UNLOCKED | Criteria met, badge earned |

## Tier Examples

### Sample Challenge: "December Sprint"

| Tier | Badge | Rides Required | Discount |
|------|-------|----------------|----------|
| 1 | Copper 1 | 1-5 | 5% |
| 2 | Copper 2 | 6-10 | 10% |
| 3 | Bronze 1 | 11-20 | 15% |
| 4 | Bronze 2 | 21-30 | 20% |
| 5 | Silver | 31-50 | 30% |
| 6 | Gold | 51-75 | 50% |
| 7 | Platinum | 76-100 | 100% |

**Completion Example:**
- Enterprise completes 45 rides
- Earns: Copper 1 + Copper 2 + Bronze 1 + Bronze 2 + Silver = 5+10+15+20+30 = 80% discount

## Audit Trail

### Activity Log Data
- Date
- Editor (Admin email)
- Action (Created, Updated Status, etc.)
- Log details (Old value -> New value)

## API Endpoints

### B2B Portal
- `GET /api/challenges/active` - Get active challenge
- `GET /api/challenges/history` - Challenge history
- `GET /api/challenges/{id}` - Challenge details
- `GET /api/challenges/{id}/progress` - Current progress

### Admin Panel
- `GET /api/admin/challenges` - All challenges
- `POST /api/admin/challenges` - Create challenge
- `GET /api/admin/challenges/{id}` - Challenge details
- `PUT /api/admin/challenges/{id}` - Update challenge (UPCOMING only)
- `DELETE /api/admin/challenges/{id}` - Delete challenge (UPCOMING only)
- `POST /api/admin/challenges/{id}/activate` - Activate
- `POST /api/admin/challenges/{id}/deactivate` - Deactivate
- `GET /api/admin/challenges/{id}/enterprises` - Participating enterprises
- `GET /api/admin/challenges/{id}/activity` - Activity log
