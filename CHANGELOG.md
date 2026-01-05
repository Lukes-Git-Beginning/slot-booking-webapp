# Changelog

All notable changes to Central Business Tool Hub will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.3.15] - 2026-01-05 - CSRF Security & Systemd Hardening Fixes

### Fixed
- **CSRF Protection Complete**: Added CSRF tokens to 3 vulnerable templates
  - `templates/index.html` - Booking form now includes CSRF token (fixes HTTP 400 "Ungültige Anfrage" error)
  - `templates/my_calendar.html` - Added CSRF meta tag + fetch patching for 3 POST endpoints
  - `templates/customization_shop.html` - Added CSRF meta tag + fetch patching for 3 POST endpoints
- **Systemd File Permissions**: Fixed "Read-only file system" errors in gamification stats
  - Removed `/opt/business-hub/static` from `ReadOnlyPaths`
  - Added `/opt/business-hub/static` to `ReadWritePaths`
  - Changed ownership: `chown -R www-data:www-data /opt/business-hub/static/`
  - Restored gamification data writes after 6 days of failed writes (last success: 2025-12-30)

### Security
- **100% CSRF Protection**: All 30 POST endpoints now protected
  - 3 base templates with global fetch patching (hub/base.html, slots/base.html, t2/base.html)
  - 2 standalone templates with manual CSRF protection (my_calendar.html, customization_shop.html)
  - Traditional form with hidden CSRF field (index.html)
- **Systemd Security Hardening** maintained with adjusted permissions:
  - `ProtectSystem=strict` remains active
  - Static directory writable for gamification data (dual-write architecture)
  - Templates directory remains read-only

### Changed
- **JSON File Timestamps**: All gamification files updated (scores.json, user_badges.json, mvp_badges.json, daily_user_stats.json)
- **Server Configuration**: `/etc/systemd/system/business-hub.service` updated with new ReadWritePaths

### Technical
- **Sentry Errors Resolved**: 4 "Read-only file system" errors eliminated
  - `FileLockException: scores.json.lock`
  - `Fehler beim Speichern der User Badges`
  - `Fehler beim Speichern der MVP-Badges`
  - `Fehler beim Speichern der Daily User Stats`

---

## [3.3.14] - 2025-12-11 - T2 Feature Flag Rollback & Bugfixes

### Changed
- **T2 Feature Flag Rollback**: `T2_MODULAR_BLUEPRINTS: false` (zurück zu Legacy-System)

### Fixed
- **Bucket Config Import-Error**: 7 Import-Statements korrigiert
- **Draw History PostgreSQL Migration**: Analytics-Service migriert zu PostgreSQL-First
- **114 historische Draws** sichtbar (sara.mast: 30, ann-kathrin.welge: 26, dominik.mikic: 25)

### Performance
- **PostgreSQL Query-Zeit**: ~50ms für Draw-History-Abfragen

---

## [3.3.11] - 2025-11-23 - T2 Calendly Booking System + Projekt-Cleanup

### Added
- **T2 Calendly 4-Step Booking Flow**:
  - New Templates: `booking_calendly.html` (714 lines) + `my_bookings.html` (689 lines)
  - 4-Step Wizard: Berater wählen → Datum wählen → Zeitslot wählen → Bestätigung
  - Mock vs. Real Calendar: Coaches use mock data, Berater use Google Calendar API
- **On-Demand Availability Scanning**:
  - New Service: `t2_dynamic_availability.py` (398 lines)
  - Real-time availability scanning for 3 Coaches + 3 Berater
  - Working hours: 08:00-17:00, 30-minute slots
- **T2 Analytics Service**:
  - New Service: `t2_analytics_service.py` (114 lines)
  - 2h-Analytics API for Admin Dashboard
- **11 New API Endpoints** in `t2.py` (+1025 lines, total: 1947 lines):
  - `/t2/booking/calendly` - 4-Step Booking Flow
  - `/t2/my-bookings` - Appointment Overview
  - `/t2/api/available-dates` - Available days for month
  - `/t2/api/available-times` - Free time slots for day
  - `/t2/api/book-appointment` - Book appointment
  - `/t2/api/cancel-booking/<id>` - Cancel appointment
  - `/t2/api/reschedule-booking/<id>` - Reschedule appointment
  - 4 additional status/update endpoints

