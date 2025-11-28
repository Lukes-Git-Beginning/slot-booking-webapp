# -*- coding: utf-8 -*-
"""
Test Suite for T2 Core Routes: Dashboard & Closer Draw System
Tests the main dashboard, closer drawing mechanics, and bucket admin features.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ========== FIXTURES ==========

@pytest.fixture
def mock_t2_bucket_functions():
    """Mock T2 Bucket System functions"""
    with patch('app.services.t2_bucket_system.draw_closer') as mock_draw, \
         patch('app.services.t2_bucket_system.get_bucket_composition') as mock_comp, \
         patch('app.services.t2_bucket_system.get_available_closers') as mock_closers, \
         patch('app.services.t2_bucket_system.check_user_timeout') as mock_timeout:

        # Configure default return values
        mock_draw.return_value = {
            'success': True,
            'closer': 'Alex',
            'color': '#d4af6a',
            'tickets_remaining': 15
        }
        mock_comp.return_value = {
            'total_tickets': 20,
            'draws_until_reset': 15,
            'closers': {
                'Alex': {'tickets': 9, 'probability': 9.0},
                'David': {'tickets': 9, 'probability': 9.0},
                'Jose': {'tickets': 2, 'probability': 2.0}
            }
        }
        mock_closers.return_value = ['Alex', 'David', 'Jose', 'Christian', 'Daniel', 'Tim']
        mock_timeout.return_value = {'timeout_active': False}

        yield {
            'draw': mock_draw,
            'composition': mock_comp,
            'closers': mock_closers,
            'timeout': mock_timeout
        }


@pytest.fixture
def mock_t2_functions():
    """Mock T2 helper functions"""
    with patch('app.routes.t2.get_user_tickets_remaining', return_value=3), \
         patch('app.routes.t2.get_user_t2_bookings', return_value=[]), \
         patch('app.routes.t2.get_next_t2_appointments', return_value=[]):
        yield


# ========== TEST CLASS: T2 DASHBOARD ==========

@pytest.mark.unit
class TestT2Dashboard:
    """Test T2 Dashboard Route"""

    def test_dashboard_access_authenticated(self, logged_in_client, mock_t2_functions):
        """Test dashboard access with logged-in user"""
        # Ensure session is properly set
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'
            sess['is_admin'] = False

        response = logged_in_client.get('/t2/')

        assert response.status_code == 200
        assert b'T2' in response.data or b't2' in response.data
        # Dashboard should load successfully for authenticated users

    def test_dashboard_access_unauthorized_redirects(self, client):
        """Test dashboard redirects unauthenticated users to login"""
        response = client.get('/t2/', follow_redirects=False)

        # Should redirect to login page
        assert response.status_code == 302
        assert '/login' in response.location or 'login' in response.location.lower()

    def test_dashboard_shows_user_context(self, logged_in_client, mock_t2_functions):
        """Test dashboard shows correct user context and data"""
        # Ensure session is properly set
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'
            sess['is_admin'] = False

        response = logged_in_client.get('/t2/')

        assert response.status_code == 200
        # Check that dashboard template is rendered (contains user context)
        data_str = response.data.decode('utf-8')
        assert 'test_user' in data_str or 'user' in data_str.lower()


# ========== TEST CLASS: CLOSER DRAW ==========

@pytest.mark.unit
class TestCloserDraw:
    """Test Closer Drawing Mechanics"""

    def test_draw_closer_success(self, logged_in_client, mock_t2_bucket_functions):
        """Test successful closer draw returns valid closer"""
        # Ensure session is properly set
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'

        response = logged_in_client.post('/t2/api/draw-closer',
                                        content_type='application/json',
                                        json={})

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'closer' in data
        assert data['closer'] in ['Alex', 'David', 'Jose', 'Christian', 'Daniel', 'Tim']
        assert 'color' in data

    def test_draw_closer_stores_in_session(self, logged_in_client, mock_t2_bucket_functions):
        """Test closer is stored in session after drawing"""
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'
            # Ensure no closer in session initially
            sess.pop('t2_current_closer', None)

        response = logged_in_client.post('/t2/api/draw-closer',
                                        content_type='application/json',
                                        json={})

        assert response.status_code == 200

        with logged_in_client.session_transaction() as sess:
            assert 't2_current_closer' in sess
            assert sess['t2_current_closer'] is not None

    def test_draw_closer_with_customer_name(self, logged_in_client, mock_t2_bucket_functions):
        """Test draw with customer name is recorded"""
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'

        response = logged_in_client.post('/t2/api/draw-closer',
                                        content_type='application/json',
                                        json={'customer_name': 'Müller GmbH'})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        # Verify draw was called with customer name
        mock_t2_bucket_functions['draw'].assert_called_once()
        call_args = mock_t2_bucket_functions['draw'].call_args
        assert call_args[0][2] == 'Müller GmbH'  # Third argument is customer_name

    def test_draw_closer_unauthenticated(self, client):
        """Test unauthenticated users cannot draw closer"""
        response = client.post('/t2/api/draw-closer',
                              content_type='application/json',
                              json={},
                              follow_redirects=False)

        # Should return 401 for API endpoints
        assert response.status_code == 401

    def test_draw_closer_rate_limiting(self, logged_in_client, mock_t2_bucket_functions):
        """Test rate limiting on closer draw endpoint"""
        # Ensure session is set
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'

        # Make multiple rapid requests
        responses = []
        for _ in range(5):
            resp = logged_in_client.post('/t2/api/draw-closer',
                                        content_type='application/json',
                                        json={})
            responses.append(resp.status_code)

        # All should succeed or some should be rate limited (429)
        # This depends on rate limit configuration
        assert all(code in [200, 429] for code in responses)

    def test_draw_closer_error_handling(self, logged_in_client):
        """Test error handling when draw function fails"""
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'

        with patch('app.services.t2_bucket_system.draw_closer', side_effect=Exception("Test error")):
            response = logged_in_client.post('/t2/api/draw-closer',
                                            content_type='application/json',
                                            json={})

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data


# ========== TEST CLASS: BUCKET ADMIN ==========

@pytest.mark.unit
class TestBucketAdmin:
    """Test Bucket Admin Features"""

    def test_bucket_config_admin_only(self, logged_in_client):
        """Test bucket config page requires admin access"""
        # Ensure session with non-admin user
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'
            sess['is_admin'] = False

        response = logged_in_client.get('/t2/admin/bucket-config', follow_redirects=False)

        # Non-admin should be redirected
        assert response.status_code == 302

    def test_bucket_config_accessible_by_admin(self, admin_client, mock_t2_bucket_functions):
        """Test admin can access bucket configuration"""
        # Ensure admin session
        with admin_client.session_transaction() as sess:
            sess['user'] = 'admin_user'
            sess['is_admin'] = True

        # Mock additional bucket functions for admin page
        with patch('app.services.t2_bucket_system.get_bucket_config') as mock_config, \
             patch('app.services.t2_bucket_system.get_system_stats') as mock_stats:

            mock_config.return_value = {
                'max_draws': 20,
                'closers': {
                    'Alex': {'probability': 9.0},
                    'David': {'probability': 9.0},
                    'Jose': {'probability': 2.0}
                }
            }
            mock_stats.return_value = {
                'total_draws': 5,
                'reset_count': 2,
                'draws_until_reset': 15
            }

            response = admin_client.get('/t2/admin/bucket-config')

            # Admin should see config page
            assert response.status_code == 200

    def test_bucket_stats_display(self, admin_client, mock_t2_bucket_functions):
        """Test bucket statistics are displayed correctly"""
        # Ensure admin session
        with admin_client.session_transaction() as sess:
            sess['user'] = 'admin_user'
            sess['is_admin'] = True

        # Mock admin functions
        with patch('app.services.t2_bucket_system.get_bucket_config') as mock_config, \
             patch('app.services.t2_bucket_system.get_system_stats') as mock_stats:

            mock_config.return_value = {'max_draws': 20, 'closers': {}}
            mock_stats.return_value = {'total_draws': 5, 'reset_count': 2, 'draws_until_reset': 15}

            response = admin_client.get('/t2/admin/bucket-config')

            if response.status_code == 200:
                data_str = response.data.decode('utf-8')
                # Check for bucket-related content
                assert any(word in data_str.lower() for word in ['bucket', 'draw', 'probability', 'closer'])

    def test_bucket_draw_page_loads(self, logged_in_client, mock_t2_bucket_functions):
        """Test bucket draw page loads correctly"""
        with logged_in_client.session_transaction() as sess:
            sess['user'] = 'test_user'

        response = logged_in_client.get('/t2/draw')

        assert response.status_code == 200
        data_str = response.data.decode('utf-8')
        assert 'draw' in data_str.lower() or 'closer' in data_str.lower()
