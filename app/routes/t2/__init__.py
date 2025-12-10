# -*- coding: utf-8 -*-
"""
T2 Closer System - Modular Blueprint Structure

This maintains backward compatibility with existing endpoints via Flask blueprint nesting.
Endpoint names are preserved through url_prefix inheritance.

Blueprint Structure:
- core.py: Dashboard, health checks (5 routes)
- booking.py: Calendly booking flow (11 routes)
- bucket.py: Bucket system & closer draws (8 routes)
- admin.py: Admin config & analytics (26 routes)
- utils.py: Shared utilities

Migration Status: Phase 2 - Blueprint structure preparation
Feature Flag: T2_MODULAR_BLUEPRINTS (default: false, uses t2_legacy.py)
"""

from flask import Blueprint

# Create parent blueprint
t2_bp = Blueprint('t2', __name__, url_prefix='/t2')


def init_app(app):
    """
    Register T2 blueprints with Flask app.

    ONLY called when feature flag T2_MODULAR_BLUEPRINTS=true
    Otherwise, t2_legacy.py is used (backward compatibility).

    Args:
        app: Flask application instance

    Returns:
        t2_bp: Configured T2 parent blueprint
    """
    from .core import core_bp
    from .booking import booking_bp
    from .bucket import bucket_bp
    from .admin import admin_bp

    # Register sub-blueprints (inherits /t2 prefix from parent)
    # url_prefix='' means routes are directly under /t2 (no additional nesting)
    t2_bp.register_blueprint(core_bp, url_prefix='')
    t2_bp.register_blueprint(booking_bp, url_prefix='')
    t2_bp.register_blueprint(bucket_bp, url_prefix='')
    t2_bp.register_blueprint(admin_bp, url_prefix='')

    # Register parent blueprint with app
    app.register_blueprint(t2_bp)

    app.logger.info('✅ T2 Modular Blueprints ENABLED')
    return t2_bp