### Fixed
- `tracking_system.py`: Added Singleton instance (fixed import error)
- `draw_closer.html`: Updated redirect to Calendly booking
- `legacy_routes.py`: Removed legacy analytics import

### Removed
- **Massive Project Cleanup (51 files, 245KB freed)**:
  - 22 old backups from `data/backups/`
  - 13 legacy files (9 static JSON files, 4 deployment scripts - 491 lines)
  - 8 legacy templates & scripts (2844 lines total):
    - `analytics_dashboard.html` (628 lines)
    - `executive_monthly_report.html` (200 lines)
    - `executive_weekly_report.html` (133 lines)
    - `t2/calendar_new.html` (404 lines) - Replaced by booking_calendly.html
    - `generate_feature_presentation.py` (1228 lines)
    - `migrate_passwords_to_bcrypt.py` (203 lines)
    - `run_backfill.py` (48 lines)
    - `check_event_tags.py` (62 lines)
  - `persist/` directory (path nesting bugfix from v3.3.5)

### Performance
- **Codebase Reduction**: -1733 lines (4655 deleted, 2922 added)
- **Disk Space**: 245KB freed
- **Better Maintainability**: 51 obsolete files removed

---

## [3.3.10] - 2025-11-21 - PostgreSQL Booking-System Migration

### Added
- **Full PostgreSQL Migration** for Booking System:
  - 2 new SQLAlchemy Models: `Booking` (16 fields) + `BookingOutcome` (10 fields)
  - 24 Database Tables total with 121 Performance Indexes (previously: 22 tables, 101 indexes)
  - Dual-Write Pattern: New bookings written to both PostgreSQL + JSON
  - Smart Wrapper with Fallback: My Calendar uses PostgreSQL, falls back to JSON on error
  - 20 Performance Indexes: Optimized for username+date, customer, week_number, booking_id queries
- **364 Historical Bookings Migrated** (2025-11-21):
  - Phase 1 - JSONL Migration: 26 bookings from `bookings.jsonl` → PostgreSQL
  - Phase 2 - Calendar Backfill: 338 bookings extracted from Google Calendar
  - 9 Users tracked: Christian, Yasmine, Dominik, Ladislav, Tim, Sonja, Simon, Alexandra, Patrick
- **Automatic Synchronization**:
  - Daily Cronjob: 23:00 UTC (01:00 Berlin Time)
  - Function: New Google Calendar Events → PostgreSQL
  - Location: `/opt/business-hub/scripts/run_calendar_sync.sh`
  - Logs: `/var/log/business-hub/calendar-sync.log`
- **Alembic Migration**: `57a8e7357e0c` successfully deployed on production server

### Fixed
- **Index Conflicts** in existing models:
  - `gamification.py`: Renamed idx_active → idx_daily_quests_active, idx_completed → idx_quest_progress_completed, idx_active_goals → idx_personal_goals_active
  - `weekly.py`: Renamed idx_pending → idx_weekly_activities_pending

### Changed
- **My Calendar** rebuilt on PostgreSQL:
  - New function `get_user_bookings_from_db()` reads directly from PostgreSQL
  - New function `get_user_bookings()` as Smart Wrapper with Auto-Detection
  - Fallback mechanism: Automatically falls back to JSONL on PostgreSQL errors

### Performance
- PostgreSQL Read: 10x faster than JSONL for historical data
- My Calendar Load Time: 800ms → <200ms (364 bookings)
- Cronjob Runtime: <2s for complete Calendar sync

---

## [3.3.8] - 2025-11-18 - Activity Tracking & Code Quality

### Added
- **Login Activity Tracking System**:
  - Login-History Tracking: Complete tracking of all login attempts (Success/Fail)
  - Tracking Details: IP address, Browser, Device type (Desktop/Mobile/Tablet), Timestamp
  - Online Status Monitoring: Real-time tracking of active users (15-min timeout)
  - Admin Dashboards: New pages for Login History and Online Users
  - API Endpoints: 5 REST APIs for AJAX updates and statistics
  - Login Statistics: Peak hours, Unique IPs, Failed logins, Logins per hour/day
  - Service File: `app/services/activity_tracking.py`
  - Data Format: JSON-based (`login_history.json`, `online_sessions.json`)

