# -*- coding: utf-8 -*-
"""Weekly/monthly reports and period-based statistics."""

import os
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

import pytz

from app.services.tracking_system.utils import _get_german_weekday

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")

# PostgreSQL Models
try:
    from app.models import Booking, BookingOutcome, DailyMetrics, is_postgres_enabled
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

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


def get_weekly_report(tracker, week_number=None):
    """Generiere erweiterten Wochenbericht (PG-First, JSON-Fallback)"""
    if week_number is None:
        week_number = datetime.now(TZ).isocalendar()[1]

    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _get_weekly_report_pg(week_number)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"PG get_weekly_report failed, falling back to JSON: {e}")

    # 2. JSON-Fallback
    return _get_weekly_report_json(tracker, week_number)


def _get_weekly_report_pg(week_number):
    """PG: Generiere Wochenbericht aus Booking + BookingOutcome"""
    from app.utils.db_utils import db_session_scope_no_commit
    with db_session_scope_no_commit() as session:
        year = datetime.now(TZ).year

        report = {
            "week": week_number,
            "year": year,
            "metrics": {
                "total_bookings": 0,
                "total_outcomes": 0,
                "no_shows": 0,
                "completed": 0,
                "cancelled": 0,
                "by_day": defaultdict(lambda: {"bookings": 0, "no_shows": 0, "completed": 0, "cancelled": 0}),
                "by_user": defaultdict(lambda: {"bookings": 0, "no_shows": 0, "completed": 0, "success_rate": 0}),
                "by_hour": defaultdict(lambda: {"total": 0, "no_shows": 0, "completed": 0}),
                "top_no_show_times": [],
                "top_success_times": [],
                "high_risk_customers": []
            }
        }

        # Bookings for this week
        booking_rows = session.query(Booking).filter(
            Booking.week_number == week_number
        ).all()

        for b in booking_rows:
            report["metrics"]["total_bookings"] += 1
            report["metrics"]["by_day"][b.weekday]["bookings"] += 1
            if b.username:
                report["metrics"]["by_user"][b.username]["bookings"] += 1

        # Outcomes: filter by ISO week from date
        from datetime import date as date_type
        jan4 = date_type(year, 1, 4)
        start_of_week = jan4 + timedelta(weeks=week_number - 1, days=-jan4.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        outcome_rows = session.query(BookingOutcome).filter(
            BookingOutcome.date >= start_of_week,
            BookingOutcome.date <= end_of_week
        ).all()

        if not booking_rows and not outcome_rows:
            return None

        for o in outcome_rows:
            report["metrics"]["total_outcomes"] += 1
            weekday = o.date.strftime("%A")
            hour = o.time[:2] + ":00" if o.time else "00:00"

            if o.outcome == "no_show":
                report["metrics"]["no_shows"] += 1
                report["metrics"]["by_day"][weekday]["no_shows"] += 1
                report["metrics"]["by_hour"][hour]["no_shows"] += 1
            elif o.outcome == "completed":
                report["metrics"]["completed"] += 1
                report["metrics"]["by_day"][weekday]["completed"] += 1
                report["metrics"]["by_hour"][hour]["completed"] += 1
            elif o.outcome == "cancelled":
                report["metrics"]["cancelled"] += 1
                report["metrics"]["by_day"][weekday]["cancelled"] += 1

            report["metrics"]["by_hour"][hour]["total"] += 1

        # Success rates per user
        for user, data in report["metrics"]["by_user"].items():
            if data["bookings"] > 0:
                data["success_rate"] = round(
                    (data.get("completed", 0) / data["bookings"]) * 100, 2
                )

        # Hour stats
        hour_stats = []
        for hour, data in report["metrics"]["by_hour"].items():
            if data["total"] > 0:
                hour_stats.append({
                    "hour": hour,
                    "no_show_rate": round((data["no_shows"] / data["total"]) * 100, 2),
                    "success_rate": round((data["completed"] / data["total"]) * 100, 2),
                    "total": data["total"]
                })

        hour_stats.sort(key=lambda x: x["no_show_rate"], reverse=True)
        report["metrics"]["top_no_show_times"] = hour_stats[:3]
        hour_stats.sort(key=lambda x: x["success_rate"], reverse=True)
        report["metrics"]["top_success_times"] = hour_stats[:3]

        if report["metrics"]["total_outcomes"] > 0:
            report["metrics"]["overall_no_show_rate"] = round(
                (report["metrics"]["no_shows"] / report["metrics"]["total_outcomes"]) * 100, 2
            )
            report["metrics"]["overall_completion_rate"] = round(
                (report["metrics"]["completed"] / report["metrics"]["total_outcomes"]) * 100, 2
            )
            report["metrics"]["overall_cancellation_rate"] = round(
                (report["metrics"]["cancelled"] / report["metrics"]["total_outcomes"]) * 100, 2
            )

        return report


def _get_weekly_report_json(tracker, week_number):
    """JSON-Fallback: Generiere Wochenbericht aus JSONL-Dateien"""
    report = {
        "week": week_number,
        "year": datetime.now(TZ).year,
        "metrics": {
            "total_bookings": 0,
            "total_outcomes": 0,
            "no_shows": 0,
            "completed": 0,
            "cancelled": 0,
            "by_day": defaultdict(lambda: {"bookings": 0, "no_shows": 0, "completed": 0, "cancelled": 0}),
            "by_user": defaultdict(lambda: {"bookings": 0, "no_shows": 0, "completed": 0, "success_rate": 0}),
            "by_hour": defaultdict(lambda: {"total": 0, "no_shows": 0, "completed": 0}),
            "top_no_show_times": [],
            "top_success_times": [],
            "high_risk_customers": []
        }
    }

    if os.path.exists(tracker.bookings_file):
        with open(tracker.bookings_file, "r", encoding="utf-8") as f:
            for line in f:
                booking = json.loads(line)
                if booking.get("week_number") == week_number:
                    report["metrics"]["total_bookings"] += 1
                    weekday = booking["weekday"]
                    report["metrics"]["by_day"][weekday]["bookings"] += 1
                    if booking.get("user"):
                        report["metrics"]["by_user"][booking["user"]]["bookings"] += 1

    if os.path.exists(tracker.outcomes_file):
        with open(tracker.outcomes_file, "r", encoding="utf-8") as f:
            for line in f:
                outcome = json.loads(line)
                outcome_date = datetime.strptime(outcome["date"], "%Y-%m-%d")
                if outcome_date.isocalendar()[1] == week_number:
                    report["metrics"]["total_outcomes"] += 1
                    weekday = outcome_date.strftime("%A")
                    hour = outcome["time"][:2] + ":00"
                    if outcome["outcome"] == "no_show":
                        report["metrics"]["no_shows"] += 1
                        report["metrics"]["by_day"][weekday]["no_shows"] += 1
                        report["metrics"]["by_hour"][hour]["no_shows"] += 1
                    elif outcome["outcome"] == "completed":
                        report["metrics"]["completed"] += 1
                        report["metrics"]["by_day"][weekday]["completed"] += 1
                        report["metrics"]["by_hour"][hour]["completed"] += 1
                    elif outcome["outcome"] == "cancelled":
                        report["metrics"]["cancelled"] += 1
                        report["metrics"]["by_day"][weekday]["cancelled"] += 1
                    report["metrics"]["by_hour"][hour]["total"] += 1

    for user, data in report["metrics"]["by_user"].items():
        if data["bookings"] > 0:
            data["success_rate"] = round(
                (data.get("completed", 0) / data["bookings"]) * 100, 2
            )

    hour_stats = []
    for hour, data in report["metrics"]["by_hour"].items():
        if data["total"] > 0:
            no_show_rate = (data["no_shows"] / data["total"]) * 100
            success_rate = (data["completed"] / data["total"]) * 100
            hour_stats.append({
                "hour": hour,
                "no_show_rate": round(no_show_rate, 2),
                "success_rate": round(success_rate, 2),
                "total": data["total"]
            })

    hour_stats.sort(key=lambda x: x["no_show_rate"], reverse=True)
    report["metrics"]["top_no_show_times"] = hour_stats[:3]
    hour_stats.sort(key=lambda x: x["success_rate"], reverse=True)
    report["metrics"]["top_success_times"] = hour_stats[:3]

    if report["metrics"]["total_outcomes"] > 0:
        report["metrics"]["overall_no_show_rate"] = round(
            (report["metrics"]["no_shows"] / report["metrics"]["total_outcomes"]) * 100, 2
        )
        report["metrics"]["overall_completion_rate"] = round(
            (report["metrics"]["completed"] / report["metrics"]["total_outcomes"]) * 100, 2
        )
        report["metrics"]["overall_cancellation_rate"] = round(
            (report["metrics"]["cancelled"] / report["metrics"]["total_outcomes"]) * 100, 2
        )

    return report


def get_weekly_stats(tracker, year, week_number):
    """
    Statistiken für eine spezifische ISO-Woche
    """
    try:
        # Berechne Start (Montag) und Ende (Sonntag) der ISO-Woche
        first_day_of_year = datetime(year, 1, 1).date()
        first_thursday = first_day_of_year + timedelta(days=(3 - first_day_of_year.weekday() + 7) % 7)
        first_monday_week1 = first_thursday - timedelta(days=3)
        start_date = first_monday_week1 + timedelta(weeks=week_number - 1)
        end_date = start_date + timedelta(days=6)

        stats = get_stats_for_period(tracker, str(start_date), str(end_date))
        stats["year"] = year
        stats["week"] = week_number
        stats["week_label"] = f"KW {week_number}/{year}"

        return stats

    except Exception as e:
        logger.error(f"Fehler bei get_weekly_stats: {e}")
        return {
            "year": year,
            "week": week_number,
            "week_label": f"KW {week_number}/{year}",
            "days_tracked": 0,
            "total_slots": 0,
            "completed": 0,
            "no_shows": 0,
            "appearance_rate": 0.0,
            "daily_data": []
        }


def get_monthly_stats(tracker, year, month):
    """
    Statistiken für einen spezifischen Monat
    """
    try:
        from calendar import monthrange

        start_date = datetime(year, month, 1).date()
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day).date()

        month_names = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
                      "Juli", "August", "September", "Oktober", "November", "Dezember"]

        stats = get_stats_for_period(tracker, str(start_date), str(end_date))
        stats["year"] = year
        stats["month"] = month
        stats["month_label"] = f"{month_names[month]} {year}"

        return stats

    except Exception as e:
        logger.error(f"Fehler bei get_monthly_stats: {e}")
        return {
            "year": year,
            "month": month,
            "month_label": f"Monat {month}/{year}",
            "days_tracked": 0,
            "total_slots": 0,
            "completed": 0,
            "no_shows": 0,
            "appearance_rate": 0.0,
            "daily_data": []
        }


