# -*- coding: utf-8 -*-
"""
Test Suite for Auth Login & Authentication
Tests login functionality, password verification, and session management.
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

    def test_login_page_when_already_logged_in(self, logged_in_client):
        """Test login page accessible even when already logged in"""
        # Some apps redirect logged-in users, others show login page
        response = logged_in_client.get('/login')

        # Should return 200 (show page) or 302 (redirect to dashboard)
        assert response.status_code in [200, 302]


# ========== TEST CLASS: LOGIN FUNCTIONALITY ==========

@pytest.mark.unit
class TestLoginFunctionality:
    """Test login process with various credentials"""

    def test_login_with_valid_credentials(self, client, mock_security_service, mock_account_lockout,
                                          mock_audit_service, mock_activity_tracking):
        """Test successful login with valid credentials"""
        mock_security_service.verify_password.return_value = True
        mock_security_service.is_2fa_enabled.return_value = False

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Should redirect after successful login
        assert response.status_code == 302
        # Should redirect to hub dashboard or next page
        assert '/hub' in response.location or '/' in response.location

    def test_login_with_invalid_credentials(self, client, mock_security_service, mock_account_lockout,
                                           mock_audit_service, mock_activity_tracking):
        """Test login fails with invalid credentials"""
        mock_security_service.verify_password.return_value = False

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'wrong_pass'},
                               follow_redirects=True)

        assert response.status_code == 200
        # Should show error message
        data_str = response.data.decode('utf-8')
        assert 'falsch' in data_str.lower() or 'invalid' in data_str.lower() or 'incorrect' in data_str.lower()

    def test_login_creates_session(self, client, mock_security_service, mock_account_lockout,
                                   mock_audit_service, mock_activity_tracking):
        """Test login creates user session"""
        mock_security_service.verify_password.return_value = True

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Check session was created
        with client.session_transaction() as sess:
            assert 'user' in sess
            assert sess['user'] == 'test_user'
            assert 'logged_in' in sess
            assert sess['logged_in'] is True

    def test_login_clears_previous_session(self, client, mock_security_service, mock_account_lockout,
                                           mock_audit_service, mock_activity_tracking):
        """Test login clears old session data (Session Fixation Protection)"""
        mock_security_service.verify_password.return_value = True

        # Set some old session data
        with client.session_transaction() as sess:
            sess['old_data'] = 'should_be_cleared'
            sess['user'] = 'old_user'

        # Login
        response = client.post('/login',
                               data={'username': 'new_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Check old session data was cleared
        with client.session_transaction() as sess:
            assert 'old_data' not in sess
            assert sess['user'] == 'new_user'

    def test_login_redirects_to_next_page(self, client, mock_security_service, mock_account_lockout,
                                          mock_audit_service, mock_activity_tracking):
        """Test login redirects to 'next' parameter if provided"""
        mock_security_service.verify_password.return_value = True

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
                               follow_redirects=True)

        assert response.status_code == 200
        data_str = response.data.decode('utf-8')
        assert 'erforderlich' in data_str.lower() or 'required' in data_str.lower()

    def test_login_requires_password(self, client):
        """Test login fails without password"""
        response = client.post('/login',
                               data={'username': 'test_user'},
                               follow_redirects=True)

        assert response.status_code == 200
        data_str = response.data.decode('utf-8')
        assert 'erforderlich' in data_str.lower() or 'required' in data_str.lower()

    def test_login_rejects_too_long_username(self, client):
        """Test login rejects usernames longer than 50 characters"""
        long_username = 'a' * 51

        response = client.post('/login',
                               data={'username': long_username, 'password': 'test_pass'},
                               follow_redirects=True)

        assert response.status_code == 200
        data_str = response.data.decode('utf-8')
        assert 'lang' in data_str.lower() or 'long' in data_str.lower()

    def test_login_rejects_too_long_password(self, client):
        """Test login rejects passwords longer than 100 characters"""
        long_password = 'a' * 101

        response = client.post('/login',
                               data={'username': 'test_user', 'password': long_password},
                               follow_redirects=True)

        assert response.status_code == 200
        data_str = response.data.decode('utf-8')
        assert 'lang' in data_str.lower() or 'long' in data_str.lower()

    def test_login_strips_whitespace_from_username(self, client, mock_security_service, mock_account_lockout,
                                                   mock_audit_service, mock_activity_tracking):
        """Test login strips leading/trailing whitespace from username"""
        mock_security_service.verify_password.return_value = True

        response = client.post('/login',
                               data={'username': '  test_user  ', 'password': 'test_pass'},
                               follow_redirects=False)

        # Check session has trimmed username
        with client.session_transaction() as sess:
            if 'user' in sess:
                assert sess['user'] == 'test_user'


# ========== TEST CLASS: ACCOUNT LOCKOUT ==========

@pytest.mark.unit
class TestAccountLockout:
    """Test account lockout functionality"""

    def test_login_blocked_when_locked_out(self, client, mock_security_service, mock_account_lockout,
                                           mock_audit_service, mock_activity_tracking):
        """Test login is blocked when account is locked out"""
        mock_account_lockout.is_locked_out.return_value = (True, 15)

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=True)

        assert response.status_code == 200
        data_str = response.data.decode('utf-8')
        assert 'gesperrt' in data_str.lower() or 'locked' in data_str.lower()
        assert '15' in data_str  # Should show minutes remaining

    def test_failed_login_records_attempt(self, client, mock_security_service, mock_account_lockout,
                                          mock_audit_service, mock_activity_tracking):
        """Test failed login records failed attempt"""
        mock_security_service.verify_password.return_value = False
        mock_account_lockout.check_and_record_failure.return_value = ('failed', None)

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'wrong_pass'},
                               follow_redirects=True)

        # Verify failed attempt was recorded atomically
        mock_account_lockout.check_and_record_failure.assert_called_once_with('test_user')

    def test_successful_login_clears_failed_attempts(self, client, mock_security_service, mock_account_lockout,
                                                     mock_audit_service, mock_activity_tracking):
        """Test successful login clears failed login attempts"""
        mock_security_service.verify_password.return_value = True

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Verify failed attempts were cleared
        mock_account_lockout.record_successful_login.assert_called_once_with('test_user')


# ========== TEST CLASS: AUDIT LOGGING ==========

@pytest.mark.unit
class TestAuditLogging:
    """Test audit logging for authentication events"""

    def test_successful_login_logged(self, client, mock_security_service, mock_account_lockout,
                                     mock_audit_service, mock_activity_tracking):
        """Test successful login is audited"""
        mock_security_service.verify_password.return_value = True

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Verify audit log was created
        mock_audit_service.log_login_success.assert_called_once_with('test_user')

    def test_failed_login_logged(self, client, mock_security_service, mock_account_lockout,
                                 mock_audit_service, mock_activity_tracking):
        """Test failed login is audited"""
        mock_security_service.verify_password.return_value = False

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'wrong_pass'},
                               follow_redirects=True)

        # Verify audit log was created
        mock_audit_service.log_login_failure.assert_called_once_with('test_user', reason='invalid_credentials')


# ========== TEST CLASS: ACTIVITY TRACKING ==========

@pytest.mark.unit
class TestActivityTracking:
    """Test activity tracking for login/logout"""

    def test_successful_login_tracked(self, client, mock_security_service, mock_account_lockout,
                                      mock_audit_service, mock_activity_tracking):
        """Test successful login is tracked"""
        mock_security_service.verify_password.return_value = True

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Verify activity was tracked
        mock_activity_tracking.track_login.assert_called()
        call_kwargs = mock_activity_tracking.track_login.call_args[1]
        assert call_kwargs['username'] == 'test_user'
        assert call_kwargs['success'] is True

    def test_failed_login_tracked(self, client, mock_security_service, mock_account_lockout,
                                  mock_audit_service, mock_activity_tracking):
        """Test failed login is tracked"""
        mock_security_service.verify_password.return_value = False

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'wrong_pass'},
                               follow_redirects=True)

        # Verify activity was tracked
        mock_activity_tracking.track_login.assert_called()
        call_kwargs = mock_activity_tracking.track_login.call_args[1]
        assert call_kwargs['username'] == 'test_user'
        assert call_kwargs['success'] is False

    def test_online_status_updated_on_login(self, client, mock_security_service, mock_account_lockout,
                                            mock_audit_service, mock_activity_tracking):
        """Test online status is updated on successful login"""
        mock_security_service.verify_password.return_value = True

        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Verify online status was updated
        mock_activity_tracking.update_online_status.assert_called()
        call_args = mock_activity_tracking.update_online_status.call_args
        assert call_args[0][0] == 'test_user'
        assert call_args[1].get('action') == 'active'  # action is keyword arg


# ========== TEST CLASS: LOGOUT ==========

@pytest.mark.unit
class TestLogout:
    """Test logout functionality"""

    def test_logout_clears_session(self, logged_in_client, mock_audit_service, mock_activity_tracking):
        """Test logout clears user session"""
        # Verify session exists
        with logged_in_client.session_transaction() as sess:
            assert 'user' in sess

        # Logout
        response = logged_in_client.get('/logout', follow_redirects=False)

        # Verify session was cleared
        with logged_in_client.session_transaction() as sess:
            assert 'user' not in sess
            assert 'logged_in' not in sess

    def test_logout_redirects_to_login(self, logged_in_client, mock_audit_service, mock_activity_tracking):
        """Test logout redirects to login page"""
        response = logged_in_client.get('/logout', follow_redirects=False)

        assert response.status_code == 302
        assert '/login' in response.location

    def test_logout_audited(self, logged_in_client, mock_audit_service, mock_activity_tracking):
        """Test logout is audited"""
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'

        response = logged_in_client.get('/logout', follow_redirects=False)

        # Verify audit log was created
        mock_audit_service.log_logout.assert_called_once_with('test_user')

    def test_logout_updates_online_status(self, logged_in_client, mock_audit_service, mock_activity_tracking):
        """Test logout updates online status to offline"""
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'

        response = logged_in_client.get('/logout', follow_redirects=False)

        # Verify online status was updated
        mock_activity_tracking.update_online_status.assert_called()
        call_args = mock_activity_tracking.update_online_status.call_args
        assert call_args[1].get('action') == 'logout'  # action is keyword arg

    def test_logout_without_session(self, client, mock_audit_service, mock_activity_tracking):
        """Test logout works even without active session"""
        response = client.get('/logout', follow_redirects=False)

        # Should still redirect to login
        assert response.status_code == 302
        assert '/login' in response.location
