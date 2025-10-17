# -*- coding: utf-8 -*-
"""
Rate Limiting Utilities
Centralized rate limit decorators for all endpoints
"""

from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

# Global limiter instance (initialized in extensions.py)
_limiter = None


def init_rate_limiter(limiter):
    """Initialize global limiter reference"""
    global _limiter
    _limiter = limiter
    logger.info("Rate limiter initialized")


def get_limiter():
    """Get limiter instance"""
    return _limiter


# ========== RATE LIMIT DECORATORS ==========

def rate_limit_booking(func):
    """
    Rate limit for booking endpoints
    10 requests per minute (DOS protection)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _limiter:
            # Use limiter.limit decorator
            decorated = _limiter.limit("10 per minute", methods=["POST"])(func)
            return decorated(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper


def rate_limit_api(func):
    """
    Rate limit for API endpoints
    30 requests per minute
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _limiter:
            decorated = _limiter.limit("30 per minute")(func)
            return decorated(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper


def rate_limit_api_strict(func):
    """
    Strict rate limit for sensitive API endpoints
    10 requests per minute
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _limiter:
            decorated = _limiter.limit("10 per minute")(func)
            return decorated(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper


def rate_limit_t2(func):
    """
    Rate limit for T2 endpoints
    15 requests per minute (balanced for UX)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _limiter:
            decorated = _limiter.limit("15 per minute", methods=["POST"])(func)
            return decorated(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper


def rate_limit_admin(func):
    """
    Rate limit for admin endpoints
    50 requests per minute (higher for admin workflows)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _limiter:
            decorated = _limiter.limit("50 per minute")(func)
            return decorated(*args, **kwargs)
        return func(*args, **kwargs)
    return wrapper


# ========== ERROR HANDLERS ==========

def handle_rate_limit_error(e):
    """Custom error handler for rate limit exceeded"""
    logger.warning(f"Rate limit exceeded: {request.remote_addr} -> {request.endpoint}")

    # Return JSON for API endpoints, HTML for web endpoints
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'Zu viele Anfragen. Bitte warten Sie einen Moment.',
            'retry_after': e.description if hasattr(e, 'description') else 60
        }), 429
    else:
        # Return HTML error page
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rate Limit Exceeded</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .error-box {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 500px;
                }
                h1 { color: #d4af6a; margin: 0 0 20px 0; }
                p { color: #666; line-height: 1.6; }
                .retry-btn {
                    display: inline-block;
                    margin-top: 20px;
                    padding: 12px 30px;
                    background: #d4af6a;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    transition: background 0.3s;
                }
                .retry-btn:hover { background: #c2ae7f; }
            </style>
        </head>
        <body>
            <div class="error-box">
                <h1>⏱️ Zu viele Anfragen</h1>
                <p>Sie haben zu viele Anfragen in kurzer Zeit gesendet.</p>
                <p>Bitte warten Sie einen Moment und versuchen Sie es dann erneut.</p>
                <a href="javascript:window.history.back()" class="retry-btn">Zurück</a>
            </div>
        </body>
        </html>
        ''', 429


# ========== HELPER FUNCTIONS ==========

def get_request_identifier():
    """Get unique identifier for rate limiting (IP + User Agent)"""
    return f"{request.remote_addr}_{request.headers.get('User-Agent', 'unknown')[:50]}"


def is_rate_limited(key: str, limit: int, window: int = 60) -> bool:
    """
    Check if key is rate limited

    Args:
        key: Unique key for rate limiting
        limit: Max requests in window
        window: Time window in seconds

    Returns:
        True if rate limited, False otherwise
    """
    if not _limiter:
        return False

    # Use limiter's internal check
    try:
        return _limiter.test(key)
    except:
        return False
