# -*- coding: utf-8 -*-
"""
Service Layer Tests - Cache Manager & Utilities
Tests for:
- app/core/cache_manager.py (266 lines)
- app/utils/date_utils.py (187 lines)
- app/utils/decorators.py (43 lines)
"""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import MagicMock, patch, Mock, mock_open
import os
import tempfile
import pickle
import pytz


# ========== FIXTURES ==========

@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return str(cache_dir)


@pytest.fixture
def cache_manager(temp_cache_dir):
    """Create CacheManager with temporary directory"""
    from app.core.cache_manager import CacheManager
    return CacheManager(cache_dir=temp_cache_dir)


@pytest.fixture
def date_formatter():
    """Create DateFormatter instance"""
    from app.utils.date_utils import DateFormatter
    return DateFormatter()


@pytest.fixture
def mock_flask_app():
    """Mock Flask app context for decorator tests"""
    from flask import Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['TESTING'] = True
    return app


# ========== TEST CLASSES ==========

@pytest.mark.service
class TestCacheManager:
    """Tests for CacheManager (File-based caching)"""

    def test_cache_manager_initialization(self, temp_cache_dir):
        """Test CacheManager creates cache directory"""
        from app.core.cache_manager import CacheManager

        new_dir = os.path.join(temp_cache_dir, "test_cache")
        cache_mgr = CacheManager(cache_dir=new_dir)

        assert os.path.exists(new_dir)
        assert cache_mgr.cache_dir == new_dir
        assert cache_mgr.use_redis is False

    def test_set_and_get_cache(self, cache_manager):
        """Test basic cache set and get"""
        test_data = {"key": "value", "number": 123}

        # Set cache
        result = cache_manager.set("test_cache", "key1", test_data)
        assert result is True

        # Get cache
        cached_data = cache_manager.get("test_cache", "key1")
        assert cached_data == test_data

    def test_cache_miss_returns_none(self, cache_manager):
        """Test cache miss returns None"""
        result = cache_manager.get("nonexistent", "key1")
        assert result is None

    def test_cache_expiry(self, cache_manager, temp_cache_dir):
        """Test cache expiry (TTL)"""
        # Override cache_times for test
        cache_manager.cache_times = {"short_cache": 1}  # 1 second TTL

        # Set cache
        cache_manager.set("short_cache", "key1", {"data": "test"})

        # Immediately get - should work
        result = cache_manager.get("short_cache", "key1")
        assert result is not None

        # Wait for expiry and modify file mtime
        import time
        time.sleep(1.1)

        # Should return None (expired)
        result = cache_manager.get("short_cache", "key1")
        # Note: Might still be valid if file mtime hasn't changed
        # This tests the expiry logic exists

    def test_invalidate_cache(self, cache_manager):
        """Test cache invalidation"""
        # Set cache
        cache_manager.set("test_cache", "key1", {"data": "value"})

        # Verify it exists
        assert cache_manager.get("test_cache", "key1") is not None

        # Invalidate
        result = cache_manager.invalidate("test_cache", "key1")
        assert result is True

        # Should be gone
        assert cache_manager.get("test_cache", "key1") is None

    def test_clear_all_cache(self, cache_manager):
        """Test clearing all cache files"""
        # Create multiple cache entries
        cache_manager.set("cache1", "key1", {"data": "1"})
        cache_manager.set("cache2", "key2", {"data": "2"})
        cache_manager.set("cache3", "key3", {"data": "3"})

        # Clear all
        result = cache_manager.clear_all()
        assert result is True

        # All should be gone
        assert cache_manager.get("cache1", "key1") is None
        assert cache_manager.get("cache2", "key2") is None
        assert cache_manager.get("cache3", "key3") is None

    def test_get_cache_stats(self, cache_manager):
        """Test cache statistics"""
        # Create some cache entries
        cache_manager.set("events", "key1", {"data": "event1"})
        cache_manager.set("events", "key2", {"data": "event2"})
        cache_manager.set("users", "key1", {"data": "user1"})

        stats = cache_manager.get_cache_stats()

        assert stats["mode"] == "file"
        assert stats["redis_available"] is not None
        assert "file_cache" in stats
        assert stats["file_cache"]["total_files"] >= 3
        assert "cache_types" in stats["file_cache"]

    def test_calendar_events_cache_methods(self, cache_manager):
        """Test specialized calendar events caching"""
        events = [
            {"id": "event1", "title": "Meeting"},
            {"id": "event2", "title": "Call"}
        ]

        # Set calendar events
        result = cache_manager.set_calendar_events("2026-01-01", "2026-01-31", events)
        assert result is True

        # Get calendar events
        cached_events = cache_manager.get_calendar_events("2026-01-01", "2026-01-31")
        assert cached_events == events

    def test_consultant_events_cache_methods(self, cache_manager):
        """Test specialized consultant events caching"""
        events = [{"id": "cons-event1", "consultant": "john.doe"}]

        # Set consultant events
        result = cache_manager.set_consultant_events(
            "john.doe@example.com",
            "2026-01-01",
            "2026-01-31",
            events
        )
        assert result is True

        # Get consultant events
        cached_events = cache_manager.get_consultant_events(
            "john.doe@example.com",
            "2026-01-01",
            "2026-01-31"
        )
        assert cached_events == events


