# -*- coding: utf-8 -*-
"""
Flask middleware and request processing
"""

from flask import Flask, session, redirect, url_for, request
from functools import wraps
from app.config.base import config


def init_middleware(app: Flask) -> None:
    """Initialize middleware for the Flask app"""

    @app.before_request
    def require_login():
        """Check if user is logged in for protected routes"""
        # List of endpoints that don't require login
        public_endpoints = ['auth.login', 'main.favicon', 'static']

        # Allow access to public endpoints
        if request.endpoint in public_endpoints:
            return

        # Check if user is logged in (compatible with old and new session format)
        if 'user' not in session or not session.get('user'):
            return redirect(url_for('auth.login'))

        # Also check logged_in flag for backward compatibility
        if not session.get("logged_in"):
            return redirect(url_for('auth.login'))

    print("SUCCESS: Middleware initialized successfully")


def require_admin(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user not in config.get_admin_users():
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def require_login_decorator(f):
    """Decorator for login requirement (alternative to middleware)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session.get('user'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function