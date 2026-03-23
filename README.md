# Central Business Tool Hub

**Version:** 3.3.19 | **Status:** Production | **Server:** https://berater.zfa.gmbh/

Professional multi-tool platform combining slot booking, T2 appointment management, gamification, and business analytics.

---

## Quick Start

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/Lukes-Git-Beginning/slot-booking-webapp.git
cd slot-booking-webapp

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (copy and edit)
cp .env.example .env

# 5. Run application
python run.py
```

Application available at `http://localhost:5000`

### Environment Variables

Create a `.env` file with the following required variables:

```bash
# Core
SECRET_KEY=your-secret-key-here
USERLIST=user:pass,user2:pass2
ADMIN_USERS=admin1,admin2

# Google Calendar (Base64-encoded Service Account JSON)
GOOGLE_CREDS_BASE64=<base64-encoded-credentials>
CENTRAL_CALENDAR_ID=central-calendar@example.com
CONSULTANTS=Name1:email1@example.com,Name2:email2@example.com

# Optional
SENTRY_DSN=<your-sentry-dsn>  # Error tracking
```

**Google Calendar Setup:**
1. Create Service Account in Google Cloud Console
2. Enable Google Calendar API
3. Download JSON credentials
4. Base64 encode: `cat credentials.json | base64 -w 0`
5. Add to `.env` as `GOOGLE_CREDS_BASE64`

---

## Key Features

### 🎯 Slot Booking System
- 30-minute appointment slots for 8 consultants
- Google Calendar integration (real-time sync)
- Drag & drop Kanban board (7 status columns)
- Customer tracking & analytics
- German NRW holiday blocking

### 📞 T2 Appointment System
- 2-hour coaching sessions
- Weighted dice draw system (3 coaches)
- Calendly-style 4-step booking flow
- PostgreSQL-backed booking history

### 🎮 Gamification Engine
- 50+ achievements (6 rarity tiers)
- XP & level system with prestige
- Daily quests & mini-games
- Cosmetics shop (themes, avatars, effects)
- Competitive leaderboards

### 📊 Business Analytics
- Real-time booking analytics
- Consultant performance tracking
- PDF report generation (ZFA branded)
- Login activity & online status tracking
- Audit logging (10,000 event retention)

### 🔒 Security
- **CSRF Protection:** 100% coverage (30/30 endpoints)
- **Password Security:** bcrypt hashing (12 rounds)
- **2FA:** TOTP-based (Google Authenticator)
- **Rate Limiting:** Nginx + Flask dual-layer
- **CSP:** Nonce-based Content-Security-Policy (script-src)
- **Systemd Hardening:** ProtectSystem=strict, ReadWritePaths isolation
- **Account Lockout:** 3-tier progressive (5/10/15 attempts)

---

## Tech Stack

**Backend:** Flask 3.1.1, Python 3.11+, PostgreSQL, Gunicorn (4 workers)
**Frontend:** Tailwind CSS + DaisyUI, Alpine.js, Jinja2
**Infrastructure:** Hetzner VPS, Nginx, Systemd, Ubuntu 22.04 LTS
**APIs:** Google Calendar API v3, Discord Webhooks
**Monitoring:** Sentry error tracking

---

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_booking_service.py -v
```

**Test Coverage:** 573 tests passing (34 test files)

See [docs/TESTING.md](docs/TESTING.md) for comprehensive testing guide.

### CI/CD

- **GitHub Actions:** CI on push/PR (pytest), auto-deploy to production
- **CodeRabbit:** AI-powered code reviews on pull requests
- **Discord Webhooks:** Deployment notifications

---

## Deployment

### Production Server (Hetzner VPS)

**Server:** 91.98.192.233
**URL:** https://berater.zfa.gmbh/
**SSH:** `ssh -i ~/.ssh/server_key root@91.98.192.233`

### Quick Deployment Workflow

```bash
# 1. Backup (ALWAYS!)
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && tar -czf /tmp/backup_$(date +%Y%m%d_%H%M).tar.gz data/persistent/"

# 2. Transfer files
scp -i ~/.ssh/server_key <file> root@91.98.192.233:/opt/business-hub/<path>

# 3. Restart service
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"

