# -*- coding: utf-8 -*-
"""
Error Handlers Blueprint
Zentrale Fehlerbehandlung für alle HTTP-Fehler
"""

from flask import Blueprint, render_template, request, session, jsonify
from datetime import datetime
import logging
import traceback
import uuid

# Blueprint für Error Handlers
error_handlers_bp = Blueprint('error_handlers', __name__)

logger = logging.getLogger(__name__)

# ========== HTTP ERROR HANDLERS ==========

@error_handlers_bp.app_errorhandler(400)
def bad_request_error(error):
    """400 Bad Request"""
    error_id = generate_error_id()
    log_error(400, error, error_id)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': 'Die Anfrage ist ungültig oder fehlerhaft.',
            'error_id': error_id
        }), 400

    return render_template('errors/400.html', error_id=error_id), 400


@error_handlers_bp.app_errorhandler(401)
def unauthorized_error(error):
    """401 Unauthorized"""
    error_id = generate_error_id()
    log_error(401, error, error_id)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Authentifizierung erforderlich.',
            'error_id': error_id
        }), 401

    return render_template('errors/401.html', error_id=error_id), 401


@error_handlers_bp.app_errorhandler(403)
def forbidden_error(error):
    """403 Forbidden"""
    error_id = generate_error_id()
    log_error(403, error, error_id)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'Zugriff verweigert.',
            'error_id': error_id
        }), 403

    return render_template('errors/403.html', error_id=error_id), 403


@error_handlers_bp.app_errorhandler(404)
def page_not_found_error(error):
    """404 Not Found"""
    error_id = generate_error_id()
    log_error(404, error, error_id)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': 'Die angeforderte Ressource wurde nicht gefunden.',
            'error_id': error_id
        }), 404

    return render_template('errors/404.html', error_id=error_id), 404


@error_handlers_bp.app_errorhandler(405)
def method_not_allowed_error(error):
    """405 Method Not Allowed"""
    error_id = generate_error_id()
    log_error(405, error, error_id)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Method Not Allowed',
            'message': 'Die HTTP-Methode ist für diese Ressource nicht erlaubt.',
            'error_id': error_id
        }), 405

    return render_template('errors/generic.html',
                         error_code='405',
                         error_message='Die HTTP-Methode ist für diese Ressource nicht erlaubt.',
                         error_id=error_id), 405


@error_handlers_bp.app_errorhandler(429)
def rate_limit_error(error):
    """429 Too Many Requests"""
    error_id = generate_error_id()
    log_error(429, error, error_id)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Too Many Requests',
            'message': 'Zu viele Anfragen. Bitte versuche es später erneut.',
            'error_id': error_id
        }), 429

    return render_template('errors/generic.html',
                         error_code='429',
                         error_message='Du hast zu viele Anfragen in kurzer Zeit gesendet. Bitte warte einen Moment.',
                         error_id=error_id), 429


@error_handlers_bp.app_errorhandler(500)
def internal_server_error(error):
    """500 Internal Server Error"""
    error_id = generate_error_id()
    log_error(500, error, error_id, include_traceback=True)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'Ein interner Serverfehler ist aufgetreten.',
            'error_id': error_id
        }), 500

    return render_template('errors/500.html', error_id=error_id), 500


@error_handlers_bp.app_errorhandler(502)
def bad_gateway_error(error):
    """502 Bad Gateway"""
    error_id = generate_error_id()
    log_error(502, error, error_id)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Bad Gateway',
            'message': 'Der Server hat eine ungültige Antwort erhalten.',
            'error_id': error_id
        }), 502

    return render_template('errors/generic.html',
                         error_code='502',
                         error_message='Der Server hat eine ungültige Antwort von einem vorgelagerten Server erhalten.',
                         error_id=error_id), 502


@error_handlers_bp.app_errorhandler(503)
def service_unavailable_error(error):
    """503 Service Unavailable"""
    error_id = generate_error_id()
    log_error(503, error, error_id)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Service Unavailable',
            'message': 'Der Service ist temporär nicht verfügbar.',
            'error_id': error_id
        }), 503

    # Check if maintenance mode is active
    if is_maintenance_mode():
        return render_template('errors/maintenance.html', error_id=error_id), 503

    return render_template('errors/generic.html',
                         error_code='503',
                         error_message='Der Service ist temporär nicht verfügbar. Bitte versuche es später erneut.',
                         error_id=error_id), 503


@error_handlers_bp.app_errorhandler(504)
def gateway_timeout_error(error):
    """504 Gateway Timeout"""
    error_id = generate_error_id()
    log_error(504, error, error_id)

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Gateway Timeout',
            'message': 'Der Server hat zu lange für eine Antwort gebraucht.',
            'error_id': error_id
        }), 504

    return render_template('errors/generic.html',
                         error_code='504',
                         error_message='Der Server hat zu lange für eine Antwort gebraucht. Bitte versuche es erneut.',
                         error_id=error_id), 504


# ========== EXCEPTION HANDLERS ==========

@error_handlers_bp.app_errorhandler(Exception)
def handle_unexpected_error(error):
    """Handle unexpected exceptions"""
    error_id = generate_error_id()

    # Log the full traceback for debugging
    logger.error(f"Unexpected error {error_id}: {str(error)}")
    logger.error(traceback.format_exc())

    # Don't expose internal errors in production
    if is_development_mode():
        error_message = str(error)
    else:
        error_message = 'Ein unerwarteter Fehler ist aufgetreten.'

    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Unexpected Error',
            'message': error_message,
            'error_id': error_id
        }), 500

    return render_template('errors/500.html',
                         error_id=error_id,
                         error_message=error_message), 500


