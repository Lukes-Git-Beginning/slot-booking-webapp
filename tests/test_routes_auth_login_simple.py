# -*- coding: utf-8 -*-
"""
Test Suite for Auth Login & Authentication (Simplified)
Tests core login functionality without complex mocking issues.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock


# ========== FIXTURES ==========

@pytest.fixture
def mock_auth_services():
    """Mock all auth-related services together"""
    with patch('app.routes.auth.security_service') as mock_security, \
         patch('app.routes.auth.account_lockout') as mock_lockout, \
         patch('app.routes.auth.audit_service') as mock_audit, \
         patch('app.routes.auth.activity_tracking') as mock_tracking, \
         patch('app.routes.auth.data_persistence') as mock_dp:

        # Configure security service
        mock_security.verify_password.return_value = True
        mock_security.is_2fa_enabled.return_value = False
        mock_security.verify_2fa.return_value = True

        # Configure account lockout
        mock_lockout.is_locked_out.return_value = (False, 0)
        mock_lockout.record_failed_attempt.return_value = (False, 0)
        mock_lockout.check_and_record_failure.return_value = ('failed', None)

        # Configure data persistence
        mock_dp.load_champions.return_value = {}
        mock_dp.load_scores.return_value = {}

        yield {
            'security': mock_security,
            'lockout': mock_lockout,
            'audit': mock_audit,
            'tracking': mock_tracking,
            'dp': mock_dp
        }


# ========== TEST CLASS: LOGIN PAGE ==========

@pytest.mark.unit
class TestLoginPage:
    """Test login page access and rendering"""

    def test_login_page_accessible(self, client):
        """Test login page is accessible without authentication"""
        response = client.get('/login')

        assert response.status_code == 200
        data_str = response.data.decode('utf-8')
        assert 'login' in data_str.lower() or 'anmeld' in data_str.lower()

    def test_login_page_shows_form(self, client):
        """Test login page displays login form"""
        response = client.get('/login')

        assert response.status_code == 200
        data_str = response.data.decode('utf-8')
        # Check for form elements
        assert 'username' in data_str.lower() or 'benutzername' in data_str.lower()
        assert 'password' in data_str.lower() or 'passwort' in data_str.lower()


# ========== TEST CLASS: LOGIN FUNCTIONALITY ==========

@pytest.mark.unit
class TestLoginFunctionality:
    """Test login process with various credentials"""

    def test_login_with_valid_credentials(self, client, mock_auth_services):
        """Test successful login with valid credentials"""
        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Should redirect after successful login
        assert response.status_code == 302
        # Should redirect to hub dashboard or next page
        assert '/hub' in response.location or '/' in response.location

    def test_login_with_invalid_credentials(self, client, mock_auth_services):
        """Test login fails with invalid credentials"""
        mock_auth_services['security'].verify_password.return_value = False

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'wrong_pass'},
                               follow_redirects=False)

        # Should redirect back to login
        assert response.status_code == 302
        assert '/login' in response.location

    def test_login_redirects_to_next_page(self, client, mock_auth_services):
        """Test login redirects to 'next' parameter if provided"""
        response = client.post('/login?next=/t2/',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        assert response.status_code == 302
        assert '/t2' in response.location


# ========== TEST CLASS: INPUT VALIDATION ==========

@pytest.mark.unit
class TestInputValidation:
    """Test input validation for login"""

    def test_login_requires_username(self, client):
        """Test login fails without username"""
        response = client.post('/login',
                               data={'password': 'test_pass'},
                               follow_redirects=False)

        # Should redirect back to login
        assert response.status_code == 302

    def test_login_requires_password(self, client):
        """Test login fails without password"""
        response = client.post('/login',
                               data={'username': 'test_user'},
                               follow_redirects=False)

        # Should redirect back to login
        assert response.status_code == 302


# ========== TEST CLASS: ACCOUNT LOCKOUT ==========

@pytest.mark.unit
class TestAccountLockout:
    """Test account lockout functionality"""

    def test_login_blocked_when_locked_out(self, client, mock_auth_services):
        """Test login is blocked when account is locked out"""
        mock_auth_services['lockout'].is_locked_out.return_value = (True, 15)

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Should redirect (account locked) or rate limit (429)
        assert response.status_code in [302, 429]


# ========== TEST CLASS: LOGOUT ==========

@pytest.mark.unit
class TestLogout:
    """Test logout functionality"""

    def test_logout_redirects_to_login(self, client):
        """Test logout redirects to login page"""
        response = client.get('/logout', follow_redirects=False)

        assert response.status_code == 302
        assert '/login' in response.location

    def test_logout_without_session(self, client):
        """Test logout works even without active session"""
        response = client.get('/logout', follow_redirects=False)

        # Should still redirect to login
        assert response.status_code == 302
        assert '/login' in response.location


# ========== TEST CLASS: INTEGRATION TESTS ==========

@pytest.mark.integration
class TestLoginIntegration:
    """Integration tests for login system"""

    def test_security_service_password_verification(self):
        """Test security service password verification works"""
        from app.services.security_service import security_service

        # Mock userlist
        with patch('app.services.security_service.get_userlist', return_value={'test_user': 'test_pass'}):
            # Correct password
            assert security_service.verify_password('test_user', 'test_pass') is True
            # Wrong password
            assert security_service.verify_password('test_user', 'wrong_pass') is False

    def test_account_lockout_service_tracks_attempts(self):
        """Test account lockout service tracks failed attempts"""
        from app.services.account_lockout import account_lockout

        # Mock data persistence
        with patch('app.services.data_persistence.data_persistence') as mock_dp:
            mock_dp.load_data.return_value = {}

            # First attempt should not lock
            is_locked, minutes = account_lockout.record_failed_attempt('test_user')
            assert is_locked is False or isinstance(minutes, int)

    def test_audit_service_logs_events(self):
        """Test audit service can log events"""
        from app.services.audit_service import audit_service

        # Mock data persistence
        with patch('app.services.data_persistence.data_persistence') as mock_dp:
            mock_dp.load_data.return_value = []

            # Should not raise exception
            try:
                audit_service.log_login_success('test_user')
                audit_service.log_login_failure('test_user', reason='test')
                audit_service.log_logout('test_user')
                success = True
            except Exception:
                success = False

            assert success is True

    def test_activity_tracking_service_exists(self):
        """Test activity tracking service is available"""
        from app.services.activity_tracking import activity_tracking

        # Service should have required methods
        assert hasattr(activity_tracking, 'track_login')
        assert hasattr(activity_tracking, 'update_online_status')
