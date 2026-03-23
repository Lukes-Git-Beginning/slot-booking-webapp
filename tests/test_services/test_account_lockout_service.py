# -*- coding: utf-8 -*-
"""
Service Layer Tests - Account Lockout Service
Tests for app/services/account_lockout.py
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


# ========== FIXTURES ==========

@pytest.fixture
def lockout_service():
    """Create AccountLockoutService instance with PG disabled"""
    with patch.dict('os.environ', {'USE_POSTGRES': 'false'}):
        from app.services.account_lockout import AccountLockoutService
        return AccountLockoutService()


@pytest.fixture
def empty_lockout_data():
    return {}


@pytest.fixture
def locked_account_data():
    locked_until = (datetime.now() + timedelta(minutes=30)).isoformat()
    return {
        'testuser': {
            'failed_attempts': 5,
            'first_attempt': datetime.now().isoformat(),
            'last_attempt': datetime.now().isoformat(),
            'locked_until': locked_until
        }
    }


@pytest.fixture
def expired_lockout_data():
    locked_until = (datetime.now() - timedelta(minutes=5)).isoformat()
    return {
        'testuser': {
            'failed_attempts': 5,
            'first_attempt': datetime.now().isoformat(),
            'last_attempt': datetime.now().isoformat(),
            'locked_until': locked_until
        }
    }


# ========== TESTS: is_locked_out ==========

class TestIsLockedOut:
    def test_unknown_user_not_locked(self, lockout_service):
        with patch.object(lockout_service, '_load_lockout_data', return_value={}):
            is_locked, minutes = lockout_service.is_locked_out('unknown')
            assert is_locked is False
            assert minutes is None

    def test_active_lock_returns_true(self, lockout_service, locked_account_data):
        with patch.object(lockout_service, '_load_lockout_data', return_value=locked_account_data), \
             patch.object(lockout_service, '_save_lockout_data'):
            is_locked, minutes = lockout_service.is_locked_out('testuser')
            assert is_locked is True
            assert minutes is not None
            assert minutes > 0

    def test_expired_lock_returns_false(self, lockout_service, expired_lockout_data):
        with patch.object(lockout_service, '_load_lockout_data', return_value=expired_lockout_data), \
             patch.object(lockout_service, '_save_lockout_data'):
            is_locked, minutes = lockout_service.is_locked_out('testuser')
            assert is_locked is False
            assert minutes is None


# ========== TESTS: record_failed_attempt ==========

class TestRecordFailedAttempt:
    def test_first_attempt_not_locked(self, lockout_service):
        saved = {}

        def mock_save(data):
            saved.update(data)

        with patch.object(lockout_service, '_load_lockout_data', return_value={}), \
             patch.object(lockout_service, '_save_lockout_data', side_effect=mock_save):
            is_locked, duration = lockout_service.record_failed_attempt('newuser')
            assert is_locked is False
            assert duration is None
            assert 'newuser' in saved
            assert saved['newuser']['failed_attempts'] == 1

    def test_tier1_lockout(self, lockout_service):
        """Nach max_attempts_tier1 Versuchen wird Tier-1-Sperre ausgeloest"""
        tier1 = lockout_service.max_attempts_tier1
        existing = {
            'testuser': {
                'failed_attempts': tier1 - 1,
                'first_attempt': datetime.now().isoformat(),
                'last_attempt': datetime.now().isoformat(),
                'locked_until': None
            }
        }
        saved = {}

        def mock_save(data):
            saved.update(data)

        with patch.object(lockout_service, '_load_lockout_data', return_value=existing), \
             patch.object(lockout_service, '_save_lockout_data', side_effect=mock_save):
            is_locked, duration = lockout_service.record_failed_attempt('testuser')
            assert is_locked is True
            assert duration == lockout_service.lockout_duration_tier1


# ========== TESTS: check_and_record_failure ==========

class TestCheckAndRecordFailure:
    def test_already_locked_returns_locked(self, lockout_service, locked_account_data):
        with patch.object(lockout_service, '_load_lockout_data', return_value=locked_account_data):
            result, minutes = lockout_service.check_and_record_failure('testuser')
            assert result == 'locked'
            assert minutes is not None

    def test_new_failure_returns_failed(self, lockout_service):
        with patch.object(lockout_service, '_load_lockout_data', return_value={}), \
             patch.object(lockout_service, '_save_lockout_data'):
            result, _ = lockout_service.check_and_record_failure('newuser')
            assert result == 'failed'

    def test_tier1_lockout_returns_now_locked(self, lockout_service):
        tier1 = lockout_service.max_attempts_tier1
        existing = {
            'testuser': {
                'failed_attempts': tier1 - 1,
                'first_attempt': datetime.now().isoformat(),
                'last_attempt': datetime.now().isoformat(),
                'locked_until': None
            }
        }
        with patch.object(lockout_service, '_load_lockout_data', return_value=existing), \
             patch.object(lockout_service, '_save_lockout_data'):
            result, duration = lockout_service.check_and_record_failure('testuser')
            assert result == 'now_locked'
            assert duration == lockout_service.lockout_duration_tier1


# ========== TESTS: record_successful_login ==========

class TestRecordSuccessfulLogin:
    def test_clears_failed_attempts(self, lockout_service, locked_account_data):
        saved = {}

        def mock_save(data):
            saved.update(data)

        with patch.object(lockout_service, '_load_lockout_data', return_value=locked_account_data), \
             patch.object(lockout_service, '_save_lockout_data', side_effect=mock_save):
            lockout_service.record_successful_login('testuser')
            assert 'testuser' not in saved

    def test_no_op_for_unknown_user(self, lockout_service):
        with patch.object(lockout_service, '_load_lockout_data', return_value={}), \
             patch.object(lockout_service, '_save_lockout_data') as mock_save:
            lockout_service.record_successful_login('unknown')
            mock_save.assert_not_called()


# ========== TESTS: admin_unlock ==========

class TestAdminUnlock:
    def test_unlock_existing_account(self, lockout_service, locked_account_data):
        saved = {}

        def mock_save(data):
            saved.update(data)

        with patch.object(lockout_service, '_load_lockout_data', return_value=locked_account_data), \
             patch.object(lockout_service, '_save_lockout_data', side_effect=mock_save):
            result = lockout_service.admin_unlock('testuser')
            assert result is True
            assert 'testuser' not in saved

    def test_unlock_unknown_returns_false(self, lockout_service):
        with patch.object(lockout_service, '_load_lockout_data', return_value={}):
            result = lockout_service.admin_unlock('nobody')
            assert result is False


# ========== TESTS: get_all_locked_accounts ==========

class TestGetAllLockedAccounts:
    def test_returns_active_locks(self, lockout_service, locked_account_data):
        with patch.object(lockout_service, '_load_lockout_data', return_value=locked_account_data):
            accounts = lockout_service.get_all_locked_accounts()
            assert len(accounts) == 1
            assert accounts[0]['username'] == 'testuser'
            assert accounts[0]['minutes_remaining'] > 0

    def test_excludes_expired_locks(self, lockout_service, expired_lockout_data):
        with patch.object(lockout_service, '_load_lockout_data', return_value=expired_lockout_data):
            accounts = lockout_service.get_all_locked_accounts()
            assert len(accounts) == 0

    def test_empty_when_no_data(self, lockout_service):
        with patch.object(lockout_service, '_load_lockout_data', return_value={}):
            accounts = lockout_service.get_all_locked_accounts()
            assert accounts == []


# ========== TESTS: Dual-Write (PG disabled) ==========

class TestDualWriteDisabled:
    """Stellt sicher dass Service mit USE_POSTGRES=false korrekt auf JSON-Fallback faellt"""

    def test_load_falls_back_to_json(self, lockout_service):
        mock_data = {'user1': {'failed_attempts': 1, 'first_attempt': None, 'last_attempt': None, 'locked_until': None}}
        with patch('app.services.account_lockout.USE_POSTGRES', False), \
             patch('app.services.account_lockout.data_persistence') as mock_dp:
            mock_dp.load_data.return_value = mock_data
            result = lockout_service._load_lockout_data()
            mock_dp.load_data.assert_called_once_with(lockout_service.lockout_file, {})
            assert result == mock_data

    def test_save_writes_json_only(self, lockout_service):
        data = {'user1': {'failed_attempts': 3, 'first_attempt': None, 'last_attempt': None, 'locked_until': None}}
        with patch('app.services.account_lockout.USE_POSTGRES', False), \
             patch('app.services.account_lockout.data_persistence') as mock_dp:
            lockout_service._save_lockout_data(data)
            mock_dp.save_data.assert_called_once_with(lockout_service.lockout_file, data)
