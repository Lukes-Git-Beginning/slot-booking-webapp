# -*- coding: utf-8 -*-
"""
Tracking System Package — backward-compatible re-exports.

All external imports continue to work unchanged:
    from app.services.tracking_system import BookingTracker
    from app.services.tracking_system import tracking_system
    from app.services.tracking_system import recalculate_all_outcomes
    from app.services.tracking_system import run_daily_outcome_check
    from app.services.tracking_system import backfill_september_data
"""

import os
import json
import logging
from datetime import datetime, timedelta

import pytz

from app.services.tracking_system.core import BookingTracker

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")


# ----------------- Utility Funktionen -----------------
def recalculate_all_outcomes():
    """
    Neuberechnung aller Outcomes mit korrigiertem Mapping
    Nützlich nach Änderung der Farb-Logik
    """
    tracker = BookingTracker()

    # Lösche alte Outcomes
    if os.path.exists(tracker.outcomes_file):
        os.rename(tracker.outcomes_file, tracker.outcomes_file + ".backup")

    # Lösche alte Metriken
    if os.path.exists(tracker.metrics_file):
        os.rename(tracker.metrics_file, tracker.metrics_file + ".backup")

    logger.info("Recalculating all outcomes with new color mapping...")

    # Berechne die letzten 30 Tage neu
    today = datetime.now(TZ).date()
    for i in range(30):
        check_date = today - timedelta(days=i)
        tracker.check_daily_outcomes(check_date)

    logger.info("Recalculation complete!")


def backfill_september_data():
    """
    Backfill tracking data from September 2nd, 2025 to today
    This will scan the Google Calendar and process all historical appointments
    """
    from app.config.base import config
    from app.core.google_calendar import get_google_calendar_service

    service = get_google_calendar_service()
    CENTRAL_CALENDAR_ID = config.CENTRAL_CALENDAR_ID

    logger.info("Starting September data backfill...")

    tracker = BookingTracker()

    # Set start date to September 2nd, 2025
    start_date = datetime(2025, 9, 2).date()
    today = datetime.now(TZ).date()

    # Calculate total days
    total_days = (today - start_date).days + 1
    processed_days = 0

    logger.info(f"Backfilling from {start_date} to {today} ({total_days} days)")

    # Process each day
    current_date = start_date
    while current_date <= today:
        try:
            logger.debug(f"Processing {current_date} ({processed_days + 1}/{total_days})")
            tracker.check_daily_outcomes(current_date)
            processed_days += 1

        except Exception as e:
            logger.error(f"Error processing {current_date}: {e}")

        current_date += timedelta(days=1)

    logger.info(f"Backfill complete! Processed {processed_days} days")
    logger.info("Dashboard will now show data from September 2nd onwards")


# ----------------- Cron Job Function -----------------
def run_daily_outcome_check():
    """
    Diese Funktion sollte täglich um 21:00 Uhr laufen
    Kann in GitHub Actions oder als Cron Job eingerichtet werden
    """
    tracker = BookingTracker()

    # Prüfe heutigen Tag
    today = datetime.now(TZ).date()
    outcomes = tracker.check_daily_outcomes(today)

    # Optional: Prüfe auch gestern (falls der Job mal ausfällt)
    yesterday = today - timedelta(days=1)
    tracker.check_daily_outcomes(yesterday)

    logger.info(f"Daily outcome check completed at {datetime.now(TZ).strftime('%H:%M')}")

    # Tracking-Luecken pruefen
    try:
        gaps = tracker.detect_tracking_gaps(lookback_days=7)
        if gaps:
            logger.warning(f"Tracking gaps found during daily check: {gaps}")
    except Exception as e:
        logger.warning(f"Gap detection failed: {e}")

    # Generiere Dashboard
    dashboard = tracker.get_performance_dashboard()

    # Sende Alert bei vielen No-Shows
    if dashboard["last_7_days"].get("no_show_rate", 0) > 20:
        logger.warning(f"ALERT: High no-show rate (7 days): {dashboard['last_7_days']['no_show_rate']}%")

    # Generiere Wochenbericht am Montag
    if datetime.now(TZ).weekday() == 0:  # Montag
        last_week = datetime.now(TZ).isocalendar()[1] - 1
        report = tracker.get_weekly_report(last_week)

        report_file = os.path.join(tracker.data_dir, f"weekly_report_{last_week}.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"Weekly report generated: {report_file}")


# ----------------- Singleton Instance -----------------
tracking_system = BookingTracker()
