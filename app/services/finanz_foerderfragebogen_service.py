# -*- coding: utf-8 -*-
"""
Foerderfragebogen Service - CRUD and Eligibility Calculation

Based on the ZFA Erfassungsbogen für Förderungen PDF.
Manages the subsidy questionnaire lifecycle with JSON-based answers.
"""

import json
import logging
from datetime import datetime

from app.models import get_db_session
from app.models.finanzberatung import FinanzFoerderFragebogen
from app.config.foerder_katalog import (
    get_eligible_foerderungen,
    get_total_yearly_benefit,
)

logger = logging.getLogger(__name__)


# Direct model columns (not in JSON answers)
STAMM_FIELDS = [
    'mandant_vorname', 'mandant_nachname', 'mandant_geburtsdatum', 'mandant_beruf',
    'partner_vorname', 'partner_nachname', 'partner_geburtsdatum', 'partner_beruf',
    'anschrift', 'anzahl_kindergeldberechtigt',
    'brutto_mandant', 'brutto_partner',
    'weitere_einkuenfte_mandant', 'weitere_einkuenfte_partner',
    'staatsangehoerigkeit_mandant', 'staatsangehoerigkeit_partner',
    'weitere_notizen',
]

BOOL_STAMM = {'schufa_mandant', 'schufa_partner'}
INT_STAMM = {'anzahl_kindergeldberechtigt'}
FLOAT_STAMM = {'brutto_mandant', 'brutto_partner'}


def _coerce_stamm(field, value):
    """Coerce a stamm field value to correct type."""
    if value is None or value == '' or value == 'null':
        return None
    if field in BOOL_STAMM:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ('true', '1', 'ja', 'yes', 'on')
    if field in INT_STAMM:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if field in FLOAT_STAMM:
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

    def save_answers(self, session_id: int, data: dict, username: str) -> FinanzFoerderFragebogen:
        """
        Save all questionnaire data, calculate eligibility, and store results.

        Args:
            session_id: The session ID
            data: Full form data dict (stamm fields + answers + kinder)
            username: Who completed the questionnaire
        """
        db = get_db_session()
        try:
            ffb = db.query(FinanzFoerderFragebogen).filter_by(
                session_id=session_id
            ).first()
            if not ffb:
                ffb = FinanzFoerderFragebogen(session_id=session_id)
                db.add(ffb)

            # Set stamm fields (direct columns)
            for field in STAMM_FIELDS:
                if field in data:
                    setattr(ffb, field, _coerce_stamm(field, data[field]))
            for field in BOOL_STAMM:
                if field in data:
                    setattr(ffb, field, _coerce_stamm(field, data[field]))

            # Set kinder
            if 'kinder' in data:
                kinder = data['kinder']
                if isinstance(kinder, str):
                    ffb.kinder = kinder
                else:
                    ffb.kinder = json.dumps(kinder, ensure_ascii=False)

            # All other fields go into JSON answers
            answers = {}
            skip_fields = set(STAMM_FIELDS) | BOOL_STAMM | {'kinder', 'csrf_token'}
            for key, value in data.items():
                if key not in skip_fields:
                    answers[key] = value
            ffb.set_answers(answers)

            # Calculate eligibility
            full_data = ffb.to_full_dict()
            eligible = get_eligible_foerderungen(full_data)
            total_benefit = get_total_yearly_benefit(full_data)

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
                "FFB saved for session %s: %d eligible, %.0f EUR/year",
                session_id, len(eligible), total_benefit
            )
            return ffb
        except Exception as e:
            db.rollback()
            logger.error("Failed to save FFB for session %s: %s", session_id, e, exc_info=True)
            raise
        finally:
            db.close()

    def autosave(self, session_id: int, data: dict):
        """Save answers without eligibility calculation (called on step change)."""
        db = get_db_session()
        try:
            ffb = db.query(FinanzFoerderFragebogen).filter_by(
                session_id=session_id
            ).first()
            if not ffb:
                ffb = FinanzFoerderFragebogen(session_id=session_id)
                db.add(ffb)

            # Set stamm fields
            for field in STAMM_FIELDS:
                if field in data:
                    setattr(ffb, field, _coerce_stamm(field, data[field]))
            for field in BOOL_STAMM:
                if field in data:
                    setattr(ffb, field, _coerce_stamm(field, data[field]))

            # Kinder
            if 'kinder' in data:
                kinder = data['kinder']
                ffb.kinder = json.dumps(kinder, ensure_ascii=False) if isinstance(kinder, list) else kinder

            # JSON answers
            answers = ffb.get_answers()
            skip_fields = set(STAMM_FIELDS) | BOOL_STAMM | {'kinder', 'csrf_token'}
            for key, value in data.items():
                if key not in skip_fields:
                    answers[key] = value
            ffb.set_answers(answers)

            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.warning("FFB autosave failed for session %s: %s", session_id, e)
            return False
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


# Singleton
foerderfragebogen_service = FinanzFoerderFragebogenService()
