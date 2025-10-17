# -*- coding: utf-8 -*-
"""
Flask extensions initialization
Centralizes all external integrations
"""

from flask import Flask
from typing import Optional
import logging

# Logger setup
logger = logging.getLogger(__name__)

# Global instances that will be initialized in init_extensions
cache_manager = None
data_persistence = None
error_handler = None
level_system = None
tracking_system = None
limiter = None


def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions and external services"""
    global cache_manager, data_persistence, error_handler, level_system, tracking_system, limiter

    # Import and initialize cache manager
    from app.core.cache_manager import cache_manager as cm
    cache_manager = cm

    # Import and initialize data persistence
    from app.services.data_persistence import data_persistence as dp
    data_persistence = dp

    # Initialize data persistence from static if missing
    try:
        data_persistence.bootstrap_from_static_if_missing()
        data_persistence.auto_cleanup_backups()
    except Exception as e:
        logger.warning(f"Persistenz-Init Hinweis", extra={'error': str(e)})

    # Import and initialize error handler
    from app.utils.error_handler import error_handler as eh
    error_handler = eh
    error_handler.init_app(app)

    # Import and initialize level system
    from app.services.level_system import level_system as ls
    level_system = ls

    # Import and initialize tracking system
    try:
        from app.services.tracking_system import BookingTracker
        tracking_system = BookingTracker()
    except Exception as e:
        logger.warning(f"Could not initialize tracking system", extra={'error': str(e)})
        tracking_system = None

    # Initialize Flask-Limiter for rate limiting (security)
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        from app.utils.rate_limiting import init_rate_limiter, handle_rate_limit_error

        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["10000 per day", "500 per hour"],
            storage_uri="memory://",  # In-memory storage (use Redis for production scaling)
            strategy="fixed-window"
        )

        # Register custom error handler
        app.errorhandler(429)(handle_rate_limit_error)

        # Initialize rate limiting module
        init_rate_limiter(limiter)

        logger.info("Rate limiting initialized successfully")
    except Exception as e:
        logger.warning(f"Could not initialize rate limiter", extra={'error': str(e)})
        limiter = None

    logger.info("All extensions initialized successfully")