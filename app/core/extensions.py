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
hubspot_service = None  # HubSpot CRM Integration
limiter = None
csrf = None  # CSRF Protection
sess = None  # Flask-Session with Redis


def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions and external services"""
    global cache_manager, data_persistence, error_handler, level_system, tracking_system, hubspot_service, limiter, csrf, sess

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
        data_persistence.validate_data_integrity()
        data_persistence.validate_scores_integrity()
    except Exception as e:
        logger.warning(f"Persistenz-Init Hinweis", extra={'error': str(e)})

    # Pre-hash USERLIST passwords to eliminate plaintext fallback
    try:
        from app.services.security_service import security_service
        security_service.migrate_userlist_passwords()
    except Exception as e:
        logger.warning(f"USERLIST password migration skipped: {e}")

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
        _verify_tracking_write_access(tracking_system)

        # Tracking-Luecken erkennen
        try:
            gaps = tracking_system.detect_tracking_gaps(lookback_days=14)
            if gaps:
                logger.warning(f"Tracking gaps on startup: {len(gaps)} missing workdays")
        except Exception as gap_err:
            logger.debug(f"Gap detection skipped: {gap_err}")

    except Exception as e:
        logger.warning(f"Could not initialize tracking system", extra={'error': str(e)})
        tracking_system = None

    # Initialize HubSpot CRM Integration (graceful degradation)
    try:
        from app.services.hubspot_service import hubspot_service as hs
        hubspot_service = hs
        hubspot_service.init_app(app)
    except Exception as e:
        logger.info(f"HubSpot integration not initialized: {e}")
        hubspot_service = None

    # Initialize CSRF Protection (Security Critical)
    try:
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect(app)
        logger.info("CSRF protection initialized successfully")
    except Exception as e:
        logger.error(f"CRITICAL: Could not initialize CSRF protection: {e}")
        csrf = None

    # Initialize Flask-Limiter for rate limiting (security)
    import os
    if os.getenv('TESTING', '').lower() in ('true', '1'):
        limiter = None
        logger.info("Rate limiting disabled in test mode")
    else:
        try:
            from flask_limiter import Limiter
            from flask_limiter.util import get_remote_address
            from app.utils.rate_limiting import init_rate_limiter, handle_rate_limit_error

            # Use Redis for rate limiting if available
            redis_url = os.getenv('REDIS_URL')
            storage_uri = redis_url if redis_url else "memory://"

            limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                default_limits=["10000 per day", "500 per hour"],
                storage_uri=storage_uri,
                strategy="fixed-window"
            )

            # Register custom error handler
            app.errorhandler(429)(handle_rate_limit_error)

            # Initialize rate limiting module
            init_rate_limiter(limiter)

            if redis_url:
                logger.info("Rate limiting initialized with Redis backend")
            else:
                logger.info("Rate limiting initialized with memory backend")
        except Exception as e:
            logger.warning(f"Could not initialize rate limiter", extra={'error': str(e)})
            limiter = None

    # Initialize Flask-Session with Redis backend (if available)
    init_session_storage(app)

    # Initialize Celery task queue (graceful degradation if Redis unavailable)
    try:
        from app.core.celery_init import celery_init_app
        celery_app = celery_init_app(app)

        # Auto-discover task modules
        celery_app.autodiscover_tasks(['app.services'], related_name='finanz_tasks')
    except Exception as e:
        logger.info(f"Celery not initialized: {e}")

    logger.info("All extensions initialized successfully")


def _verify_tracking_write_access(tracker) -> None:
    """Proaktiver Startup-Check: Sind Tracking-Dateien beschreibbar?"""
    import os
    paths_to_check = [
        tracker.data_dir,
        tracker.bookings_file,
        tracker.outcomes_file,
    ]
    problems = []
    for path in paths_to_check:
        if os.path.exists(path) and not os.access(path, os.W_OK):
            problems.append(path)

    if problems:
        msg = f"TRACKING WRITE ACCESS DENIED: {', '.join(problems)}"
        logger.critical(msg)
        try:
            from app.services.notification_service import notification_service
            notification_service.create_notification(
                roles=['admin'],
                title='Tracking-Dateien nicht beschreibbar!',
                message=f'Folgende Pfade sind nicht beschreibbar: {", ".join(problems)}. '
                        f'Bitte Dateiberechtigungen prüfen (chown www-data:www-data).',
                notification_type='error',
                show_popup=True
            )
        except Exception:
            pass
    else:
        logger.info("Tracking write access verified OK")


def _install_save_session_guard(app: Flask) -> None:
    """Wrap save_session to prevent empty sessions from overwriting valid Redis data.

    An empty session (only '_permanent') typically means Redis had a read hiccup
    and Flask-Session created a blank session with the same SID. Saving it would
    destroy the real user data. This guard skips the save in that case.
    """
    iface = app.session_interface
    original_save = iface.save_session

    def guarded_save_session(sa_app, sa_session, response):
        meaningful_keys = [k for k in sa_session if k not in ('_permanent', '_id')]
        if not meaningful_keys:
            # Session has no user data — don't persist to Redis
            sid = getattr(sa_session, 'sid', 'unknown')
            logger.debug(
                "save_session guard: skipping save for empty session sid=%s",
                str(sid)[:8] + '...',
            )
            return
        return original_save(sa_app, sa_session, response)

    iface.save_session = guarded_save_session
    logger.info("Session save guard installed — empty sessions will not overwrite Redis")


def init_session_storage(app: Flask) -> None:
    """Initialize Flask-Session with Redis backend (if available)"""
    global sess
    import os

    redis_url = os.getenv('REDIS_URL')

    if redis_url:
        try:
            from flask_session import Session
            import redis

            # Configure Flask-Session to use Redis
            app.config['SESSION_TYPE'] = 'redis'
            app.config['SESSION_PERMANENT'] = True
            app.config['SESSION_USE_SIGNER'] = True
            app.config['SESSION_KEY_PREFIX'] = 'session:'

            # Create Redis connection for sessions
            app.config['SESSION_REDIS'] = redis.from_url(
                redis_url,
                decode_responses=False,  # Store pickled session data
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # Verify Redis is actually reachable (from_url is lazy)
            app.config['SESSION_REDIS'].ping()

            # Initialize Flask-Session
            sess = Session(app)

            # CRITICAL: Guard save_session to prevent empty sessions from
            # overwriting valid user data in Redis. When Redis has a brief
            # read timeout, open_session() returns an empty session with the
            # same SID. Without this guard, save_session() would persist
            # that empty session, permanently destroying the user's login.
            _install_save_session_guard(app)

            logger.info("Redis session storage activated")

            # Also update Flask-Limiter to use Redis
            global limiter
            if limiter:
                logger.info("Flask-Limiter switched to Redis backend")

        except Exception as e:
            logger.warning(f"WARNING: Redis session unavailable, falling back to filesystem sessions: {e}")
            _init_filesystem_session(app)
    else:
        logger.info("REDIS_URL not set, using filesystem sessions")
        _init_filesystem_session(app)


def _init_filesystem_session(app: Flask) -> None:
    """Initialize filesystem-backed sessions with a persistent directory"""
    global sess
    import os

    session_dir = os.path.join(app.config.get('PERSIST_BASE', 'data'), 'sessions')
    os.makedirs(session_dir, exist_ok=True)

    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = session_dir
    app.config['SESSION_FILE_THRESHOLD'] = 500
    app.config['SESSION_PERMANENT'] = True

    try:
        from flask_session import Session
        sess = Session(app)
        logger.info(f"Filesystem session storage activated: {session_dir}")
    except ImportError:
        sess = None
        logger.info("Flask-Session not installed, using default cookie sessions")