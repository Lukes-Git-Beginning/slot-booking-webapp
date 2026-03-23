# -*- coding: utf-8 -*-
"""
Tests fuer Block 7 — UserManagementService PG Dual-Write

Testet:
- _load_registry: PG-first read
- _save_registry: Dual-Write (PG + JSON)
- add_user: PG INSERT nach JSON-Write
- delete_user: PG Soft-Delete
- reset_password: PG password_hash Update
- Fallback zu JSON wenn USE_POSTGRES=False
"""

import pytest
from unittest.mock import MagicMock, patch, call

# Import at module level so pytz is resolved before any patching
from app.services.user_management_service import UserManagementService, USER_ROLES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service():
    """Erstellt eine UserManagementService-Instanz ohne echte Files."""
    return UserManagementService.__new__(UserManagementService)


def _make_pg_user(username='alice', is_active=True, is_admin=False, role='user'):
    user = MagicMock()
    user.username = username
    user.is_active = is_active
    user.is_admin = is_admin
    user.role = role
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
# _load_registry — PG-first read
# ---------------------------------------------------------------------------

class TestLoadRegistry:
    """Tests fuer _load_registry mit PG-first Logik."""

    def test_load_registry_returns_pg_data_when_available(self):
        """Wenn PG verfuegbar, werden Daten aus der users-Tabelle gelesen."""
        svc = _make_service()

        pg_user_active = _make_pg_user('alice', is_active=True, is_admin=True, role='admin')
        pg_user_inactive = _make_pg_user('bob', is_active=False, is_admin=False, role='user')

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [pg_user_active, pg_user_inactive]

        with patch('app.services.user_management_service.USE_POSTGRES', True), \
             patch('app.services.user_management_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.user_management_service.db_session_scope', return_value=_make_ctx(mock_session)):
            result = svc._load_registry()

        assert 'alice' in result['added_users']
        assert 'bob' in result['added_users']
        assert 'bob' in result['deleted_users']
        assert result['admin_overrides'].get('alice') is True
        assert result['roles'].get('alice') == 'admin'

    def test_load_registry_falls_back_to_json_on_pg_error(self):
        """Bei PG-Fehler wird JSON-Fallback aufgerufen."""
        svc = _make_service()

        fallback_data = {
            'added_users': {'charlie': True},
            'deleted_users': [],
            'admin_overrides': {},
            'roles': {'charlie': 'berater'}
        }

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = fallback_data

        with patch('app.services.user_management_service.USE_POSTGRES', True), \
             patch('app.services.user_management_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.user_management_service.db_session_scope', return_value=_make_error_ctx()), \
             patch('app.services.user_management_service.data_persistence', mock_dp):
            result = svc._load_registry()

        assert 'charlie' in result['added_users']
        assert result['roles']['charlie'] == 'berater'

    def test_load_registry_uses_json_when_postgres_disabled(self):
        """Mit USE_POSTGRES=False wird direkt JSON gelesen."""
        svc = _make_service()

        json_data = {
            'added_users': {'dave': True},
            'deleted_users': [],
            'admin_overrides': {},
            'roles': {'dave': 'telefonist'}
        }

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = json_data

        with patch('app.services.user_management_service.USE_POSTGRES', False), \
             patch('app.services.user_management_service.data_persistence', mock_dp):
            result = svc._load_registry()

        assert 'dave' in result['added_users']
        mock_dp.load_data.assert_called_once()


# ---------------------------------------------------------------------------
# _save_registry — Dual-Write
# ---------------------------------------------------------------------------

class TestSaveRegistry:
    """Tests fuer _save_registry Dual-Write."""

    def test_save_registry_writes_to_pg_and_json(self):
        """Dual-Write: PG-Update + JSON-Write werden beide ausgefuehrt."""
        svc = _make_service()

        registry = {
            'added_users': {'alice': True},
            'deleted_users': [],
            'admin_overrides': {'alice': True},
            'roles': {'alice': 'admin'}
        }

        pg_user = _make_pg_user('alice', is_active=True, is_admin=False, role='user')
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = pg_user

        mock_dp = MagicMock()

        with patch('app.services.user_management_service.USE_POSTGRES', True), \
             patch('app.services.user_management_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.user_management_service.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.user_management_service.data_persistence', mock_dp):
            svc._save_registry(registry)

        # PG: is_admin und role wurden gesetzt
        assert pg_user.is_admin is True
        assert pg_user.role == 'admin'
        # JSON write immer
        mock_dp.save_data.assert_called_once()

    def test_save_registry_json_write_even_on_pg_error(self):
        """JSON-Write findet auch bei PG-Fehler statt."""
        svc = _make_service()

        registry = {
            'added_users': {},
            'deleted_users': ['eve'],
            'admin_overrides': {},
            'roles': {}
        }

        mock_dp = MagicMock()

        with patch('app.services.user_management_service.USE_POSTGRES', True), \
             patch('app.services.user_management_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.user_management_service.db_session_scope', return_value=_make_error_ctx()), \
             patch('app.services.user_management_service.data_persistence', mock_dp):
            svc._save_registry(registry)

        # JSON wird trotzdem geschrieben
        mock_dp.save_data.assert_called_once()

    def test_save_registry_sets_is_active_false_for_deleted(self):
        """User in deleted_users bekommt is_active=False in PG."""
        svc = _make_service()

        registry = {
            'added_users': {},
            'deleted_users': ['frank'],
            'admin_overrides': {},
            'roles': {'frank': 'user'}
        }

        pg_user = _make_pg_user('frank', is_active=True)
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = pg_user

        mock_dp = MagicMock()

        with patch('app.services.user_management_service.USE_POSTGRES', True), \
             patch('app.services.user_management_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.user_management_service.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.user_management_service.data_persistence', mock_dp):
            svc._save_registry(registry)

        assert pg_user.is_active is False


