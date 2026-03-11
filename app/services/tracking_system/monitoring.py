# -*- coding: utf-8 -*-
"""Detect tracking gaps in JSON and PostgreSQL data."""

import os
import json
import logging
from datetime import datetime, timedelta

import pytz

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")

# PostgreSQL Models
try:
    from app.models import BookingOutcome, is_postgres_enabled
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


def detect_tracking_gaps(tracker, lookback_days=14):
    """
    Erkennt fehlende Tracking-Tage in JSON und PostgreSQL.
    Prueft die letzten N Werktage auf Luecken.

    Returns:
        Liste fehlender Datums-Strings (YYYY-MM-DD)
    """
    today = datetime.now(TZ).date()
    missing_dates = []

    # JSON-Daten laden
    json_dates = set()
    if os.path.exists(tracker.metrics_file):
        try:
            with open(tracker.metrics_file, "r", encoding="utf-8") as f:
                all_metrics = json.load(f)
            json_dates = set(all_metrics.keys())
        except Exception:
            pass

    # PG-Daten pruefen
    pg_dates = set()
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            from app.utils.db_utils import db_session_scope_no_commit
            from sqlalchemy import func
            cutoff = today - timedelta(days=lookback_days)
            with db_session_scope_no_commit() as session:
                rows = session.query(
                    func.distinct(BookingOutcome.date)
                ).filter(BookingOutcome.date >= cutoff).all()
                pg_dates = {str(row[0]) for row in rows}
        except Exception:
            pass

    # Pruefe jeden Werktag im Lookback-Fenster
    current_date = today - timedelta(days=lookback_days)
    while current_date <= today - timedelta(days=1):
        if current_date.weekday() < 5:
            date_str = str(current_date)
            if date_str not in json_dates and date_str not in pg_dates:
                missing_dates.append(date_str)
        current_date += timedelta(days=1)

    if missing_dates:
        logger.warning(f"Tracking-Luecken: {len(missing_dates)} Werktage ohne Daten: {missing_dates}")
        try:
            from app.services.notification_service import notification_service
            notification_service.create_notification(
                roles=['admin'],
                title='Tracking-Luecken erkannt',
                message=f'{len(missing_dates)} Werktage ohne Tracking-Daten: {", ".join(missing_dates[:5])}{"..." if len(missing_dates) > 5 else ""}',
                notification_type='warning',
                show_popup=False
            )
        except Exception:
            pass

    return missing_dates
