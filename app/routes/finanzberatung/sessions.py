# -*- coding: utf-8 -*-
"""
Finanzberatung Sessions Sub-Blueprint - Session CRUD and Management

Routes:
- GET  /sessions               - Session list page
- GET  /sessions/create        - Session creation form
- POST /sessions/create        - Handle session creation
- GET  /sessions/<id>          - Session detail page
- POST /sessions/<id>/generate-token - Generate upload token (AJAX)
- POST /sessions/<id>/notes    - Auto-save notes (AJAX)
- POST /sessions/<id>/status   - Transition status (AJAX)
- POST /sessions/<id>/assign-closer - Assign closer
- GET  /sessions/<id>/documents - Get documents as JSON
- POST /sessions/<id>/deactivate-token - Deactivate upload token (AJAX)
"""

import logging
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, session as flask_session, abort,
)

from app.utils.decorators import require_login
from app.services.finanz_session_service import FinanzSessionService
from app.services.finanz_upload_service import FinanzUploadService
from app.models.finanzberatung import SessionStatus, TokenType

logger = logging.getLogger(__name__)

sessions_bp = Blueprint('finanz_sessions', __name__)

# Service instances
session_service = FinanzSessionService()
upload_service = FinanzUploadService()


def _get_current_user():
    """Get the current logged-in username from Flask session."""
    return flask_session.get('user')


def _is_admin():
    """Check if current user has admin privileges."""
    from app.config.base import config
    user = _get_current_user()
    return user and user in config.get_admin_users()


# ---------------------------------------------------------------------------
# 1. GET /sessions - Session list page
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions')
@require_login
def session_list():
    """Show session list -- own sessions for openers, all for admins."""
    try:
        current_user = _get_current_user()
        if _is_admin():
            sessions = session_service.list_sessions(username=None)
        else:
            sessions = session_service.list_sessions(username=current_user)

        return render_template(
            'finanzberatung/session_list.html',
            sessions=sessions,
        )
    except Exception as e:
        logger.error("Error loading session list: %s", e, exc_info=True)
        flash('Fehler beim Laden der Sessions.', 'error')
        return redirect(url_for('hub.dashboard'))


# ---------------------------------------------------------------------------
# 2. GET /sessions/create - Session creation form
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/create', methods=['GET'])
@require_login
def session_create_form():
    """Show session creation form."""
    return render_template('finanzberatung/session_create.html')


# ---------------------------------------------------------------------------
# 3. POST /sessions/create - Handle session creation
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/create', methods=['POST'])
@require_login
def session_create():
    """Create a new session and auto-generate T1 upload token."""
    try:
        current_user = _get_current_user()

        # Extract and validate form data
        customer_name = (request.form.get('customer_name', '') or '').strip()
        session_type = request.form.get('session_type', '')
        appointment_date_str = request.form.get('appointment_date', '')

        if not customer_name:
            flash('Bitte geben Sie einen Kundennamen ein.', 'error')
            return redirect(url_for('finanzberatung.finanz_sessions.session_create_form'))

        if session_type not in ('erstberatung', 'folgeberatung'):
            flash('Bitte waehlen Sie eine gueltige Beratungsart.', 'error')
            return redirect(url_for('finanzberatung.finanz_sessions.session_create_form'))

        # Parse appointment date
        appointment_date = None
        if appointment_date_str:
            try:
                appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Ungueltiges Datumsformat.', 'error')
                return redirect(url_for('finanzberatung.finanz_sessions.session_create_form'))

        # Create session
        new_session = session_service.create_session(
            opener_username=current_user,
            customer_name=customer_name,
            session_type=session_type,
            appointment_date=appointment_date,
        )

        # Auto-generate T1 upload token
        try:
            upload_service.generate_token(new_session.id, TokenType.T1)
            logger.info(
                "T1 token auto-generated for session %s", new_session.id
            )
        except Exception as e:
            logger.error(
                "Failed to auto-generate T1 token for session %s: %s",
                new_session.id, e, exc_info=True,
            )
            flash('Session erstellt, aber Token konnte nicht generiert werden.', 'warning')

        flash(f'Session fuer "{customer_name}" wurde erfolgreich erstellt.', 'success')
        return redirect(
            url_for('finanzberatung.finanz_sessions.session_detail', session_id=new_session.id)
        )

    except Exception as e:
        logger.error("Error creating session: %s", e, exc_info=True)
        flash('Fehler beim Erstellen der Session.', 'error')
        return redirect(url_for('finanzberatung.finanz_sessions.session_create_form'))


