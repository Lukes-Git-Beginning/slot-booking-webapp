# -*- coding: utf-8 -*-
"""Daily outcome checking: scan calendar events, classify outcomes, write metrics."""

import os
import re
import json
import logging
from datetime import datetime, timedelta, time
from collections import defaultdict

import pytz

from app.services.tracking_system.utils import _atomic_json_write
from app.services.tracking_system.converters import _get_potential_type, _get_outcome_from_title_and_color
from app.services.tracking_system.customer_profiles import _update_customer_profiles

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")

CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")

# Berater-Konfiguration für Consultant-Extraction
from app.config.base import consultant_config

# Mapping: Login-Username → Display-Name
USERNAME_TO_DISPLAY = {
    "ann-kathrin.welge": "Ann-Kathrin",
    "christian.mast": "Christian",
    "dominik.mikic": "Dominik",
    "sara.mast": "Sara",
    "sonja.mast": "Sonja",
    "tim.kreisel": "Tim",
    "simon.mast": "Simon",
    "alexandra.börner": "Alexandra",
    "ladislav.heka": "Ladislav",
    "yasmine.schumacher": "Yasmine",
    "benjamin.kerstan": "Ben",
    "yannis.maeusle": "Yannis",
    "admin": "Admin",
}

# PostgreSQL Models
try:
    from app.models import BookingOutcome, DailyMetrics, is_postgres_enabled
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


