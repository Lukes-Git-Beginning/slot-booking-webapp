# -*- coding: utf-8 -*-
"""
Development configuration - Enhanced for better development experience
"""

import os
from .base import Config


class DevelopmentConfig(Config):
    """Development-specific configuration with enhanced debugging"""
    DEBUG = True
    TESTING = False

    # Use local persist directory for development
    PERSIST_BASE = "data/persistent"

    # Development-specific logging
    LOG_LEVEL = "DEBUG"

    # Enhanced development features
    DEVELOPMENT_MODE = True
    SHOW_DEBUG_INFO = True

    # Shorter cache times for development
    CACHE_TIMEOUT = 60  # 1 minute instead of 5

    # Development-specific error handling
    PROPAGATE_EXCEPTIONS = True

    # Allow longer booking window for testing
    MAX_BOOKING_DAYS_AHEAD = int(os.getenv("MAX_BOOKING_DAYS_AHEAD", "90"))