# 4. Verify
curl -I https://berater.zfa.gmbh/health  # Should return 200 OK
```

**Systemd Service:**
- Location: `/etc/systemd/system/business-hub.service`
- User: `www-data`
- Workers: 4 (gthread)
- Security: ProtectSystem=strict, ReadWritePaths isolation

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for comprehensive deployment guide including systemd hardening details.

---

## Architecture

### Project Structure

```
slot_booking_webapp/
├── app/
│   ├── __init__.py           # Application factory
│   ├── config/               # Configuration classes (base.py)
│   ├── core/                 # Core infrastructure (calendar, cache, extensions, middleware)
│   ├── models/               # SQLAlchemy models (user, booking, t2_booking, gamification, etc.)
│   ├── routes/               # Blueprints (15+ blueprints)
│   │   ├── admin/            # Admin panel (dashboard, tracking, reports, telefonie, users, export)
│   │   ├── t2/               # T2 modular blueprints (core, booking, bucket, admin)
│   │   └── gamification/     # Gamification routes
│   ├── services/             # Business logic (27 services)
│   └── utils/                # Helpers (19 modules: decorators, rate limiting, error handling, etc.)
├── templates/                # Jinja2 templates (60+ HTML files)
│   ├── hub/                  # Central hub (dashboard, profile, settings, base)
│   ├── slots/                # Slot booking (booking, day_view, dashboard, base)
│   ├── t2/                   # T2 system (dashboard, booking, draw, analytics, calendar, etc.)
│   ├── analytics/            # Business intelligence (dashboard, executive, lead_insights, team_performance)
│   └── errors/               # Error pages (400, 401, 403, 404, 500, maintenance, base)
├── static/                   # CSS, JS, images
├── data/persistent/          # JSON databases (26 files) & persistent storage
├── tests/                    # Pytest test suite (26 files, 200+ tests)
├── docs/                     # Comprehensive documentation
├── deployment/               # Server configs (nginx, systemd, backup scripts)
└── scripts/                  # Automation (availability, sync, migration)
```

### Data Flow

```
User Request → Nginx (Rate Limiting)
    → Gunicorn (4 Workers, gthread)
        → Flask App (Blueprint routing)
            → Service Layer (Business logic)
                → Data Persistence (PostgreSQL + JSON dual-write)
                    → Google Calendar API (if applicable)
```

### Service Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE DEPENDENCY MAP                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐          │
│  │   ROUTES    │────▶│     SERVICES     │────▶│   DATA LAYER    │          │
│  └─────────────┘     └──────────────────┘     └─────────────────┘          │
│                                                                             │
│  T1 Booking Flow:                                                           │
│  booking_routes ──▶ booking_service ──▶ tracking_system                    │
│                                              │                              │
│                                              ▼                              │
│                                     achievement_system                      │
│                                              │                              │
│                                              ▼                              │
│                                      data_persistence ──▶ PostgreSQL/JSON  │
│                                              │                              │
│                                              ▼                              │
│                                        audit_service                        │
│                                                                             │
│  T2 Booking Flow:                                                           │
│  t2_routes ──▶ t2_bucket_system ──▶ PostgreSQL (t2_bookings)               │
│                       │                                                     │
│                       ▼                                                     │
│               notification_service                                          │
│                                                                             │
│  Gamification Flow:                                                         │
│  hub_routes ──▶ data_persistence (scores) ──▶ level_system                 │
│                                                    │                        │
│                                                    ▼                        │
│                                            achievement_system               │
│                                                    │                        │
│                                                    ▼                        │
│                                             cosmetics_shop (coins)          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Key Services (27 total):

Core Data & Persistence:
├── data_persistence       → Scores, Badges, Coins (PostgreSQL + JSON dual-write)
├── tracking_system        → Booking outcomes, Customer tracking
├── audit_service          → Security logging, User actions
├── activity_tracking      → User activity & session tracking

T1 Booking:
├── booking_service        → Slot availability & calendar booking
├── holiday_service        → German NRW holiday blocking

T2 Appointment System:
├── t2_bucket_system       → T2 dice draw, Coach assignments
├── t2_analytics_service   → T2 performance metrics
├── t2_availability_service → Coach availability management
├── t2_calendar_parser     → Calendar integration for T2
├── t2_dynamic_availability → Dynamic scheduling

Gamification:
├── achievement_system     → 50+ badges, XP awards
├── level_system           → XP → Level calculation
├── prestige_system        → Prestige progression
├── cosmetics_shop         → Theme purchases, Avatar unlocks
├── personalization_system → Profile customization
├── daily_quests           → Daily challenges, Progress tracking
├── daily_reward_system    → Daily reward distribution
├── weekly_points          → Weekly leaderboards & champions
├── consultant_ranking     → Consultant ranking system

Analytics & Reporting:
├── analytics_service      → Business intelligence dashboards
├── executive_reports      → PDF report generation (ZFA branded)

Notifications & Integrations:
├── notification_service   → In-app notifications, Popups
├── discord_webhook_service → Discord notifications

Security:
├── security_service       → Password hashing, 2FA (TOTP)
├── account_lockout        → Progressive account lockout

Internal:
└── refactoring_status_service → Refactoring tracking
```

