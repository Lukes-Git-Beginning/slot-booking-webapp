# -*- coding: utf-8 -*-
"""
Foerderfragebogen Service - CRUD and Eligibility Calculation

Manages the subsidy questionnaire lifecycle:
- Create/update questionnaire for a session
- Calculate eligibility based on answers
- Mark questionnaire as completed
"""

import json
import logging
from datetime import datetime

from app.models import get_db_session
from app.models.finanzberatung import FinanzFoerderFragebogen, FinanzSession
from app.config.foerder_katalog import (
    get_eligible_foerderungen,
    get_total_yearly_benefit,
)

logger = logging.getLogger(__name__)


# Fields that map from form data to model columns
ANSWER_FIELDS = [
    'geburtsdatum', 'familienstand', 'kinder_anzahl', 'kinder_geburtsjahre',
    'beschaeftigung', 'rv_pflichtig', 'bruttojahreseinkommen', 'zve',
    'arbeitgeber_vl', 'arbeitgeber_bav',
    'kinder_im_haushalt_u18', 'kinder_in_ausbildung', 'v0800_beantragt',
    'schwangerschaft_geplant',
    'wohnsituation', 'immobilie_geplant', 'bausparvertrag',
    'hat_riester', 'hat_ruerup', 'hat_bav', 'hat_bu', 'hat_pflegezusatz',
    'hat_vl_vertrag',
]

BOOL_FIELDS = {
    'rv_pflichtig', 'arbeitgeber_vl', 'arbeitgeber_bav',
    'v0800_beantragt', 'schwangerschaft_geplant', 'bausparvertrag',
    'hat_riester', 'hat_ruerup', 'hat_bav', 'hat_pflegezusatz', 'hat_vl_vertrag',
}

INT_FIELDS = {
    'kinder_anzahl', 'kinder_im_haushalt_u18', 'kinder_in_ausbildung',
}

FLOAT_FIELDS = {
    'bruttojahreseinkommen', 'zve',
}


def _coerce_value(field: str, value):
    """Coerce form value to correct Python type."""
    if value is None or value == '' or value == 'null':
        return None

    if field in BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ('true', '1', 'ja', 'yes', 'on')

    if field in INT_FIELDS:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    if field in FLOAT_FIELDS:
        try:
            return float(str(value).replace(',', '.'))
        except (ValueError, TypeError):
            return None

    return str(value)


class FinanzFoerderFragebogenService:
    """Service for managing the subsidy questionnaire."""

    def get_or_create(self, session_id: int) -> FinanzFoerderFragebogen:
        """Get existing questionnaire or create a new one for the session."""
        db = get_db_session()
        try:
            ffb = db.query(FinanzFoerderFragebogen).filter_by(
                session_id=session_id
            ).first()

            if not ffb:
                ffb = FinanzFoerderFragebogen(session_id=session_id)
                db.add(ffb)
                db.commit()
                db.refresh(ffb)
                logger.info("Created new FFB for session %s", session_id)

            return ffb
        except Exception as e:
            db.rollback()
            logger.error("Failed to get/create FFB for session %s: %s", session_id, e)
            raise
        finally:
            db.close()

    def save_answers(self, session_id: int, form_data: dict, username: str) -> FinanzFoerderFragebogen:
        """
        Save questionnaire answers, calculate eligibility, and store results.

        Args:
            session_id: The session to save answers for
            form_data: Dict of field_name -> value from the form
            username: Who completed the questionnaire

        Returns:
            Updated FinanzFoerderFragebogen
        """
        db = get_db_session()
        try:
            ffb = db.query(FinanzFoerderFragebogen).filter_by(
                session_id=session_id
            ).first()

            if not ffb:
                ffb = FinanzFoerderFragebogen(session_id=session_id)
                db.add(ffb)

            # Set answer fields
            for field in ANSWER_FIELDS:
                if field in form_data:
                    setattr(ffb, field, _coerce_value(field, form_data[field]))

            # Calculate eligibility
            answers = ffb.to_answers_dict()
            eligible = get_eligible_foerderungen(answers)
            total_benefit = get_total_yearly_benefit(answers)

            ffb.eligible_foerderungen = json.dumps(
                [{'id': f['id'], 'name': f['name'], 'kategorie': f['kategorie'],
                  'details': f.get('details', ''), 'schaetz_vorteil': f.get('schaetz_vorteil', 0)}
                 for f in eligible],
                ensure_ascii=False
            )
            ffb.potential_yearly_benefit = total_benefit
            ffb.completed_at = datetime.utcnow()
            ffb.completed_by = username

            db.commit()
            db.refresh(ffb)

            logger.info(
                "FFB saved for session %s: %d eligible subsidies, %.0f EUR/year benefit",
                session_id, len(eligible), total_benefit
            )
            return ffb

        except Exception as e:
            db.rollback()
            logger.error("Failed to save FFB for session %s: %s", session_id, e, exc_info=True)
            raise
        finally:
            db.close()

    def get_results(self, session_id: int) -> dict:
        """Get questionnaire results for display."""
        db = get_db_session()
        try:
            ffb = db.query(FinanzFoerderFragebogen).filter_by(
                session_id=session_id
            ).first()

            if not ffb or not ffb.completed_at:
                return None

            eligible = []
            if ffb.eligible_foerderungen:
                try:
                    eligible = json.loads(ffb.eligible_foerderungen)
                except json.JSONDecodeError:
                    eligible = []

            return {
                'completed_at': ffb.completed_at,
                'completed_by': ffb.completed_by,
                'eligible_count': len(eligible),
                'eligible_foerderungen': eligible,
                'potential_yearly_benefit': ffb.potential_yearly_benefit or 0,
            }
        finally:
            db.close()


# Singleton instance
foerderfragebogen_service = FinanzFoerderFragebogenService()