# ========== CUSTOM ERROR ROUTES ==========

@error_handlers_bp.route('/error/maintenance')
def maintenance_mode():
    """Display maintenance page"""
    return render_template('errors/maintenance.html'), 503


@error_handlers_bp.route('/error/test/<int:error_code>')
def test_error(error_code):
    """Test error pages (development only)"""
    if not is_development_mode():
        return render_template('errors/404.html'), 404

    # Trigger the appropriate error
    if error_code == 400:
        from werkzeug.exceptions import BadRequest
        raise BadRequest()
    elif error_code == 401:
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized()
    elif error_code == 403:
        from werkzeug.exceptions import Forbidden
        raise Forbidden()
    elif error_code == 404:
        from werkzeug.exceptions import NotFound
        raise NotFound()
    elif error_code == 405:
        from werkzeug.exceptions import MethodNotAllowed
        raise MethodNotAllowed()
    elif error_code == 429:
        from werkzeug.exceptions import TooManyRequests
        raise TooManyRequests()
    elif error_code == 500:
        raise Exception("Test internal server error")
    elif error_code == 502:
        from werkzeug.exceptions import BadGateway
        raise BadGateway()
    elif error_code == 503:
        from werkzeug.exceptions import ServiceUnavailable
        raise ServiceUnavailable()
    elif error_code == 504:
        from werkzeug.exceptions import RequestTimeout
        raise RequestTimeout()
    else:
        return render_template('errors/generic.html',
                             error_code=str(error_code),
                             error_message=f'Test error {error_code}'), error_code


# ========== UTILITY FUNCTIONS ==========

def generate_error_id() -> str:
    """Generate unique error ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"ERR-{timestamp}-{unique_id}"


def log_error(status_code: int, error: Exception, error_id: str, include_traceback: bool = False):
    """Log error with context information"""
    user = session.get('user', 'Anonymous')
    url = request.url
    method = request.method
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', 'Unknown')[:100]

    error_context = {
        'error_id': error_id,
        'status_code': status_code,
        'error': str(error),
        'user': user,
        'url': url,
        'method': method,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'timestamp': datetime.now().isoformat()
    }

    logger.error(f"HTTP {status_code} Error {error_id}: {error}", extra=error_context)

    if include_traceback:
        logger.error(f"Traceback for {error_id}:\n{traceback.format_exc()}")

    # Send to error tracking service (implement as needed)
    try:
        send_to_error_tracking(error_context)
    except Exception as e:
        logger.warning(f"Failed to send error to tracking service: {e}")


def is_maintenance_mode() -> bool:
    """Check if maintenance mode is active"""
    try:
        # Check for maintenance mode file or configuration
        import os
        maintenance_file = os.path.join(os.getcwd(), '.maintenance')
        return os.path.exists(maintenance_file)
    except (OSError, IOError):
        return False


def is_development_mode() -> bool:
    """Check if running in development mode"""
    try:
        from flask import current_app
        return current_app.debug or current_app.config.get('ENV') == 'development'
    except (RuntimeError, AttributeError):
        # Kein App-Context verfügbar
        return False


def send_to_error_tracking(error_context: dict):
    """
    Send error to structured logging system

    Writes errors to:
    1. error.log (standard logging)
    2. errors/critical.jsonl (structured logs for critical errors)
    3. Admin notifications (for critical errors)
    """
    import json
    from pathlib import Path

    # Always log to standard logger
    logger.error(
        f"Error tracked: {error_context['error_id']}",
        extra=error_context
    )

    # Write critical errors to structured JSONL log
    if error_context.get('status_code', 0) >= 500:
        try:
            from app.config.base import config
            log_dir = Path(config.PERSIST_BASE) / 'persistent' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)

            critical_log = log_dir / 'critical_errors.jsonl'

            with open(critical_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_context, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.warning(f"Failed to write critical error log: {e}")

    # Notify admins for critical errors
    if error_context.get('status_code', 0) >= 500:
        try:
            from app.services.notification_service import notification_service

            error_summary = (
                f"Status: {error_context.get('status_code', 'Unknown')}\n"
                f"Error ID: {error_context.get('error_id', 'Unknown')}\n"
                f"URL: {error_context.get('url', 'Unknown')}\n"
                f"User: {error_context.get('user', 'Anonymous')}"
            )

            notification_service.create_notification(
                roles=['admin'],
                title=f"Server Error {error_context.get('status_code', '500')}",
                message=error_summary,
                notification_type='error',
                show_popup=False
            )
        except Exception as e:
            logger.warning(f"Failed to send admin notification: {e}")

    # Development mode: log to console
    if is_development_mode():
        logger.debug(f"\n{'='*80}")
        logger.debug(f"ERROR TRACKING: {error_context['error_id']}")
        logger.debug(json.dumps(error_context, indent=2, ensure_ascii=False))
        logger.debug(f"{'='*80}\n")


# ========== CONTEXT PROCESSORS ==========

@error_handlers_bp.app_context_processor
def inject_error_helpers():
    """Inject error-related template helpers"""
    def moment():
        """Mock moment.js-like functionality for templates"""
        class MockMoment:
            def format(self, format_str):
                return datetime.now().strftime(format_str.replace('DD', '%d').replace('MM', '%m').replace('YYYY', '%Y').replace('HH', '%H').replace('mm', '%M').replace('ss', '%S'))

            def subtract(self, amount, unit):
                if unit == 'minutes':
                    return MockMoment()
                return MockMoment()

        return MockMoment()

    return dict(moment=moment)