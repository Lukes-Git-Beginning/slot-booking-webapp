# -*- coding: utf-8 -*-
"""
Development configuration
"""

from .base import Config


class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    TESTING = False

    # Use local persist directory for development
    PERSIST_BASE = "data/persistent"

    # Development-specific logging
    LOG_LEVEL = "DEBUG"