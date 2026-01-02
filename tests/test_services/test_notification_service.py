# -*- coding: utf-8 -*-
"""
Service Layer Tests - Notification Service
Tests for app/services/notification_service.py (260 lines)
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock
import uuid


# ========== FIXTURES ==========

@pytest.fixture
def notification_service():
    """Create NotificationService instance"""
    from app.services.notification_service import NotificationService
    return NotificationService()


@pytest.fixture
def mock_notifications_data():
    """Mock notifications data"""
    return {
        "test.user": [
            {
                "id": "notif-001",
                "type": "info",
                "title": "Test Notification 1",
                "message": "This is test notification 1",
                "timestamp": "2026-01-01T10:00:00",
                "read": False,
                "dismissed": False,
                "show_popup": True,
                "roles": ["admin"],
                "actions": []
            },
            {
                "id": "notif-002",
                "type": "success",
                "title": "Test Notification 2",
                "message": "This is test notification 2",
                "timestamp": "2026-01-02T11:00:00",
                "read": True,
                "dismissed": False,
                "show_popup": False,
                "roles": ["admin"],
                "actions": [{"text": "View", "url": "/test"}]
            },
            {
                "id": "notif-003",
                "type": "warning",
                "title": "Dismissed Notification",
                "message": "This is dismissed",
                "timestamp": "2026-01-03T12:00:00",
                "read": False,
                "dismissed": True,
                "show_popup": False,
                "roles": ["admin"],
                "actions": []
            }
        ],
        "alexander.nehm": [
            {
                "id": "notif-004",
                "type": "error",
                "title": "Error Notification",
                "message": "Something went wrong",
                "timestamp": "2026-01-04T13:00:00",
                "read": False,
                "dismissed": False,
                "show_popup": True,
                "roles": ["admin", "closer"],
                "actions": []
            }
        ]
    }


# ========== TEST CLASSES ==========

@pytest.mark.service
class TestRoleMapping:
    """Tests for role-based user mapping"""

    def test_get_users_by_roles_admin(self, notification_service):
        """Test getting admin users"""
        users = notification_service._get_users_by_roles(['admin'])

        assert isinstance(users, list)
        assert 'alexander.nehm' in users
        assert 'david.nehm' in users
        assert 'simon.mast' in users
        assert 'luke.hoppe' in users

    def test_get_users_by_roles_multiple(self, notification_service):
        """Test getting users from multiple roles"""
        users = notification_service._get_users_by_roles(['admin', 'coach'])

        assert isinstance(users, list)
        # Admin + Coach users (deduplicated)
        assert 'alexander.nehm' in users  # Both admin and coach
        assert 'david.nehm' in users
        assert 'jose.torspecken' in users  # Coach only

    def test_get_users_by_roles_all(self, notification_service):
        """Test 'all' role returns all users"""
        users = notification_service._get_users_by_roles(['all'])

        assert isinstance(users, list)
        assert len(users) > 10  # Should have many users
        # Check some users from different roles
        assert 'alexander.nehm' in users
        assert 'ann-kathrin.welge' in users
        assert 'alexandra.börner' in users

    def test_get_users_by_roles_unknown_role(self, notification_service):
        """Test unknown role returns empty list"""
        users = notification_service._get_users_by_roles(['unknown_role'])

        assert users == []

    def test_get_users_by_roles_deduplication(self, notification_service):
        """Test users are deduplicated across roles"""
        # alexander.nehm is in admin, closer, and coach
        users = notification_service._get_users_by_roles(['admin', 'closer', 'coach'])

        assert isinstance(users, list)
        # Count occurrences - should only appear once
        assert users.count('alexander.nehm') == 1


@pytest.mark.service
class TestCreateNotification:
    """Tests for creating notifications"""

    def test_create_notification_success(self, notification_service):
        """Test successful notification creation"""
        with patch.object(notification_service, '_load_all_notifications', return_value={}):
            with patch.object(notification_service, '_save_all_notifications') as mock_save:

                result = notification_service.create_notification(
                    roles=['admin'],
                    title='Test Title',
                    message='Test Message',
                    notification_type='info',
                    show_popup=True
                )

                # Should create for all admin users
                assert isinstance(result, dict)
                assert len(result) == 4  # 4 admin users
                assert 'alexander.nehm' in result
                assert mock_save.called

    def test_create_notification_with_actions(self, notification_service):
        """Test notification with action buttons"""
        with patch.object(notification_service, '_load_all_notifications', return_value={}):
            with patch.object(notification_service, '_save_all_notifications') as mock_save:

                actions = [
                    {'text': 'View Details', 'url': '/details'},
                    {'text': 'Dismiss', 'url': '/dismiss'}
                ]

                result = notification_service.create_notification(
                    roles=['coach'],
                    title='New Feature',
                    message='Check out the new feature',
                    notification_type='success',
                    show_popup=True,
                    actions=actions
                )

                # Verify save was called with correct data
                saved_data = mock_save.call_args[0][0]
                # Check one of the coach users
                assert 'jose.torspecken' in saved_data
                assert len(saved_data['jose.torspecken'][0]['actions']) == 2

    def test_create_notification_all_roles(self, notification_service):
        """Test notification for 'all' roles"""
        with patch.object(notification_service, '_load_all_notifications', return_value={}):
            with patch.object(notification_service, '_save_all_notifications') as mock_save:

                result = notification_service.create_notification(
                    roles=['all'],
                    title='System Maintenance',
                    message='System will be down',
                    notification_type='warning'
                )

                # Should create for many users
                assert len(result) > 10

    def test_create_notification_no_users(self, notification_service):
        """Test notification with unknown role (no users)"""
        with patch.object(notification_service, '_load_all_notifications', return_value={}):
            with patch.object(notification_service, '_save_all_notifications') as mock_save:

                result = notification_service.create_notification(
                    roles=['unknown_role'],
                    title='Test',
                    message='Message'
                )

                # Should return empty dict
                assert result == {}
                # Should not save
                assert not mock_save.called


@pytest.mark.service
class TestGetNotifications:
    """Tests for retrieving notifications"""

    def test_get_user_notifications_all(self, notification_service, mock_notifications_data):
        """Test getting all non-dismissed notifications"""
        with patch.object(notification_service, '_load_all_notifications', return_value=mock_notifications_data):

            result = notification_service.get_user_notifications('test.user')

            # Should get 2 notifications (notif-003 is dismissed)
            assert len(result) == 2
            assert result[0]['id'] == 'notif-002'  # Sorted by timestamp (newest first)
            assert result[1]['id'] == 'notif-001'

    def test_get_user_notifications_popup_only(self, notification_service, mock_notifications_data):
        """Test filtering for popup notifications only"""
        with patch.object(notification_service, '_load_all_notifications', return_value=mock_notifications_data):

            result = notification_service.get_user_notifications(
                'test.user',
                show_popup_only=True
            )

            # Only notif-001 has show_popup=True
            assert len(result) == 1
            assert result[0]['id'] == 'notif-001'
            assert result[0]['show_popup'] is True

    def test_get_user_notifications_unread_only(self, notification_service, mock_notifications_data):
        """Test filtering for unread notifications only"""
        with patch.object(notification_service, '_load_all_notifications', return_value=mock_notifications_data):

            result = notification_service.get_user_notifications(
                'test.user',
                unread_only=True
            )

            # Only notif-001 is unread (notif-002 is read, notif-003 is dismissed)
            assert len(result) == 1
            assert result[0]['id'] == 'notif-001'
            assert result[0]['read'] is False

    def test_get_user_notifications_empty(self, notification_service):
        """Test getting notifications for user with none"""
        with patch.object(notification_service, '_load_all_notifications', return_value={}):

            result = notification_service.get_user_notifications('new.user')

            assert result == []


@pytest.mark.service
class TestMarkAsRead:
    """Tests for marking notifications as read"""

    def test_mark_as_read_success(self, notification_service, mock_notifications_data):
        """Test successfully marking notification as read"""
        with patch.object(notification_service, '_load_all_notifications', return_value=mock_notifications_data.copy()):
            with patch.object(notification_service, '_save_all_notifications') as mock_save:

                result = notification_service.mark_as_read('test.user', 'notif-001')

                assert result is True
                # Verify notification was marked as read
                saved_data = mock_save.call_args[0][0]
                notif = next(n for n in saved_data['test.user'] if n['id'] == 'notif-001')
                assert notif['read'] is True

    def test_mark_as_read_not_found(self, notification_service, mock_notifications_data):
        """Test marking non-existent notification"""
        with patch.object(notification_service, '_load_all_notifications', return_value=mock_notifications_data):
            with patch.object(notification_service, '_save_all_notifications') as mock_save:

                result = notification_service.mark_as_read('test.user', 'invalid-id')

                assert result is False
                # Should not save
                assert not mock_save.called

    def test_mark_all_as_read(self, notification_service, mock_notifications_data):
        """Test marking all notifications as read"""
        with patch.object(notification_service, '_load_all_notifications', return_value=mock_notifications_data.copy()):
            with patch.object(notification_service, '_save_all_notifications') as mock_save:

                count = notification_service.mark_all_as_read('test.user')

                # Should mark 1 notification (notif-001), notif-002 already read, notif-003 dismissed
                assert count == 1
                assert mock_save.called


@pytest.mark.service
class TestDismissNotification:
    """Tests for dismissing notifications"""

    def test_dismiss_notification_success(self, notification_service, mock_notifications_data):
        """Test successfully dismissing notification"""
        with patch.object(notification_service, '_load_all_notifications', return_value=mock_notifications_data.copy()):
            with patch.object(notification_service, '_save_all_notifications') as mock_save:

                result = notification_service.dismiss_notification('test.user', 'notif-001')

                assert result is True
                # Verify notification was dismissed
                saved_data = mock_save.call_args[0][0]
                notif = next(n for n in saved_data['test.user'] if n['id'] == 'notif-001')
                assert notif['dismissed'] is True

    def test_dismiss_notification_not_found(self, notification_service, mock_notifications_data):
        """Test dismissing non-existent notification"""
        with patch.object(notification_service, '_load_all_notifications', return_value=mock_notifications_data):
            with patch.object(notification_service, '_save_all_notifications') as mock_save:

                result = notification_service.dismiss_notification('test.user', 'invalid-id')

                assert result is False
                assert not mock_save.called


@pytest.mark.service
class TestUnreadCount:
    """Tests for unread notification count"""

    def test_get_unread_count(self, notification_service, mock_notifications_data):
        """Test getting unread count"""
        with patch.object(notification_service, '_load_all_notifications', return_value=mock_notifications_data):

            count = notification_service.get_unread_count('test.user')

            # Only notif-001 is unread (and not dismissed)
            assert count == 1

    def test_get_unread_count_zero(self, notification_service):
        """Test unread count for user with no notifications"""
        with patch.object(notification_service, '_load_all_notifications', return_value={}):

            count = notification_service.get_unread_count('new.user')

            assert count == 0
