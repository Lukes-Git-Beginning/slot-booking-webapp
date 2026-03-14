# -*- coding: utf-8 -*-
"""
Foerderfragebogen Routes - ZFA Subsidy Questionnaire Wizard

Routes:
- GET /sessions/<id>/foerderfragebogen: Render wizard form
- POST /sessions/<id>/foerderfragebogen: Save answers and calculate eligibility
- POST /sessions/<id>/foerderfragebogen/autosave: AJAX auto-save on step change
- POST /sessions/<id>/foerderfragebogen/calculate: AJAX eligibility preview
"""

import logging

from flask import (
    Blueprint, render_template, request, session as flask_session,
    redirect, url_for, flash, jsonify,
)

from app.models import get_db_session
from app.models.finanzberatung import FinanzSession
from app.services.finanz_foerderfragebogen_service import foerderfragebogen_service
from app.config.foerder_katalog import calculate_eligibility, get_total_yearly_benefit

logger = logging.getLogger(__name__)

questionnaire_bp = Blueprint(
    'finanz_questionnaire', __name__
)


def _get_session_or_404(session_id):
    """Get FinanzSession or return None with flash."""
    db = get_db_session()
    try:
        fs = db.query(FinanzSession).get(session_id)
        if not fs:
            flash("Session nicht gefunden", "error")
            return None
        return fs
    finally:
        db.close()


@questionnaire_bp.route('/sessions/<int:session_id>/foerderfragebogen')
def foerderfragebogen(session_id):
    """Render the subsidy questionnaire wizard."""
    fs = _get_session_or_404(session_id)
    if not fs:
        return redirect(url_for('finanzberatung.finanz_sessions.session_list'))

    ffb = foerderfragebogen_service.get_or_create(session_id)
    existing = ffb.to_full_dict() if ffb else {}

    return render_template(
        'finanzberatung/foerderfragebogen.html',
        session=fs,
        session_id=session_id,
        answers=existing,
    )


@questionnaire_bp.route('/sessions/<int:session_id>/foerderfragebogen', methods=['POST'])
def save_foerderfragebogen(session_id):
    """Save questionnaire answers and calculate eligibility."""
    fs = _get_session_or_404(session_id)
    if not fs:
        return redirect(url_for('finanzberatung.finanz_sessions.session_list'))

    username = flask_session.get('user', 'unknown')

    try:
        form_data = request.form.to_dict()
        foerderfragebogen_service.save_answers(session_id, form_data, username)

        flash("Förderfragebogen gespeichert — Ergebnisse berechnet!", "success")
        return redirect(url_for(
            'finanzberatung.finanz_questionnaire.foerderfragebogen',
            session_id=session_id,
            show_results='true',
        ))
    except Exception as e:
        logger.error("Failed to save FFB: %s", e, exc_info=True)
        flash("Fehler beim Speichern des Fragebogens", "error")
        return redirect(url_for(
            'finanzberatung.finanz_questionnaire.foerderfragebogen',
            session_id=session_id,
        ))


@questionnaire_bp.route('/sessions/<int:session_id>/foerderfragebogen/autosave', methods=['POST'])
def autosave_foerderfragebogen(session_id):
    """AJAX: Auto-save answers on step change."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        ok = foerderfragebogen_service.autosave(session_id, data)
        return jsonify({'ok': ok})
    except Exception as e:
        logger.warning("FFB autosave failed for session %s: %s", session_id, e)
        return jsonify({'error': str(e)}), 500


@questionnaire_bp.route('/sessions/<int:session_id>/foerderfragebogen/calculate', methods=['POST'])
def calculate_foerderfragebogen(session_id):
    """AJAX: Calculate eligibility without saving (live preview)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        results = calculate_eligibility(data)
        eligible = [r for r in results if r['eligible']]
        total = get_total_yearly_benefit(data)

        return jsonify({
            'eligible': eligible,
            'total_count': len(eligible),
            'total_yearly_benefit': total,
        })
    except Exception as e:
        logger.error("FFB calculation failed: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500