# ---------------------------------------------------------------------------
# 4. GET /sessions/<id> - Session detail page
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>')
@require_login
def session_detail(session_id):
    """Show session detail with QR code, notes, documents, and token management."""
    try:
        current_user = _get_current_user()

        # Get session (admin sees all, opener sees own)
        if _is_admin():
            finanz_session = session_service.get_session(session_id, username=None)
        else:
            finanz_session = session_service.get_session(session_id, username=current_user)

        if finanz_session is None:
            abort(404)

        # Get active token and generate QR if exists
        active_token = upload_service.get_active_token(session_id)
        qr_code = None
        if active_token:
            # Regenerate QR for display
            import base64
            import io
            import os
            import qrcode

            base_url = os.getenv(
                'FINANZ_UPLOAD_BASE_URL', 'https://berater.zfa.gmbh'
            ).rstrip('/')
            upload_url = f"{base_url}/finanzberatung/upload/{active_token.token}"

            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(upload_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_code = base64.b64encode(buffer.getvalue()).decode()

        # Get documents
        documents = session_service.get_session_documents(session_id)

        # Check followup eligibility
        can_followup = upload_service.can_generate_followup(session_id)

        # Determine allowed status transitions
        current_status = SessionStatus(finanz_session.status)
        allowed_transitions = finanz_session.VALID_TRANSITIONS.get(current_status, [])

        return render_template(
            'finanzberatung/session_detail.html',
            session=finanz_session,
            active_token=active_token,
            qr_code=qr_code,
            documents=documents,
            can_followup=can_followup,
            allowed_transitions=allowed_transitions,
            SessionStatus=SessionStatus,
        )

    except Exception as e:
        logger.error("Error loading session detail %s: %s", session_id, e, exc_info=True)
        flash('Fehler beim Laden der Session.', 'error')
        return redirect(url_for('finanzberatung.finanz_sessions.session_list'))


# ---------------------------------------------------------------------------
# 5. POST /sessions/<id>/generate-token - Generate new token (AJAX)
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/generate-token', methods=['POST'])
@require_login
def generate_token(session_id):
    """Generate a new upload token for the session. Returns JSON."""
    try:
        data = request.get_json(silent=True) or {}
        token_type_str = data.get('token_type', 't1')

        # Validate token type
        try:
            token_type = TokenType(token_type_str)
        except ValueError:
            return jsonify({
                'success': False,
                'message': f'Ungueltiger Token-Typ: {token_type_str}',
            }), 400

        # For followup: check eligibility
        if token_type == TokenType.FOLLOWUP:
            if not upload_service.can_generate_followup(session_id):
                return jsonify({
                    'success': False,
                    'message': 'Folge-Token kann erst nach Ablauf des T1-Tokens erstellt werden.',
                }), 400

        # Generate token
        token, qr_base64 = upload_service.generate_token(session_id, token_type)

        return jsonify({
            'success': True,
            'token_id': token.id,
            'token_value': token.token,
            'qr_base64': qr_base64,
            'expires_at': token.expires_at.isoformat(),
            'token_type': token.token_type,
        })

    except Exception as e:
        logger.error(
            "Error generating token for session %s: %s",
            session_id, e, exc_info=True,
        )
        return jsonify({
            'success': False,
            'message': 'Fehler beim Erstellen des Tokens.',
        }), 500


# ---------------------------------------------------------------------------
# 6. POST /sessions/<id>/notes - Auto-save notes (AJAX)
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/notes', methods=['POST'])
@require_login
def save_notes(session_id):
    """Auto-save notes for a session. Returns JSON."""
    try:
        current_user = _get_current_user()
        data = request.get_json(silent=True) or {}
        field = data.get('field', '')
        content = data.get('content', '')

        if field not in ('t1_notes', 't2_notes'):
            return jsonify({
                'success': False,
                'message': 'Ungueltiges Notizfeld.',
            }), 400

        success = session_service.update_notes(
            session_id=session_id,
            field=field,
            content=content,
            username=current_user,
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'Notizen gespeichert.',
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Notizen konnten nicht gespeichert werden. Keine Berechtigung.',
            }), 403

    except Exception as e:
        logger.error(
            "Error saving notes for session %s: %s",
            session_id, e, exc_info=True,
        )
        return jsonify({
            'success': False,
            'message': 'Fehler beim Speichern der Notizen.',
        }), 500


