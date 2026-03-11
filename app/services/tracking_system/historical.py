# -*- coding: utf-8 -*-
"""Historical data loading, user bookings, consultant performance, stats since date."""

import os
import re
import json
import logging
from datetime import datetime, timedelta, time
from collections import defaultdict

import pytz

from app.services.tracking_system.utils import _get_german_weekday
from app.services.tracking_system.converters import _extract_status_from_title, _clean_customer_name

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")

CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")

# Mapping: Login-Username → Display-Name (für Telefonisten-Ranking)
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
    from app.models import Booking, BookingOutcome, DailyMetrics, is_postgres_enabled
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


def get_user_bookings(tracker, user, start_date, end_date):
    """
    Hole alle Buchungen eines Users fuer einen bestimmten Zeitraum (PG-First, JSON-Fallback)
    """
    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _get_user_bookings_pg(user, start_date, end_date)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"PG get_user_bookings failed, falling back to JSON: {e}")

    # 2. JSON-Fallback
    try:
        bookings = []

        if not os.path.exists(tracker.bookings_file):
            return bookings

        with open(tracker.bookings_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        booking = json.loads(line)
                        if booking.get("user") == user:
                            booking_date = booking.get("date")
                            if start_date <= booking_date <= end_date:
                                bookings.append({
                                    "date": booking["date"],
                                    "time_slot": booking["time"],
                                    "customer_name": booking["customer"],
                                    "color_id": booking["color_id"],
                                    "description": booking.get("description", ""),
                                    "potential_type": booking.get("potential_type", "unknown")
                                })
                    except json.JSONDecodeError:
                        continue

        return bookings

    except Exception as e:
        logger.error(f"Fehler beim Laden der User-Buchungen: {e}")
        return []


def _get_user_bookings_pg(user, start_date, end_date):
    """PG: Lade Buchungen eines Users fuer Zeitraum"""
    from app.utils.db_utils import db_session_scope_no_commit
    with db_session_scope_no_commit() as session:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if isinstance(end_date, str) else end_date
        rows = session.query(Booking).filter(
            Booking.username == user,
            Booking.date >= start_dt,
            Booking.date <= end_dt
        ).order_by(Booking.date).all()
        if not rows:
            return []
        bookings = []
        for b in rows:
            bookings.append({
                "date": str(b.date),
                "time_slot": b.time,
                "customer_name": b.customer,
                "color_id": b.color_id,
                "description": "",
                "potential_type": b.potential_type or "unknown"
            })
        return bookings


def load_all_bookings(tracker):
    """
    Lade alle Buchungen (PG-First, JSON-Fallback)
    """
    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _load_all_bookings_pg()
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"PG load_all_bookings failed, falling back to JSON: {e}")

    # 2. JSON-Fallback
    try:
        bookings = []

        if not os.path.exists(tracker.bookings_file):
            return bookings

        with open(tracker.bookings_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        booking = json.loads(line)
                        bookings.append(booking)
                    except json.JSONDecodeError:
                        continue

        return bookings

    except Exception as e:
        logger.error(f"Fehler beim Laden aller Buchungen: {e}")
        return []


def _load_all_bookings_pg():
    """PG: Lade alle Buchungen aus Booking-Tabelle"""
    from app.utils.db_utils import db_session_scope_no_commit
    with db_session_scope_no_commit() as session:
        rows = session.query(Booking).order_by(Booking.date.desc()).all()
        if not rows:
            return None
        bookings = []
        for b in rows:
            bookings.append({
                "booking_id": b.booking_id,
                "customer": b.customer,
                "date": str(b.date),
                "time": b.time,
                "weekday": b.weekday,
                "week_number": b.week_number,
                "user": b.username,
                "potential_type": b.potential_type,
                "color_id": b.color_id,
                "description_length": b.description_length,
                "has_description": b.has_description,
                "booking_lead_time": b.booking_lead_time,
                "booked_at_hour": b.booked_at_hour,
                "booked_on_weekday": b.booked_on_weekday,
                "booking_timestamp": b.booking_timestamp.isoformat() if b.booking_timestamp else None
            })
        return bookings


def load_historical_data(tracker):
    """Lädt historische Daten für erweiterte Analysen"""
    try:
        historical_stats_file = "data/historical/historical_stats.json"
        historical_bookings_file = "data/historical/historical_bookings.jsonl"
        historical_outcomes_file = "data/historical/historical_outcomes.jsonl"

        historical_data = {
            "stats": {},
            "bookings": [],
            "outcomes": []
        }

        # Lade Statistiken
        if os.path.exists(historical_stats_file):
            with open(historical_stats_file, "r", encoding="utf-8") as f:
                historical_data["stats"] = json.load(f)

        # Lade historische Buchungen
        if os.path.exists(historical_bookings_file):
            with open(historical_bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            booking = json.loads(line)
                            historical_data["bookings"].append(booking)
                        except json.JSONDecodeError:
                            continue

        # Lade historische Outcomes
        if os.path.exists(historical_outcomes_file):
            with open(historical_outcomes_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            outcome = json.loads(line)
                            historical_data["outcomes"].append(outcome)
                        except json.JSONDecodeError:
                            continue

        return historical_data

    except Exception as e:
        logger.error(f"Fehler beim Laden der historischen Daten: {e}")
        return {"stats": {}, "bookings": [], "outcomes": []}


def _get_last_n_workdays(n=5):
    """Helper: Finde die letzten N Werktage."""
    today = datetime.now(TZ).date()
    workdays = []
    current_date = today
    while len(workdays) < n:
        if current_date.weekday() < 5:
            workdays.append(current_date)
        current_date -= timedelta(days=1)
        if (today - current_date).days > 20:
            break
    return workdays


def _get_last_n_workdays_stats_pg(tracker, n=5):
    """PG-First: Lade letzte N Werktage aus DailyMetrics (zuverlaessiger als BookingOutcome)."""
    from app.utils.db_utils import db_session_scope_no_commit

    workdays = _get_last_n_workdays(n)
    if not workdays:
        return []

    with db_session_scope_no_commit() as session:
        results = session.query(DailyMetrics).filter(
            DailyMetrics.date.in_(workdays)
        ).all()

        pg_data = {row.date: row for row in results}

        stats = []
        for date in workdays:
            if date in pg_data:
                row = pg_data[date]
                total_slots = row.total_slots or 0
                completed = row.completed or 0
                appearance_rate = round((completed / total_slots) * 100, 1) if total_slots > 0 else 0.0
                stats.append({
                    "date": date.strftime("%d.%m.%Y"),
                    "weekday": date.strftime("%A"),
                    "weekday_de": _get_german_weekday(date.weekday()),
                    "total_slots": total_slots,
                    "completed": completed,
                    "no_shows": row.no_shows or 0,
                    "ghosts": row.ghosts or 0,
                    "cancelled": row.cancelled or 0,
                    "rescheduled": row.rescheduled or 0,
                    "overhang": row.overhang or 0,
                    "appearance_rate": appearance_rate
                })
            else:
                stats.append({
                    "date": date.strftime("%d.%m.%Y"),
                    "weekday": date.strftime("%A"),
                    "weekday_de": _get_german_weekday(date.weekday()),
                    "total_slots": 0, "completed": 0, "no_shows": 0,
                    "ghosts": 0, "cancelled": 0, "rescheduled": 0,
                    "overhang": 0, "appearance_rate": 0.0
                })

        return stats


def get_last_n_workdays_stats(tracker, n=5):
    """
    Hole Statistiken für die letzten N Werktage (Mo-Fr)
    Für Admin Tracking-Dashboard (PG-First, JSON-Fallback)
    """
    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _get_last_n_workdays_stats_pg(tracker, n)
            if result:
                return result
        except Exception as e:
            logger.warning(f"PG load failed for workday stats, falling back to JSON: {e}")

    # 2. JSON-Fallback
    try:
        if not os.path.exists(tracker.metrics_file):
            return []

        with open(tracker.metrics_file, "r", encoding="utf-8") as f:
            all_metrics = json.load(f)

        workdays = _get_last_n_workdays(n)

        stats = []
        for date in workdays:
            date_str = str(date)
            if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                metrics = all_metrics[date_str]

                total_slots = metrics.get("total_slots", 0)
                completed = metrics.get("completed", 0)
                no_shows = metrics.get("no_shows", 0)
                ghosts = metrics.get("ghosts", 0)
                cancelled = metrics.get("cancelled", 0)
                rescheduled = metrics.get("rescheduled", 0)
                overhang = metrics.get("overhang", 0)

                if total_slots > 0:
                    appearance_rate = round((completed / total_slots) * 100, 1)
                else:
                    appearance_rate = 0.0

                stats.append({
                    "date": date.strftime("%d.%m.%Y"),
                    "weekday": date.strftime("%A"),
                    "weekday_de": _get_german_weekday(date.weekday()),
                    "total_slots": total_slots,
                    "completed": completed,
                    "no_shows": no_shows,
                    "ghosts": ghosts,
                    "cancelled": cancelled,
                    "rescheduled": rescheduled,
                    "overhang": overhang,
                    "appearance_rate": appearance_rate
                })
            else:
                stats.append({
                    "date": date.strftime("%d.%m.%Y"),
                    "weekday": date.strftime("%A"),
                    "weekday_de": _get_german_weekday(date.weekday()),
                    "total_slots": 0,
                    "completed": 0,
                    "no_shows": 0,
                    "ghosts": 0,
                    "cancelled": 0,
                    "rescheduled": 0,
                    "overhang": 0,
                    "appearance_rate": 0.0
                })

        return stats

    except Exception as e:
        logger.error(f"Fehler beim Laden der Werktags-Statistiken: {e}")
        return []


def _get_stats_since_date_pg(tracker, start_date_str, end_date_str=None):
    """PG-First: Lade aggregierte Stats aus DailyMetrics (zuverlaessiger als BookingOutcome)."""
    from app.utils.db_utils import db_session_scope_no_commit
    from sqlalchemy import func

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    today = datetime.now(TZ).date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else today

    with db_session_scope_no_commit() as session:
        # Aggregat-Totals aus DailyMetrics
        totals = session.query(
            func.sum(DailyMetrics.total_slots).label('total_slots'),
            func.sum(DailyMetrics.completed).label('completed'),
            func.sum(DailyMetrics.no_shows).label('no_shows'),
            func.sum(DailyMetrics.ghosts).label('ghosts'),
            func.sum(DailyMetrics.cancelled).label('cancelled'),
            func.sum(DailyMetrics.rescheduled).label('rescheduled'),
            func.sum(DailyMetrics.overhang).label('overhang'),
            func.count(DailyMetrics.id).label('days_tracked')
        ).filter(
            DailyMetrics.date >= start_date,
            DailyMetrics.date <= end_date,
            DailyMetrics.total_slots > 0
        ).first()

        # Daily-Data fuer Charts + Tabelle (nur Werktage)
        daily_rows = session.query(DailyMetrics).filter(
            DailyMetrics.date >= start_date,
            DailyMetrics.date <= end_date,
            DailyMetrics.total_slots > 0
        ).order_by(DailyMetrics.date).all()

        daily_data = []
        for row in daily_rows:
            if row.date.weekday() < 5:
                slots = row.total_slots or 0
                completed = row.completed or 0
                appearance_rate = round((completed / slots) * 100, 1) if slots > 0 else 0.0
                daily_data.append({
                    "date": row.date.strftime("%d.%m.%Y"),
                    "weekday": _get_german_weekday(row.date.weekday()),
                    "weekday_de": _get_german_weekday(row.date.weekday()),
                    "total_slots": slots,
                    "completed": completed,
                    "no_shows": row.no_shows or 0,
                    "ghosts": row.ghosts or 0,
                    "cancelled": row.cancelled or 0,
                    "rescheduled": row.rescheduled or 0,
                    "overhang": row.overhang or 0,
                    "appearance_rate": appearance_rate
                })

        total_slots = totals.total_slots or 0
        total_completed = totals.completed or 0
        total_no_shows = totals.no_shows or 0
        total_ghosts = totals.ghosts or 0

        if total_slots > 0:
            appearance_rate = round((total_completed / total_slots) * 100, 1)
            no_show_rate = round((total_no_shows / total_slots) * 100, 1)
            ghost_rate = round((total_ghosts / total_slots) * 100, 1)
        else:
            appearance_rate = no_show_rate = ghost_rate = 0.0

        return {
            "start_date": start_date.strftime("%d.%m.%Y"),
            "end_date": end_date.strftime("%d.%m.%Y"),
            "days_tracked": totals.days_tracked or 0,
            "total_days": (end_date - start_date).days + 1,
            "total_slots": total_slots,
            "completed": total_completed,
            "no_shows": total_no_shows,
            "ghosts": total_ghosts,
            "cancelled": totals.cancelled or 0,
            "rescheduled": totals.rescheduled or 0,
            "overhang": totals.overhang or 0,
            "appearance_rate": appearance_rate,
            "completion_rate": appearance_rate,
            "no_show_rate": no_show_rate,
            "ghost_rate": ghost_rate,
            "daily_data": daily_data
        }


def get_stats_since_date(tracker, start_date_str="2025-09-01"):
    """
    Hole Gesamt-Statistiken seit einem bestimmten Datum
    PG-First, JSON-Fallback
    """
    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _get_stats_since_date_pg(tracker, start_date_str)
            if result and result.get("total_slots", 0) > 0:
                return result
        except Exception as e:
            logger.warning(f"PG load failed for stats since {start_date_str}, falling back to JSON: {e}")

    # 2. JSON-Fallback
    try:
        if not os.path.exists(tracker.metrics_file):
            return {
                "start_date": start_date_str,
                "days_tracked": 0,
                "total_slots": 0,
                "completed": 0,
                "no_shows": 0,
                "ghosts": 0,
                "cancelled": 0,
                "rescheduled": 0,
                "overhang": 0,
                "appearance_rate": 0.0,
                "completion_rate": 0.0,
                "no_show_rate": 0.0,
                "ghost_rate": 0.0,
                "daily_data": []
            }

        with open(tracker.metrics_file, "r", encoding="utf-8") as f:
            all_metrics = json.load(f)

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        today = datetime.now(TZ).date()

        # Aggregierte Werte
        total_slots = 0
        total_completed = 0
        total_no_shows = 0
        total_ghosts = 0
        total_cancelled = 0
        total_rescheduled = 0
        total_overhang = 0
        days_with_data = 0
        daily_data = []

        # Iteriere über alle Tage seit Start
        current_date = start_date
        while current_date <= today:
            date_str = str(current_date)

            if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                metrics = all_metrics[date_str]
                slots = metrics.get("total_slots", 0)

                if slots > 0:
                    completed = metrics.get("completed", 0)
                    no_shows = metrics.get("no_shows", 0)
                    ghosts = metrics.get("ghosts", 0)
                    cancelled = metrics.get("cancelled", 0)
                    rescheduled = metrics.get("rescheduled", 0)
                    overhang = metrics.get("overhang", 0)

                    total_slots += slots
                    total_completed += completed
                    total_no_shows += no_shows
                    total_ghosts += ghosts
                    total_cancelled += cancelled
                    total_rescheduled += rescheduled
                    total_overhang += overhang
                    days_with_data += 1

                    # Für Trend-Chart
                    if slots > 0:
                        appearance_rate = round((completed / slots) * 100, 1)
                    else:
                        appearance_rate = 0.0

                    if current_date.weekday() < 5:
                        daily_data.append({
                            "date": current_date.strftime("%d.%m.%Y"),
                            "weekday": _get_german_weekday(current_date.weekday()),
                            "weekday_de": _get_german_weekday(current_date.weekday()),
                            "total_slots": slots,
                            "completed": completed,
                            "no_shows": no_shows,
                            "ghosts": ghosts,
                            "cancelled": cancelled,
                            "rescheduled": rescheduled,
                            "overhang": overhang,
                            "appearance_rate": appearance_rate
                        })

            current_date += timedelta(days=1)

        # Berechne Raten
        if total_slots > 0:
            appearance_rate = round((total_completed / total_slots) * 100, 1)
        else:
            appearance_rate = 0.0

        if total_slots > 0:
            completion_rate = round((total_completed / total_slots) * 100, 1)
            no_show_rate = round((total_no_shows / total_slots) * 100, 1)
            ghost_rate = round((total_ghosts / total_slots) * 100, 1)
        else:
            completion_rate = 0.0
            no_show_rate = 0.0
            ghost_rate = 0.0

        return {
            "start_date": start_date.strftime("%d.%m.%Y"),
            "end_date": today.strftime("%d.%m.%Y"),
            "days_tracked": days_with_data,
            "total_days": (today - start_date).days + 1,
            "total_slots": total_slots,
            "completed": total_completed,
            "no_shows": total_no_shows,
            "ghosts": total_ghosts,
            "cancelled": total_cancelled,
            "rescheduled": total_rescheduled,
            "overhang": total_overhang,
            "appearance_rate": appearance_rate,
            "completion_rate": completion_rate,
            "no_show_rate": no_show_rate,
            "ghost_rate": ghost_rate,
            "daily_data": daily_data
        }

    except Exception as e:
        logger.error(f"Fehler beim Laden der Statistiken seit {start_date_str}: {e}")
        return {
            "start_date": start_date_str,
            "days_tracked": 0,
            "total_slots": 0,
            "completed": 0,
            "no_shows": 0,
            "ghosts": 0,
            "cancelled": 0,
            "rescheduled": 0,
            "overhang": 0,
            "appearance_rate": 0.0,
            "completion_rate": 0.0,
            "no_show_rate": 0.0,
            "ghost_rate": 0.0,
            "daily_data": []
        }


def _get_bookings_by_creation_date_pg(start_date_str, end_date_str):
    """PG-First: Zaehle T1-Buchungen nach Erstellungs-Datum aus PostgreSQL."""
    from app.utils.db_utils import db_session_scope_no_commit
    from sqlalchemy import func

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    with db_session_scope_no_commit() as session:
        rows = session.query(
            Booking.username,
            func.count(Booking.id).label('booking_count')
        ).filter(
            func.date(Booking.booking_timestamp) >= start_date,
            func.date(Booking.booking_timestamp) <= end_date
        ).group_by(Booking.username).all()

        total = 0
        by_user = {}
        for row in rows:
            display_name = USERNAME_TO_DISPLAY.get(row.username.lower(), row.username)
            by_user[display_name] = by_user.get(display_name, 0) + row.booking_count
            total += row.booking_count

        return {"total_bookings": total, "by_user": by_user}


def get_bookings_by_creation_date(tracker, start_date_str, end_date_str):
    """
    Zähle T1-Buchungen nach BUCHUNGSERSTELLUNG (nicht Termin-Datum).
    PG-First, JSON-Fallback.
    """
    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _get_bookings_by_creation_date_pg(start_date_str, end_date_str)
            if result and result.get("total_bookings", 0) > 0:
                return result
        except Exception as e:
            logger.warning(f"PG load failed for bookings by creation date, falling back to JSON: {e}")

    # 2. JSON-Fallback
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        total_bookings = 0
        by_user = defaultdict(int)

        if not os.path.exists(tracker.bookings_file):
            return {"total_bookings": 0, "by_user": {}}

        with open(tracker.bookings_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    booking = json.loads(line)
                    timestamp_str = booking.get("timestamp", "")
                    if not timestamp_str:
                        continue

                    try:
                        booking_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        booking_date = booking_timestamp.date()
                    except (ValueError, TypeError):
                        logger.debug(f"Skipped booking with bad timestamp: {timestamp_str[:50]}")
                        continue

                    if start_date <= booking_date <= end_date:
                        total_bookings += 1
                        user = booking.get("user", "Unknown")
                        by_user[user] += 1

                except (json.JSONDecodeError, ValueError):
                    continue

        # Map usernames to display names
        mapped_by_user = {}
        for user, count in by_user.items():
            display_name = USERNAME_TO_DISPLAY.get(user.lower(), user)
            mapped_by_user[display_name] = mapped_by_user.get(display_name, 0) + count

        return {
            "total_bookings": total_bookings,
            "by_user": mapped_by_user
        }

    except Exception as e:
        logger.error(f"Fehler bei get_bookings_by_creation_date: {e}")
        return {"total_bookings": 0, "by_user": {}}


def _get_consultant_performance_pg(start_date_str, end_date_str):
    """PG-First: Berater-Performance aus BookingOutcome aggregieren."""
    from app.utils.db_utils import db_session_scope_no_commit
    from sqlalchemy import func, case

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    with db_session_scope_no_commit() as session:
        rows = session.query(
            BookingOutcome.consultant,
            func.count().label('total_slots'),
            func.sum(case((BookingOutcome.outcome == 'completed', 1), else_=0)).label('completed'),
            func.sum(case((BookingOutcome.outcome == 'no_show', 1), else_=0)).label('no_shows'),
            func.sum(case((BookingOutcome.outcome == 'ghost', 1), else_=0)).label('ghosts'),
            func.sum(case((BookingOutcome.outcome == 'cancelled', 1), else_=0)).label('cancelled'),
            func.sum(case((BookingOutcome.outcome == 'rescheduled', 1), else_=0)).label('rescheduled'),
            func.sum(case((BookingOutcome.outcome == 'overhang', 1), else_=0)).label('overhang'),
        ).filter(
            BookingOutcome.date >= start_date,
            BookingOutcome.date <= end_date,
            BookingOutcome.consultant.isnot(None),
            BookingOutcome.consultant != 'Unknown'
        ).group_by(BookingOutcome.consultant).all()

        result = {}
        for row in rows:
            consultant_name = row.consultant or "Unknown"
            completed = row.completed or 0
            no_shows = row.no_shows or 0
            ghosts = row.ghosts or 0

            appearance_rate = 0.0
            denominator = completed + no_shows + ghosts
            if denominator > 0:
                appearance_rate = round((completed / denominator) * 100, 1)

            result[consultant_name] = {
                "total_slots": row.total_slots or 0,
                "completed": completed,
                "no_shows": no_shows,
                "ghosts": ghosts,
                "cancelled": row.cancelled or 0,
                "rescheduled": row.rescheduled or 0,
                "overhang": row.overhang or 0,
                "appearance_rate": appearance_rate
            }

        return result


def get_consultant_performance(tracker, start_date_str, end_date_str):
    """
    Berechne Berater-Performance.
    PG-First (aus BookingOutcome), Fallback auf Google Calendar API.
    """
    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _get_consultant_performance_pg(start_date_str, end_date_str)
            if result:
                return result
        except Exception as e:
            logger.warning(f"PG load failed for consultant performance, falling back to Calendar API: {e}")

    # 2. Google Calendar API Fallback
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        consultant_stats = defaultdict(lambda: {
            "total_slots": 0,
            "completed": 0,
            "no_shows": 0,
            "ghosts": 0,
            "cancelled": 0,
            "rescheduled": 0,
            "overhang": 0,
            "pending": 0
        })

        # 1. Lade alle Buchungen aus bookings.jsonl für User-Mapping
        booking_lookup = {}
        if os.path.exists(tracker.bookings_file):
            with open(tracker.bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        booking = json.loads(line)
                        customer = booking.get("customer", "").lower().strip()
                        date = booking.get("date", "")
                        key = f"{date}_{customer}"
                        booking_lookup[key] = booking.get("user", "Unknown")
                    except Exception:
                        continue

        # 2. Lade Google Calendar Events
        start_time = TZ.localize(datetime.combine(start_date, time.min))
        end_time = TZ.localize(datetime.combine(end_date, time.max))

        events_result = tracker.service.events().list(
            calendarId=CENTRAL_CALENDAR_ID,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500
        ).execute()

        events = events_result.get('items', [])

        # 3. Verarbeite Events und extrahiere Status aus Titel
        for event in events:
            summary = event.get('summary', '')

            # Skip Platzhalter (nur Zahlen) und Exit
            if not summary or summary.isdigit() or 'exit' in summary.lower():
                continue

            # Parse Event-Datum
            start_dt = event.get('start', {}).get('dateTime', '')
            if not start_dt:
                continue

            try:
                event_datetime = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                event_date = event_datetime.date()
            except Exception:
                continue

            # Extrahiere Status aus Titel
            status = _extract_status_from_title(summary)

            # Finde den zugehörigen User aus bookings.jsonl
            customer_name = _clean_customer_name(summary)
            lookup_key = f"{event_date.strftime('%Y-%m-%d')}_{customer_name.lower().strip()}"
            consultant = booking_lookup.get(lookup_key)

            # Fallback: Parse [Booked by: X] aus Description
            if not consultant:
                description = event.get("description", "")
                booked_by_match = re.search(r'\[Booked by:\s*([^\]]+)\]', description)
                if booked_by_match:
                    consultant = booked_by_match.group(1).strip().lower()
                else:
                    consultant = "Unknown"
                    logger.info(
                        f"Unmatched event: '{summary}' clean='{customer_name}' "
                        f"date={event_date} key='{lookup_key}'"
                    )

            # Map username to display name for ranking
            consultant = USERNAME_TO_DISPLAY.get(consultant.lower(), consultant)

            # Zähle nach Status
            consultant_stats[consultant]["total_slots"] += 1

            if status == 'erschienen':
                consultant_stats[consultant]["completed"] += 1
            elif status == 'ghost':
                consultant_stats[consultant]["ghosts"] += 1
            elif status == 'nicht erschienen':
                consultant_stats[consultant]["no_shows"] += 1
            elif status == 'abgesagt':
                consultant_stats[consultant]["cancelled"] += 1
            elif status == 'überhang' or status == 'ueberhang':
                consultant_stats[consultant]["overhang"] += 1
            elif status == 'verschoben':
                consultant_stats[consultant]["rescheduled"] += 1
            else:
                consultant_stats[consultant]["pending"] += 1

        # Diagnostic
        unknown_slots = consultant_stats.get("Unknown", {}).get("total_slots", 0)
        if unknown_slots > 0:
            logger.warning(f"Consultant performance: {unknown_slots} events attributed to 'Unknown'")

        # 4. Berechne Erschienen-Quote pro Consultant
        result = {}
        for consultant, stats in consultant_stats.items():
            total = stats["total_slots"]
            completed = stats["completed"]

            appearance_rate = 0.0
            if total > 0:
                denominator = completed + stats["no_shows"] + stats["ghosts"]
                if denominator > 0:
                    appearance_rate = round((completed / denominator) * 100, 1)

            result[consultant] = {
                "total_slots": total,
                "completed": completed,
                "no_shows": stats["no_shows"],
                "ghosts": stats["ghosts"],
                "cancelled": stats["cancelled"],
                "rescheduled": stats["rescheduled"],
                "overhang": stats["overhang"],
                "appearance_rate": appearance_rate
            }

        return result

    except Exception as e:
        logger.error(f"Fehler bei get_consultant_performance: {e}")
        return {}