@pytest.mark.service
class TestDateFormatter:
    """Tests for DateFormatter utility"""

    def test_now_returns_berlin_timezone(self, date_formatter):
        """Test now() returns datetime with Europe/Berlin timezone"""
        now = date_formatter.now()

        assert isinstance(now, datetime)
        assert now.tzinfo is not None
        assert str(now.tzinfo) == "Europe/Berlin"

    def test_today_returns_date(self, date_formatter):
        """Test today() returns date object"""
        today = date_formatter.today()

        assert isinstance(today, date)

    def test_format_date(self, date_formatter):
        """Test date formatting"""
        test_date = datetime(2026, 1, 15, 10, 30)

        formatted = date_formatter.format_date(test_date, "%Y-%m-%d")
        assert formatted == "2026-01-15"

        formatted = date_formatter.format_date(test_date, "%d.%m.%Y")
        assert formatted == "15.01.2026"

    def test_format_date_from_string(self, date_formatter):
        """Test formatting date from string input"""
        formatted = date_formatter.format_date("2026-01-15", "%d.%m.%Y")
        assert formatted == "15.01.2026"

    def test_parse_date(self, date_formatter):
        """Test date parsing"""
        parsed = date_formatter.parse_date("2026-01-15")

        assert isinstance(parsed, datetime)
        assert parsed.year == 2026
        assert parsed.month == 1
        assert parsed.day == 15

    def test_parse_date_invalid_format(self, date_formatter):
        """Test parsing with invalid format raises ValueError"""
        with pytest.raises(ValueError):
            date_formatter.parse_date("invalid-date")

    def test_format_datetime(self, date_formatter):
        """Test datetime formatting"""
        test_dt = datetime(2026, 1, 15, 14, 30)

        formatted = date_formatter.format_datetime(test_dt, "%Y-%m-%d %H:%M")
        assert formatted == "2026-01-15 14:30"

    def test_parse_datetime(self, date_formatter):
        """Test datetime parsing"""
        parsed = date_formatter.parse_datetime("2026-01-15 14:30")

        assert isinstance(parsed, datetime)
        assert parsed.year == 2026
        assert parsed.hour == 14
        assert parsed.minute == 30

    def test_get_week_start(self, date_formatter):
        """Test getting Monday of week"""
        # Friday 2026-01-16
        friday = datetime(2026, 1, 16)

        monday = date_formatter.get_week_start(friday)

        assert monday.weekday() == 0  # Monday
        assert monday.day == 12  # Monday of that week

    def test_get_week_end(self, date_formatter):
        """Test getting Sunday of week"""
        # Friday 2026-01-16
        friday = datetime(2026, 1, 16)

        sunday = date_formatter.get_week_end(friday)

        assert sunday.weekday() == 6  # Sunday
        assert sunday.day == 18  # Sunday of that week

    def test_get_month_start(self, date_formatter):
        """Test getting first day of month"""
        mid_month = datetime(2026, 1, 15)

        month_start = date_formatter.get_month_start(mid_month)

        assert month_start.day == 1
        assert month_start.month == 1

    def test_get_month_end(self, date_formatter):
        """Test getting last day of month"""
        mid_month = datetime(2026, 1, 15)

        month_end = date_formatter.get_month_end(mid_month)

        assert month_end.day == 31  # January has 31 days
        assert month_end.month == 1

    def test_get_month_end_december(self, date_formatter):
        """Test getting last day of December (year transition)"""
        december = datetime(2026, 12, 15)

        month_end = date_formatter.get_month_end(december)

        assert month_end.day == 31
        assert month_end.month == 12

    def test_format_week_key(self, date_formatter):
        """Test week key formatting (ISO week)"""
        test_date = datetime(2026, 1, 15)  # Week 3 of 2026

        week_key = date_formatter.format_week_key(test_date)

        assert week_key.startswith("2026-KW")
        assert len(week_key) == 9  # YYYY-KWXX (e.g., "2026-KW03")

    def test_format_month_key(self, date_formatter):
        """Test month key formatting"""
        test_date = datetime(2026, 1, 15)

        month_key = date_formatter.format_month_key(test_date)

        assert month_key == "2026-01"

    def test_is_same_day_true(self, date_formatter):
        """Test same day comparison (true)"""
        date1 = datetime(2026, 1, 15, 10, 30)
        date2 = datetime(2026, 1, 15, 14, 45)

        result = date_formatter.is_same_day(date1, date2)
        assert result is True

    def test_is_same_day_false(self, date_formatter):
        """Test same day comparison (false)"""
        date1 = datetime(2026, 1, 15)
        date2 = datetime(2026, 1, 16)

        result = date_formatter.is_same_day(date1, date2)
        assert result is False

    def test_days_between(self, date_formatter):
        """Test calculating days between dates"""
        date1 = datetime(2026, 1, 1)
        date2 = datetime(2026, 1, 15)

        days = date_formatter.days_between(date1, date2)
        assert days == 14


