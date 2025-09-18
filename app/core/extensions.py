# -*- coding: utf-8 -*-
"""
Flask extensions initialization
Centralizes all external integrations
"""

from flask import Flask
from typing import Optional

# Global instances that will be initialized in init_extensions
cache_manager = None
data_persistence = None
error_handler = None
level_system = None
tracking_system = None


def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions and external services"""
    global cache_manager, data_persistence, error_handler, level_system, tracking_system

    # Import and initialize cache manager
    from cache_manager import cache_manager as cm
    cache_manager = cm

    # Import and initialize data persistence
    from data_persistence import data_persistence as dp
    data_persistence = dp

    # Initialize data persistence from static if missing
    try:
        data_persistence.bootstrap_from_static_if_missing()
        data_persistence.auto_cleanup_backups()
    except Exception as e:
        print(f"WARNING: Persistenz-Init Hinweis: {e}")

    # Import and initialize error handler
    from error_handler import error_handler as eh
    error_handler = eh
    error_handler.init_app(app)

    # Import and initialize level system
    from level_system import level_system as ls
    level_system = ls

    # Import and initialize tracking system
    try:
        from tracking_system import BookingTracker
        tracking_system = BookingTracker()
    except Exception as e:
        print(f"WARNING: Could not initialize tracking system: {e}")
        tracking_system = None

    print("SUCCESS: All extensions initialized successfully")