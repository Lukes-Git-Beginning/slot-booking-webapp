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

    from app import create_app

    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-for-testing',
    })

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
        sess['is_admin'] = False
        sess['last_activity'] = datetime.now().isoformat()
    yield client


@pytest.fixture(scope='function')
def admin_client(client, app):
    """Create Flask test client with admin session"""
    with client.session_transaction() as sess:
        sess['user'] = 'admin_user'
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


# Markers for categorizing tests
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (may require mocking)")
    config.addinivalue_line("markers", "slow: Slow tests (skip with -m 'not slow')")