# ---------------------------------------------------------------------------
# 7. POST /sessions/<id>/status - Transition status (AJAX)
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/status', methods=['POST'])
@require_login
def transition_status(session_id):
    """Transition session to a new status. Returns JSON."""
    try:
        current_user = _get_current_user()
        data = request.get_json(silent=True) or {}
        new_status_str = data.get('new_status', '')

        # Validate status
        try:
            new_status = SessionStatus(new_status_str)
        except ValueError:
            return jsonify({
                'success': False,
                'message': f'Ungueltiger Status: {new_status_str}',
            }), 400

        updated_session = session_service.transition_status(
            session_id=session_id,
            new_status=new_status,
            username=current_user,
        )

        return jsonify({
            'success': True,
            'new_status': updated_session.status,
            'message': f'Status auf "{new_status.value}" geaendert.',
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e),
        }), 400
    except LookupError as e:
        return jsonify({
            'success': False,
            'message': str(e),
        }), 404
    except Exception as e:
        logger.error(
            "Error transitioning session %s: %s",
            session_id, e, exc_info=True,
        )
        return jsonify({
            'success': False,
            'message': 'Fehler beim Statuswechsel.',
        }), 500


# ---------------------------------------------------------------------------
# 8. POST /sessions/<id>/assign-closer - Assign closer
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/assign-closer', methods=['POST'])
@require_login
def assign_closer(session_id):
    """Assign a closer to the session."""
    try:
        closer_username = (request.form.get('closer_username', '') or '').strip()

        if not closer_username:
            flash('Bitte waehlen Sie einen Closer aus.', 'error')
            return redirect(
                url_for('finanzberatung.finanz_sessions.session_detail', session_id=session_id)
            )

        session_service.assign_closer(session_id, closer_username)
        flash(f'Closer "{closer_username}" wurde zugewiesen.', 'success')

    except LookupError as e:
        flash(str(e), 'error')
    except Exception as e:
        logger.error(
            "Error assigning closer to session %s: %s",
            session_id, e, exc_info=True,
        )
        flash('Fehler beim Zuweisen des Closers.', 'error')

    return redirect(
        url_for('finanzberatung.finanz_sessions.session_detail', session_id=session_id)
    )


# ---------------------------------------------------------------------------
# 9. GET /sessions/<id>/documents - Get documents as JSON
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/documents')
@require_login
def get_documents(session_id):
    """Get session documents as JSON. Optional `since` param for SSE reconnect."""
    try:
        documents = session_service.get_session_documents(session_id)

        # Optional filter by timestamp
        since_str = request.args.get('since')
        if since_str:
            try:
                since = datetime.fromisoformat(since_str)
                documents = [d for d in documents if d.created_at and d.created_at > since]
            except (ValueError, TypeError):
                pass

        return jsonify([
            {
                'id': doc.id,
                'original_filename': doc.original_filename,
                'file_size': doc.file_size,
                'mime_type': doc.mime_type,
                'status': doc.status,
                'document_type': doc.document_type,
                'created_at': doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ])

    except Exception as e:
        logger.error(
            "Error loading documents for session %s: %s",
            session_id, e, exc_info=True,
        )
        return jsonify({'error': 'Fehler beim Laden der Dokumente.'}), 500


# ---------------------------------------------------------------------------
# 10. POST /sessions/<id>/deactivate-token - Deactivate upload token (AJAX)
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/deactivate-token', methods=['POST'])
@require_login
def deactivate_token(session_id):
    """Deactivate an upload token. Returns JSON."""
    try:
        current_user = _get_current_user()
        data = request.get_json(silent=True) or {}
        token_id = data.get('token_id')

        if not token_id:
            return jsonify({
                'success': False,
                'message': 'Token-ID fehlt.',
            }), 400

        token_id = int(token_id)
        success = upload_service.deactivate_token(token_id)

        if success:
            logger.info(
                "Token %s deactivated by %s for session %s",
                token_id, current_user, session_id,
            )
            return jsonify({
                'success': True,
                'message': 'Token wurde deaktiviert.',
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Token nicht gefunden oder bereits deaktiviert.',
            }), 404

    except Exception as e:
        logger.error(
            "Error deactivating token for session %s: %s",
            session_id, e, exc_info=True,
        )
        return jsonify({
            'success': False,
            'message': 'Fehler beim Deaktivieren des Tokens.',
        }), 500
