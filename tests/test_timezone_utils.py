# -*- coding: utf-8 -*-
"""
Tests for Timezone Utilities

Tests UTC normalization, ISO parsing, and timezone-safe datetime operations.
"""

import pytest
from datetime import datetime, timedelta
import pytz

from app.utils.timezone_utils import (
    now_utc,
    parse_iso_to_utc,
    to_utc,
    to_berlin_tz,
    format_berlin_iso,
    safe_timedelta,
    is_timeout_active,
    BERLIN_TZ,
    UTC_TZ
)


class TestNowUtc:
    """Tests for now_utc() function"""

    def test_returns_utc_datetime(self):
        """Should return current time in UTC"""
        result = now_utc()
        assert result.tzinfo == UTC_TZ
        assert isinstance(result, datetime)

    def test_returns_current_time(self):
        """Should return time close to actual current time"""
        before = datetime.now(UTC_TZ)
        result = now_utc()
        after = datetime.now(UTC_TZ)

        # Should be within 1 second
        assert before <= result <= after


class TestParseIsoToUtc:
    """Tests for parse_iso_to_utc() function"""

    def test_parse_explicit_offset(self):
        """Should parse ISO string with explicit offset"""
        iso_string = "2025-12-05T16:43:51.610017+01:00"
        result = parse_iso_to_utc(iso_string)

        assert result.tzinfo == UTC_TZ
        # 16:43:51 Berlin time = 15:43:51 UTC
        assert result.hour == 15
        assert result.minute == 43

    def test_parse_utc_notation(self):
        """Should parse ISO string with Z notation"""
        iso_string = "2025-12-05T15:43:51Z"
        result = parse_iso_to_utc(iso_string)

        assert result.tzinfo == UTC_TZ
        assert result.hour == 15
        assert result.minute == 43

    def test_parse_naive_datetime(self):
        """Should parse naive datetime and assume Berlin TZ"""
        iso_string = "2025-12-05 16:43:51"
        result = parse_iso_to_utc(iso_string)

        assert result.tzinfo == UTC_TZ
        # 16:43:51 Berlin time = 15:43:51 UTC
        assert result.hour == 15

    def test_parse_with_microseconds(self):
        """Should handle microseconds correctly"""
        iso_string = "2025-12-05T16:43:51.123456+01:00"
        result = parse_iso_to_utc(iso_string)

        assert result.microsecond == 123456

    def test_parse_empty_string(self):
        """Should raise ValueError for empty string"""
        with pytest.raises(ValueError, match="ISO string cannot be empty"):
            parse_iso_to_utc("")

    def test_parse_invalid_format(self):
        """Should raise ValueError for invalid format"""
        with pytest.raises(ValueError, match="Invalid ISO datetime format"):
            parse_iso_to_utc("not a datetime")


class TestToUtc:
    """Tests for to_utc() function"""

    def test_convert_berlin_to_utc(self):
        """Should convert Berlin datetime to UTC"""
        berlin_dt = BERLIN_TZ.localize(datetime(2025, 12, 5, 16, 43))
        result = to_utc(berlin_dt)

        assert result.tzinfo == UTC_TZ
        assert result.hour == 15  # Berlin 16:00 = UTC 15:00

    def test_convert_utc_to_utc(self):
        """Should handle UTC datetime correctly"""
        utc_dt = datetime(2025, 12, 5, 15, 43, tzinfo=UTC_TZ)
        result = to_utc(utc_dt)

        assert result.tzinfo == UTC_TZ
        assert result.hour == 15

    def test_convert_naive_datetime(self):
        """Should convert naive datetime (assumes Berlin TZ)"""
        naive_dt = datetime(2025, 12, 5, 16, 43)
        result = to_utc(naive_dt)

        assert result.tzinfo == UTC_TZ
        assert result.hour == 15

    def test_none_raises_error(self):
        """Should raise ValueError for None"""
        with pytest.raises(ValueError, match="Datetime cannot be None"):
            to_utc(None)


class TestToBerlinTz:
    """Tests for to_berlin_tz() function"""

    def test_convert_utc_to_berlin(self):
        """Should convert UTC to Berlin time"""
        utc_dt = datetime(2025, 12, 5, 15, 43, tzinfo=UTC_TZ)
        result = to_berlin_tz(utc_dt)

        assert result.tzinfo.zone == "Europe/Berlin"
        assert result.hour == 16  # UTC 15:00 = Berlin 16:00

    def test_convert_berlin_to_berlin(self):
        """Should handle Berlin datetime correctly"""
        berlin_dt = BERLIN_TZ.localize(datetime(2025, 12, 5, 16, 43))
        result = to_berlin_tz(berlin_dt)

        assert result.tzinfo.zone == "Europe/Berlin"
        assert result.hour == 16

    def test_none_raises_error(self):
        """Should raise ValueError for None"""
        with pytest.raises(ValueError, match="Datetime cannot be None"):
            to_berlin_tz(None)


