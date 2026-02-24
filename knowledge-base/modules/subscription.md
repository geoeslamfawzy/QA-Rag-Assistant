---
module: subscription
version: 1.0
last_updated: 2024-01-15
dependencies:
  - payment_processing
  - user_management
  - notification
---

# Subscription Module

## Overview

The subscription module manages user subscription plans, billing cycles, and plan changes. It integrates closely with payment processing for charges and user management for access control.

## Key Concepts

### Subscription Plans
- **Basic**: Entry-level plan with limited features
- **Premium**: Full-featured plan with all capabilities
- **Enterprise**: Custom plan with dedicated support

### Billing Cycles
- Monthly billing (default)
- Annual billing (discounted)
- Custom billing cycles for enterprise

### Plan Changes
- Upgrades: Immediate access, prorated billing
- Downgrades: Effective at end of current cycle
- Cancellations: Access until end of paid period

## Business Rules

1. Users can only have one active subscription at a time
2. Plan changes require valid payment method on file
3. Downgrades do not provide refunds
4. Upgrades are charged immediately with proration
5. Cancelled subscriptions cannot be reactivated (must create new)

## Integration Points

### Payment Processing
- Subscription charges are processed via payment module
- Failed payments trigger grace period (3 days)
- After grace period, subscription is suspended

### User Management
- Subscription status affects feature access
- Plan tier determines permission set
- Account deletion requires subscription cancellation first

### Notifications
- Plan change confirmation emails
- Payment failure notifications
- Renewal reminder emails (7 days before)
- Expiration warning emails

## State Machine

See `state_machines/subscription_states.md` for detailed state transitions.

## API Endpoints

- `POST /api/subscriptions` - Create subscription
- `GET /api/subscriptions/{id}` - Get subscription details
- `PATCH /api/subscriptions/{id}` - Update subscription
- `DELETE /api/subscriptions/{id}` - Cancel subscription
- `POST /api/subscriptions/{id}/upgrade` - Upgrade plan
- `POST /api/subscriptions/{id}/downgrade` - Downgrade plan
