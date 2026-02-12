# -*- coding: utf-8 -*-
"""
Pytest Configuration and Fixtures for Central Business Tool Hub
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing"""
    # Set test environment variables
    os.environ['SECRET_KEY'] = 'test-secret-key-for-testing'
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'true'
    os.environ['USERLIST'] = 'test_user:test_pass,admin_user:admin_pass'
    os.environ['ADMIN_USERS'] = 'admin_user'

    # Mock Google credentials loading at the source
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False

    with patch('app.utils.credentials.load_google_credentials', return_value=mock_creds), \
         patch('app.core.google_calendar.GoogleCalendarService._initialize_service'), \
         patch('app.services.tracking_system.build', return_value=MagicMock()):

        from app import create_app

        app = create_app()
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SECRET_KEY': 'test-secret-key-for-testing',
            'SESSION_COOKIE_HTTPONLY': False,  # Allow test client to access session
            'SESSION_COOKIE_SECURE': False,     # Not needed for testing
            'SESSION_TYPE': None,  # Use default Flask cookie sessions for test client compatibility
        })

        # Enable session preservation in test context
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False

        # Reset to default Flask cookie sessions for test client compatibility
        # Flask-Session's server-side sessions break session_transaction()
        from flask.sessions import SecureCookieSessionInterface
        app.session_interface = SecureCookieSessionInterface()

        yield app


@pytest.fixture(scope='function')
def client(app):
    """Create Flask test client"""
    with app.test_client() as client:
        yield client


@pytest.fixture(scope='function')
def app_context(app):
    """Create Flask application context"""
    with app.app_context():
        yield app


@pytest.fixture(scope='function')
def logged_in_client(client, app):
    """Create Flask test client with logged-in session"""
    with client.session_transaction() as sess:
        sess['user'] = 'test_user'
        sess['logged_in'] = True
        sess['is_admin'] = False
        sess['last_activity'] = datetime.now().isoformat()
    yield client


@pytest.fixture(scope='function')
def admin_client(client, app):
    """Create Flask test client with admin session"""
    with client.session_transaction() as sess:
        sess['user'] = 'admin_user'
        sess['logged_in'] = True
        sess['is_admin'] = True
        sess['last_activity'] = datetime.now().isoformat()
    yield client


