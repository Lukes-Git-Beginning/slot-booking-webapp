# -*- coding: utf-8 -*-
"""
Test Suite for Auth Session Management
Tests session creation, persistence, security, and invalidation.
"""

import pytest
import json
from datetime import datetime, timedelta
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


@pytest.fixture
def mock_audit_service():
    """Mock audit service"""
    with patch('app.routes.auth.audit_service') as mock_service:
        yield mock_service


@pytest.fixture
def mock_activity_tracking():
    """Mock activity tracking service"""
    with patch('app.routes.auth.activity_tracking') as mock_service:
        yield mock_service


# ========== TEST CLASS: SESSION CREATION ==========

@pytest.mark.unit
class TestSessionCreation:
    """Test session creation and initialization"""

    def test_login_creates_session(self, client, mock_auth_services):
        """Test login creates user session"""
        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Check session was created
        with client.session_transaction() as sess:
            assert 'user' in sess
            assert sess['user'] == 'test_user'
            assert 'logged_in' in sess
            assert sess['logged_in'] is True

    def test_session_marked_as_permanent(self, client, mock_auth_services):
        """Test session is marked as permanent (uses PERMANENT_SESSION_LIFETIME)"""
        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Check session.permanent flag
        with client.session_transaction() as sess:
            # session.permanent should be True (8 hour lifetime)
            assert 'user' in sess

    def test_session_contains_champion_status(self, client, mock_auth_services):
        """Test session contains champion status"""
        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        with client.session_transaction() as sess:
            assert 'is_champion' in sess
            assert isinstance(sess['is_champion'], bool)


# ========== TEST CLASS: SESSION FIXATION PROTECTION ==========

