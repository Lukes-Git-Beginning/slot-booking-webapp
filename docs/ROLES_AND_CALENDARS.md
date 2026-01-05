# Roles and Calendar Configuration

**Version:** 3.3.15
**Last Updated:** 2026-01-05

This document describes the role-based access control system and calendar configurations for the Central Business Tool Hub.

---

## 📋 Table of Contents

1. [System Roles Overview](#system-roles-overview)
2. [Role Definitions](#role-definitions)
3. [User List](#user-list)
4. [Calendar Systems](#calendar-systems)
5. [Role Permissions](#role-permissions)
6. [Configuration](#configuration)

---

## 🎭 System Roles Overview

The Business Tool Hub uses a multi-role system where users can have multiple roles simultaneously. There are 6 primary roles that determine access to different features.

### Role Hierarchy

```
admin
  ├── Full system access
  └── User management, configuration, analytics

closer
  ├── T2 System access
  └── 2-hour appointment management

opener
  ├── T1 Slot-Booking access
  └── 30-minute slot management

coach
  ├── T2 Coach role (drawable in dice system)
  └── Provides consultations

telefonist
  ├── Telefonie dashboard access
  └── Call tracking and analytics

service
  ├── Service-related features
  └── Customer support functions
```

---

## 👥 Role Definitions

### 1. Admin

**Purpose:** System administration and configuration
**User Count:** 4
**Key Features:**
- Full access to all system features
- User management (add, edit, delete users)
- System configuration (blocked dates, calendar settings)
- Analytics dashboards (all users, global stats)
- Notification management
- Security settings (2FA enforcement)

**Users:** alexander.nehm, david.nehm, simon.mast, luke.hoppe

---

### 2. Closer

**Purpose:** T2 system participants (Berater)
**User Count:** 6
**Key Features:**
- Access to T2-Closer dice system
- Book 2-hour appointments with drawn coaches
- View T2 analytics and statistics
- Cancel and reschedule T2 bookings
- View draw history

**Users:** jose.torspecken, alexander.nehm, david.nehm, tim.kreisel, christian.mast, daniel.herbort

**T2 Booking System:**
- Appointment Length: 2 hours
- Drawing System: Weighted probability for 3 coaches
- Booking Methods: Calendly-style 4-step flow

---

### 3. Opener

**Purpose:** T1 slot-booking system (Berater)
**User Count:** 8
**Key Features:**
- Book 30-minute customer appointments
- Access to "My Calendar" Kanban board
- View and manage customer bookings
- Reschedule and cancel appointments
- Customer status tracking (Erschienen, Nicht Erschienen, Ghost, etc.)

**Users:** christian.mast, tim.kreisel, daniel.herbort, sonja.mast, simon.mast, dominik.mikic, ann-kathrin.welge, sara.mast

**Availability Patterns:**
- **Standard (Vollzeit):** ann-kathrin.welge, sara.mast, dominik.mikic
  - Full daily availability (08:00-17:00)
  - More time slots available
- **Extended (Teilzeit/T2-Priorität):** simon.mast, sonja.mast, tim.kreisel, christian.mast, daniel.herbort
  - Limited slots due to T2 responsibilities
  - Reduced availability windows

---

### 4. Coach

**Purpose:** T2 consultation providers
**User Count:** 3
**Key Features:**
- Drawable in T2 dice system
- Provide 2-hour consultations to Berater
- View assigned bookings
- Access to coach analytics

**Users:** alexander.nehm, david.nehm, jose.torspecken

**Coach Selection:**
- Weighted probability system (configurable)
- Standard probabilities: 9-9-2 (Alex: 9.0, David: 9.0, Jose: 2.0)
- Degressive draw system (probability decreases with each draw)
- Maximum 20 draws per day before reset

---

### 5. Telefonist

**Purpose:** Phone call tracking and management
**User Count:** 9
**Key Features:**
- Access to Telefonie analytics dashboard
- View call performance metrics (Show/No-Show rates)
- Personal call statistics
- Performance rankings

**Users:** tim.kreisel, christian.mast, ladislav.heka, sonja.mast, simon.mast, alexandra.börner, yasmine.schumacher, ann-kathrin.welge, sara.mast

**Metrics Tracked:**
- Total calls made
- Show rate percentage
- No-show count
- Performance ranking

---

### 6. Service

**Purpose:** Customer service and support functions
**User Count:** 3
**Key Features:**
- Service-related dashboard access
- Customer support tools
- Special service features

**Users:** alexandra.börner, vanessa.wagner, simon.mast

---

## 📊 User List

### Complete User Roster (17 Users)

| Username | Admin | Closer | Opener | Coach | Telefonist | Service |
|----------|:-----:|:------:|:------:|:-----:|:----------:|:-------:|
| alexander.nehm | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| david.nehm | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| jose.torspecken | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| luke.hoppe | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| simon.mast | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| tim.kreisel | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| christian.mast | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| daniel.herbort | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| sonja.mast | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| dominik.mikic | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| ann-kathrin.welge | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| sara.mast | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| ladislav.heka | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| yasmine.schumacher | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| alexandra.börner | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| vanessa.wagner | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| patrick.falkenstein | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Role Distribution

- **Multi-role Users:** 8 users have 2+ roles
- **Highest Privileges:** alexander.nehm, david.nehm (3 roles each)
- **Single-role Users:** 9 users
- **No System Roles:** patrick.falkenstein (basic access only)

---

## 📅 Calendar Systems

The Business Tool Hub integrates with Google Calendar for booking management.

### Central Calendar

**Purpose:** Main booking calendar for T1 appointments
**Calendar ID:** Configured in `.env` as `CENTRAL_CALENDAR_ID`
**Usage:** All 30-minute customer bookings
**Features:**
- Color-coded events by status
- Auto-tagging with `booked_by:<username>`
- Booking metadata in event descriptions

### Consultant Calendars

**Purpose:** Individual calendars for T1 openers
**Configuration:** `.env` variable `CONSULTANTS`
**Format:** `Name:email@domain.com,Name2:email2@domain.com`

**T1 Slot-Booking Consultants (8):**
1. Ann-Kathrin Welge
2. Sara Mast
3. Dominik Mikic
4. Simon Mast
5. Sonja Mast
6. Tim Kreisel
7. Christian Mast
8. Daniel Herbort

**Booking Behavior:**
- **Standard Consultants:** Full availability generated (08:00-17:00, 30-min slots)
- **Extended Consultants:** Limited availability (partial day slots)
- Availability refreshed 5x daily: 08:00, 11:00, 14:00, 17:00, 20:00 Berlin Time

---

### T2 Calendar System

**Purpose:** 2-hour appointment booking for T2 system
**Booking Methods:**
1. **Mock Calendar (Coaches):** Simulated availability for testing
2. **Real Calendar (Berater):** Live Google Calendar integration

**T2 Consultants (3 Coaches):**
1. Alexander Nehm
2. David Nehm
3. Jose Torspecken

**Booking Process:**
1. Closer draws a coach via dice system
2. Closer views available dates (on-demand scanning)
3. Closer selects 2-hour time slot
4. System creates calendar event with metadata

---

## 🔐 Role Permissions

### Feature Access Matrix

| Feature | Admin | Closer | Opener | Coach | Telefonist | Service |
|---------|:-----:|:------:|:------:|:-----:|:----------:|:-------:|
| **Hub Dashboard** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **T1 Slot Booking** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **My Calendar** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **T2 Draw Closer** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **T2 My Bookings** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **T2 Calendar (Calendly)** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **T2 Analytics** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Telefonie Dashboard** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Admin Users** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Admin Blocked Dates** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Gamification Shop** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Security (2FA, Pwd)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Endpoint Protection

**Implementation:** Decorator-based role checking
**Example Decorators:**
- `@require_login` - Requires authenticated session
- `@admin_required` - Requires admin role
- `@closer_required` - Requires closer role (T2 routes)

**File Locations:**
- `app/utils/decorators.py` - Core decorators
- `app/routes/t2/admin.py:37-46` - `@admin_required` implementation
- Various route files - Endpoint protection

---

## ⚙️ Configuration

### Environment Variables

**Role Configuration (`.env`):**

```bash
# Admin Users (comma-separated)
ADMIN_USERS=alexander.nehm,david.nehm,simon.mast,luke.hoppe

# Full User List (username:password pairs)
USERLIST=alexander.nehm:pass,david.nehm:pass,jose.torspecken:pass,...

# T1 Consultants (Name:email pairs)
CONSULTANTS=Ann-Kathrin Welge:ann-kathrin.welge@example.com,Sara Mast:sara.mast@example.com,...

# Central Calendar ID
CENTRAL_CALENDAR_ID=central-calendar@example.com
```

### Role Assignment Logic

**Hardcoded Roles:**
- Roles are currently hardcoded in the codebase based on username
- Admin status checked via `ADMIN_USERS` environment variable
- Closer/opener/coach roles defined in route access checks

**Future Improvement:**
- Consider database-backed role management
- Dynamic role assignment via admin UI
- Role inheritance and permission groups

---

## 📝 Notes

### Username Migration (2025-10-23)

All 17 users migrated from short usernames to full names:
- `d.mikic` → `dominik.mikic`
- `l.hoppe` → `luke.hoppe`
- `a.nehm` → `alexander.nehm`
- etc.

**Impact:** All `.env` files and JSON databases updated. No legacy short usernames remain in production.

### T2 System Role Overlap

**Closer vs. Coach:**
- Closers can be coaches (alexander.nehm, david.nehm)
- Closers draw coaches and book appointments
- Coaches provide consultations to closers
- 3 users are both closer AND coach

### Calendar Availability Generation

**Timing:** 5 times daily (Berlin Time)
- 08:00 - Morning availability
- 11:00 - Mid-morning refresh
- 14:00 - Afternoon refresh
- 17:00 - Late afternoon refresh
- 20:00 - Evening refresh

**Files:** `scripts/generate_availability.py`
**Cronjob:** `/opt/business-hub/scripts/run_availability.sh`

---

## 🔄 Change History

| Date | Change | Impact |
|------|--------|--------|
| 2026-01-05 | Documentation created | Initial comprehensive role documentation |
| 2025-10-23 | Username migration | 17 users migrated to full names |
| 2025-11-23 | T2 Calendly system | 4-step booking flow added |
| 2025-11-21 | PostgreSQL migration | Booking data moved to database |

---

**Document Owner:** Luke Hoppe
**Review Frequency:** Quarterly or when roles change
