# -*- coding: utf-8 -*-
"""
Production configuration
"""

from .base import Config


class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False
    TESTING = False

    # Production logging
    LOG_LEVEL = "WARNING"

    # Security enhancements for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'