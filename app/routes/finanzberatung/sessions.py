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
- GET  /sessions/<id>/checklist - Checklist data as JSON (AJAX)
- POST /sessions/<id>/verify-field - Verify/update a field (AJAX)
- POST /sessions/<id>/manual-contract - Add manual contract (AJAX)
- POST /sessions/<id>/start-analysis - Trigger pipeline (AJAX)
- POST /sessions/<id>/generate-scorecard - Generate scorecard (AJAX)
- GET  /sessions/<id>/export/excel - Excel export
- GET  /sessions/<id>/export/pdf - PDF export
"""

import logging
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, session as flask_session, abort, send_file,
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


def _check_session_access(session_id):
    """Verify current user owns the session (opener/closer/admin). Aborts 404 otherwise."""
    current_user = _get_current_user()
    if _is_admin():
        s = session_service.get_session(session_id, username=None)
    else:
        s = session_service.get_session(session_id, username=current_user)
    if s is None:
        abort(404)
    return s, current_user


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

        # Tab-based status filtering
        active_tab = request.args.get('tab', 'alle')
        tab_filters = {
            'aktiv': {'active'},
            'bearbeitung': {'in_analysis', 'analyzed'},
            'abgeschlossen': {'verified', 'archived'},
        }
        if active_tab in tab_filters:
            allowed = tab_filters[active_tab]
            sessions = [s for s in sessions if s.status in allowed]

        return render_template(
            'finanzberatung/session_list.html',
            sessions=sessions,
            active_tab=active_tab,
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
            flash('Bitte wählen Sie eine gültige Beratungsart.', 'error')
            return redirect(url_for('finanzberatung.finanz_sessions.session_create_form'))

        # Parse appointment date
        appointment_date = None
        if appointment_date_str:
            try:
                appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Ungültiges Datumsformat.', 'error')
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
        upload_url = None
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
        if isinstance(finanz_session.status, SessionStatus):
            current_status = finanz_session.status
        else:
            try:
                current_status = SessionStatus[finanz_session.status]
            except KeyError:
                current_status = SessionStatus(finanz_session.status)
        allowed_transitions = finanz_session.VALID_TRANSITIONS.get(current_status, [])

        # Build checklist data for the UI
        checklist_data = _build_checklist_data(session_id)

        # Get scorecards
        from app.models.finanzberatung import FinanzScorecard
        from app.models import get_db_session as _get_db
        db = _get_db()
        try:
            scorecards = db.query(FinanzScorecard).filter(
                FinanzScorecard.session_id == session_id
            ).all()
            scorecard_data = [
                {
                    'category': sc.category,
                    'rating': sc.rating,
                    'assessment': sc.assessment,
                    'details': sc.details,
                    'is_overall': sc.is_overall,
                }
                for sc in scorecards
            ]
        except Exception:
            scorecard_data = []
        finally:
            db.close()

        # Determine if user is closer
        is_closer = (current_user == finanz_session.closer_username)

        return render_template(
            'finanzberatung/session_detail.html',
            session=finanz_session,
            active_token=active_token,
            qr_code=qr_code,
            documents=documents,
            can_followup=can_followup,
            upload_url=upload_url,
            allowed_transitions=allowed_transitions,
            SessionStatus=SessionStatus,
            checklist_data=checklist_data,
            scorecard_data=scorecard_data,
            is_closer=is_closer,
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
                'message': f'Ungültiger Token-Typ: {token_type_str}',
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
            'token_type': token.token_type.value if hasattr(token.token_type, 'value') else str(token.token_type),
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
                'message': 'Ungültiges Notizfeld.',
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
                'message': f'Ungültiger Status: {new_status_str}',
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
            flash('Bitte wählen Sie einen Closer aus.', 'error')
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


# ---------------------------------------------------------------------------
# Helper: Build checklist data from extracted documents
# ---------------------------------------------------------------------------
def _build_checklist_data(session_id: int) -> list:
    """
    Build checklist data for the session detail UI.

    Returns a list of contract dicts, each with:
    - type_key, type_label, icon, document_id, document_name
    - fields: list of {name, label, priority, type, value, confidence,
               source_page, source_text, status (green/yellow/red/gray), verified}
    - completeness: {muss_total, muss_filled, percent_muss, ...}
    """
    from app.config.finanz_checklist import (
        CONTRACT_TYPES, get_fields_for_type, get_field_status,
        compute_completeness, PRIORITY_LABELS,
    )
    from app.models.finanzberatung import FinanzDocument, FinanzExtractedData, DocumentStatus
    from app.models import get_db_session as _get_db

    db = _get_db()
    try:
        docs = db.query(FinanzDocument).filter(
            FinanzDocument.session_id == session_id,
            FinanzDocument.status == DocumentStatus.ANALYZED,
        ).all()

        result = []
        for doc in docs:
            type_key = doc.document_type or "sonstige"
            ct = CONTRACT_TYPES.get(type_key)
            if not ct:
                continue

            # Get extracted data for this document
            extracted = db.query(FinanzExtractedData).filter(
                FinanzExtractedData.document_id == doc.id
            ).all()
            extracted_map = {}
            for ed in extracted:
                extracted_map[ed.field_name] = {
                    "value": ed.field_value,
                    "confidence": ed.confidence,
                    "source_page": ed.source_page,
                    "source_text": ed.source_text,
                    "verified": ed.verified,
                    "verified_by": ed.verified_by,
                    "id": ed.id,
                }

            # Build field list with status
            field_defs = get_fields_for_type(type_key)
            fields = []
            for fdef in field_defs:
                ed = extracted_map.get(fdef["name"])
                fields.append({
                    "name": fdef["name"],
                    "label": fdef["label"],
                    "priority": fdef["priority"],
                    "priority_label": PRIORITY_LABELS.get(fdef["priority"], ""),
                    "type": fdef["type"],
                    "value": ed["value"] if ed else None,
                    "confidence": ed["confidence"] if ed else None,
                    "source_page": ed["source_page"] if ed else None,
                    "source_text": ed["source_text"] if ed else None,
                    "verified": ed["verified"] if ed else False,
                    "verified_by": ed.get("verified_by") if ed else None,
                    "extracted_data_id": ed["id"] if ed else None,
                    "status": get_field_status(fdef, ed),
                })

            completeness = compute_completeness(type_key, extracted_map)

            result.append({
                "type_key": type_key,
                "type_label": ct["label"],
                "icon": ct.get("icon", "file"),
                "category": ct.get("category", "sonstiges"),
                "document_id": doc.id,
                "document_name": doc.original_filename,
                "classification_confidence": doc.classification_confidence,
                "fields": fields,
                "completeness": completeness,
            })

        return result
    except Exception as e:
        logger.error("Error building checklist data for session %s: %s", session_id, e, exc_info=True)
        return []
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 11. GET /sessions/<id>/checklist - Checklist data as JSON (AJAX)
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/checklist')
@require_login
def get_checklist(session_id):
    """Get checklist data as JSON for dynamic updates."""
    try:
        checklist = _build_checklist_data(session_id)
        return jsonify(checklist)
    except Exception as e:
        logger.error("Error loading checklist for session %s: %s", session_id, e, exc_info=True)
        return jsonify({'error': 'Fehler beim Laden der Checkliste.'}), 500


# ---------------------------------------------------------------------------
# 12. POST /sessions/<id>/verify-field - Verify or update a field (AJAX)
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/verify-field', methods=['POST'])
@require_login
def verify_field(session_id):
    """Verify or update an extracted data field."""
    try:
        _session, current_user = _check_session_access(session_id)
        data = request.get_json(silent=True) or {}
        extracted_data_id = data.get('extracted_data_id')
        new_value = data.get('value')
        action = data.get('action', 'verify')  # 'verify' or 'update'

        if not extracted_data_id:
            return jsonify({'success': False, 'message': 'Feld-ID fehlt.'}), 400

        from app.models.finanzberatung import FinanzExtractedData
        from app.models import get_db_session as _get_db
        db = _get_db()
        try:
            ed = db.query(FinanzExtractedData).filter(
                FinanzExtractedData.id == int(extracted_data_id)
            ).first()
            if ed is None:
                return jsonify({'success': False, 'message': 'Feld nicht gefunden.'}), 404

            if action == 'verify':
                ed.verified = True
                ed.verified_by = current_user
                ed.verified_at = datetime.now(timezone.utc)
                ed.confidence = 1.0
            elif action == 'update':
                if new_value is not None:
                    ed.field_value = str(new_value)
                ed.verified = True
                ed.verified_by = current_user
                ed.verified_at = datetime.now(timezone.utc)
                ed.confidence = 1.0

            db.commit()
            logger.info(
                "Field %s %s by %s (session %s)",
                extracted_data_id, action, current_user, session_id,
            )
            return jsonify({
                'success': True,
                'message': 'Feld aktualisiert.',
                'value': ed.field_value,
                'verified': ed.verified,
            })
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error("Error verifying field in session %s: %s", session_id, e, exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren.'}), 500


# ---------------------------------------------------------------------------
# 13. POST /sessions/<id>/manual-contract - Add manual contract (AJAX)
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/manual-contract', methods=['POST'])
@require_login
def add_manual_contract(session_id):
    """Add a manually entered contract with fields."""
    try:
        _session, current_user = _check_session_access(session_id)
        data = request.get_json(silent=True) or {}
        type_key = data.get('type_key', '')
        fields = data.get('fields', {})

        from app.config.finanz_checklist import CONTRACT_TYPES, get_fields_for_type

        if type_key not in CONTRACT_TYPES:
            return jsonify({'success': False, 'message': 'Unbekannte Vertragsart.'}), 400

        from app.models.finanzberatung import (
            FinanzDocument, FinanzExtractedData, DocumentType, DocumentStatus,
        )
        from app.models import get_db_session as _get_db
        db = _get_db()
        try:
            # Create a virtual document for manual entry
            try:
                doc_type = DocumentType(type_key)
            except ValueError:
                doc_type = DocumentType.SONSTIGE

            ct = CONTRACT_TYPES[type_key]
            doc = FinanzDocument(
                session_id=session_id,
                original_filename=f"Manuell: {ct['label']}",
                stored_filename=f"manual_{session_id}_{type_key}_{datetime.now(timezone.utc).timestamp():.0f}",
                file_hash=f"manual_{session_id}_{type_key}_{datetime.now(timezone.utc).timestamp():.0f}",
                file_size=0,
                mime_type="application/manual",
                document_type=doc_type,
                status=DocumentStatus.ANALYZED,
                classification_confidence=1.0,
                extracted_text="Manuell erfasst",
                page_count=0,
            )
            db.add(doc)
            db.flush()  # Get doc.id

            # Add fields
            field_defs = get_fields_for_type(type_key)
            field_map = {f["name"]: f for f in field_defs}
            count = 0
            for fname, fvalue in fields.items():
                if not fvalue or fname not in field_map:
                    continue
                fdef = field_map[fname]
                ed = FinanzExtractedData(
                    document_id=doc.id,
                    field_name=fname,
                    field_value=str(fvalue),
                    field_type=fdef["type"],
                    confidence=1.0,
                    source_text="Manuell erfasst",
                    verified=True,
                    verified_by=current_user,
                    verified_at=datetime.now(timezone.utc),
                )
                db.add(ed)
                count += 1

            db.commit()
            logger.info(
                "Manual contract added: type=%s, fields=%d, user=%s, session=%s",
                type_key, count, current_user, session_id,
            )
            return jsonify({
                'success': True,
                'message': f'{ct["label"]} manuell hinzugefuegt ({count} Felder).',
                'document_id': doc.id,
            })

        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error("Error adding manual contract to session %s: %s", session_id, e, exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler beim Hinzufuegen.'}), 500


# ---------------------------------------------------------------------------
# 14. POST /sessions/<id>/start-analysis - Trigger pipeline (AJAX)
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/start-analysis', methods=['POST'])
@require_login
def start_analysis(session_id):
    """Trigger the document processing pipeline for unprocessed documents."""
    try:
        _check_session_access(session_id)
        from app.models.finanzberatung import FinanzDocument, DocumentStatus
        from app.models import get_db_session as _get_db

        db = _get_db()
        try:
            # Find documents that need processing
            docs = db.query(FinanzDocument).filter(
                FinanzDocument.session_id == session_id,
                FinanzDocument.status == DocumentStatus.UPLOADED,
            ).all()

            if not docs:
                return jsonify({
                    'success': True,
                    'message': 'Keine unverarbeiteten Dokumente vorhanden.',
                    'queued': 0,
                })

            # Launch pipelines
            from app.services.finanz_tasks import process_document_pipeline
            queued = 0
            for doc in docs:
                try:
                    process_document_pipeline(doc.id, session_id)
                    queued += 1
                except Exception as e:
                    logger.error("Failed to queue pipeline for doc %s: %s", doc.id, e)

            return jsonify({
                'success': True,
                'message': f'{queued} Dokument(e) in Analyse-Queue.',
                'queued': queued,
            })
        finally:
            db.close()

    except Exception as e:
        logger.error("Error starting analysis for session %s: %s", session_id, e, exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler beim Starten der Analyse.'}), 500


# ---------------------------------------------------------------------------
# 15. POST /sessions/<id>/generate-scorecard - Generate scorecard (AJAX)
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/generate-scorecard', methods=['POST'])
@require_login
def generate_scorecard(session_id):
    """Generate scorecards for the session."""
    try:
        _check_session_access(session_id)
        from app.services.finanz_scorecard_service import FinanzScorecardService
        service = FinanzScorecardService()
        results = service.generate_scorecard(session_id)
        return jsonify({
            'success': True,
            'message': f'{len(results)} Bewertungen erstellt.',
            'scorecards': results,
        })
    except Exception as e:
        logger.error("Error generating scorecard for session %s: %s", session_id, e, exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler bei der Bewertung.'}), 500


# ---------------------------------------------------------------------------
# 16. GET /sessions/<id>/export/excel - Excel export
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/export/excel')
@require_login
def export_excel(session_id):
    """Download Excel export for the session."""
    try:
        current_user = _get_current_user()
        from app.services.finanz_export_service import FinanzExportService

        service = FinanzExportService()
        buffer = service.export_excel(session_id)

        # Audit log
        try:
            finanz_session = session_service.get_session(session_id, username=None)
            customer = finanz_session.customer_name if finanz_session else 'Unbekannt'
            from app.services.audit_service import audit_service
            audit_service.log('finanz_export', current_user, {
                'session_id': session_id,
                'format': 'excel',
                'customer_name': customer,
            })
        except Exception:
            pass

        filename = f"Finanzberatung_{session_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return send_file(
            buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        logger.error("Error exporting Excel for session %s: %s", session_id, e, exc_info=True)
        flash('Fehler beim Excel-Export.', 'error')
        return redirect(url_for('finanzberatung.finanz_sessions.session_detail', session_id=session_id))


# ---------------------------------------------------------------------------
# 17. GET /sessions/<id>/export/pdf - PDF export
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/export/pdf')
@require_login
def export_pdf(session_id):
    """Download PDF export for the session."""
    try:
        current_user = _get_current_user()
        from app.services.finanz_export_service import FinanzExportService

        service = FinanzExportService()
        buffer = service.export_pdf(session_id)

        # Audit log
        try:
            finanz_session = session_service.get_session(session_id, username=None)
            customer = finanz_session.customer_name if finanz_session else 'Unbekannt'
            from app.services.audit_service import audit_service
            audit_service.log('finanz_export', current_user, {
                'session_id': session_id,
                'format': 'pdf',
                'customer_name': customer,
            })
        except Exception:
            pass

        filename = f"Finanzberatung_{session_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        logger.error("Error exporting PDF for session %s: %s", session_id, e, exc_info=True)
        flash('Fehler beim PDF-Export.', 'error')
        return redirect(url_for('finanzberatung.finanz_sessions.session_detail', session_id=session_id))


# ---------------------------------------------------------------------------
# 18. GET /sessions/<id>/contract-types - Available contract types for manual add
# ---------------------------------------------------------------------------
@sessions_bp.route('/sessions/<int:session_id>/contract-types')
@require_login
def get_contract_types(session_id):
    """Get all available contract types with their fields for the manual add modal."""
    from app.config.finanz_checklist import (
        CONTRACT_TYPES, CHECKLIST_CATEGORIES, get_fields_for_type,
    )
    categories = []
    for cat_key, cat_def in CHECKLIST_CATEGORIES.items():
        types = []
        for type_key in cat_def["types"]:
            ct = CONTRACT_TYPES.get(type_key)
            if ct:
                types.append({
                    "key": type_key,
                    "label": ct["label"],
                    "icon": ct.get("icon", "file"),
                    "fields": get_fields_for_type(type_key),
                })
        categories.append({
            "key": cat_key,
            "label": cat_def["label"],
            "types": types,
        })
    return jsonify(categories)
