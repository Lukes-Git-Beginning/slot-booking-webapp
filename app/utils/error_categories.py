# -*- coding: utf-8 -*-
"""
Error Categories
Standardized error categorization for consistent error handling
"""

from enum import Enum


class ErrorCategory(Enum):
    """Error categories for user-facing error messages"""

    # User-fixable errors
    VALIDATION = "validation"
    SLOT_FULL = "slot_full"
    SLOT_LOCKED = "slot_locked"
    HOLIDAY_BLOCKED = "holiday_blocked"

    # Calendar API errors
    CALENDAR_QUOTA = "calendar_quota"
    CALENDAR_RATE_LIMIT = "calendar_rate_limit"
    CALENDAR_NETWORK = "calendar_network"
    CALENDAR_INVALID_DATA = "calendar_invalid_data"
    CALENDAR_UNAVAILABLE = "calendar_unavailable"

    # Tracking errors
    TRACKING_FAILED = "tracking_failed"

    # Authentication/Authorization
    CSRF_TOKEN = "csrf_token"
    SESSION_EXPIRED = "session_expired"

    # System errors
    DATABASE = "database"
    INTERNAL = "internal"
    CONFIGURATION = "configuration"