def check_daily_outcomes(tracker, check_date=None):
    """
    Prüft alle Termine eines Tages auf No-Shows/Outcomes
    Standardmäßig prüft es den aktuellen Tag
    Sollte täglich um 21:00 Uhr laufen
    """
    if check_date is None:
        check_date = datetime.now(TZ).date()
    else:
        check_date = datetime.strptime(check_date, "%Y-%m-%d").date() if isinstance(check_date, str) else check_date

    logger.debug(f"Checking outcomes for {check_date}")

    # Hole alle Events des Tages
    start_time = TZ.localize(datetime.combine(check_date, time.min))
    end_time = TZ.localize(datetime.combine(check_date, time.max))

    try:
        events_result = tracker.service.events().list(
            calendarId=CENTRAL_CALENDAR_ID,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=100
        ).execute()

        events = events_result.get('items', [])
        outcomes_tracked = 0
        pg_failed_count = 0

        for event in events:
            # Skip Platzhalter (nur Zahlen)
            if event.get("summary", "").isdigit():
                continue

            # Extrahiere Daten
            customer_name = event.get("summary", "Unknown")
            color_id = event.get("colorId", "9")  # Default: Graphit
            event_start = event.get("start", {}).get("dateTime")

            if not event_start:
                continue

            event_time = datetime.fromisoformat(event_start).strftime("%H:%M")

            # Extrahiere Telefonist aus Event-Organizer
            consultant_name = "Unknown"
            consultant_email = None
            consultants_map = consultant_config.get_consultants()

            # Hole Organizer Email (Telefonist der den Termin erstellt hat)
            organizer = event.get("organizer", {})
            organizer_email = organizer.get("email", "").lower()

            # Matche Organizer Email gegen Consultants Map
            if organizer_email:
                for name, email in consultants_map.items():
                    if organizer_email == email.lower():
                        consultant_name = name
                        consultant_email = organizer_email
                        break

            # Fallback: Parse [Booked by: X] aus Description
            if consultant_name == "Unknown":
                description = event.get("description", "")
                booked_by_match = re.search(r'\[Booked by:\s*([^\]]+)\]', description)
                if booked_by_match:
                    username = booked_by_match.group(1).strip().lower()
                    # Map username to display name
                    consultant_name = USERNAME_TO_DISPLAY.get(username, username.title())

            # WICHTIG: Nutze titel-basierte Outcome-Bestimmung
            outcome = _get_outcome_from_title_and_color(customer_name, color_id)

            # Track outcome
            outcome_data = {
                "id": f"{check_date}_{event_time}_{customer_name}".replace(" ", "_"),
                "timestamp": datetime.now(TZ).isoformat(),
                "customer": customer_name,
                "date": str(check_date),
                "time": event_time,
                "outcome": outcome,
                "color_id": color_id,
                "potential_type": _get_potential_type(color_id),
                "checked_at": datetime.now(TZ).strftime("%H:%M"),
                "description": event.get("description", ""),
                "consultant": consultant_name,
                "consultant_email": consultant_email
            }

            # Spezielle Behandlung für No-Shows
            if outcome == "no_show":
                outcome_data["alert"] = "NO_SHOW_DETECTED"
                logger.warning(f"No-Show detected: {customer_name} at {event_time}")
            elif outcome == "cancelled":
                logger.info(f"Cancelled: {customer_name} at {event_time}")
            elif outcome == "completed":
                logger.info(f"Completed: {customer_name} at {event_time} (Color: {color_id})")

            # ========== PostgreSQL Dual-Write (mit Retry) ==========
            pg_write_ok = False
            if POSTGRES_AVAILABLE and is_postgres_enabled():
                for attempt in range(2):
                    try:
                        from app.utils.db_utils import db_session_scope
                        with db_session_scope() as db_session:
                            outcome_id = outcome_data["id"]
                            existing = db_session.query(BookingOutcome).filter_by(
                                outcome_id=outcome_id
                            ).first()

                            if existing:
                                existing.outcome = outcome
                                existing.color_id = color_id
                                existing.potential_type = outcome_data["potential_type"]
                                existing.checked_at = outcome_data["checked_at"]
                                existing.description = outcome_data.get("description", "")
                                existing.is_alert = outcome == "no_show"
                                existing.consultant = outcome_data.get("consultant")
                                existing.consultant_email = outcome_data.get("consultant_email")
                            else:
                                pg_outcome = BookingOutcome(
                                    outcome_id=outcome_id,
                                    customer=customer_name,
                                    date=check_date,
                                    time=event_time,
                                    outcome=outcome,
                                    color_id=color_id,
                                    potential_type=outcome_data["potential_type"],
                                    description=outcome_data.get("description", ""),
                                    is_alert=outcome == "no_show",
                                    checked_at=outcome_data["checked_at"],
                                    outcome_timestamp=datetime.now(TZ),
                                    consultant=outcome_data.get("consultant"),
                                    consultant_email=outcome_data.get("consultant_email")
                                )
                                db_session.add(pg_outcome)
                        pg_write_ok = True
                        break
                    except Exception as e:
                        if attempt == 0:
                            import time as time_mod
                            time_mod.sleep(1)
                            logger.warning(f"PG outcome write retry for {outcome_data['id']}: {e}")
                        else:
                            pg_failed_count += 1
                            logger.error(f"PG outcome write FAILED after retry for {outcome_data['id']}: {e}")

            # Speichere Outcome (JSONL)
            with open(tracker.outcomes_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(outcome_data, ensure_ascii=False) + "\n")

            # HubSpot Queue Hook: Ghost/No-Show/Cancelled/Rescheduled → Review-Queue
            if outcome in ("ghost", "no_show", "cancelled", "rescheduled"):
                try:
                    _queue_hubspot_outcome(outcome_data)
                except Exception as hs_err:
                    logger.warning(f"HubSpot queue hook failed: {hs_err}")

            outcomes_tracked += 1

        if pg_failed_count > 0:
            logger.error(f"PG outcome writes: {pg_failed_count} of {outcomes_tracked} FAILED for {check_date}")
        logger.info(f"Tracked {outcomes_tracked} outcomes for {check_date}")

        # Berechne Tagesmetriken
        _calculate_daily_metrics(tracker, check_date, events)

        # Update Kundenprofile
        _update_customer_profiles(tracker)

        return outcomes_tracked

    except Exception as e:
        logger.error(f"Error checking outcomes: {e}")
        return 0