@pytest.fixture(scope='function')
def temp_data_dir():
    """Create temporary directory for test data"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope='function')
def mock_data_persistence(temp_data_dir):
    """Mock DataPersistence with temporary directory"""
    from app.services.data_persistence import DataPersistence

    # Create a new instance with temp directories
    persistence = DataPersistence()
    persistence.data_dir = temp_data_dir / "persistent"
    persistence.backup_dir = temp_data_dir / "backups"
    persistence.static_dir = temp_data_dir / "static"

    # Create directories
    persistence.data_dir.mkdir(parents=True, exist_ok=True)
    persistence.backup_dir.mkdir(parents=True, exist_ok=True)
    persistence.static_dir.mkdir(parents=True, exist_ok=True)

    yield persistence


@pytest.fixture(scope='function')
def mock_google_calendar():
    """Mock Google Calendar Service"""
    with patch('app.core.google_calendar.GoogleCalendarService') as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        # Default mock responses
        mock_instance.is_configured.return_value = True
        mock_instance.get_events.return_value = {'items': []}
        mock_instance.create_event.return_value = {'id': 'test-event-123'}

        yield mock_instance


@pytest.fixture(scope='function')
def sample_user_data():
    """Sample user data for testing"""
    return {
        'test_user': {
            'points': 100,
            'level': 5,
            'badges': ['first_booking', 'streak_3'],
            'total_bookings': 25
        },
        'admin_user': {
            'points': 500,
            'level': 15,
            'badges': ['first_booking', 'streak_7', 'monthly_champion'],
            'total_bookings': 150
        }
    }


@pytest.fixture(scope='function')
def sample_scores_data():
    """Sample scores data for testing"""
    return {
        'test_user': 100,
        'admin_user': 500,
        'another_user': 250
    }


@pytest.fixture(scope='function')
def sample_badges_data():
    """Sample badges data for testing"""
    return {
        'test_user': ['first_booking', 'streak_3'],
        'admin_user': ['first_booking', 'streak_7', 'monthly_champion']
    }


@pytest.fixture(scope='function')
def sample_calendar_events():
    """Sample Google Calendar events for testing"""
    return {
        'items': [
            {
                'id': 'event1',
                'summary': 'Müller, Hans',
                'start': {'dateTime': '2025-01-15T14:00:00+01:00'},
                'end': {'dateTime': '2025-01-15T16:00:00+01:00'},
                'colorId': '2',
                'description': '[Booked by: test_user]'
            },
            {
                'id': 'event2',
                'summary': 'Schmidt, Anna',
                'start': {'dateTime': '2025-01-15T16:00:00+01:00'},
                'end': {'dateTime': '2025-01-15T18:00:00+01:00'},
                'colorId': '9',
                'description': '[Booked by: admin_user]'
            },
            {
                'id': 'event3',
                'summary': 'T1-bereit Weber',
                'start': {'dateTime': '2025-01-15T09:00:00+01:00'},
                'end': {'dateTime': '2025-01-15T11:00:00+01:00'},
                'colorId': '1',
                'description': ''
            }
        ]
    }


@pytest.fixture(scope='function')
def sample_availability():
    """Sample availability data for testing"""
    return {
        '2025-01-15 09:00': ['Berater1', 'Berater2'],
        '2025-01-15 11:00': ['Berater1', 'Berater2', 'Berater3'],
        '2025-01-15 14:00': ['Berater1', 'Berater2', 'Berater3'],
        '2025-01-15 16:00': ['Berater1', 'Berater2'],
        '2025-01-15 18:00': ['Berater1'],
        '2025-01-15 20:00': ['Berater1', 'Berater2', 'Berater3']
    }


@pytest.fixture(scope='function')
def sample_t2_bucket_state():
    """Sample T2 bucket system state for testing"""
    return {
        'closers': {
            'Alex': {'probability': 9.0, 'original_probability': 9.0},
            'David': {'probability': 9.0, 'original_probability': 9.0},
            'Jose': {'probability': 2.0, 'original_probability': 2.0}
        },
        'draw_count': 0,
        'max_draws': 20,
        'history': []
    }


@pytest.fixture(scope='function')
def sample_t2_bookings():
    """Sample T2 bookings for testing"""
    return [
        {
            'booking_id': 'T2-ABC123',
            'customer_name': 'Mustermann, Max',
            'email': 'max@example.com',
            'date': '2025-12-15',
            'time': '14:00',
            'coach': 'Alex',
            'berater': 'Christian',
            'topic': 'Verkaufsgespräch',
            'status': 'confirmed',
            'booked_by': 'test_user',
            'booked_at': '2025-11-28T10:00:00'
        },
        {
            'booking_id': 'T2-DEF456',
            'customer_name': 'Schmidt, Anna',
            'email': 'anna@example.com',
            'date': '2025-12-20',
            'time': '16:00',
            'coach': 'David',
            'berater': 'Daniel',
            'topic': 'Beratungsgespräch',
            'status': 'confirmed',
            'booked_by': 'admin_user',
            'booked_at': '2025-11-28T11:00:00'
        }
    ]


@pytest.fixture(scope='function')
def sample_notifications():
    """Sample notifications for testing"""
    return {
        'test_user': [
            {
                'id': 'notif-1',
                'type': 'info',
                'title': 'Welcome',
                'message': 'Welcome to the system!',
                'timestamp': '2025-11-28T10:00:00',
                'read': False,
                'dismissed': False,
                'show_popup': True,
                'roles': ['all']
            },
            {
                'id': 'notif-2',
                'type': 'success',
                'title': 'Feature Update',
                'message': 'New T2 booking system is live!',
                'timestamp': '2025-11-27T15:00:00',
                'read': True,
                'dismissed': False,
                'show_popup': False,
                'roles': ['closer', 'admin']
            }
        ],
        'admin_user': [
            {
                'id': 'notif-3',
                'type': 'warning',
                'title': 'System Maintenance',
                'message': 'Scheduled maintenance on Sunday',
                'timestamp': '2025-11-26T12:00:00',
                'read': False,
                'dismissed': False,
                'show_popup': True,
                'roles': ['admin']
            }
        ]
    }


# ========== MOCK SERVICE FIXTURES ==========

@pytest.fixture(scope='function')
def mock_security_service():
    """Mock Security Service for authentication and 2FA"""
    with patch('app.routes.auth.security_service') as mock_service:
        # Default configurations
        mock_service.verify_password.return_value = True
        mock_service.is_2fa_enabled.return_value = False
        mock_service.verify_2fa.return_value = True
        mock_service.setup_2fa.return_value = (
            'JBSWY3DPEHPK3PXP',  # secret
            'data:image/png;base64,iVBORw0KG...',  # qr_code
            ['12345678', '87654321', '11223344']  # backup_codes
        )
        mock_service.enable_2fa.return_value = (True, '2FA erfolgreich aktiviert')
        mock_service.disable_2fa.return_value = (True, '2FA erfolgreich deaktiviert')
        mock_service.get_backup_codes.return_value = ['12345678', '87654321']
        mock_service.change_password.return_value = (True, 'Passwort geändert')

        yield mock_service


@pytest.fixture(scope='function')
def mock_account_lockout():
    """Mock Account Lockout Service for rate limiting"""
    with patch('app.routes.auth.account_lockout') as mock_service:
        # Default: not locked out
        mock_service.is_locked_out.return_value = (False, 0)
        mock_service.record_failed_attempt.return_value = (False, 0)
        mock_service.check_and_record_failure.return_value = ('failed', None)
        mock_service.record_successful_login.return_value = None

        yield mock_service


@pytest.fixture(scope='function')
def mock_audit_service():
    """Mock Audit Service for logging"""
    with patch('app.routes.auth.audit_service') as mock_service:
        # All audit methods just pass
        mock_service.log_login_success.return_value = None
        mock_service.log_login_failure.return_value = None
        mock_service.log_logout.return_value = None
        mock_service.log_2fa_setup.return_value = None
        mock_service.log_password_change.return_value = None

        yield mock_service


@pytest.fixture(scope='function')
def mock_activity_tracking():
    """Mock Activity Tracking Service"""
    with patch('app.routes.auth.activity_tracking') as mock_service:
        # Default tracking methods
        mock_service.track_login.return_value = None
        mock_service.update_online_status.return_value = None
        mock_service.get_user_activity.return_value = {}

        yield mock_service


@pytest.fixture(scope='function')
def mock_t2_bucket_system():
    """Mock T2 Bucket System for closer draws"""
    with patch('app.routes.t2.t2_bucket_system') as mock_service:
        # Default draw result
        mock_service.draw_closer.return_value = 'Alex'
        mock_service.get_bucket_state.return_value = {
            'closers': {
                'Alex': {'probability': 9.0, 'original_probability': 9.0},
                'David': {'probability': 9.0, 'original_probability': 9.0},
                'Jose': {'probability': 2.0, 'original_probability': 2.0}
            },
            'draw_count': 5,
            'max_draws': 20
        }
        mock_service.reset_bucket.return_value = None

        yield mock_service


@pytest.fixture(scope='function')
def mock_t2_analytics_service():
    """Mock T2 Analytics Service"""
    with patch('app.services.t2_analytics_service.t2_analytics_service') as mock_service:
        # Default analytics responses
        mock_service.get_user_draw_stats.return_value = {
            'total_draws': 15,
            'unique_closers': 3,
            'most_drawn_closer': 'Alex',
            'draws_by_closer': {'Alex': 8, 'David': 5, 'Jose': 2}
        }
        mock_service.get_combined_user_stats.return_value = {
            't1_slots_booked': 25,
            't2_bookings': 10,
            'total_draws': 15,
            'tickets_remaining': 3
        }
        mock_service.get_user_draw_history.return_value = {
            'draws': [],
            'total': 0,
            'limit': 50,
            'offset': 0
        }
        mock_service.get_2h_booking_analytics.return_value = {
            'berater_stats': {},
            'coach_stats': {},
            'overall': {'total_bookings': 0}
        }

        yield mock_service


@pytest.fixture(scope='function')
def mock_notification_service():
    """Mock Notification Service"""
    with patch('app.services.notification_service.notification_service') as mock_service:
        # Default notification methods
        mock_service.get_user_notifications.return_value = []
        mock_service.create_notification.return_value = 'notif-123'
        mock_service.mark_as_read.return_value = True
        mock_service.dismiss_notification.return_value = True

        yield mock_service


@pytest.fixture(scope='function')
def mock_tracking_system():
    """Mock Tracking System for bookings"""
    with patch('app.services.tracking_system.tracking_system') as mock_service:
        # Default tracking methods
        mock_service.track_booking.return_value = None
        mock_service.get_user_bookings.return_value = []
        mock_service.get_booking_stats.return_value = {
            'total': 0,
            'this_week': 0,
            'this_month': 0
        }

        yield mock_service


# ========== DATABASE TESTING FIXTURES ==========

@pytest.fixture(scope='session')
def test_db_engine():
    """Create test database engine (SQLite in-memory for fast tests)"""
    from sqlalchemy import create_engine

    # Use SQLite in-memory database for tests
    engine = create_engine('sqlite:///:memory:', echo=False)

    # Create all tables
    from app.models.base import Base
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope='function')
def db_session(test_db_engine):
    """Provide transactional database session for each test"""
    from sqlalchemy.orm import sessionmaker

    # Create connection and transaction
    connection = test_db_engine.connect()
    transaction = connection.begin()

    # Create session bound to connection
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # Rollback everything (isolate tests)
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope='function')
def db_with_app(app, db_session):
    """Database session with Flask app context"""
    with app.app_context():
        # Patch db.session to use our test session
        with patch('app.models.base.db.session', db_session):
            yield db_session


# Markers for categorizing tests
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (may require mocking)")
    config.addinivalue_line("markers", "slow: Slow tests (skip with -m 'not slow')")
    config.addinivalue_line("markers", "database: Database model tests")