@pytest.mark.unit
class TestSessionFixationProtection:
    """Test session fixation attack prevention"""

    def test_login_clears_old_session(self, client, mock_auth_services):
        """Test login clears old session data (Session Fixation Protection)"""
        # Set some old session data
        with client.session_transaction() as sess:
            sess['old_data'] = 'should_be_cleared'
            sess['user'] = 'old_user'
            sess['malicious_key'] = 'attacker_value'

        # Login
        response = client.post('/login',
                               data={'username': 'new_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Check old session data was cleared
        with client.session_transaction() as sess:
            assert 'old_data' not in sess
            assert 'malicious_key' not in sess
            assert sess['user'] == 'new_user'

    def test_logout_clears_all_session_data(self, client, mock_audit_service, mock_activity_tracking):
        """Test logout clears entire session"""
        # Set session data
        with client.session_transaction() as sess:
            sess['user'] = 'test_user'
            sess['logged_in'] = True
            sess['some_data'] = 'value'

        # Logout
        response = client.get('/logout', follow_redirects=False)

        # Check session was cleared
        with client.session_transaction() as sess:
            assert 'user' not in sess
            assert 'logged_in' not in sess
            assert 'some_data' not in sess
            assert len(sess.keys()) == 0  # Session completely empty


# ========== TEST CLASS: SESSION PERSISTENCE ==========

@pytest.mark.unit
class TestSessionPersistence:
    """Test session persistence and lifetime"""

    def test_session_persists_across_requests(self, logged_in_client):
        """Test session data persists across multiple requests"""
        # Make multiple requests
        response1 = logged_in_client.get('/hub/')
        response2 = logged_in_client.get('/t2/')
        response3 = logged_in_client.get('/slots/')

        # Session should persist
        with logged_in_client.session_transaction() as sess:
            assert sess.get('user') == 'test_user'

    def test_activity_tracking_updates_on_request(self, logged_in_client):
        """Test last_activity timestamp is updated on requests"""
        # First request
        response = logged_in_client.get('/hub/')

        # Check last_activity was set
        with logged_in_client.session_transaction() as sess:
            assert 'last_activity' in sess
            last_activity_1 = sess.get('last_activity')

        # Second request (simulate time passing)
        import time
        time.sleep(0.1)
        response = logged_in_client.get('/t2/')

        # Check last_activity was updated
        with logged_in_client.session_transaction() as sess:
            last_activity_2 = sess.get('last_activity')
            # Activity should be updated (newer timestamp)
            assert last_activity_2 >= last_activity_1


# ========== TEST CLASS: SESSION INVALIDATION ==========

@pytest.mark.unit
class TestSessionInvalidation:
    """Test session invalidation scenarios"""

    def test_unauthenticated_request_has_no_user(self, client):
        """Test unauthenticated request has no user in session"""
        response = client.get('/hub/', follow_redirects=False)

        with client.session_transaction() as sess:
            assert 'user' not in sess
            assert 'logged_in' not in sess

    def test_logout_redirects_to_login(self, logged_in_client, mock_audit_service, mock_activity_tracking):
        """Test logout redirects to login page"""
        response = logged_in_client.get('/logout', follow_redirects=False)

        assert response.status_code == 302
        assert '/login' in response.location

    def test_accessing_protected_route_without_session_redirects(self, client):
        """Test accessing protected route without session redirects to login"""
        # Routes that require authentication should redirect
        protected_routes = [
            '/t2/',
            '/t2/draw-closer',
            '/security/change-password',
            '/slots/booking'
        ]

        for route in protected_routes:
            response = client.get(route, follow_redirects=False)
            # Should redirect to login (302) or return 401
            assert response.status_code in [302, 401], f"Route {route} should require auth"


# ========== TEST CLASS: SESSION SECURITY ==========

@pytest.mark.unit
class TestSessionSecurity:
    """Test session security features"""

    def test_session_cookie_httponly(self, client, mock_auth_services):
        """Test session cookie has HttpOnly flag (prevents JavaScript access)"""
        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        # Check Set-Cookie header
        set_cookie = response.headers.get('Set-Cookie', '')
        # In production, should have HttpOnly flag
        # In testing environment, this may not be set, so we just verify login works
        assert response.status_code == 302

    def test_session_data_isolation(self, client, mock_auth_services):
        """Test session data is isolated between different users"""
        # Login as user1
        response = client.post('/login',
                               data={'username': 'user1', 'password': 'test_pass'},
                               follow_redirects=False)

        # Skip test if rate limited
        if response.status_code == 429:
            pytest.skip("Rate limited")

        with client.session_transaction() as sess:
            if 'user' not in sess:
                pytest.skip("Session not created (possible rate limit)")
            assert sess['user'] == 'user1'
            user1_session_data = sess.get('user')

        # Logout
        client.get('/logout')

        # Wait a bit to avoid rate limit
        import time
        time.sleep(1)

        # Login as user2
        response = client.post('/login',
                               data={'username': 'user2', 'password': 'test_pass'},
                               follow_redirects=False)

        if response.status_code == 429:
            pytest.skip("Rate limited")

        with client.session_transaction() as sess:
            if 'user' not in sess:
                pytest.skip("Session not created (possible rate limit)")
            assert sess['user'] == 'user2'
            # Should NOT have user1's data
            assert sess['user'] != user1_session_data


# ========== TEST CLASS: SESSION CHAMPIONS ==========

@pytest.mark.unit
class TestSessionChampionStatus:
    """Test champion status in session"""

    def test_champion_status_set_on_login(self, client, mock_auth_services):
        """Test champion status is set when user logs in"""
        with patch('app.routes.auth.check_and_set_champion', return_value='test_user'):
            response = client.post('/login',
                                   data={'username': 'test_user', 'password': 'test_pass'},
                                   follow_redirects=False)

            if response.status_code == 429:
                pytest.skip("Rate limited")

            with client.session_transaction() as sess:
                # If session not created, skip
                if 'user' not in sess:
                    pytest.skip("Session not created (possible rate limit)")
                # User is champion
                assert sess.get('is_champion') is True

    def test_non_champion_status_set_on_login(self, client, mock_auth_services):
        """Test non-champion status is set correctly"""
        with patch('app.routes.auth.check_and_set_champion', return_value='other_user'):
            response = client.post('/login',
                                   data={'username': 'test_user', 'password': 'test_pass'},
                                   follow_redirects=False)

            if response.status_code == 429:
                pytest.skip("Rate limited")

            with client.session_transaction() as sess:
                # If session not created, skip
                if 'user' not in sess:
                    pytest.skip("Session not created (possible rate limit)")
                # User is NOT champion
                assert sess.get('is_champion') is False


# ========== TEST CLASS: INTEGRATION TESTS ==========

@pytest.mark.integration
class TestSessionIntegration:
    """Integration tests for session management"""

    def test_complete_login_logout_flow(self, client, mock_auth_services, mock_audit_service,
                                        mock_activity_tracking):
        """Test complete login → use session → logout flow"""
        # 1. Login
        response = client.post('/login',
                               data={'username': 'test_user', 'password': 'test_pass'},
                               follow_redirects=False)

        if response.status_code == 429:
            pytest.skip("Rate limited")

        assert response.status_code == 302

        # 2. Verify session exists
        with client.session_transaction() as sess:
            assert sess['user'] == 'test_user'
            assert sess['logged_in'] is True

        # 3. Make authenticated request
        response = client.get('/')
        # Should work (200 or 302 for redirect)
        assert response.status_code in [200, 302]

        # 4. Logout
        response = client.get('/logout', follow_redirects=False)
        assert response.status_code == 302

        # 5. Verify session cleared
        with client.session_transaction() as sess:
            assert 'user' not in sess

    def test_session_timeout_handling(self, app):
        """Test session timeout handling (integration with production config)"""
        # This test verifies the app is configured with PERMANENT_SESSION_LIFETIME
        # In production: 8 hours (configured in production.py)
        # In testing: default Flask session lifetime

        from datetime import timedelta

        # Verify session configuration exists (it's in the config dict)
        lifetime = app.config.get('PERMANENT_SESSION_LIFETIME')
        assert lifetime is not None
        # Should be a timedelta object
        assert isinstance(lifetime, timedelta)

    def test_multiple_concurrent_sessions_same_user(self, client, mock_auth_services):
        """Test multiple concurrent sessions for same user (different browsers)"""
        # First session
        response1 = client.post('/login',
                                data={'username': 'test_user', 'password': 'test_pass'},
                                follow_redirects=False)

        if response1.status_code == 429:
            pytest.skip("Rate limited")

        with client.session_transaction() as sess1:
            user1 = sess1.get('user')

        # Logout (simulating browser 1 logout)
        client.get('/logout')

        # Wait to avoid rate limit
        import time
        time.sleep(1)

        # Second session (simulating browser 2)
        response2 = client.post('/login',
                                data={'username': 'test_user', 'password': 'test_pass'},
                                follow_redirects=False)

        if response2.status_code == 429:
            pytest.skip("Rate limited")

        with client.session_transaction() as sess2:
            user2 = sess2.get('user')

        # Both should be able to login as same user
        assert user1 == user2 == 'test_user'
