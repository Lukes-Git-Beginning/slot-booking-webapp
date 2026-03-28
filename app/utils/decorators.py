# -*- coding: utf-8 -*-
"""
Utility decorators for authentication and authorization
"""

from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request
from app.config.base import config


def require_login(f):
    """Decorator to require user login (returns JSON for API routes)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session.get('user'):
            # For API routes (/api/*), return JSON 401 instead of redirect
            if request.path.startswith('/api/'):
                return jsonify({"error": "Not authenticated", "login_required": True}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or user not in config.get_admin_users():
            flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function


def validate_same_origin(f):
    """Decorator to validate Origin/Referer header for CSRF-exempt JSON-API routes.
    Blocks cross-origin POST/PUT/DELETE requests that don't come from our own domain."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            origin = request.headers.get('Origin') or ''
            referer = request.headers.get('Referer') or ''
            server_host = request.host  # e.g. "berater.zfa.gmbh" or "localhost:5000"

            origin_ok = False
            if origin:
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                origin_ok = parsed.netloc == server_host
            elif referer:
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                origin_ok = parsed.netloc == server_host
            else:
                # No Origin/Referer: same-origin requests from some browsers
                # (e.g. older browsers, non-CORS fetch). Allow as safe.
                origin_ok = True

            if not origin_ok:
                return jsonify({"error": "Cross-origin request blocked"}), 403
        return f(*args, **kwargs)
    return decorated_function


def require_user(f):
    """Decorator that ensures user exists in session (alternative to require_login)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function