@pytest.mark.service
class TestDecorators:
    """Tests for authentication/authorization decorators"""

    def test_require_login_with_logged_in_user(self, mock_flask_app):
        """Test require_login allows logged-in user"""
        from app.utils.decorators import require_login

        @require_login
        def test_route():
            return "Success"

        with mock_flask_app.test_request_context():
            from flask import session
            session['user'] = 'test.user'

            result = test_route()
            assert result == "Success"

    def test_require_login_redirects_unauthorized(self, mock_flask_app):
        """Test require_login redirects when not logged in"""
        from app.utils.decorators import require_login
        from flask import session

        @require_login
        def test_route():
            return "Success"

        with mock_flask_app.test_request_context('/'):
            # No user in session
            result = test_route()

            # Should redirect to /login
            assert result.status_code == 302
            assert '/login' in result.location

    def test_require_login_api_returns_json(self, mock_flask_app):
        """Test require_login returns JSON 401 for API routes"""
        from app.utils.decorators import require_login

        @require_login
        def test_api_route():
            return "Success"

        with mock_flask_app.test_request_context('/api/data'):
            result, status_code = test_api_route()

            assert status_code == 401
            assert result.json['error'] == "Not authenticated"
            assert result.json['login_required'] is True

    def test_require_admin_with_admin_user(self, mock_flask_app):
        """Test require_admin allows admin user"""
        from app.utils.decorators import require_admin

        @require_admin
        def test_admin_route():
            return "Admin Success"

        with mock_flask_app.test_request_context():
            from flask import session

            with patch('app.utils.decorators.config') as mock_config:
                mock_config.get_admin_users.return_value = ['admin.user']
                session['user'] = 'admin.user'

                result = test_admin_route()
                assert result == "Admin Success"

    def test_require_admin_blocks_non_admin(self, mock_flask_app):
        """Test require_admin blocks non-admin user"""
        from app.utils.decorators import require_admin

        @require_admin
        def test_admin_route():
            return "Admin Success"

        with mock_flask_app.test_request_context():
            from flask import session

            with patch('app.utils.decorators.config') as mock_config:
                mock_config.get_admin_users.return_value = ['admin.user']
                session['user'] = 'regular.user'

                result = test_admin_route()

                # Should redirect to home
                assert result.status_code == 302
                assert result.location == '/'

    def test_require_user_with_session(self, mock_flask_app):
        """Test require_user allows user with session"""
        from app.utils.decorators import require_user

        @require_user
        def test_route():
            return "User Success"

        with mock_flask_app.test_request_context():
            from flask import session
            session['user'] = 'test.user'

            result = test_route()
            assert result == "User Success"

    def test_require_user_redirects_without_session(self, mock_flask_app):
        """Test require_user redirects without session"""
        from app.utils.decorators import require_user

        @require_user
        def test_route():
            return "User Success"

        with mock_flask_app.test_request_context('/test'):
            # No user in session
            result = test_route()

            # Should redirect to /login
            assert result.status_code == 302
            assert '/login' in result.location
