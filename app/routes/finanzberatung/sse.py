# -*- coding: utf-8 -*-
"""
Finanzberatung SSE Routes - Server-Sent Events Streaming Endpoints

Provides real-time streaming for document upload notifications:
- GET /sse/stream/<session_id> -- Session-specific live feed
- GET /sse/global              -- Global toast notifications for current user

All routes require login (only consultants see SSE streams).
"""

import logging

from flask import Blueprint, Response, session as flask_session, stream_with_context, abort

from app.utils.decorators import require_login
from app.services.finanz_sse_service import sse_manager

logger = logging.getLogger(__name__)

sse_bp = Blueprint('finanz_sse', __name__)


def _get_current_user():
    """Get current logged-in username from Flask session."""
    return flask_session.get('user')


def _is_admin():
    """Check if current user has admin privileges."""
    from app.config.base import config
    user = _get_current_user()
    return user and user in config.get_admin_users()


def _sse_response(generator):
    """Create an SSE Response with proper headers."""
    return Response(
        stream_with_context(generator),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


@sse_bp.route('/sse/stream/<int:session_id>')
@require_login
def stream_session(session_id):
    """
    SSE streaming endpoint for a specific session's live upload feed.

    Verifies user has access to the session (owns it or is admin).
    """
    current_user = _get_current_user()

    # Verify access to session
    try:
        from app.services.finanz_session_service import FinanzSessionService
        service = FinanzSessionService()

        if _is_admin():
            finanz_session = service.get_session(session_id, username=None)
        else:
            finanz_session = service.get_session(session_id, username=current_user)

        if finanz_session is None:
            abort(404)
    except Exception as e:
        logger.error("SSE access check failed for session %s: %s", session_id, e)
        abort(403)

    channel = f"finanz:session:{session_id}"
    logger.info("SSE stream opened: session %s by user %s", session_id, current_user)

    return _sse_response(sse_manager.stream(channel))


@sse_bp.route('/sse/global')
@require_login
def stream_global():
    """
    SSE streaming endpoint for global toast notifications.

    Subscribes to user-specific channel for the current user.
    Shows toast notifications on ANY Hub page.
    """
    current_user = _get_current_user()

    if not current_user:
        abort(401)

    channel = f"finanz:user:{current_user}"
    logger.info("SSE global stream opened for user: %s", current_user)

    return _sse_response(sse_manager.stream(channel))