def _queue_hubspot_outcome(outcome_data):
    """Erstelle ein HubSpot Review-Queue Item fuer Ghost/No-Show Outcomes."""
    from app.services.hubspot_service import hubspot_service
    from app.services.hubspot_queue_service import hubspot_queue_service

    if not hubspot_service.is_available:
        return

    # Deal suchen
    booking_data = {
        'customer_name': outcome_data.get('customer', ''),
        'date': outcome_data.get('date', ''),
        'time': outcome_data.get('time', ''),
    }

    # Email aus Description extrahieren falls vorhanden
    description = outcome_data.get('description', '')
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', description)
    if email_match:
        booking_data['email'] = email_match.group(0)

    deal_info = hubspot_service.find_deal_for_booking(booking_data)
    outcome = outcome_data.get('outcome', '')

    # Bestimme suggested action + stage + note
    if outcome == 'ghost' and deal_info:
        was_in_rueckholung = hubspot_service.was_deal_in_stage(
            deal_info['id'], 'rueckholung'
        )
        if was_in_rueckholung:
            suggested_action = 'ghost_repeat'
            stage = hubspot_service.config.STAGE_MAPPING['ghost_repeat']
            note = '2x Ghost - automatisch verschoben'
        else:
            suggested_action = 'ghost_first'
            stage = hubspot_service.config.STAGE_MAPPING['ghost_first']
            note = 'Ghost - automatisch zur Rueckholung'
    elif outcome == 'no_show':
        suggested_action = 'no_show'
        stage = hubspot_service.config.STAGE_MAPPING['no_show']
        note = 'Nicht erschienen - automatisch verschoben'
    elif outcome == 'cancelled':
        suggested_action = 'cancelled'
        stage = hubspot_service.config.STAGE_MAPPING.get('cancelled', '')
        note = 'Storniert - Deal-Stage prüfen'
    elif outcome == 'rescheduled':
        suggested_action = 'rescheduled'
        stage = hubspot_service.config.STAGE_MAPPING.get('rescheduled', '')
        note = 'Termin verschoben - zur Rückholung'
    else:
        # Ghost ohne Deal
        suggested_action = 'ghost_first'
        stage = hubspot_service.config.STAGE_MAPPING.get('ghost_first', '')
        note = 'Ghost - kein Deal gefunden'

    hubspot_queue_service.add_to_queue(
        outcome_data=outcome_data,
        deal_info=deal_info,
        suggested_action=suggested_action,
        stage=stage,
        note=note,
    )

    # Notification an Admins bei erstem Item des Batches
    pending_count = hubspot_queue_service.get_pending_count()
    if pending_count == 1:
        try:
            from app.services.notification_service import notification_service
            notification_service.create_notification(
                roles=['admin'],
                title='HubSpot Queue',
                message='Neue Ghost/No-Show Outcomes warten auf Review.',
                notification_type='info',
                show_popup=False,
            )
        except Exception:
            pass


