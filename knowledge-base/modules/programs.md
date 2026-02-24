---
module: programs
version: 1.0
last_updated: 2024-02-24
dependencies:
  - users
  - trips
  - b2b_portal
---

# Programs Module

## Overview

The Programs module allows administrators to define, manage, and customize ride policies for user groups. Programs control schedules, service access, permissions, and approval workflows.

## Users Tab

### User List
- Displays all platform users
- Searchable by email or username

### Filtering
- Programs
- Groups
- User Status

### Editing User Details
- Group assignment
- Role: Program Moderator, Business Admin, or Rider
- Ride Approval Settings: Follow program settings or require specific approval

### User Actions
- Edit (via edit icon)
- Delete (via delete icon with confirmation)

### Inviting New Users

**General Invitation:**
1. Click "Invite Users" button
2. Select Group and Program
3. Enter Email Address or Phone Number
4. Bulk invite via CSV upload (template available)
5. Generate shareable invitation link

## Groups Tab

### Group List
- Searchable by group name
- Actions: Edit, Delete

### Deleting Groups
- If group has members: Must migrate to another group before deletion

### Editing Groups
Two tabs:
1. **Group Users**: Add users to group
2. **Settings**: Group configuration

### Creating New Group
Required fields:
- Group Name
- Assigned Program
- Add users (optional)

## My Programs Page

### Program List
- Searchable by Program Name
- Actions: Edit, Deactivate, Activate, Delete

### Program Lifecycle
- Active programs can be deactivated
- Deactivation requires group transfer if assigned
- Only inactive programs can be deleted

## Creating a New Program

### Program Information & Restrictions

**Basic Info:**
- Program Name (required)
- Program Type (optional)

**Addresses (Geo-fencing):**
- Departure location (default: "Any location inside the country")
- Destination location
- Round trips toggle
- Specific location restriction example: "Boufaric" = trips must start from there

### Rides Schedule

**Frequency (Days):**
| Option | Days |
|--------|------|
| Daily | All days |
| Working Days | Sun-Thu (blocks Fri/Sat) |
| Weekend | Fri/Sat only |
| Custom | Admin selects specific days |

**Time Range:**
| Option | Hours |
|--------|-------|
| Morning | 5:00 - 14:00 |
| Working Hours | 7:00 - 18:00 |
| Day | 0:00 - 24:00 |
| Custom | Admin selects range |

### Permissions

**Ride Limit per Member:**
- Set by: Day, Week, or Month
- "Unlimited trips" checkbox available

**Budget per Member per Ride:**
- Set by: Trip, Day, Week, or Month
- "Unlimited budget" checkbox available

**Ride Request Auto-approval:**
- Toggle: ON = auto-approve, OFF = manual approval required

**Show Price to Members:**
- Toggle: Controls price visibility

### Services

- Select available ride services (Classic, Comfort, Premium, Cargo, etc.)
- Services can be permitted or removed per program

## Business Rules

### User Rules
- RULE-PROG-001: Users must belong to a group to access a program
- RULE-PROG-002: Role change to Program Moderator grants program-level management
- RULE-PROG-003: Bulk invite supported via CSV

### Group Rules
- RULE-PROG-004: Group deletion requires member migration
- RULE-PROG-005: Default group exists for new users

### Program Rules
- RULE-PROG-006: Program deactivation requires group transfer
- RULE-PROG-007: Only inactive programs can be deleted
- RULE-PROG-008: Geo-fencing restricts pickup/dropoff locations

### Schedule Rules
- RULE-PROG-009: Working Days = Sunday to Thursday
- RULE-PROG-010: Weekend = Friday and Saturday (regional)

### Permission Rules
- RULE-PROG-011: Ride limits enforced per member per period
- RULE-PROG-012: Budget limits enforced per member per period
- RULE-PROG-013: Auto-approval OFF = trips go to Ride Requests

### Service Rules
- RULE-PROG-014: Available services filtered by program configuration
- RULE-PROG-015: Cargo services have specific constraints

## API Endpoints

- `GET /api/programs` - List programs
- `POST /api/programs` - Create program
- `GET /api/programs/{id}` - Get program details
- `PUT /api/programs/{id}` - Update program
- `DELETE /api/programs/{id}` - Delete program (inactive only)
- `POST /api/programs/{id}/activate` - Activate program
- `POST /api/programs/{id}/deactivate` - Deactivate program
- `GET /api/groups` - List groups
- `POST /api/groups` - Create group
- `PUT /api/groups/{id}` - Update group
- `DELETE /api/groups/{id}` - Delete group (after migration)
- `POST /api/users/invite` - Invite users
- `POST /api/users/bulk-invite` - Bulk invite via CSV
