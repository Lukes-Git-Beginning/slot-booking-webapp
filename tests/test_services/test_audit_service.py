# -*- coding: utf-8 -*-
"""
Service Layer Tests - Audit Service
Tests for app/services/audit_service.py
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


# ========== FIXTURES ==========

@pytest.fixture
def audit_service():
    """Create AuditService instance with PG disabled"""
    with patch.dict('os.environ', {'USE_POSTGRES': 'false'}):
        from app.services.audit_service import AuditService
        return AuditService()


@pytest.fixture
def sample_events():
    return [
        {
            'timestamp': '2026-01-01T10:00:00.000000Z',
            'event_type': 'auth',
            'action': 'login_success',
            'user': 'alice',
            'ip_address': '127.0.0.1',
            'user_agent': 'TestBrowser/1.0',
            'severity': 'info',
            'details': {}
        },
        {
            'timestamp': '2026-01-02T11:00:00.000000Z',
            'event_type': 'auth',
            'action': 'login_failure',
            'user': 'bob',
            'ip_address': '192.168.1.1',
            'user_agent': 'TestBrowser/2.0',
            'severity': 'warning',
            'details': {'reason': 'invalid_credentials'}
        },
        {
            'timestamp': '2026-01-03T12:00:00.000000Z',
            'event_type': 'security',
            'action': 'security_alert_brute_force',
            'user': 'system',
            'ip_address': '10.0.0.1',
            'user_agent': 'unknown',
            'severity': 'critical',
            'details': {'target': 'admin'}
        },
        {
            'timestamp': '2026-01-04T13:00:00.000000Z',
            'event_type': 'admin',
            'action': 'user_created',
            'user': 'admin',
            'ip_address': '127.0.0.1',
            'user_agent': 'TestBrowser/1.0',
            'severity': 'info',
            'details': {'target_user': 'newuser'}
        }
    ]


# ========== TESTS: log_event ==========

class TestLogEvent:
    def test_log_event_writes_to_json(self, audit_service, app):
        saved_data = []

        def mock_save(key, data):
            saved_data.clear()
            saved_data.extend(data)

        with app.test_request_context('/'):
            with patch('app.services.audit_service.USE_POSTGRES', False), \
                 patch('app.services.audit_service.data_persistence') as mock_dp, \
                 patch('app.services.audit_service.session', {'user': 'testuser'}):
                mock_dp.load_data.return_value = []
                mock_dp.save_data.side_effect = mock_save

                audit_service.log_event('auth', 'login_success', user='alice', severity='info')

                mock_dp.save_data.assert_called_once()
                assert len(saved_data) == 1
                event = saved_data[0]
                assert event['event_type'] == 'auth'
                assert event['action'] == 'login_success'
                assert event['user'] == 'alice'
                assert event['severity'] == 'info'

    def test_log_event_does_not_raise_on_error(self, audit_service):
        """log_event darf nie eine Exception nach aussen werfen"""
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch('app.services.audit_service.data_persistence') as mock_dp, \
             patch('app.services.audit_service.request', None), \
             patch('app.services.audit_service.session', {}):
            mock_dp.load_data.side_effect = Exception("Storage error")

            # Darf nicht werfen
            audit_service.log_event('auth', 'test_event')


# ========== TESTS: get_recent_events ==========

class TestGetRecentEvents:
    def test_returns_all_events(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            events = audit_service.get_recent_events(limit=100)
            assert len(events) == 4

    def test_respects_limit(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            events = audit_service.get_recent_events(limit=2)
            assert len(events) == 2

    def test_filters_by_event_type(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            events = audit_service.get_recent_events(event_type='auth')
            assert all(e['event_type'] == 'auth' for e in events)
            assert len(events) == 2

    def test_returns_newest_first(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            events = audit_service.get_recent_events()
            # Nach reverse() sollte neuestes Event zuerst kommen
            assert events[0]['timestamp'] > events[-1]['timestamp']


# ========== TESTS: get_user_events ==========

class TestGetUserEvents:
    def test_returns_events_for_user(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            events = audit_service.get_user_events('alice')
            assert len(events) == 1
            assert events[0]['user'] == 'alice'

    def test_returns_empty_for_unknown_user(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            events = audit_service.get_user_events('nobody')
            assert events == []


# ========== TESTS: get_failed_logins ==========

class TestGetFailedLogins:
    def test_returns_recent_failures(self, audit_service):
        # Format wie vom AuditService erzeugt: datetime.now(timezone.utc).isoformat() + 'Z'
        # Ergibt z.B. '2026-03-23T19:00:00.000000+00:00Z'
        recent_ts = datetime.now(timezone.utc).isoformat() + 'Z'
        events = [
            {'timestamp': recent_ts, 'action': 'login_failure', 'event_type': 'auth',
             'user': 'bob', 'severity': 'warning', 'details': {}, 'ip_address': '1.2.3.4', 'user_agent': ''},
        ]
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=events):
            failures = audit_service.get_failed_logins(hours=24)
            assert len(failures) == 1

    def test_excludes_old_failures(self, audit_service):
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat() + 'Z'
        events = [
            {'timestamp': old_ts, 'action': 'login_failure', 'event_type': 'auth',
             'user': 'bob', 'severity': 'warning', 'details': {}, 'ip_address': '1.2.3.4', 'user_agent': ''},
        ]
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=events):
            failures = audit_service.get_failed_logins(hours=24)
            assert len(failures) == 0


# ========== TESTS: get_critical_events ==========

class TestGetCriticalEvents:
    def test_returns_only_critical(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            events = audit_service.get_critical_events()
            assert all(e['severity'] == 'critical' for e in events)
            assert len(events) == 1


# ========== TESTS: search_events ==========

class TestSearchEvents:
    def test_search_by_user(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            results = audit_service.search_events(user='admin')
            assert all(e['user'] == 'admin' for e in results)

    def test_search_by_severity(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            results = audit_service.search_events(severity='warning')
            assert all(e['severity'] == 'warning' for e in results)

    def test_combined_filters(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            results = audit_service.search_events(event_type='auth', severity='info')
            assert all(e['event_type'] == 'auth' and e['severity'] == 'info' for e in results)

    def test_empty_results_for_no_match(self, audit_service, sample_events):
        with patch('app.services.audit_service.USE_POSTGRES', False), \
             patch.object(audit_service, '_load_audit_log', return_value=sample_events):
            results = audit_service.search_events(user='nobody')
            assert results == []


# ========== TESTS: Convenience Methods ==========

class TestConvenienceMethods:
    def test_log_login_success(self, audit_service):
        with patch.object(audit_service, 'log_event') as mock_log:
            audit_service.log_login_success('alice')
            mock_log.assert_called_once_with(
                event_type='auth', action='login_success', user='alice', severity='info'
            )

    def test_log_login_failure(self, audit_service):
        with patch.object(audit_service, 'log_event') as mock_log:
            audit_service.log_login_failure('bob', reason='wrong_password')
            mock_log.assert_called_once_with(
                event_type='auth',
                action='login_failure',
                details={'username': 'bob', 'reason': 'wrong_password'},
                severity='warning',
                user='bob'
            )

    def test_log_security_alert(self, audit_service):
        with patch.object(audit_service, 'log_event') as mock_log:
            audit_service.log_security_alert('brute_force', {'target': 'admin'})
            mock_log.assert_called_once_with(
                event_type='security',
                action='security_alert_brute_force',
                details={'target': 'admin'},
                severity='critical'
            )

    def test_log_admin_action(self, audit_service):
        with patch.object(audit_service, 'log_event') as mock_log:
            audit_service.log_admin_action('reset_password', {'target': 'user1'}, 'admin')
            mock_log.assert_called_once_with(
                event_type='admin',
                action='reset_password',
                details={'target': 'user1'},
                severity='info',
                user='admin'
            )


# ========== TESTS: _save_audit_log Rotation ==========

class TestAuditLogRotation:
    def test_rotation_limits_entries(self, audit_service):
        large_log = [
            {
                'timestamp': f'2026-01-01T{i:02d}:00:00Z',
                'event_type': 'auth', 'action': 'test',
                'user': 'user', 'severity': 'info', 'details': {}
            }
            for i in range(20)
        ]
        audit_service.max_entries = 5

        with patch('app.services.audit_service.data_persistence') as mock_dp:
            audit_service._save_audit_log(large_log)
            call_args = mock_dp.save_data.call_args
            saved = call_args[0][1]
            assert len(saved) == 5
            # Aelteste werden geloescht, neueste bleiben
            assert saved[-1]['timestamp'] == '2026-01-01T19:00:00Z'