def _calculate_daily_metrics(tracker, date, events):
    """Berechne und speichere Tagesstatistiken"""
    metrics = {
        "date": str(date),
        "total_slots": 0,
        "no_shows": 0,
        "ghosts": 0,
        "completed": 0,
        "cancelled": 0,
        "rescheduled": 0,
        "overhang": 0,
        "by_hour": defaultdict(lambda: {"total": 0, "no_shows": 0, "ghosts": 0, "completed": 0, "cancelled": 0, "rescheduled": 0, "overhang": 0}),
        "by_user": defaultdict(lambda: {"total": 0, "no_shows": 0, "ghosts": 0, "completed": 0}),
        "by_potential": defaultdict(lambda: {"total": 0, "completed": 0}),
        "calculated_at": datetime.now(TZ).isoformat()
    }

    for event in events:
        # Skip Platzhalter
        if event.get("summary", "").isdigit():
            continue

        metrics["total_slots"] += 1

        color_id = event.get("colorId", "9")
        customer_name = event.get("summary", "Unknown")
        outcome = _get_outcome_from_title_and_color(customer_name, color_id)
        potential_type = _get_potential_type(color_id)

        # Zähle Outcomes
        if outcome == "ghost":
            metrics["ghosts"] += 1
        elif outcome == "no_show":
            metrics["no_shows"] += 1
        elif outcome == "completed":
            metrics["completed"] += 1
        elif outcome == "cancelled":
            metrics["cancelled"] += 1
        elif outcome == "rescheduled":
            metrics["rescheduled"] += 1
        elif outcome == "overhang":
            metrics["overhang"] += 1

        # Nach Stunde
        event_start = event.get("start", {}).get("dateTime")
        if event_start:
            hour = datetime.fromisoformat(event_start).strftime("%H:00")
            metrics["by_hour"][hour]["total"] += 1
            if outcome == "ghost":
                metrics["by_hour"][hour]["ghosts"] += 1
            elif outcome == "no_show":
                metrics["by_hour"][hour]["no_shows"] += 1
            elif outcome == "completed":
                metrics["by_hour"][hour]["completed"] += 1
            elif outcome == "cancelled":
                metrics["by_hour"][hour]["cancelled"] += 1
            elif outcome == "rescheduled":
                metrics["by_hour"][hour]["rescheduled"] += 1
            elif outcome == "overhang":
                metrics["by_hour"][hour]["overhang"] += 1

        # Nach Potential-Typ
        if potential_type not in ["no_show", "cancelled"]:
            metrics["by_potential"][potential_type]["total"] += 1
            if outcome == "completed":
                metrics["by_potential"][potential_type]["completed"] += 1

    # Berechne Raten
    if metrics["total_slots"] > 0:
        metrics["no_show_rate"] = round(metrics["no_shows"] / metrics["total_slots"] * 100, 2)
        metrics["ghost_rate"] = round(metrics["ghosts"] / metrics["total_slots"] * 100, 2)
        metrics["completion_rate"] = round(metrics["completed"] / metrics["total_slots"] * 100, 2)
        metrics["cancellation_rate"] = round(metrics["cancelled"] / metrics["total_slots"] * 100, 2)
    else:
        metrics["no_show_rate"] = 0
        metrics["ghost_rate"] = 0
        metrics["completion_rate"] = 0
        metrics["cancellation_rate"] = 0

    # PG Write (upsert by date)
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            from app.utils.db_utils import db_session_scope
            with db_session_scope() as session:
                from datetime import date as date_type
                metric_date = datetime.strptime(str(date), "%Y-%m-%d").date() if not isinstance(date, date_type) else date
                existing = session.query(DailyMetrics).filter_by(date=metric_date).first()
                if existing:
                    existing.total_slots = metrics["total_slots"]
                    existing.no_shows = metrics["no_shows"]
                    existing.ghosts = metrics["ghosts"]
                    existing.completed = metrics["completed"]
                    existing.cancelled = metrics["cancelled"]
                    existing.rescheduled = metrics["rescheduled"]
                    existing.overhang = metrics["overhang"]
                    existing.no_show_rate = metrics.get("no_show_rate", 0)
                    existing.ghost_rate = metrics.get("ghost_rate", 0)
                    existing.completion_rate = metrics.get("completion_rate", 0)
                    existing.cancellation_rate = metrics.get("cancellation_rate", 0)
                    existing.by_hour = json.dumps(dict(metrics["by_hour"]))
                    existing.by_user = json.dumps(dict(metrics["by_user"]))
                    existing.by_potential = json.dumps(dict(metrics["by_potential"]))
                    existing.calculated_at = datetime.fromisoformat(metrics["calculated_at"])
                else:
                    session.add(DailyMetrics(
                        date=metric_date,
                        total_slots=metrics["total_slots"],
                        no_shows=metrics["no_shows"],
                        ghosts=metrics["ghosts"],
                        completed=metrics["completed"],
                        cancelled=metrics["cancelled"],
                        rescheduled=metrics["rescheduled"],
                        overhang=metrics["overhang"],
                        no_show_rate=metrics.get("no_show_rate", 0),
                        ghost_rate=metrics.get("ghost_rate", 0),
                        completion_rate=metrics.get("completion_rate", 0),
                        cancellation_rate=metrics.get("cancellation_rate", 0),
                        by_hour=json.dumps(dict(metrics["by_hour"])),
                        by_user=json.dumps(dict(metrics["by_user"])),
                        by_potential=json.dumps(dict(metrics["by_potential"])),
                        calculated_at=datetime.fromisoformat(metrics["calculated_at"])
                    ))
            logger.debug("Daily metrics written to PG")
        except Exception as e:
            logger.warning(f"PG daily metrics write failed: {e}")

    # Speichere Metriken (JSON dual-write pattern)
    try:
        if os.path.exists(tracker.metrics_file):
            with open(tracker.metrics_file, "r", encoding="utf-8") as f:
                all_metrics = json.load(f)
        else:
            all_metrics = {}

        all_metrics[str(date)] = metrics

        # Primary storage (atomic write)
        _atomic_json_write(tracker.metrics_file, all_metrics)

        # Secondary persistent storage (atomic write)
        try:
            _atomic_json_write(tracker.persistent_metrics_file, all_metrics)
        except Exception as e:
            logger.warning(f"Could not write to persistent metrics: {e}")

        logger.debug("Daily metrics saved")
        logger.debug(f"Completed: {metrics['completed']} ({metrics['completion_rate']}%)")
        logger.debug(f"No-Shows: {metrics['no_shows']} ({metrics['no_show_rate']}%)")
        logger.debug(f"Cancelled: {metrics['cancelled']} ({metrics['cancellation_rate']}%)")

    except Exception as e:
        logger.error(f"Error saving metrics: {e}")
