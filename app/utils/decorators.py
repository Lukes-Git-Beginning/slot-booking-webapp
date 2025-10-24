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


def require_user(f):
    """Decorator that ensures user exists in session (alternative to require_login)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function