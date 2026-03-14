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

from flask import Blueprint, flash, redirect, request, session, url_for

from app.config.base import FinanzConfig as finanz_config

# Parent blueprint
finanzberatung_bp = Blueprint(
    'finanzberatung', __name__, url_prefix='/finanzberatung'
)


@finanzberatung_bp.before_request
def require_finanz_access():
    """Restrict finanzberatung to openers, closers, and admins.

    Upload routes are excluded -- customers access those via token without
    login. SSE is for logged-in consultants only and is NOT excluded.
    """
    # Feature flag check
    if not finanz_config.FINANZ_ENABLED:
        flash("Finanzberatung ist nicht aktiviert", "warning")
        return redirect(url_for('hub.dashboard'))

    # Skip upload routes (customer-facing, token-based, no login required)
    endpoint = request.endpoint or ''
    if 'upload' in endpoint:
        return None

    # Require login for all other routes
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))

    # Role check
    from app.routes.hub import has_tool_access
    if not has_tool_access(user, 'finanzberatung'):
        # SSE endpoints: silent 403 instead of flash+redirect (avoids flash spam)
        if 'sse' in endpoint:
            from flask import abort
            abort(403)
        flash("Kein Zugriff auf Finanzberatung", "error")
        return redirect(url_for('hub.dashboard'))


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

    try:
        from .questionnaire import questionnaire_bp
        finanzberatung_bp.register_blueprint(questionnaire_bp, url_prefix='')
    except ImportError:
        app.logger.warning("Finanzberatung questionnaire sub-blueprint not yet available")

    # Register parent blueprint with app
    app.register_blueprint(finanzberatung_bp)

    app.logger.info("Finanzberatung blueprint registered")
    mode = "live" if finanz_config.FINANZ_LLM_ENABLED else "mock"
    app.logger.info("Finanzberatung LLM mode: %s", mode)
    return finanzberatung_bp
