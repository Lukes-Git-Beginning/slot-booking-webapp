# Case Study: Central Business Tool Hub

## Executive Summary

A production-grade internal business platform serving 17 users with appointment booking, gamification, and analytics capabilities. Built with Flask, integrated with Google Calendar API, and deployed on Hetzner VPS with 99.9% uptime since October 2025.

**Key Achievements:**
- Reduced Google Calendar API calls by 90% (105 → 10 per page load)
- Implemented comprehensive security (2FA, CSRF, Rate Limiting)
- Built gamification system with 50+ badges and leveling
- Achieved 98% test coverage on security-critical code

---

## 1. Problem & Context

### Business Challenge

A financial consulting firm (17 consultants) needed to replace their manual appointment booking process. Requirements included:

- **Multi-consultant scheduling** - 9 consultants with individual calendars
- **Capacity management** - 3 slots per consultant per time slot
- **Employee motivation** - Gamification to incentivize booking performance
- **Analytics** - Track show/no-show rates and performance metrics

### Constraints

- Small team (no dedicated DevOps)
- Limited budget (single VPS deployment)
- Integration with existing Google Calendar workflows
- German-speaking users (UI localization)

---

## 2. Architecture Decisions

### Application Factory Pattern

```python
def create_app(config_object: Optional[str] = None) -> Flask:
    app = Flask(__name__)
    init_extensions(app)
    init_middleware(app)
    register_blueprints(app)
    register_error_handlers(app)
    return app
```

**Why:** Enables testing with different configurations, clean separation of concerns, and deferred imports to avoid circular dependencies.

### Service-Oriented Architecture

```
app/
├── routes/          # HTTP handlers (thin)
├── services/        # Business logic (20+ services)
├── core/            # Shared infrastructure
└── config/          # Environment-aware configuration
```

**Why:** Services are independently testable, routes remain thin HTTP handlers, and business logic is reusable.

### JSON-Based Persistence (Strategic Choice)

**Decision:** Use JSON files instead of PostgreSQL

**Rationale:**
- 17 users don't require relational database overhead
- Simpler deployment without database management
- Sufficient for gamification/tracking data structures
- Documented migration path to PostgreSQL when scaling

**Implementation:**
```python
class DataPersistence:
    def save_data(self, filename: str, data: Any) -> bool:
        # Atomic writes with temp file + rename
        # Automatic backup before each write
        # Dual-path storage (persistent + static)
```

---

## 3. Technical Highlights

### Google Calendar API Optimization

**Problem:** Initial implementation made 105 API calls per page load (1 per consultant × multiple endpoints).

**Solution:**
- Implemented pagination for 4,800+ events
- Aggressive caching (30-minute default TTL)
- Rate limiting before hitting Google quotas
- Batch operations for weekly summary

```python
def get_all_events_paginated(self, calendar_id, time_min, time_max):
    """Load ALL events in 2,500-event pages (max 10 pages = 25,000 events)"""
    all_events = []
    page_token = None

    while True:
        result = self._make_api_call(calendar_id, time_min, time_max, page_token)
        all_events.extend(result.get('items', []))

        page_token = result.get('nextPageToken')
        if not page_token:
            break

    return all_events
```

**Result:** Reduced API calls from 105 to ~10 per page load (90% reduction).

### Gamification System

**Components:**
- **50+ Badges** across 6 rarity tiers (common → mythic)
- **Level System** with exponential XP progression
- **Prestige System** with 6 levels and 5 masteries each
- **Daily Quests** with dynamic objectives
- **Cosmetics Shop** with themes and effects

**Technical Implementation:**
```python
# Achievement checking runs on booking events
def check_achievements(username: str, event_type: str) -> List[Badge]:
    user_stats = load_user_stats(username)

    earned_badges = []
    for badge in ALL_BADGES:
        if badge.check_condition(user_stats):
            earned_badges.append(badge)
            award_badge(username, badge)

    return earned_badges
```

### Security Implementation

**Multi-Layer Security:**

1. **Authentication**
   - bcrypt password hashing (12 rounds)
   - Two-factor authentication (TOTP)
   - Account lockout after failed attempts
   - Session fixation protection

2. **Authorization**
   - Role-based access control
   - Admin-only endpoints
   - User-specific data isolation

3. **Protection**
   - CSRF tokens on all forms
   - Rate limiting (Flask-Limiter)
   - Security headers (CSP, X-Frame-Options)
   - Input validation and sanitization

```python
def hash_password(self, password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_2fa(self, username: str, code: str) -> bool:
    # TOTP verification
    totp = pyotp.TOTP(user_2fa['secret'])
    if totp.verify(code):
        return True

    # Backup code verification (single-use)
    if code.upper() in backup_codes:
        backup_codes.remove(code.upper())
        return True

    return False
```

### T2 Bucket System (Probability Algorithm)

**Business Logic:** Fair distribution of T2 appointments to closers based on weighted probability with degressive mechanics.

