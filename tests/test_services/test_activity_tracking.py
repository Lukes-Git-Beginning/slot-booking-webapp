# -*- coding: utf-8 -*-
"""
Tests fuer Block 7 — ActivityTrackingService PG Dual-Write

Testet:
- track_login: last_login Sync zu PG
- update_online_status: last_activity Sync zu PG
- get_online_users: PG-first read
- Fallback zu JSON wenn USE_POSTGRES=False
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Import at module level to avoid pytz issues during patching
from app.services.activity_tracking import ActivityTrackingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service():
    svc = ActivityTrackingService.__new__(ActivityTrackingService)
    svc.login_history_file = 'login_history'
    svc.online_sessions_file = 'online_sessions'
    return svc


def _make_pg_user(username='alice', last_login=None, last_activity=None, is_active=True):
    user = MagicMock()
    user.username = username
    user.last_login = last_login
    user.last_activity = last_activity
    user.is_active = is_active
    return user


def _make_ctx(session):
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _make_error_ctx():
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(side_effect=Exception("PG down"))
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# track_login — last_login Sync
# ---------------------------------------------------------------------------

class TestTrackLogin:
    """Tests fuer track_login PG-Sync."""

    def test_track_login_syncs_last_login_to_pg_on_success(self):
        """Erfolgreicher Login aktualisiert last_login in PG."""
        svc = _make_service()

        pg_user = _make_pg_user('alice')
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = pg_user

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.activity_tracking.USE_POSTGRES', True), \
             patch('app.services.activity_tracking.POSTGRES_AVAILABLE', True), \
             patch('app.services.activity_tracking.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            svc.track_login('alice', '127.0.0.1', 'Mozilla/5.0', success=True)

        # last_login wurde gesetzt
        assert pg_user.last_login is not None

    def test_track_login_does_not_sync_on_failed_login(self):
        """Fehlgeschlagener Login aktualisiert last_login NICHT in PG."""
        svc = _make_service()

        pg_user = _make_pg_user('alice')
        mock_session = MagicMock()

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.activity_tracking.USE_POSTGRES', True), \
             patch('app.services.activity_tracking.POSTGRES_AVAILABLE', True), \
             patch('app.services.activity_tracking.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            svc.track_login('alice', '127.0.0.1', 'Mozilla/5.0', success=False)

        # kein PG-Query bei fehlgeschlagenem Login
        assert not mock_session.query.called

    def test_track_login_no_pg_write_when_disabled(self):
        """Mit USE_POSTGRES=False kein PG-Write."""
        svc = _make_service()

        mock_session = MagicMock()

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.activity_tracking.USE_POSTGRES', False), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            svc.track_login('alice', '127.0.0.1', 'Mozilla/5.0', success=True)

        assert not mock_session.query.called

    def test_track_login_pg_error_does_not_raise(self):
        """PG-Fehler bei track_login wird still geloggt, kein Exception."""
        svc = _make_service()

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.activity_tracking.USE_POSTGRES', True), \
             patch('app.services.activity_tracking.POSTGRES_AVAILABLE', True), \
             patch('app.services.activity_tracking.db_session_scope', return_value=_make_error_ctx()), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            # Darf keine Exception werfen
            svc.track_login('alice', '127.0.0.1', 'Mozilla/5.0', success=True)


# ---------------------------------------------------------------------------
# update_online_status — last_activity Sync
# ---------------------------------------------------------------------------

class TestUpdateOnlineStatus:
    """Tests fuer update_online_status PG-Sync."""

    def test_update_online_status_active_syncs_last_activity(self):
        """action='active' aktualisiert last_activity in PG."""
        svc = _make_service()

        pg_user = _make_pg_user('alice')
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = pg_user

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.activity_tracking.USE_POSTGRES', True), \
             patch('app.services.activity_tracking.POSTGRES_AVAILABLE', True), \
             patch('app.services.activity_tracking.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            svc.update_online_status('alice', 'sess-123', action='active')

        assert pg_user.last_activity is not None

    def test_update_online_status_logout_no_pg_write(self):
        """action='logout' schreibt nicht in PG."""
        svc = _make_service()

        mock_session = MagicMock()

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {'alice': {'session_id': 'sess-123', 'last_activity': '2026-01-01T10:00:00', 'status': 'online'}}

        with patch('app.services.activity_tracking.USE_POSTGRES', True), \
             patch('app.services.activity_tracking.POSTGRES_AVAILABLE', True), \
             patch('app.services.activity_tracking.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            svc.update_online_status('alice', 'sess-123', action='logout')

        # Kein PG-Query bei logout
        assert not mock_session.query.called

    def test_update_online_status_no_pg_write_when_disabled(self):
        """Mit USE_POSTGRES=False kein PG-Write."""
        svc = _make_service()

        mock_session = MagicMock()

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.activity_tracking.USE_POSTGRES', False), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            svc.update_online_status('alice', 'sess-123', action='active')

        assert not mock_session.query.called


# ---------------------------------------------------------------------------
# get_online_users — PG-first read
# ---------------------------------------------------------------------------

class TestGetOnlineUsers:
    """Tests fuer get_online_users PG-first Logik."""

    def test_get_online_users_returns_pg_data_when_available(self):
        """Wenn PG verfuegbar, werden Online-User aus PG gelesen."""
        svc = _make_service()

        now = datetime.now()
        recent_activity = now - timedelta(minutes=5)

        pg_user = _make_pg_user('alice', last_activity=recent_activity, is_active=True)

        mock_session = MagicMock()
        # query().filter(...).order_by(...).all() chain
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [pg_user]

        with patch('app.services.activity_tracking.USE_POSTGRES', True), \
             patch('app.services.activity_tracking.POSTGRES_AVAILABLE', True), \
             patch('app.services.activity_tracking.db_session_scope', return_value=_make_ctx(mock_session)):
            result = svc.get_online_users(timeout_minutes=15)

        assert len(result) == 1
        assert result[0]['username'] == 'alice'
        assert result[0]['status'] == 'online'

    def test_get_online_users_falls_back_to_json_on_pg_error(self):
        """Bei PG-Fehler werden Online-User aus JSON gelesen."""
        svc = _make_service()

        from datetime import datetime
        import pytz
        tz = pytz.timezone('Europe/Berlin')
        now_str = datetime.now(tz).isoformat()

        json_sessions = {
            'bob': {
                'session_id': 'sess-abc',
                'last_activity': now_str,
                'status': 'online'
            }
        }

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = json_sessions

        with patch('app.services.activity_tracking.USE_POSTGRES', True), \
             patch('app.services.activity_tracking.POSTGRES_AVAILABLE', True), \
             patch('app.services.activity_tracking.db_session_scope', return_value=_make_error_ctx()), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            result = svc.get_online_users(timeout_minutes=15)

        assert any(u['username'] == 'bob' for u in result)

    def test_get_online_users_uses_json_when_postgres_disabled(self):
        """Mit USE_POSTGRES=False werden Online-User aus JSON gelesen."""
        svc = _make_service()

        from datetime import datetime
        import pytz
        tz = pytz.timezone('Europe/Berlin')
        now_str = datetime.now(tz).isoformat()

        json_sessions = {
            'charlie': {
                'session_id': 'sess-xyz',
                'last_activity': now_str,
                'status': 'online'
            }
        }

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = json_sessions

        with patch('app.services.activity_tracking.USE_POSTGRES', False), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            result = svc.get_online_users(timeout_minutes=15)

        assert any(u['username'] == 'charlie' for u in result)

    def test_get_online_users_filters_expired_sessions_in_json_fallback(self):
        """Abgelaufene JSON-Sessions werden herausgefiltert."""
        svc = _make_service()

        from datetime import datetime, timedelta
        import pytz
        tz = pytz.timezone('Europe/Berlin')
        old_time = (datetime.now(tz) - timedelta(minutes=30)).isoformat()

        json_sessions = {
            'expired_user': {
                'session_id': 'sess-old',
                'last_activity': old_time,
                'status': 'online'
            }
        }

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = json_sessions

        with patch('app.services.activity_tracking.USE_POSTGRES', False), \
             patch('app.services.activity_tracking.data_persistence', mock_dp):
            result = svc.get_online_users(timeout_minutes=15)

        # Abgelaufene Session nicht in der Liste
        assert not any(u['username'] == 'expired_user' for u in result)
