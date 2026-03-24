# -*- coding: utf-8 -*-
"""
Flask middleware and request processing
"""

from flask import Flask, session, redirect, url_for, request, make_response
from functools import wraps
import logging
from app.config.base import config

# Logger setup
logger = logging.getLogger(__name__)


def init_middleware(app: Flask) -> None:
    """Initialize middleware for the Flask app"""

    @app.before_request
    def require_login():
        """Check if user is logged in for protected routes"""
        # List of endpoints that don't require login
        public_endpoints = [
            'auth.login',
            'main.favicon',
            'static',
            # Health check endpoints (no auth required for monitoring)
            'health.health_check',
            'health.readiness_check',
            'health.liveness_check',
            'health.metrics',
            'health.ping'
        ]

        # Allow access to public endpoints
        if request.endpoint in public_endpoints:
            return

        # Also allow health checks via URL path (in case endpoint name differs)
        if request.path.startswith('/health'):
            return

        # Allow public finanzberatung upload routes (token-based auth, no login)
        if request.path.startswith('/finanzberatung/upload/'):
            return

        # SSE endpoints have their own @require_login decorator.
        # Excluding them prevents the redirect → save_session loop that
        # overwrites Redis with an empty session on every SSE reconnect.
        if request.path.startswith('/finanzberatung/sse/'):
            return

        # Logout clears the session itself — middleware must not interfere
        if request.path == '/logout':
            return

        # Check if user is logged in
        if 'user' not in session or not session.get('user'):
            sid = getattr(session, 'sid', 'unknown')
            is_new = getattr(session, 'new', 'unknown')
            logger.warning(
                "Session invalid - sid: %s, new: %s, keys: %s, Path: %s, IP: %s",
                str(sid)[:8] + '...', is_new, list(session.keys()),
                request.path, request.remote_addr
            )

            # CRITICAL: Prevent Flask-Session from overwriting a potentially
            # valid Redis session with this empty session data.
            # If Redis had a read hiccup, open_session() returns an empty
            # session with the same SID — saving it would destroy the real data.
            session.clear()
            resp = make_response(redirect('/login'))
            resp.delete_cookie(
                app.config.get('SESSION_COOKIE_NAME', 'session'),
                path='/',
                domain=app.config.get('SESSION_COOKIE_DOMAIN'),
            )
            return resp

    logger.info("Middleware initialized successfully")


def require_admin(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user not in config.get_admin_users():
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function


def require_login_decorator(f):
    """Decorator for login requirement (alternative to middleware)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session.get('user'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function