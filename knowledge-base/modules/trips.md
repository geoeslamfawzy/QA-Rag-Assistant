---
module: trips
version: 1.0
last_updated: 2024-02-24
dependencies:
  - programs
  - payments
  - b2b_portal
---

# Trips Module

## Overview

The Trips module handles all ride booking functionality for the B2B Corporate Portal. It supports instant and scheduled trips, multi-stop journeys, guest bookings, and comprehensive trip management.

## Book Rides

### Rider Selection
- **Book for me**: Admin books for themselves
- **Select a rider**: Book for another member
- **Request for a guest**: Book for non-member (guest cannot self-book)

### Booking Options

**Instant vs Scheduled**
- Instant: Immediate booking
- Scheduled: "Book for later" toggle enables date/time selection

**Multi-stop Trips**
- Fields: Departure, Stop 1, ..., Destination
- Add/remove stops dynamically

**Service Selection**
- Available services depend on program settings
- Options: Classic, Comfort, Premium, Business Classic, Yassir Luxury, etc.

**Repeat Booking**
- Available for scheduled trips only
- Recurrence configuration

### Booking Confirmation

**Confirmation Pop-up Details:**
- Departure, stops, Destination
- Date/Time and Estimated Arrival
- Service and Price
- Distance
- Rider name, Program, Group

### Ride Placement

| Booking Type | Placement |
|--------------|-----------|
| Instant | Ongoing Rides tab |
| Scheduled | Upcoming Rides tab |
| Requires Approval | Ride Requests tab |

## Trip Statuses

### Complete Status List

| Status | Description |
|--------|-------------|
| PENDING | Awaiting driver acceptance |
| ACCEPTED | Driver accepted, en route to pickup |
| DRIVER_ARRIVED | Driver at pickup location |
| STARTED | Trip in progress |
| FINISHED | Trip completed (equivalent to Completed) |
| DRIVER_CANCELED | Driver cancelled the trip |
| RIDER_CANCELED | Rider cancelled the trip |
| DRIVER_COMING_CANCELED | Cancelled while driver en route |
| DRIVER_COMING_RIDER_CANCELED | Rider cancelled while driver en route |
| NO_DRIVER_AVAILABLE | No driver found for the request |
| DRIVER_ABANDONED | Driver abandoned the trip |
| RIDER_ABANDONED | Rider abandoned the trip |
| ADJUSTED | Fare adjustment applied |
| TRIP_REQUEST_EXPIRED | Scheduled request expired |
| TRIP_REQUEST_DECLINED | Request declined |
| BOOK_ASSIGNED | Book assigned to driver |

## Trips Management (B2B Portal)

### Trip Summary
- Total Trips count
- Completed Trips count
- Click redirects to Trips page with filter

### Filtering
- Date Range
- Riders
- Trip Status

### Export
- "Export rides" button
- Downloads filtered trip list

### Trip Data Columns
- Rider
- Locations (Departure -> Destination)
- Stops
- Date
- Trip ID
- Price
- Status

### Re-booking Feature
- "Request again" action
- Redirects to Book Rides with pre-filled details
- Admin must confirm booking

## Trips Management (Admin Panel)

### Export Configuration
- Date Selection: Start Date, End Date (max 31 days)
- Filter: Finished Trips or Requested Trips
- Delivery: Async email with attachment

### Search & Filtering
- Trip Status multi-select
- Date filter
- Search by Trip ID or Rider Name

### Trip Data Columns
- Client (Name + Email)
- Locations (Pickup, Dropoff)
- Date
- Trip ID
- Trip Price
- Budget State (Before/After)
- Status
- Refund amount (if applicable)

## Business Rules

### Booking Rules
- RULE-TRIP-001: Guest users cannot self-book business trips
- RULE-TRIP-002: Available services determined by program settings
- RULE-TRIP-003: Scheduled trips can be set for repeat
- RULE-TRIP-004: Rides requiring approval go to Ride Requests tab

### Status Rules
- RULE-TRIP-005: Instant trip initial status = PENDING
- RULE-TRIP-006: Status progression: PENDING -> ACCEPTED -> DRIVER_ARRIVED -> STARTED -> FINISHED
- RULE-TRIP-007: Terminal statuses: FINISHED, *_CANCELED, NO_DRIVER_AVAILABLE

### Export Rules
- RULE-TRIP-008: Export date range cannot exceed 31 days
- RULE-TRIP-009: Export delivered via async email

### Financial Rules
- RULE-TRIP-010: Trip cost deducted from wallet (Prepaid) or accrued (Postpaid)
- RULE-TRIP-011: Refunds credited to wallet or adjusted in invoice

## State Machine

See `state_machines/trip_states.md` for detailed transitions.

## API Endpoints

- `POST /api/trips/book` - Book a ride
- `GET /api/trips` - List trips
- `GET /api/trips/{id}` - Get trip details
- `POST /api/trips/{id}/cancel` - Cancel trip
- `POST /api/trips/{id}/rebook` - Rebook previous trip
- `GET /api/trips/export` - Export trips (async)
- `GET /api/trips/ongoing` - Get ongoing rides
- `GET /api/trips/upcoming` - Get scheduled rides
- `GET /api/trips/requests` - Get pending approval requests