# ---------------------------------------------------------------------------
# add_user — PG INSERT
# ---------------------------------------------------------------------------

class TestAddUser:
    """Tests fuer add_user mit PG-Sync."""

    def _patch_add_user(self, svc, mock_session, mock_dp, existing_pg_user=None):
        """Gemeinsame Patch-Konfiguration fuer add_user Tests."""
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_pg_user

        registry_data = {
            'added_users': {},
            'deleted_users': [],
            'admin_overrides': {},
            'roles': {}
        }

        def load_data_side_effect(key, default=None):
            if key == 'user_registry':
                return registry_data
            if key == 'user_passwords':
                return {}
            return default or {}

        mock_dp.load_data.side_effect = load_data_side_effect
        mock_dp.load_scores.return_value = {}

        return registry_data

    def test_add_user_inserts_into_pg(self):
        """Neuer User wird in PG insertiert."""
        svc = _make_service()
        mock_session = MagicMock()
        mock_dp = MagicMock()

        self._patch_add_user(svc, mock_session, mock_dp)

        with patch('app.services.user_management_service.USE_POSTGRES', True), \
             patch('app.services.user_management_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.user_management_service.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.user_management_service.data_persistence', mock_dp), \
             patch.object(svc, '_get_all_usernames', return_value=[]), \
             patch.object(svc, '_load_registry', return_value={
                 'added_users': {}, 'deleted_users': [], 'admin_overrides': {}, 'roles': {}
             }), \
             patch.object(svc, '_save_registry'), \
             patch('app.services.user_management_service.security_service') as mock_sec, \
             patch('app.services.user_management_service.audit_service'):
            mock_sec.hash_password.return_value = 'hashed_pw'
            success, msg = svc.add_user('newuser', 'password123', False, 'admin')

        assert success is True
        assert mock_session.add.called

    def test_add_user_updates_existing_pg_user(self):
        """Wenn User bereits in PG vorhanden, wird er aktualisiert statt neu eingefuegt."""
        svc = _make_service()
        mock_session = MagicMock()
        mock_dp = MagicMock()

        existing = _make_pg_user('existinguser', is_active=False)
        self._patch_add_user(svc, mock_session, mock_dp, existing_pg_user=existing)

        with patch('app.services.user_management_service.USE_POSTGRES', True), \
             patch('app.services.user_management_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.user_management_service.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.user_management_service.data_persistence', mock_dp), \
             patch.object(svc, '_get_all_usernames', return_value=[]), \
             patch.object(svc, '_load_registry', return_value={
                 'added_users': {}, 'deleted_users': [], 'admin_overrides': {}, 'roles': {}
             }), \
             patch.object(svc, '_save_registry'), \
             patch('app.services.user_management_service.security_service') as mock_sec, \
             patch('app.services.user_management_service.audit_service'):
            mock_sec.hash_password.return_value = 'hashed_pw'
            success, msg = svc.add_user('existinguser', 'password123', False, 'admin')

        assert success is True
        assert existing.is_active is True
        assert not mock_session.add.called

    def test_add_user_no_pg_write_when_disabled(self):
        """Mit USE_POSTGRES=False kein PG-Write."""
        svc = _make_service()
        mock_session = MagicMock()
        mock_dp = MagicMock()

        self._patch_add_user(svc, mock_session, mock_dp)

        with patch('app.services.user_management_service.USE_POSTGRES', False), \
             patch('app.services.user_management_service.data_persistence', mock_dp), \
             patch.object(svc, '_get_all_usernames', return_value=[]), \
             patch.object(svc, '_load_registry', return_value={
                 'added_users': {}, 'deleted_users': [], 'admin_overrides': {}, 'roles': {}
             }), \
             patch.object(svc, '_save_registry'), \
             patch('app.services.user_management_service.security_service') as mock_sec, \
             patch('app.services.user_management_service.audit_service'):
            mock_sec.hash_password.return_value = 'hashed_pw'
            success, msg = svc.add_user('offlineuser', 'password123', False, 'admin')

        assert success is True
        assert not mock_session.add.called


