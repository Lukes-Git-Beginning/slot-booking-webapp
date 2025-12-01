# -*- coding: utf-8 -*-
"""
Security Routes
Passwort-Änderung und 2FA-Management
"""

from flask import Blueprint, request, jsonify, session, render_template
from app.services.security_service import security_service
from app.services.audit_service import audit_service
from app.utils.decorators import require_login
from app.core.extensions import limiter

security_bp = Blueprint('security', __name__)


@security_bp.route("/change-password", methods=["POST"])
@require_login
@limiter.limit("5 per minute")
def change_password():
    """Ändere Benutzerpasswort"""
    data = request.get_json()
    username = session.get("user")

    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    # Validation
    if not old_password or not new_password or not confirm_password:
        return jsonify({"success": False, "error": "Alle Felder sind erforderlich"}), 400

    if new_password != confirm_password:
        return jsonify({"success": False, "error": "Passwörter stimmen nicht überein"}), 400

    # Change password
    success, message = security_service.change_password(username, old_password, new_password)

    if success:
        audit_service.log_password_change(username)
        return jsonify({"success": True, "message": message})
    else:
        audit_service.log_event(
            event_type='security',
            action='password_change_failed',
            user=username,
            severity='warning',
            details={'reason': 'incorrect_old_password'}
        )
        return jsonify({"success": False, "error": message}), 400


@security_bp.route("/2fa/setup", methods=["POST"])
@require_login
@limiter.limit("10 per minute")
def setup_2fa():
    """Richte 2FA ein"""
    username = session.get("user")

    secret, qr_code, backup_codes = security_service.setup_2fa(username)

    return jsonify({
        "success": True,
        "secret": secret,
        "qr_code": qr_code,
        "backup_codes": backup_codes
    })


@security_bp.route("/2fa/enable", methods=["POST"])
@require_login
@limiter.limit("10 per minute")
def enable_2fa():
    """Aktiviere 2FA nach Verifizierung"""
    data = request.get_json()
    username = session.get("user")
    verification_code = data.get("code", "")

    success, message = security_service.enable_2fa(username, verification_code)

    if success:
        audit_service.log_2fa_enabled(username)
        return jsonify({"success": True, "message": message})
    else:
        audit_service.log_event(
            event_type='security',
            action='2fa_enable_failed',
            user=username,
            severity='warning',
            details={'reason': 'invalid_totp_code'}
        )
        return jsonify({"success": False, "error": message}), 400


@security_bp.route("/2fa/disable", methods=["POST"])
@require_login
@limiter.limit("5 per minute")
def disable_2fa():
    """Deaktiviere 2FA"""
    data = request.get_json()
    username = session.get("user")
    password = data.get("password", "")

    success, message = security_service.disable_2fa(username, password)

    if success:
        audit_service.log_2fa_disabled(username)
        return jsonify({"success": True, "message": message})
    else:
        audit_service.log_event(
            event_type='security',
            action='2fa_disable_failed',
            user=username,
            severity='warning',
            details={'reason': 'incorrect_password'}
        )
        return jsonify({"success": False, "error": message}), 400


@security_bp.route("/2fa/status", methods=["GET"])
@require_login
@limiter.limit("30 per minute")
def get_2fa_status():
    """Hole 2FA-Status des Users"""
    username = session.get("user")
    enabled = security_service.is_2fa_enabled(username)
    backup_codes = security_service.get_backup_codes(username) if enabled else []

    return jsonify({
        "success": True,
        "enabled": enabled,
        "backup_codes": backup_codes
    })
