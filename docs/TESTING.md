# Testing Guide

**Version:** 3.3.15
**Last Updated:** 2026-01-05

This document provides comprehensive testing guidelines for the Central Business Tool Hub.

---

## 📋 Table of Contents

1. [Testing Overview](#testing-overview)
2. [Test Suite Structure](#test-suite-structure)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Writing Tests](#writing-tests)
6. [CI/CD Integration](#cicd-integration)
7. [Manual Testing](#manual-testing)

---

## 🧪 Testing Overview

### Testing Framework

**Primary Framework:** pytest 7.4+
**Additional Tools:**
- pytest-cov (code coverage)
- pytest-mock (mocking)
- Flask test client (route testing)

### Test Philosophy

- **Unit Tests:** Test individual functions and classes in isolation
- **Integration Tests:** Test component interactions (database, services, APIs)
- **Route Tests:** Test HTTP endpoints with Flask test client
- **Security Tests:** Verify authentication, authorization, CSRF protection

### Coverage Goals

- **Target:** 80%+ code coverage
- **Critical Paths:** 95%+ coverage (auth, booking, payment logic)
- **Current Status:** ~75% coverage (Nov 2025)

---

## 📁 Test Suite Structure

```
tests/
├── conftest.py                           # Pytest configuration & fixtures
├── __init__.py
│
├── test_integration.py                   # Integration tests (legacy)
├── test_data_persistence.py             # Data persistence layer tests
├── test_booking_service.py              # Booking service tests
├── test_security_service.py             # Security & auth tests
├── test_utils.py                        # Utility function tests
├── test_timezone_utils.py               # Timezone handling tests
├── test_t2_bucket_system.py             # T2 dice system tests
│
├── test_database/                       # Database model tests
│   ├── test_infrastructure.py          # DB connection & setup
│   ├── test_booking_models.py          # Booking & BookingOutcome models
│   ├── test_t2_models.py                # T2 system models
│   ├── test_gamification_models.py     # Gamification models
│   ├── test_user_models.py              # User-related models
│   ├── test_cosmetics_models.py        # Cosmetics system models
│   └── test_weekly_models.py            # Weekly points models
│
├── test_services/                       # Service layer tests
│   ├── test_booking_service.py         # Booking service logic
│   ├── test_t2_bucket_service.py       # T2 bucket system service
│   ├── test_gamification_service.py    # Gamification logic
│   ├── test_notification_service.py    # Notification system
│   └── test_cache_and_utils.py         # Cache & utilities
│
└── test_routes/                         # Route/endpoint tests
    ├── test_routes_auth_login.py       # Login routes (comprehensive)
    ├── test_routes_auth_login_simple.py # Login routes (simplified)
    ├── test_routes_auth_2fa.py         # 2FA routes
    ├── test_routes_auth_session.py     # Session management
    ├── test_routes_t2_core.py          # T2 core routes
    ├── test_routes_t2_core_simple.py   # T2 core (simplified)
    ├── test_routes_t2_booking.py       # T2 booking routes
    └── test_routes_t2_analytics.py     # T2 analytics routes
```

**Total Test Files:** 26
**Estimated Test Count:** 200+ test cases

---

## 🚀 Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_booking_service.py

# Run specific test function
pytest tests/test_booking_service.py::test_create_booking

# Run tests matching pattern
pytest -k "booking"
```

### With Coverage

```bash
# Run tests with coverage report
pytest --cov=app --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open coverage report (Windows)
start htmlcov/index.html

# Open coverage report (Linux/Mac)
open htmlcov/index.html
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4
```

### Debugging Failed Tests

```bash
# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Enter debugger on failure
pytest --pdb

# Show print statements
pytest -s
```

---

## 📦 Test Categories

### 1. Unit Tests

**Purpose:** Test individual functions in isolation
**Location:** `tests/test_*.py` (root level)
**Examples:**
- `test_data_persistence.py` - JSON file operations
- `test_utils.py` - Helper functions
- `test_timezone_utils.py` - Timezone conversions

**Characteristics:**
- Fast execution (<1s per test)
- No external dependencies
- Heavy use of mocking
- High code coverage

**Example Test:**
```python
def test_calculate_duration():
    start = "08:00"
    end = "10:30"
    result = calculate_duration(start, end)
    assert result == 150  # 2.5 hours = 150 minutes
```

---

### 2. Service Tests

**Purpose:** Test business logic and service layer
**Location:** `tests/test_services/`
**Examples:**
- `test_booking_service.py` - Booking creation, validation, rescheduling
- `test_t2_bucket_service.py` - T2 dice system, probability calculations
- `test_gamification_service.py` - XP, levels, badges

**Characteristics:**
- Moderate execution time (1-3s per test)
- May use test database or mocked persistence
- Focus on business rules

**Example Test:**
```python
def test_draw_closer_probability(mock_bucket_service):
    """Test that closer is drawn according to configured probability"""
    service = T2BucketService()
    results = [service.draw_closer() for _ in range(100)]

    # David should be drawn ~45% of time (probability 9 out of 20)
    david_count = results.count('david.nehm')
    assert 35 < david_count < 55  # Allow 10% variance
```

---

### 3. Database Tests

**Purpose:** Test SQLAlchemy models and database operations
**Location:** `tests/test_database/`
**Examples:**
- `test_booking_models.py` - Booking & BookingOutcome CRUD
- `test_gamification_models.py` - Gamification models
- `test_user_models.py` - User-related models

**Characteristics:**
- Use in-memory SQLite or test PostgreSQL database
- Test model relationships, constraints, queries
- Rollback after each test

**Example Test:**
```python
def test_create_booking(db_session):
    """Test booking creation with all required fields"""
    booking = Booking(
        username='test_user',
        customer='John Doe',
        date=datetime.now().date(),
        time='10:00',
        duration=30,
        status='pending'
    )
    db_session.add(booking)
    db_session.commit()

    assert booking.id is not None
    assert booking.username == 'test_user'
```

---

### 4. Route Tests

**Purpose:** Test HTTP endpoints and request/response handling
**Location:** `tests/test_routes/`
**Examples:**
- `test_routes_auth_login.py` - Login, logout, session handling
- `test_routes_t2_booking.py` - T2 booking endpoints
- `test_routes_auth_2fa.py` - 2FA setup, verification

**Characteristics:**
- Use Flask test client
- Test HTTP methods, status codes, redirects
- Verify session state, cookies, CSRF tokens
- May require authentication fixtures

**Example Test:**
```python
def test_login_success(client):
    """Test successful login redirects to hub"""
    response = client.post('/login', data={
        'username': 'test_user',
        'password': 'test_pass'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert response.location == '/hub'

    # Verify session is set
    with client.session_transaction() as sess:
        assert sess['user'] == 'test_user'
        assert sess.get('logged_in') is True
```

---

### 5. Integration Tests

**Purpose:** Test complete workflows across multiple components
**Location:** `tests/test_integration/` or `tests/test_integration.py`
**Examples:**
- Complete booking flow (select slot → fill form → confirm → calendar)
- T2 draw flow (draw closer → select date → book → notification)
- 2FA setup flow (generate secret → scan QR → verify code → enable)

**Characteristics:**
- Slower execution (5-15s per test)
- Test multiple services, database, APIs
- Verify end-to-end behavior
- Use minimal mocking

**Example Test:**
```python
def test_complete_booking_flow(logged_in_client, mock_calendar):
    """Test complete booking from slot selection to confirmation"""
    # Step 1: View available slots
    response = logged_in_client.get('/slots/day?date=2026-01-10')
    assert response.status_code == 200
    assert b'08:00' in response.data

    # Step 2: Create booking
    response = logged_in_client.post('/book', data={
        'date': '2026-01-10',
        'hour': '08:00',
        'customer': 'Jane Doe',
        'phone': '0123456789',
        'description': 'Test booking'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Erfolgreich gebucht' in response.data

    # Step 3: Verify calendar event created
    assert mock_calendar.create_event.called
```

---

### 6. Security Tests

**Purpose:** Verify security controls (auth, CSRF, permissions)
**Location:** Embedded in route tests and dedicated `test_security_service.py`
**Examples:**
- CSRF token validation
- Unauthorized access (401/403 responses)
- Session timeout
- Password hashing
- 2FA verification

**Example Test:**
```python
def test_csrf_protection(client):
    """Test that POST without CSRF token is rejected"""
    response = client.post('/book', data={
        'date': '2026-01-10',
        'hour': '08:00'
    })

    assert response.status_code == 400  # Bad Request
```

---

## 🔧 Pytest Fixtures

Fixtures are reusable test components defined in `tests/conftest.py`.

### Core Fixtures

**`app`** (session scope)
- Creates Flask application with test configuration
- Mocks Google Calendar API credentials
- Disables CSRF for easier testing
- Used by all tests

**`client`** (function scope)
- Flask test client for making HTTP requests
- Fresh client for each test (no session)
- Usage: `response = client.get('/hub')`

**`logged_in_client`** (function scope)
- Pre-authenticated test client
- Session includes `user='test_user'`
- Usage: `response = logged_in_client.get('/my-calendar')`

**`admin_client`** (function scope)
- Pre-authenticated admin test client
- Session includes `user='admin_user'`, `is_admin=True`
- Usage: `response = admin_client.get('/admin/users')`

### Data Fixtures

**`temp_data_dir`** (function scope)
- Creates temporary directory for test data
- Automatically cleaned up after test
- Usage: `file_path = temp_data_dir / 'test.json'`

**`mock_data_persistence`** (function scope)
- Mocked data persistence service
- Prevents writing to real JSON files during tests
- Usage: `mock_data_persistence.save_scores(data)`

### Database Fixtures

**`db_session`** (function scope)
- SQLAlchemy session for database tests
- Automatically rolls back changes after test
- Usage: `db_session.add(booking)`

**Example Usage:**
```python
def test_booking_requires_auth(client):
    """Test that booking requires authentication"""
    response = client.get('/slots/booking')
    assert response.status_code == 302  # Redirect to login

def test_booking_with_auth(logged_in_client):
    """Test booking page loads when authenticated"""
    response = logged_in_client.get('/slots/booking')
    assert response.status_code == 200
```

---

## ✍️ Writing Tests

### Best Practices

1. **Use Descriptive Names**
   ```python
   # Good
   def test_booking_fails_with_invalid_phone_number():

   # Bad
   def test_booking():
   ```

2. **Arrange-Act-Assert Pattern**
   ```python
   def test_calculate_duration():
       # Arrange
       start = "08:00"
       end = "10:30"

       # Act
       result = calculate_duration(start, end)

       # Assert
       assert result == 150
   ```

3. **Test One Thing Per Test**
   ```python
   # Good - separate tests
   def test_booking_validates_customer_name():
       ...

   def test_booking_validates_phone_number():
       ...

   # Bad - testing multiple things
   def test_booking_validation():
       # Tests name AND phone AND date...
   ```

4. **Use Fixtures for Setup**
   ```python
   @pytest.fixture
   def sample_booking():
       return {
           'date': '2026-01-10',
           'time': '08:00',
           'customer': 'John Doe',
           'phone': '0123456789'
       }

   def test_booking_creation(sample_booking):
       booking = create_booking(sample_booking)
       assert booking.customer == 'John Doe'
   ```

5. **Mock External Dependencies**
   ```python
   from unittest.mock import patch

   @patch('app.services.google_calendar.GoogleCalendarService.create_event')
   def test_booking_creates_calendar_event(mock_create_event):
       create_booking(data)
       assert mock_create_event.called
   ```

### Parameterized Tests

Test multiple inputs with single test function:

```python
@pytest.mark.parametrize("start,end,expected", [
    ("08:00", "09:00", 60),
    ("10:00", "12:30", 150),
    ("14:00", "14:15", 15),
])
def test_calculate_duration_various_inputs(start, end, expected):
    result = calculate_duration(start, end)
    assert result == expected
```

### Testing Exceptions

```python
def test_invalid_date_raises_error():
    with pytest.raises(ValueError, match="Invalid date format"):
        parse_date("invalid-date")
```

---

## 🔄 CI/CD Integration

### GitHub Actions (Recommended)

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests with coverage
      run: |
        pytest --cov=app --cov-report=xml --cov-report=term

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

Install pre-commit framework:

```bash
pip install pre-commit
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

Install hooks:

```bash
pre-commit install
```

Now tests run automatically before each commit.

---

## 🧑‍💻 Manual Testing

### Local Development Testing

**1. Start Development Server:**
```bash
python run.py
```

**2. Test Checklist:**
- [ ] Login/logout works
- [ ] Create booking (T1 slot)
- [ ] View My Calendar
- [ ] Draw T2 closer
- [ ] Book T2 appointment
- [ ] Test admin features (if admin user)
- [ ] Test gamification (earn XP, check level)
- [ ] Test 2FA setup

**3. Browser Testing:**
- Chrome/Edge (primary)
- Firefox
- Safari (if available)
- Mobile browsers (responsive design)

### Production Testing (After Deployment)

**1. Health Check:**
```bash
curl -I https://berater.zfa.gmbh/health
# Should return: HTTP/1.1 200 OK
```

**2. Smoke Tests:**
- [ ] Homepage loads
- [ ] Login works
- [ ] Create test booking
- [ ] View calendar
- [ ] Check error logs (no critical errors)

**3. Verify Recent Changes:**
- Test specifically the features/fixes in latest deployment
- Check Sentry for new errors
- Monitor server logs for 10-15 minutes

**4. Rollback If Needed:**
```bash
# SSH into server
ssh -i ~/.ssh/server_key root@91.98.192.233

# Restore backup
cd /opt/business-hub
tar -xzf /tmp/backup_YYYYMMDD_HHMM.tar.gz

# Restart service
systemctl restart business-hub
```

---

## 📊 Testing CSRF Protection

After CSRF implementation (v3.3.15), verify protection:

### Automated Tests

```python
def test_booking_without_csrf_fails(client):
    """Test booking fails without CSRF token"""
    response = client.post('/book', data={
        'date': '2026-01-10',
        'time': '08:00',
        'customer': 'Test'
    })
    assert response.status_code == 400

def test_booking_with_csrf_succeeds(logged_in_client):
    """Test booking succeeds with CSRF token"""
    with logged_in_client.session_transaction() as sess:
        csrf_token = sess.get('csrf_token')

    response = logged_in_client.post('/book', data={
        'date': '2026-01-10',
        'time': '08:00',
        'customer': 'Test',
        'csrf_token': csrf_token
    })
    assert response.status_code in [200, 302]
```

### Manual Testing

**1. Check CSRF Token Presence:**
- Open https://berater.zfa.gmbh/
- Inspect booking form HTML
- Verify `<input type="hidden" name="csrf_token">` exists

**2. Test AJAX Endpoints:**
- Open browser DevTools → Network tab
- Perform action that triggers POST request (e.g., update event status)
- Verify `X-CSRFToken` header is present in request

**3. Test Token Validation:**
- Use curl to POST without CSRF token:
  ```bash
  curl -X POST https://berater.zfa.gmbh/book \
    -d "date=2026-01-10&time=08:00&customer=Test"
  ```
- Should return HTTP 400 Bad Request

---

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/2.3.x/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

---

## 🔄 Change History

| Date | Change | Impact |
|------|--------|--------|
| 2026-01-05 | Documentation created | Initial comprehensive testing guide |
| 2025-11-28 | Added T2 route tests | Increased coverage to 75% |
| 2025-11-21 | Added database model tests | PostgreSQL migration testing |

---

**Document Owner:** Luke Hoppe
**Review Frequency:** Quarterly or when test structure changes
