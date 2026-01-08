# -*- coding: utf-8 -*-
"""
Production configuration for Business Tool Hub
"""

import os
from datetime import timedelta
from .base import Config


class ProductionConfig(Config):
    """Production-specific configuration"""

    # ========================================
    # Core Flask Settings
    # ========================================
    DEBUG = False
    TESTING = False
    ENV = 'production'

    # Security: Secret Key MUST be set via environment variable
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production!")

    # ========================================
    # Session Configuration
    # ========================================
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv('SESSION_LIFETIME_HOURS', '8')))

    # ========================================
    # CSRF Protection Configuration
    # ========================================
    WTF_CSRF_ENABLED = True
    # Match CSRF token lifetime to session lifetime (8 hours = 28800 seconds)
    # Default is 3600s (1h) which causes "CSRF token expired" errors for long sessions
    WTF_CSRF_TIME_LIMIT = int(os.getenv('SESSION_LIFETIME_HOURS', '8')) * 3600
    WTF_CSRF_SSL_STRICT = True  # Require HTTPS for CSRF cookie

    # ========================================
    # Logging Configuration
    # ========================================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', '/var/log/business-hub')
    LOG_FILE = os.getenv('LOG_FILE', os.path.join(LOG_DIR, 'app.log'))

    # ========================================
    # Security Headers
    # ========================================
    # These are set in Nginx, but can be enforced here too
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(days=30)

    # ========================================
    # Performance & Caching
    # ========================================
    CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', '300'))  # 5 minutes default
    ENABLE_CACHING = os.getenv('ENABLE_CACHING', 'True').lower() in ['true', '1', 'yes']

    # ========================================
    # File Upload Settings
    # ========================================
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB

    # ========================================
    # Data Persistence
    # ========================================
    # Override base PERSIST_BASE for production
    PERSIST_BASE = os.getenv('PERSIST_BASE', '/opt/business-hub/data/persistent')
    BACKUP_DIR = os.getenv('BACKUP_DIR', '/opt/business-hub/data/backups')

    # ========================================
    # Maintenance Mode
    # ========================================
    MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'False').lower() in ['true', '1', 'yes']

    # ========================================
    # Health Checks
    # ========================================
    ENABLE_HEALTH_CHECK = os.getenv('ENABLE_HEALTH_CHECK', 'True').lower() in ['true', '1', 'yes']

    # ========================================
    # Error Handling
    # ========================================
    PROPAGATE_EXCEPTIONS = False
    TRAP_HTTP_EXCEPTIONS = True
    TRAP_BAD_REQUEST_ERRORS = True

    # ========================================
    # JSON Settings
    # ========================================
    JSON_AS_ASCII = False  # Support für deutsche Umlaute
    JSON_SORT_KEYS = False  # Performance

    # ========================================
    # Optional: External Services
    # ========================================
    SENTRY_DSN = os.getenv('SENTRY_DSN')  # Error tracking (optional)
    REDIS_URL = os.getenv('REDIS_URL')  # Cache backend (optional)