def get_stats_for_period(tracker, start_date_str, end_date_str):
    """
    Flexible Statistiken für beliebigen Zeitraum
    PG-First, JSON-Fallback
    """
    from app.services.tracking_system.historical import _get_stats_since_date_pg, get_bookings_by_creation_date

    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _get_stats_since_date_pg(tracker, start_date_str, end_date_str)
            if result and result.get("total_slots", 0) > 0:
                pg_days = result.get("days_tracked", 0)
                if pg_days > 0:
                    bookings_created_data = get_bookings_by_creation_date(tracker, start_date_str, end_date_str)
                    result["bookings_created"] = bookings_created_data.get("total_bookings", 0)
                    result["bookings_created_by_user"] = bookings_created_data.get("by_user", {})
                    return result
                else:
                    logger.info(f"PG DailyMetrics has 0 days for {start_date_str}–{end_date_str}, falling back to JSON")
        except Exception as e:
            logger.warning(f"PG load failed for period stats, falling back to JSON: {e}")

    # 2. JSON-Fallback
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        totals = {
            "total_slots": 0,
            "completed": 0,
            "no_shows": 0,
            "ghosts": 0,
            "cancelled": 0,
            "rescheduled": 0,
            "overhang": 0
        }
        daily_data = []
        days_with_data = 0

        # Lade daily_metrics.json
        if os.path.exists(tracker.metrics_file):
            with open(tracker.metrics_file, "r", encoding="utf-8") as f:
                all_metrics = json.load(f)

            current_date = start_date
            while current_date <= end_date:
                date_str = str(current_date)
                if date_str in all_metrics:
                    day_metrics = all_metrics[date_str]
                    days_with_data += 1

                    slots = day_metrics.get("total_slots", 0)
                    completed = day_metrics.get("completed", 0)
                    no_shows = day_metrics.get("no_shows", 0)
                    ghosts = day_metrics.get("ghosts", 0)
                    cancelled = day_metrics.get("cancelled", 0)
                    rescheduled = day_metrics.get("rescheduled", 0)
                    overhang = day_metrics.get("overhang", 0)

                    totals["total_slots"] += slots
                    totals["completed"] += completed
                    totals["no_shows"] += no_shows
                    totals["ghosts"] += ghosts
                    totals["cancelled"] += cancelled
                    totals["rescheduled"] += rescheduled
                    totals["overhang"] += overhang

                    # Nur Werktage zu Charts hinzufügen
                    if current_date.weekday() < 5 and slots > 0:
                        appearance_rate = round((completed / slots) * 100, 1) if slots > 0 else 0.0
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
        if totals["total_slots"] > 0:
            appearance_rate = round((totals["completed"] / totals["total_slots"]) * 100, 1)
        else:
            appearance_rate = 0.0

        if totals["total_slots"] > 0:
            no_show_rate = round((totals["no_shows"] / totals["total_slots"]) * 100, 1)
            ghost_rate = round((totals["ghosts"] / totals["total_slots"]) * 100, 1)
        else:
            no_show_rate = 0.0
            ghost_rate = 0.0

        # Hole auch Buchungen nach Erstellungsdatum
        bookings_created_data = get_bookings_by_creation_date(tracker, start_date_str, end_date_str)

        return {
            "start_date": start_date.strftime("%d.%m.%Y"),
            "end_date": end_date.strftime("%d.%m.%Y"),
            "days_tracked": days_with_data,
            "total_days": (end_date - start_date).days + 1,
            **totals,
            "appearance_rate": appearance_rate,
            "no_show_rate": no_show_rate,
            "ghost_rate": ghost_rate,
            "daily_data": daily_data,
            "bookings_created": bookings_created_data.get("total_bookings", 0),
            "bookings_created_by_user": bookings_created_data.get("by_user", {})
        }

    except Exception as e:
        logger.error(f"Fehler bei get_stats_for_period: {e}")
        return {
            "start_date": start_date_str,
            "end_date": end_date_str,
            "days_tracked": 0,
            "total_slots": 0,
            "completed": 0,
            "no_shows": 0,
            "ghosts": 0,
            "cancelled": 0,
            "rescheduled": 0,
            "overhang": 0,
            "appearance_rate": 0.0,
            "no_show_rate": 0.0,
            "ghost_rate": 0.0,
            "daily_data": [],
            "bookings_created": 0,
            "bookings_created_by_user": {}
        }