# ---------------------------------------------------------------------------
# delete_user — PG Soft-Delete
# ---------------------------------------------------------------------------

class TestDeleteUser:
    """Tests fuer delete_user mit PG Soft-Delete."""

    def test_delete_user_sets_is_active_false_in_pg(self):
        """delete_user setzt is_active=False in PG."""
        svc = _make_service()

        pg_user = _make_pg_user('victim', is_active=True)
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = pg_user

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.user_management_service.USE_POSTGRES', True), \
             patch('app.services.user_management_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.user_management_service.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.user_management_service.data_persistence', mock_dp), \
             patch.object(svc, '_get_all_usernames', return_value=['victim', 'admin']), \
             patch.object(svc, '_load_registry', return_value={
                 'added_users': {'victim': True, 'admin': True},
                 'deleted_users': [],
                 'admin_overrides': {'admin': True},
                 'roles': {'victim': 'user', 'admin': 'admin'}
             }), \
             patch.object(svc, '_save_registry'), \
             patch('app.services.user_management_service.audit_service'):
            success, msg = svc.delete_user('victim', 'admin')

        assert success is True
        assert pg_user.is_active is False

    def test_delete_user_no_pg_write_when_disabled(self):
        """Mit USE_POSTGRES=False kein PG-Write."""
        svc = _make_service()

        pg_user = _make_pg_user('victim', is_active=True)
        mock_session = MagicMock()

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.user_management_service.USE_POSTGRES', False), \
             patch('app.services.user_management_service.data_persistence', mock_dp), \
             patch.object(svc, '_get_all_usernames', return_value=['victim', 'admin']), \
             patch.object(svc, '_load_registry', return_value={
                 'added_users': {'victim': True, 'admin': True},
                 'deleted_users': [],
                 'admin_overrides': {'admin': True},
                 'roles': {}
             }), \
             patch.object(svc, '_save_registry'), \
             patch('app.services.user_management_service.audit_service'):
            success, msg = svc.delete_user('victim', 'admin')

        assert success is True
        # pg_user.is_active unberuehrt — kein PG-Zugriff
        assert pg_user.is_active is True
        assert not mock_session.query.called

    def test_delete_user_cannot_delete_self(self):
        """User kann sich nicht selbst loeschen."""
        svc = _make_service()
        success, msg = svc.delete_user('admin', 'admin')
        assert success is False
        assert 'selbst' in msg


# ---------------------------------------------------------------------------
# reset_password — PG password_hash Update
# ---------------------------------------------------------------------------

class TestResetPassword:
    """Tests fuer reset_password mit PG-Sync."""

    def test_reset_password_updates_pg_hash(self):
        """reset_password schreibt password_hash in PG."""
        svc = _make_service()

        pg_user = _make_pg_user('alice')
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = pg_user

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.user_management_service.USE_POSTGRES', True), \
             patch('app.services.user_management_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.user_management_service.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.user_management_service.data_persistence', mock_dp), \
             patch.object(svc, '_get_all_usernames', return_value=['alice']), \
             patch('app.services.user_management_service.security_service') as mock_sec, \
             patch('app.services.user_management_service.audit_service'):
            mock_sec.hash_password.return_value = 'new_hash'
            success, msg, new_pw = svc.reset_password('alice', 'admin')

        assert success is True
        assert pg_user.password_hash == 'new_hash'
        assert len(new_pw) > 0

    def test_reset_password_no_pg_write_when_disabled(self):
        """Mit USE_POSTGRES=False kein PG-Write."""
        svc = _make_service()

        pg_user = _make_pg_user('alice')
        pg_user.password_hash = 'old_hash'
        mock_session = MagicMock()

        mock_dp = MagicMock()
        mock_dp.load_data.return_value = {}

        with patch('app.services.user_management_service.USE_POSTGRES', False), \
             patch('app.services.user_management_service.data_persistence', mock_dp), \
             patch.object(svc, '_get_all_usernames', return_value=['alice']), \
             patch('app.services.user_management_service.security_service') as mock_sec, \
             patch('app.services.user_management_service.audit_service'):
            mock_sec.hash_password.return_value = 'new_hash'
            success, msg, new_pw = svc.reset_password('alice', 'admin')

        assert success is True
        # pg_user unberuehrt
        assert pg_user.password_hash == 'old_hash'
        assert not mock_session.query.called