### Fixed
- **Logger Bug**: Missing logger import in `auth.py` (prevented lockout logging)

### Changed
- **.gitignore expanded**: Pytest cache, Coverage reports, Node modules, .env variants
- **Health Check updated**: Version 3.3.7 → 3.3.8 in `/health` endpoint
- **Sentry Warning**: Documentation in requirements.txt (Free: 5K Events/month, Paid: €26+)

---

## [3.3.7] - 2025-11-12 - Professional PDF Reports & T2 Analytics

### Changed
- **PDF Telefonie System Completely Redesigned**:
  - Full Team Overview: ALL Telefonists displayed (High/Medium/Low Performers)
  - German Translation: ~50 English text sections translated to German
  - ZFA Branding: Modern design with Gold (#d4af6a) and ZFA Blue (#207487)
  - Design Improvements: Larger fonts (Title: 28pt), better padding (12px), thicker grid lines
  - Professional Footer: Golden divider + ZFA branding
  - Color Coding: Green (Top Performers), Blue (Solid Performers), Red (Development Potential)
  - Removed Measures Section: Focus on performance data

### Added
- **T2 Analytics Dashboard**: ApexCharts integration for team visualizations

---

## [3.3.6] - 2025-11-05 - Pagination System & Critical Bugfixes

### Added
- **Pagination System for 4,800+ Events**:
  - `get_all_events_paginated()` method in google_calendar.py
  - Loads ALL events in 2,500-event pages (max 10 pages = 25,000 events)
  - 5-minute cache for performance optimization
  - Complete rate limiting & quota management
  - My Calendar & My Customers now use pagination instead of fixed limits

### Fixed
- **Critical Bugfix: booking.py 500 error**:
  - Removed local `booking_logger` import (caused `UnboundLocalError`)
  - Fixed 17 failed bookings by Yasmine
  - Booking system fully functional again
- **Debug Logs Completely Removed**:
  - All 🔍-debug statements removed from calendar.py
  - All BOOKING DEBUG logs removed from booking.py
  - Production-ready code quality

### Performance
- API Quota Future-Proofing:
  - Supports 80 events/day × 60 days = 4,800 events
  - ~2 API calls per load instead of 1 (with cache: <100 requests/day)
  - Usage: 0.01% of Google Calendar limit (1M/day)

---

## [3.3.6-beta] - 2025-11-04 - Advanced Blocked Dates System

### Added
- **3 Block Types for Blocked Times**:
  - `full_day`: Full-day blocking (existing functionality)
  - `time_range`: Time-range blocking (e.g., 14:00-16:00 lunch break)
  - `date_range`: Date-range blocking (e.g., 2025-12-24 to 2025-12-31 Christmas vacation)
- **Tab-based Admin UI**:
  - Intuitive forms for each block type
  - Automatic day calculation for date ranges
  - Visual indicators for block types (icons & badges)
- **Block-Key System**:
  - Unique identification for all block types
  - Format: `YYYY-MM-DD` (full_day), `YYYY-MM-DD_HH:MM-HH:MM` (time_range), `range_YYYY-MM-DD_YYYY-MM-DD` (date_range)
  - Backward compatible with old full_day blocks
- **Booking Service Integration**:
  - `is_blocked_date()` now optionally checks time ranges
  - `get_default_availability()` respects time_range blocks
  - Prevents bookings in blocked time windows

---

## [3.3.5] - 2025-10-27 - CRITICAL BUGFIX: PERSIST_BASE Path Nesting

### Fixed
- **CRITICAL BUGFIX**: Systematic double-nesting of all databases resolved
  - `.env` corrected: `PERSIST_BASE=/opt/business-hub/data` (was: `/opt/business-hub/data/persistent`)
  - Problem: Code automatically adds `/persistent` → led to `/persistent/persistent/`
  - All 10 critical JSON files consolidated (user_badges, scores, t2_bucket_system, etc.)
  - Complete backup created before changes

### Changed
- **T2 Bucket System Configuration**:
  - Standard probabilities set to 9-9-2 (Alex: 9.0, David: 9.0, Jose: 2.0)
  - Max Draws increased to 20 (was: 10)
  - Degressive probability: Probability decreases by 1 with each draw
  - Min Probability: 0.0 (Closer can no longer be drawn when at 0)

### Documentation
- **IMPORTANT for future deployments**:
  - `PERSIST_BASE` must NEVER contain `/persistent` at the end
  - Correct: `PERSIST_BASE=/opt/business-hub/data`
  - Wrong: `PERSIST_BASE=/opt/business-hub/data/persistent`

---

## [3.3.4] - 2025-10-25 - My Calendar Phase 2: Drag & Drop Kanban

### Added
- **7-Column Kanban Board**: HubSpot-style status management
  - Pending, Erschienen, Rückholung, Sonderkunden, Verschoben, Nicht Erschienen, Ghost
- **Drag & Drop Functionality**:
  - SortableJS integration for all Kanban columns
  - Visual status updates with ghost effect
  - Automatic Google Calendar colorId synchronization
- **Reschedule Modal** (appointment rescheduling):
  - Date picker with min-date validation
  - Dynamic time slot display via AJAX (`/api/get-available-slots`)
  - Consultant dropdown with auto-selection
  - Optional note textarea
  - Complete error handling
- **3-Second Undo Function**:
  - Countdown timer after status updates
  - Revert API call on click
  - Automatic hide after timeout
- **Auto-Refresh (5 minutes)**:
  - Intelligent refresh only when tab visible (Visibility API)
  - Automatic start/stop
- **Backend API Endpoints**:
  - `/api/update-event-status`: Status update via drag & drop
  - `/api/reschedule-booking`: Old appointment → Verschoben, create new appointment
  - `/api/get-available-slots`: Availability query for selected date
- **Toast Notifications**: Success/Error/Info for all user actions
- **Backfill Script**: `backfill_booked_by_tags.py` for retroactive tagging of old events

---

## [3.3.3] - 2025-10-23 - Dark Mode Logo & Username Migration

### Changed
- **Dark Mode Logo Optimized**:
  - Transparent golden logo for header (no white box anymore)
  - Separate favicon (star logo) for browser tabs
  - `zfa-dark.png` (67KB) + `favicon.png` (285KB)
- **Username Migration**: All 17 users migrated to full names
  - `d.mikic` → `dominik.mikic`, `l.hoppe` → `luke.hoppe`, etc.
  - .env file and JSON databases fully migrated

### Fixed
- **404 Template**:
  - Purple colors replaced with ZFA Secondary Blue
  - Endpoint references corrected
- **Git History Updated**: Server successfully switched to new cleaned history

---

## [3.3.2] - 2025-10-23 - Production Hardening & Documentation

### Security
- **Git History Completely Cleaned**: All sensitive credentials removed from entire history (595 commits)

### Changed
- **Availability Generator Optimized**: 5x daily (08:00, 11:00, 14:00, 17:00, 20:00 Berlin Time)
- **README Completely Revised**:
  - Hetzner VPS documented as primary deployment
  - All Render.com references removed
  - Deployment processes updated
  - Troubleshooting with SSH commands
- **ZFA Color Scheme 100% Consistent**: Purple/Violet completely replaced with ZFA Blue (#207487)

### Added
- **Lucide Icons Integration**: Multi-timeout initialization
- **Production Deployment**: All features live and stable on Hetzner VPS

---

## [3.3.1] - 2025-10-17 - Production Hardening & Automation

### Fixed
- **Google Calendar API Fix**: ISO 8601 format - 100% success rate

### Security
- **Security Hardening**: Two-layer rate limiting (Nginx + Flask)

### Added
- **Automation**: Cache cleanup, backup rotation, log rotation
- **Cosmetics System v2**: Theme & effects with 22 PNG avatars

---

## [3.3.0] - 2025-10-16 - ZFA Rebranding & Consultant Analytics

### Changed
- **ZFA Color Scheme**: Complete migration to ZFA branding
- **Hub/Base Template System**: Automatic ZFA color integration

### Added
- **Consultant Analytics**: Show/No-Show tracking for Telefonists
- **Production Ready**: All changes deployed and tested

---

## Older Versions

For versions prior to 3.3.0, please refer to the commit history or contact the development team.