---

## Roles & Permissions

**17 Users across 6 Roles:**

| Role       | Count | Access                                      |
|------------|-------|---------------------------------------------|
| Admin      | 4     | Full system access, user management         |
| Closer     | 6     | T2 system (draw & book 2h appointments)     |
| Opener     | 8     | T1 system (book 30min customer appointments)|
| Coach      | 3     | T2 coaches (drawable, provide consultations)|
| Telefonist | 9     | Call tracking & performance analytics       |
| Service    | 3     | Service-related features                    |

See [docs/ROLES_AND_CALENDARS.md](docs/ROLES_AND_CALENDARS.md) for detailed role definitions and calendar configurations.

---

## Documentation

📚 **Comprehensive docs in [`docs/`](docs/) directory:**

| Document | Description |
|----------|-------------|
| [SECURITY.md](docs/SECURITY.md) | Security controls, CSRF protection, systemd hardening |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment procedures, systemd configuration |
| [TESTING.md](docs/TESTING.md) | Testing guide, fixtures, CI/CD integration |
| [ROLES_AND_CALENDARS.md](docs/ROLES_AND_CALENDARS.md) | User roles, permissions, calendar systems |
| [CLAUDE.md](CLAUDE.md) | Claude Code instructions, deployment workflow |
| [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Local development setup, architecture |
| [CASE_STUDY.md](docs/CASE_STUDY.md) | PostgreSQL migration case study |
| [ROADMAP.md](docs/ROADMAP.md) | Future features & improvement plans |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

### Latest (v3.3.18 - 2026-02-15)

- CSP Nonce-Migration: `unsafe-inline` aus script-src eliminiert, nonce-basierte Policy
- Test Coverage: 200+ → 573 Tests (34 Testdateien)
- CI/CD Pipeline: GitHub Actions (CI + Deploy), CodeRabbit AI Reviews, Discord Webhooks
- Score Recovery & Datenintegritäts-Validierung beim Startup
- Root-Cleanup: Archivierte Code-Artefakte entfernt

---

## Monitoring & Health

### Health Check

```bash
curl https://berater.zfa.gmbh/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "3.3.18",
  "timestamp": "2026-01-05T...",
  "database": "healthy",
  "memory": "ok"
}
```

### Error Tracking

**Sentry Integration:** https://sentry.io
**Project:** business-hub
**Region:** Germany (GDPR-compliant)

### Logs

```bash
# Application errors
tail -f /var/log/business-hub/error.log

# Access logs
tail -f /var/log/business-hub/access.log

# Systemd service logs
journalctl -u business-hub -f
```

---

## Support & Troubleshooting

### Common Issues

**Issue:** CSRF 400 Error on booking
- **Fix:** Verify CSRF token in form (see [docs/SECURITY.md](docs/SECURITY.md#testing-csrf-protection))

**Issue:** "Read-only file system" errors
- **Fix:** Check systemd ReadWritePaths (see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#troubleshooting-systemd-issues))

**Issue:** Service won't start
- **Fix:** Check logs with `journalctl -u business-hub -n 50`

### Getting Help

1. Check [docs/](docs/) for comprehensive guides
2. Review [CHANGELOG.md](CHANGELOG.md) for recent changes
3. Check server logs for error details
4. Review Sentry dashboard for production errors

---

## Contributing

This is an internal business tool. For feature requests or bug reports, contact the development team.

---

## License

Proprietary - Internal use only

---

## Credits

**Development:** Luke Hoppe
**Organization:** ZFA GmbH
**Infrastructure:** Hetzner VPS
**Version:** 3.3.19 (2026-02-15)

---

**Last Updated:** 2026-02-15
**Next Review:** 2026-05-01
