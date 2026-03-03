# -*- coding: utf-8 -*-
"""
Finanzberatung Blueprint Package - Financial Advisory Document Analysis

Blueprint Structure:
- sessions.py: Session CRUD, status transitions, notes management
- upload.py: Token-based upload, file validation, QR code generation
- sse.py: Server-Sent Events for real-time upload progress

All sub-blueprints register under /finanzberatung prefix.
Upload sub-blueprint is CSRF-exempted (external customer uploads via QR token).
"""

from flask import Blueprint

from app.config.base import FinanzConfig as finanz_config

# Parent blueprint
finanzberatung_bp = Blueprint(
    'finanzberatung', __name__, url_prefix='/finanzberatung'
)


def init_app(app):
    """
    Register Finanzberatung sub-blueprints with Flask app.

    Called from app factory when FINANZ_ENABLED=true.
    Sub-blueprint imports are lazy (inside function body) to avoid
    circular imports and to allow graceful startup when sub-blueprint
    files do not yet exist.

    Args:
        app: Flask application instance

    Returns:
        finanzberatung_bp: Configured Finanzberatung parent blueprint
    """
    # Lazy imports -- sub-blueprint files are created in Plans 02-03
    try:
        from .sessions import sessions_bp
        finanzberatung_bp.register_blueprint(sessions_bp, url_prefix='')
    except ImportError:
        app.logger.warning("Finanzberatung sessions sub-blueprint not yet available")

    try:
        from .upload import upload_bp
        finanzberatung_bp.register_blueprint(upload_bp, url_prefix='')

        # CSRF exemption for upload blueprint (external customer uploads via QR token)
        from app.core.extensions import csrf
        if csrf:
            csrf.exempt(upload_bp)
    except ImportError:
        app.logger.warning("Finanzberatung upload sub-blueprint not yet available")

    try:
        from .sse import sse_bp
        finanzberatung_bp.register_blueprint(sse_bp, url_prefix='')
    except ImportError:
        app.logger.warning("Finanzberatung SSE sub-blueprint not yet available")

    try:
        from .admin import admin_bp
        finanzberatung_bp.register_blueprint(admin_bp, url_prefix='')
    except ImportError:
        app.logger.warning("Finanzberatung admin sub-blueprint not yet available")

    # Register parent blueprint with app
    app.register_blueprint(finanzberatung_bp)

    app.logger.info("Finanzberatung blueprint registered")
    mode = "live" if finanz_config.FINANZ_LLM_ENABLED else "mock"
    app.logger.info("Finanzberatung LLM mode: %s", mode)
    return finanzberatung_bp
