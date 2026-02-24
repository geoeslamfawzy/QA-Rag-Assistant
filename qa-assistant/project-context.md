# Project Context: Yassir Mobility Ecosystem

## Product Overview

Yassir Mobility is a comprehensive ride-hailing mobility ecosystem integrated into the Yassir Super App. The system serves both individual consumers (B2C) and corporate clients (B2B) across North & West Africa (Algeria, Tunisia, Morocco, Senegal).

### Core Systems

| System | Purpose | Primary Users |
|--------|---------|---------------|
| B2B Corporate Portal | Transportation management for businesses | Business Admins, Riders |
| B2C Web Interface | Web-based booking for individuals | End-user Riders |
| Admin Panel | Internal management & operations | Ops Team, Sales Reps |
| DashOps | Central command center | Operations Employees |
| Pricing & Promotions Engine | Financial configuration | Operations Team |
| Yassir Super App (Mobile) | Primary rider interface | Riders (B2B & B2C) |
| Driver App | Service provider interface | Drivers |

## Architecture

### B2B Corporate Portal Modules
- **Dashboard**: Widget-based overview (Members, Cashback, Rides, Financials)
- **Users and Groups**: Employee management, invitations, role assignments
- **Programs**: Ride policies, schedules, permissions, service restrictions
- **Book Rides**: Instant/scheduled trips, multi-stop, guest booking
- **Payments**: Prepaid wallet / Postpaid billing
- **Trips**: History, filtering, export, re-booking
- **Referrals**: B2B referral program with rewards
- **Business Challenge**: Gamification with discount tiers
- **Gift Cards**: Digital vouchers with usage tracking
- **Support**: FAQs, tutorials, direct support channels

### Admin Panel Modules
- **Enterprises**: B2B client registry, onboarding, billing
- **Review Legal Info**: Document compliance validation
- **Manage Admins**: Internal user roles and permissions
- **Country Reports**: Financial reporting, invoices
- **Leads Management**: CRM for prospective clients
- **Services Config**: Ride type availability per region
- **Notifications**: Targeted communication campaigns
- **Referral**: Country-level referral program rules
- **Challenges**: Incentive campaign management
- **Gift Cards**: Voucher template management

## Tech Stack

- **Backend**: Microservices architecture
- **Mobile**: Yassir Super App (iOS/Android)
- **Web**: B2B Portal, Admin Panel
- **Regions**: Algeria (DZD), Tunisia, Morocco, Senegal
- **Languages**: English, French, Arabic

## Business Rules

### User Roles

| Role | System | Permissions |
|------|--------|-------------|
| Business Admin | B2B Portal | Full company management |
| Program Moderator | B2B Portal | Program-level management |
| Rider | B2B Portal + App | Book rides, view trips |
| Super Admin | Admin Panel | Full system access |
| Sales Representative | Admin Panel | Enterprise portfolio management |
| Inside Sales | Admin Panel | Lead management only |
| Operations Admin | Admin Panel | Day-to-day operations |

### Payment Plans

| Plan | Description | Key Rules |
|------|-------------|-----------|
| Prepaid | Wallet-based | Top-up required, immediate deduction |
| Postpaid | Credit-based | Monthly invoicing, budget limits |

### Commission & Pricing
- Default B2B Commission: 19%
- Final B2B Price = Base Trip Price + Commission %
- Currency: DZD (Algeria), country-specific elsewhere

### Trip States
```
PENDING -> ACCEPTED -> DRIVER_ARRIVED -> STARTED -> FINISHED
            |             |
      DRIVER_CANCELED   RIDER_CANCELED
            |
    NO_DRIVER_AVAILABLE
```

### Enterprise States
```
PENDING -> ACTIVE <-> INACTIVE
             |
        (Deleted only when INACTIVE)
```

### Referral Rewards
- **Prepaid**: Free trips (max 20 per referral, capped value)
- **Postpaid**: Invoice discount percentage

### Gift Card Rules
- Budget must cover card value
- Cards can be: Active, Deactivated, Reverted
- Remaining balance can be refunded to company wallet

### Challenge Rules
- Sequential tier progression (Copper -> Bronze -> Silver -> Gold -> Platinum)
- Discount percentage stacking (max 100%)
- Only UPCOMING challenges can be edited/deleted

## Environments

| Environment | Purpose |
|-------------|---------|
| Production | Live system |
| Staging | Pre-release testing |
| QA | Quality assurance |
| Development | Feature development |

## Constraints

1. **Geographic**: Services limited to supported cities per country
2. **Phone Prefix**: Country auto-detected from phone number (+213 = Algeria)
3. **Single Admin**: One Super Admin per Enterprise account
4. **Active Deletion**: Only INACTIVE enterprises/programs can be deleted
5. **Challenge Dates**: Cannot overlap with existing challenges
6. **Export Limits**: Trip export date range max 31 days
7. **Legal Compliance**: NIF, NIS, RC, AI documents required for B2B billing

## Known Limitations

1. **Referral Switching**: Rewards expire if payment plan changes (Prepaid <-> Postpaid)
2. **Gift Card Reversal**: Deactivates card permanently
3. **Challenge Modification**: Locked once ONGOING
4. **Single Currency**: Each country operates in local currency only
5. **Webhook Dependency**: Real-time sync with driver app status

## Cross-Module Dependencies

### Enterprise <-> Payment
- Payment plan determines dashboard widgets
- Budget status affects ride booking capability
- Invoice generation requires legal info approval

### Program <-> Users
- Group assignment mandatory for program access
- Role permissions cascade from program settings
- Program deletion requires group migration

### Trip <-> Financial
- Trip cost deducted from wallet (Prepaid) or accrued (Postpaid)
- Refunds credit wallet or adjust invoice
- Commission calculated on base fare

### Referral <-> Enterprise
- Enterprise-level rules override country defaults
- Reward type determined by referrer's payment plan
- Switching plans invalidates pending rewards