class TestFormatBerlinIso:
    """Tests for format_berlin_iso() function"""

    def test_format_utc_datetime(self):
        """Should format UTC datetime as Berlin ISO string"""
        utc_dt = datetime(2025, 12, 5, 15, 43, 0, tzinfo=UTC_TZ)
        result = format_berlin_iso(utc_dt)

        assert result.startswith("2025-12-05T16:43:00")
        assert "+01:00" in result or "+02:00" in result  # Depends on DST

    def test_format_none_uses_now(self):
        """Should use current time when dt is None"""
        result = format_berlin_iso(None)

        assert isinstance(result, str)
        assert "T" in result
        assert "+" in result


class TestSafeTimedelta:
    """Tests for safe_timedelta() function"""

    def test_subtract_same_time(self):
        """Should return zero delta for same time"""
        dt1 = parse_iso_to_utc("2025-12-05T16:43:51+01:00")
        dt2 = parse_iso_to_utc("2025-12-05T15:43:51Z")

        delta = safe_timedelta(dt1, dt2)
        assert delta.total_seconds() == 0

    def test_subtract_different_times(self):
        """Should calculate correct delta"""
        dt1 = parse_iso_to_utc("2025-12-05T16:00:00+01:00")
        dt2 = parse_iso_to_utc("2025-12-05T14:00:00+01:00")

        delta = safe_timedelta(dt1, dt2)
        assert delta.total_seconds() == 7200  # 2 hours

    def test_absolute_value(self):
        """Should return absolute value when requested"""
        dt1 = parse_iso_to_utc("2025-12-05T14:00:00+01:00")
        dt2 = parse_iso_to_utc("2025-12-05T16:00:00+01:00")

        delta = safe_timedelta(dt1, dt2, abs_value=True)
        assert delta.total_seconds() == 7200  # Always positive

    def test_none_raises_error(self):
        """Should raise ValueError for None"""
        dt = parse_iso_to_utc("2025-12-05T16:00:00+01:00")

        with pytest.raises(ValueError, match="Both datetimes must be provided"):
            safe_timedelta(dt, None)


class TestIsTimeoutActive:
    """Tests for is_timeout_active() function"""

    def test_timeout_expired(self):
        """Should return False when timeout has expired"""
        last_action = parse_iso_to_utc("2025-12-05T16:43:51+01:00")
        current = parse_iso_to_utc("2025-12-08T16:43:51+01:00")  # 3 days later

        is_active, remaining = is_timeout_active(last_action, 60, current)

        assert is_active is False
        assert remaining == 0

    def test_timeout_active(self):
        """Should return True when timeout is still active"""
        last_action = parse_iso_to_utc("2025-12-05T16:43:51+01:00")
        current = parse_iso_to_utc("2025-12-05T16:44:20+01:00")  # 29 seconds later

        is_active, remaining = is_timeout_active(last_action, 60, current)

        assert is_active is True
        assert remaining == 31  # 60 - 29 = 31 seconds remaining

    def test_timeout_just_expired(self):
        """Should return False when timeout just expired"""
        last_action = parse_iso_to_utc("2025-12-05T16:43:51+01:00")
        current = parse_iso_to_utc("2025-12-05T16:44:51+01:00")  # Exactly 60 seconds later

        is_active, remaining = is_timeout_active(last_action, 60, current)

        assert is_active is False
        assert remaining == 0

    def test_uses_current_time_if_none(self):
        """Should use current time if not provided"""
        last_action = now_utc() - timedelta(seconds=30)

        is_active, remaining = is_timeout_active(last_action, 60)

        assert is_active is True
        assert 25 <= remaining <= 35  # Should be around 30 seconds


class TestBackwardCompatibility:
    """Tests for backward compatibility with old timestamp formats"""

    def test_old_berlin_offset(self):
        """Should handle old Berlin offset format (+01:00)"""
        old_format = "2025-12-05T16:43:51.610017+01:00"
        result = parse_iso_to_utc(old_format)

        assert result.tzinfo == UTC_TZ
        assert isinstance(result, datetime)

    def test_mixed_timezone_comparison(self):
        """Should safely compare timestamps from different sources"""
        # Simulate old format (fromisoformat)
        old_timestamp = "2025-12-05T16:43:51+01:00"
        dt1 = parse_iso_to_utc(old_timestamp)

        # Simulate new format (Berlin TZ)
        dt2 = BERLIN_TZ.localize(datetime(2025, 12, 5, 16, 43, 51))
        dt2_utc = to_utc(dt2)

        # Should be equal
        delta = safe_timedelta(dt1, dt2_utc)
        assert delta.total_seconds() == 0

    def test_dst_transition(self):
        """Should handle DST transitions correctly"""
        # Summer time (CEST = UTC+2)
        summer = parse_iso_to_utc("2025-07-15T16:00:00+02:00")

        # Winter time (CET = UTC+1)
        winter = parse_iso_to_utc("2025-12-15T16:00:00+01:00")

        # Both should be normalized to UTC correctly
        assert summer.tzinfo == UTC_TZ
        assert winter.tzinfo == UTC_TZ
        assert summer.hour == 14  # 16:00 CEST = 14:00 UTC
        assert winter.hour == 15  # 16:00 CET = 15:00 UTC
