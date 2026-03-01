# -*- coding: utf-8 -*-
"""
Finanzberatung Upload Routes - Public customer document upload

Public-facing upload endpoints for customers who scan QR codes.
NO login required -- authentication via crypto-secure upload token.
CSRF-exempt (handled in blueprint __init__.py).

Routes:
- GET  /upload/<token_value>        -- Upload page (standalone mobile)
- POST /upload/<token_value>/submit -- AJAX file upload handler
- GET  /upload/<token_value>/status -- AJAX token status check
"""

import logging

from flask import Blueprint, jsonify, render_template, request

from app.config.base import FinanzConfig as finanz_config
from app.services.finanz_upload_service import FinanzUploadService

logger = logging.getLogger(__name__)

upload_bp = Blueprint('finanz_upload', __name__)

upload_service = FinanzUploadService()


@upload_bp.route('/upload/<token_value>', methods=['GET'])
def upload_page(token_value):
    """
    Render the standalone mobile upload page.

    Validates the token and shows either the upload page
    or the expired token error page.
    """
    is_valid, token, error_message = upload_service.validate_token(token_value)

    if not is_valid:
        return render_template(
            'finanzberatung/upload_expired.html',
            error_message=error_message or 'Link abgelaufen',
        ), 410

    # Get customer name from related session
    customer_name = 'Kunde'
    if token and token.session:
        customer_name = token.session.customer_name or 'Kunde'

    # Calculate remaining uploads
    remaining_uploads = max(0, token.max_uploads - token.upload_count)

    # Token expiry as ISO string for client-side countdown
    expires_at = token.expires_at.isoformat() + 'Z'

    return render_template(
        'finanzberatung/upload.html',
        customer_name=customer_name,
        token_value=token_value,
        remaining_uploads=remaining_uploads,
        expires_at=expires_at,
        max_file_size_mb=finanz_config.FINANZ_MAX_FILE_SIZE_MB,
    )


@upload_bp.route('/upload/<token_value>/submit', methods=['POST'])
def upload_submit(token_value):
    """
    Handle AJAX file upload.

    Validates token again (may have expired since page load),
    validates file via magic bytes, stores with UUID filename.
    Returns JSON response for client-side progress cards.
    """
    # Re-validate token (may have expired since page was loaded)
    is_valid, token, error_message = upload_service.validate_token(token_value)

    if not is_valid:
        logger.warning(
            "Upload rejected -- invalid token: %s (%s)",
            token_value[:8], error_message,
        )
        return jsonify({
            'error': True,
            'message': error_message or 'Token ungueltig',
        }), 403

    # Get file from request
    if 'file' not in request.files:
        return jsonify({
            'error': True,
            'message': 'Keine Datei ausgewaehlt',
        }), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({
            'error': True,
            'message': 'Keine Datei ausgewaehlt',
        }), 400

    # Validate file via magic bytes
    is_file_valid, detected_mime, file_error = upload_service.validate_file(file)
    if not is_file_valid:
        logger.warning(
            "File rejected for token %s: %s (mime: %s)",
            token_value[:8], file_error, detected_mime,
        )
        return jsonify({
            'error': True,
            'message': file_error,
        }), 400

    # Store file
    try:
        document = upload_service.store_file(
            file_storage=file,
            session_id=token.session_id,
            token_id=token.id,
            original_filename=file.filename,
            mime_type=detected_mime,
        )
    except ValueError as e:
        # Duplicate file detected
        logger.info(
            "Duplicate file rejected for session %s: %s",
            token.session_id, str(e),
        )
        return jsonify({
            'error': True,
            'message': str(e),
        }), 409
    except Exception as e:
        logger.error(
            "Failed to store file for session %s: %s",
            token.session_id, e, exc_info=True,
        )
        return jsonify({
            'error': True,
            'message': 'Fehler beim Speichern der Datei. Bitte versuchen Sie es erneut.',
        }), 500

    logger.info(
        "Document uploaded: %s for session %s (doc_id=%s)",
        file.filename, token.session_id, document.id,
    )

    return jsonify({
        'success': True,
        'document': {
            'id': document.id,
            'original_filename': document.original_filename,
            'file_size': document.file_size,
            'mime_type': document.mime_type,
            'status': document.status,
            'created_at': document.created_at.isoformat() if document.created_at else None,
        },
    })


@upload_bp.route('/upload/<token_value>/status', methods=['GET'])
def upload_status(token_value):
    """
    Token status check (AJAX endpoint for client-side polling).

    Returns current token validity, remaining uploads, and expiry time.
    Used by client to update UI without page reload.
    """
    is_valid, token, error_message = upload_service.validate_token(token_value)

    if token is None:
        return jsonify({
            'valid': False,
            'remaining_uploads': 0,
            'expires_at': None,
            'message': error_message or 'Token nicht gefunden',
        })

    remaining_uploads = max(0, token.max_uploads - token.upload_count)
    expires_at = token.expires_at.isoformat() + 'Z' if token.expires_at else None

    return jsonify({
        'valid': is_valid,
        'remaining_uploads': remaining_uploads,
        'expires_at': expires_at,
        'message': error_message if not is_valid else '',
    })