```python
T2_CLOSERS = {
    "Alex": {"probability": 9.0},   # 9 tickets
    "David": {"probability": 9.0},  # 9 tickets
    "Jose": {"probability": 2.0}    # 2 tickets
}

def draw_closer(username: str) -> Dict:
    # Draw random closer from bucket
    drawn_closer = random.choice(bucket)

    # Remove ticket and reduce probability
    bucket.remove(drawn_closer)
    probabilities[drawn_closer] -= 1.0

    # Auto-reset after 20 draws
    if total_draws >= 20:
        reset_to_defaults()

    return {"success": True, "closer": drawn_closer}
```

---

## 4. Testing Strategy

### Test Suite Overview

| Service | Tests | Coverage | Description |
|---------|-------|----------|-------------|
| `security_service.py` | 31 | 98% | Password hashing, 2FA, backup codes |
| `t2_bucket_system.py` | 36 | 89% | Probability, draws, timeout |
| `data_persistence.py` | 33 | 59% | Backup, validation, atomic writes |
| `booking_service.py` | 27 | 52% | Slot status, booking, points |

**Total: 127 tests, 125 passing**

### Testing Patterns

**Mocking External Services:**
```python
@pytest.fixture
def mock_google_calendar():
    with patch('app.core.google_calendar.GoogleCalendarService') as mock:
        mock_instance = MagicMock()
        mock_instance.get_events.return_value = {'items': []}
        mock_instance.create_event.return_value = {'id': 'test-123'}
        yield mock_instance
```

**Testing Security-Critical Code:**
```python
def test_password_hash_different_each_time(self):
    """Test that same password produces different hashes (salt)"""
    hash1 = service.hash_password('test123')
    hash2 = service.hash_password('test123')
    assert hash1 != hash2  # Different salts

def test_backup_code_single_use(self):
    """Test that backup codes can only be used once"""
    assert service.verify_2fa('user', backup_codes[0]) is True
    assert service.verify_2fa('user', backup_codes[0]) is False
```

---

## 5. Deployment & Operations

### Infrastructure

- **Server:** Hetzner VPS (91.98.192.233)
- **Stack:** Ubuntu 22.04, Nginx, Gunicorn (4 workers)
- **Memory:** ~225MB RAM usage
- **Uptime:** 99.9% since October 2025

### Automation

**Systemd Timers:**
- `achievement-processor` - Process achievements
- `daily-outcome-check` - Check booking outcomes
- `weekly-reset` - Reset weekly points
- `cache-cleanup` - Clean expired cache
- `availability-generator` - Generate slots

**Deployment Script:**
```bash
# deploy.sh
scp -i ~/.ssh/server_key $FILE root@91.98.192.233:/opt/business-hub/
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"
```

---

## 6. Metrics & Results

### Performance

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| API calls/page | 105 | 10 | 90% reduction |
| Page load time | ~3s | <1s | 66% faster |
| Cache hit rate | 0% | 85% | - |

### Business Impact

- **4,800+ events** managed in system
- **17 active users** with daily usage
- **Zero security incidents** since launch
- **Gamification engagement:** 50+ badges awarded

### Code Quality

- **86 Python files** in production
- **53 HTML templates**
- **20+ service classes**
- **Type hints** throughout codebase

---

## 7. Lessons Learned

### What Worked Well

1. **Pragmatic architecture choices** - JSON persistence for small scale was the right call
2. **Service layer separation** - Made testing and refactoring straightforward
3. **Aggressive caching** - Solved performance issues without over-engineering
4. **Security-first mindset** - 2FA, rate limiting from the start

### What I'd Do Differently

1. **Start with tests** - Added test suite late in development; earlier would have caught bugs faster
2. **PostgreSQL from start** - While JSON works, migration path adds complexity
3. **Consistent CSS framework** - Having both Bootstrap and Tailwind creates duplication
4. **API documentation** - No Swagger/OpenAPI, makes integration harder

### Technical Debt Addressed

- [x] Test coverage from <1% to 60%+ on critical services
- [ ] Migrate to PostgreSQL (documented but not implemented)
- [ ] Consolidate CSS frameworks to Tailwind only
- [ ] Add API versioning

---

## 8. Technology Stack

### Backend
- **Flask 3.1** - Web framework
- **Gunicorn** - WSGI server
- **Google Calendar API** - Calendar integration
- **bcrypt / pyotp** - Security

### Frontend
- **Tailwind CSS + DaisyUI** - Modern UI
- **Bootstrap 5** - Legacy components
- **Alpine.js** - Reactive components
- **SortableJS** - Drag & drop

### Testing
- **pytest** - Test framework
- **pytest-cov** - Coverage reports
- **pytest-mock** - Mocking utilities

### DevOps
- **Nginx** - Reverse proxy
- **Systemd** - Service management
- **Sentry** - Error tracking (optional)

---

## Contact

**Project:** Central Business Tool Hub
**Version:** 3.3.8
**Status:** Production (since October 2025)
**Uptime:** 99.9%

---

*This case study was prepared for portfolio purposes. Company and user details have been anonymized.*
