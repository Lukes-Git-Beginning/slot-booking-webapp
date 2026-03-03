# -*- coding: utf-8 -*-
"""
Finanzberatung Admin Sub-Blueprint - Session Administration & DSGVO

Routes:
- GET  /admin/sessions                       - Session list with filters
- GET  /admin/sessions/<id>                  - Session detail (readonly)
- POST /admin/sessions/<id>/mark-deletion    - DSGVO deletion mark
- POST /admin/sessions/<id>/execute-deletion - Execute file deletion
- POST /admin/batch-delete                   - Batch delete expired sessions
"""

import logging
from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify,
    session as flask_session, redirect, url_for, flash,
)

from app.utils.decorators import require_admin
from app.services.finanz_dsgvo_service import FinanzDSGVOService
from app.models import get_db_session
from app.models.finanzberatung import (
    FinanzSession, FinanzDocument, SessionStatus,
)

logger = logging.getLogger(__name__)

admin_bp = Blueprint('finanz_admin', __name__)

# Service instance
dsgvo_service = FinanzDSGVOService()


# ---------------------------------------------------------------------------
# GET /admin/sessions - Session list with filters
# ---------------------------------------------------------------------------
@admin_bp.route('/admin/sessions')
@require_admin
def admin_session_list():
    """Admin view: list all sessions with filters and deletion queue."""
    try:
        db = get_db_session()
        try:
            # Filters from query params
            status_filter = request.args.get('status', '')
            opener_filter = request.args.get('opener', '')
            date_from = request.args.get('date_from', '')
            date_to = request.args.get('date_to', '')

            query = db.query(FinanzSession)

            if status_filter:
                query = query.filter(FinanzSession.status == status_filter)
            if opener_filter:
                query = query.filter(FinanzSession.opener_username == opener_filter)
            if date_from:
                try:
                    dt_from = datetime.strptime(date_from, '%Y-%m-%d')
                    query = query.filter(FinanzSession.created_at >= dt_from)
                except ValueError:
                    pass
            if date_to:
                try:
                    dt_to = datetime.strptime(date_to, '%Y-%m-%d')
                    query = query.filter(FinanzSession.created_at <= dt_to)
                except ValueError:
                    pass

            sessions = query.order_by(FinanzSession.created_at.desc()).all()

            # Enrich with document count
            session_data = []
            for s in sessions:
                doc_count = db.query(FinanzDocument).filter(
                    FinanzDocument.session_id == s.id
                ).count()
                session_data.append({
                    'id': s.id,
                    'customer_name': s.customer_name,
                    'opener_username': s.opener_username,
                    'closer_username': s.closer_username,
                    'status': s.status,
                    'document_count': doc_count,
                    'created_at': s.created_at,
                    'appointment_date': s.appointment_date,
                    'deletion_requested_at': s.deletion_requested_at,
                })

            # Stats
            total = len(session_data)
            active_count = len([s for s in session_data if s['status'] == 'active'])
            analysis_count = len([s for s in session_data if s['status'] == 'in_analysis'])

            # Deletion queue
            deletion_queue = dsgvo_service.get_deletion_queue()

            # Unique openers for filter dropdown
            openers = sorted(set(
                s['opener_username'] for s in session_data if s['opener_username']
            ))

            # Status values for filter
            statuses = [s.value for s in SessionStatus]

            return render_template(
                'finanzberatung/admin_sessions.html',
                sessions=session_data,
                deletion_queue=deletion_queue,
                stats={
                    'total': total,
                    'active': active_count,
                    'in_analysis': analysis_count,
                    'deletion_queue': len(deletion_queue),
                },
                openers=openers,
                statuses=statuses,
                filters={
                    'status': status_filter,
                    'opener': opener_filter,
                    'date_from': date_from,
                    'date_to': date_to,
                },
            )

        finally:
            db.close()

    except Exception as e:
        logger.error("Admin session list error: %s", e, exc_info=True)
        flash('Fehler beim Laden der Admin-Sitzungen.', 'error')
        return redirect(url_for('hub.dashboard'))


# ---------------------------------------------------------------------------
# GET /admin/sessions/<id> - Session detail (readonly)
# ---------------------------------------------------------------------------
@admin_bp.route('/admin/sessions/<int:session_id>')
@require_admin
def admin_session_detail(session_id):
    """Admin readonly view of a session."""
    try:
        db = get_db_session()
        try:
            session = db.query(FinanzSession).filter(
                FinanzSession.id == session_id
            ).first()

            if session is None:
                flash('Session nicht gefunden.', 'error')
                return redirect(url_for('finanzberatung.finanz_admin.admin_session_list'))

            documents = db.query(FinanzDocument).filter(
                FinanzDocument.session_id == session_id
            ).all()

            return render_template(
                'finanzberatung/admin_session_detail.html',
                session=session,
                documents=documents,
            )

        finally:
            db.close()

    except Exception as e:
        logger.error("Admin session detail error: %s", e, exc_info=True)
        flash('Fehler beim Laden der Session-Details.', 'error')
        return redirect(url_for('finanzberatung.finanz_admin.admin_session_list'))


# ---------------------------------------------------------------------------
# POST /admin/sessions/<id>/mark-deletion - DSGVO deletion mark
# ---------------------------------------------------------------------------
@admin_bp.route('/admin/sessions/<int:session_id>/mark-deletion', methods=['POST'])
@require_admin
def mark_deletion(session_id):
    """Mark a session for DSGVO deletion (30-day retention)."""
    admin_user = flask_session.get('user', 'unknown')
    try:
        result = dsgvo_service.mark_for_deletion(session_id, admin_user)
        return jsonify({'success': True, **result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error("Mark deletion error: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Interner Fehler'}), 500


# ---------------------------------------------------------------------------
# POST /admin/sessions/<id>/execute-deletion - Execute file deletion
# ---------------------------------------------------------------------------
@admin_bp.route('/admin/sessions/<int:session_id>/execute-deletion', methods=['POST'])
@require_admin
def execute_deletion(session_id):
    """Execute file deletion after 30-day retention."""
    try:
        result = dsgvo_service.execute_deletion(session_id)
        return jsonify({'success': True, **result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error("Execute deletion error: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Interner Fehler'}), 500


# ---------------------------------------------------------------------------
# POST /admin/batch-delete - Batch delete all expired sessions
# ---------------------------------------------------------------------------
@admin_bp.route('/admin/batch-delete', methods=['POST'])
@require_admin
def batch_delete():
    """Batch delete all sessions whose retention period has expired."""
    try:
        result = dsgvo_service.batch_delete_expired()
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error("Batch deletion error: %s", e, exc_info=True)
        return jsonify({'success': False, 'error': 'Interner Fehler'}), 500
