# -*- coding: utf-8 -*-
"""
Timezone Utilities
Provides timezone-safe datetime operations with UTC normalization.

This module ensures consistent datetime handling across the application
by normalizing all datetime comparisons to UTC, avoiding issues with
different timezone representations (pytz vs. explicit offsets).
"""

from datetime import datetime, timedelta
from typing import Optional
import pytz
import logging

logger = logging.getLogger(__name__)

# Central timezone configuration
BERLIN_TZ = pytz.timezone('Europe/Berlin')
UTC_TZ = pytz.UTC


def now_utc() -> datetime:
    """
    Get current time in UTC.

    Returns:
        datetime: Current UTC time (timezone-aware)

    Example:
        >>> now = now_utc()
        >>> now.tzinfo
        <UTC>
    """
    return datetime.now(UTC_TZ)


def parse_iso_to_utc(iso_string: str) -> datetime:
    """
    Parse ISO timestamp string to UTC datetime.

    Handles multiple ISO formats and ensures backward compatibility:
    - Explicit offset: "2025-12-05T16:43:51.610017+01:00"
    - UTC notation: "2025-12-05T15:43:51Z"
    - Naive datetime (assumes Berlin TZ): "2025-12-05 15:43:51"

    Args:
        iso_string: ISO 8601 formatted datetime string

    Returns:
        datetime: UTC datetime (timezone-aware)

    Raises:
        ValueError: If iso_string cannot be parsed

    Example:
        >>> dt = parse_iso_to_utc("2025-12-05T16:43:51+01:00")
        >>> dt.tzinfo
        <UTC>
        >>> dt.isoformat()
        '2025-12-05T15:43:51+00:00'
    """
    if not iso_string:
        raise ValueError("ISO string cannot be empty")

    try:
        # Handle 'Z' notation (UTC)
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'

        # Parse ISO string
        dt = datetime.fromisoformat(iso_string)

        # Handle naive datetime (no timezone info)
        if dt.tzinfo is None:
            logger.debug(f"Naive datetime detected, assuming Berlin TZ: {iso_string}")
            dt = BERLIN_TZ.localize(dt)

        # Convert to UTC
        dt_utc = dt.astimezone(UTC_TZ)

        logger.debug(f"Parsed '{iso_string}' to UTC: {dt_utc.isoformat()}")
        return dt_utc

    except Exception as e:
        logger.error(f"Failed to parse ISO string '{iso_string}': {e}")
        raise ValueError(f"Invalid ISO datetime format: {iso_string}") from e


def to_utc(dt: datetime) -> datetime:
    """
    Convert any datetime to UTC.

    Args:
        dt: Timezone-aware or naive datetime

    Returns:
        datetime: UTC datetime (timezone-aware)

    Raises:
        ValueError: If dt is naive and no source timezone can be assumed

    Example:
        >>> berlin_dt = BERLIN_TZ.localize(datetime(2025, 12, 5, 16, 43))
        >>> utc_dt = to_utc(berlin_dt)
        >>> utc_dt.hour
        15
    """
    if dt is None:
        raise ValueError("Datetime cannot be None")

    # Handle naive datetime
    if dt.tzinfo is None:
        logger.warning(f"Naive datetime provided, assuming Berlin TZ: {dt}")
        dt = BERLIN_TZ.localize(dt)

    # Convert to UTC
    return dt.astimezone(UTC_TZ)


def to_berlin_tz(dt: datetime) -> datetime:
    """
    Convert datetime to Berlin timezone.

    Useful for display purposes and generating human-readable timestamps.

    Args:
        dt: Timezone-aware datetime

    Returns:
        datetime: Berlin timezone datetime

    Example:
        >>> utc_dt = datetime(2025, 12, 5, 15, 43, tzinfo=UTC_TZ)
        >>> berlin_dt = to_berlin_tz(utc_dt)
        >>> berlin_dt.hour
        16
    """
    if dt is None:
        raise ValueError("Datetime cannot be None")

    # Handle naive datetime
    if dt.tzinfo is None:
        logger.warning(f"Naive datetime provided, assuming UTC: {dt}")
        dt = UTC_TZ.localize(dt)

    # Convert to Berlin TZ
    return dt.astimezone(BERLIN_TZ)


def format_berlin_iso(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as ISO string in Berlin timezone.

    Args:
        dt: Datetime to format (defaults to current time)

    Returns:
        str: ISO 8601 formatted string with Berlin timezone offset

    Example:
        >>> format_berlin_iso(datetime(2025, 12, 5, 15, 43, tzinfo=UTC_TZ))
        '2025-12-05T16:43:00+01:00'
    """
    if dt is None:
        dt = now_utc()

    berlin_dt = to_berlin_tz(dt)
    return berlin_dt.isoformat()


def safe_timedelta(
    dt1: datetime,
    dt2: datetime,
    abs_value: bool = False
) -> timedelta:
    """
    Calculate timedelta between two datetimes safely.

    Normalizes both datetimes to UTC before subtraction to avoid
    timezone-related arithmetic issues.

    Args:
        dt1: First datetime
        dt2: Second datetime
        abs_value: If True, return absolute value of timedelta

    Returns:
        timedelta: dt1 - dt2 (or absolute value)

    Example:
        >>> dt1 = parse_iso_to_utc("2025-12-05T16:43:51+01:00")
        >>> dt2 = parse_iso_to_utc("2025-12-05T15:43:51Z")
        >>> delta = safe_timedelta(dt1, dt2)
        >>> delta.total_seconds()
        0.0
    """
    if dt1 is None or dt2 is None:
        raise ValueError("Both datetimes must be provided")

    # Normalize to UTC
    dt1_utc = to_utc(dt1)
    dt2_utc = to_utc(dt2)

    # Calculate delta
    delta = dt1_utc - dt2_utc

    return abs(delta) if abs_value else delta


def is_timeout_active(
    last_action_time: datetime,
    timeout_seconds: int,
    current_time: Optional[datetime] = None
) -> tuple[bool, int]:
    """
    Check if a timeout period is still active.

    Args:
        last_action_time: When the last action occurred
        timeout_seconds: Timeout duration in seconds
        current_time: Current time (defaults to now_utc())

    Returns:
        tuple: (is_active, seconds_remaining)
            - is_active: True if timeout is still active
            - seconds_remaining: Seconds until timeout expires (0 if expired)

    Example:
        >>> last_draw = parse_iso_to_utc("2025-12-05T16:43:51+01:00")
        >>> # 3 days later
        >>> is_active, remaining = is_timeout_active(last_draw, 60)
        >>> is_active
        False
        >>> remaining
        0
    """
    if current_time is None:
        current_time = now_utc()

    # Normalize to UTC
    last_action_utc = to_utc(last_action_time)
    current_utc = to_utc(current_time)

    # Calculate time elapsed
    time_since_action = current_utc - last_action_utc
    seconds_elapsed = int(time_since_action.total_seconds())

    # Check if timeout is active
    if seconds_elapsed < timeout_seconds:
        return True, timeout_seconds - seconds_elapsed
    else:
        return False, 0
