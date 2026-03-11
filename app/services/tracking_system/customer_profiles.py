# -*- coding: utf-8 -*-
"""Customer profile management: update aggregated profiles, get customer history."""

import os
import json
import logging
from datetime import datetime

import pytz

from app.services.tracking_system.utils import _atomic_json_write

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")

# PostgreSQL Models
try:
    from app.models import Booking, BookingOutcome, CustomerProfile, is_postgres_enabled
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


def _update_customer_profiles(tracker):
    """Aktualisiere Kundenprofile mit aggregierten Daten"""
    profiles = {}

    # PG-first: Aggregiere aus BookingOutcome Tabelle
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            from app.utils.db_utils import db_session_scope
            from sqlalchemy import func, case
            with db_session_scope() as session:
                results = session.query(
                    BookingOutcome.customer,
                    func.min(BookingOutcome.date).label('first_seen'),
                    func.max(BookingOutcome.date).label('last_seen'),
                    func.count().label('total_appointments'),
                    func.sum(case((BookingOutcome.outcome == 'completed', 1), else_=0)).label('completed_count'),
                    func.sum(case((BookingOutcome.outcome == 'no_show', 1), else_=0)).label('no_show_count'),
                    func.sum(case((BookingOutcome.outcome == 'cancelled', 1), else_=0)).label('cancelled_count'),
                ).group_by(BookingOutcome.customer).all()

                for row in results:
                    total = row.total_appointments or 0
                    completed = row.completed_count or 0
                    no_shows = row.no_show_count or 0
                    cancelled = row.cancelled_count or 0

                    reliability = round((completed / total) * 100, 2) if total > 0 else 100.0

                    if no_shows >= 3:
                        risk = "high"
                    elif no_shows >= 1:
                        risk = "medium"
                    else:
                        risk = "low"

                    # Upsert CustomerProfile
                    existing = session.query(CustomerProfile).filter_by(customer=row.customer).first()
                    if existing:
                        existing.first_seen = str(row.first_seen)
                        existing.last_seen = str(row.last_seen)
                        existing.total_appointments = total
                        existing.completed = completed
                        existing.no_shows = no_shows
                        existing.cancelled = cancelled
                        existing.reliability_score = reliability
                        existing.risk_level = risk
                    else:
                        session.add(CustomerProfile(
                            customer=row.customer,
                            first_seen=str(row.first_seen),
                            last_seen=str(row.last_seen),
                            total_appointments=total,
                            completed=completed,
                            no_shows=no_shows,
                            cancelled=cancelled,
                            reliability_score=reliability,
                            risk_level=risk
                        ))

                    profiles[row.customer] = {
                        "first_seen": str(row.first_seen),
                        "last_seen": str(row.last_seen),
                        "total_appointments": total,
                        "completed": completed,
                        "no_shows": no_shows,
                        "cancelled": cancelled,
                        "reliability_score": reliability,
                        "risk_level": risk
                    }

            logger.debug("Customer profiles written to PG")
        except Exception as e:
            logger.warning(f"PG customer profiles write failed, falling back to JSON: {e}")
            profiles = {}

    # JSON-Fallback: Analysiere alle Outcomes aus JSONL
    if not profiles:
        if os.path.exists(tracker.customer_file):
            try:
                with open(tracker.customer_file, "r", encoding="utf-8") as f:
                    profiles = json.load(f)
            except Exception:
                profiles = {}

        if os.path.exists(tracker.outcomes_file):
            # Reset profiles for fresh calculation from JSONL
            profiles = {}
            with open(tracker.outcomes_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        outcome = json.loads(line)
                        customer = outcome["customer"]

                        if customer not in profiles:
                            profiles[customer] = {
                                "first_seen": outcome["date"],
                                "last_seen": outcome["date"],
                                "total_appointments": 0,
                                "completed": 0,
                                "no_shows": 0,
                                "cancelled": 0,
                                "reliability_score": 100.0
                            }

                        profile = profiles[customer]
                        profile["total_appointments"] += 1
                        profile["last_seen"] = outcome["date"]

                        if outcome["outcome"] == "completed":
                            profile["completed"] += 1
                        elif outcome["outcome"] == "no_show":
                            profile["no_shows"] += 1
                        elif outcome["outcome"] == "cancelled":
                            profile["cancelled"] += 1

                        if profile["total_appointments"] > 0:
                            profile["reliability_score"] = round(
                                (profile["completed"] / profile["total_appointments"]) * 100, 2
                            )

                        if profile["no_shows"] >= 3:
                            profile["risk_level"] = "high"
                        elif profile["no_shows"] >= 1:
                            profile["risk_level"] = "medium"
                        else:
                            profile["risk_level"] = "low"

                    except Exception as e:
                        logger.error(f"Error processing outcome: {e}")
                        continue

    # Speichere aktualisierte Profile (atomic dual-write to JSON)
    _atomic_json_write(tracker.customer_file, profiles)

    # Secondary persistent storage (atomic write)
    try:
        _atomic_json_write(tracker.persistent_customer_file, profiles)
    except Exception as e:
        logger.warning(f"Could not write to persistent customers: {e}")

    logger.info(f"Updated {len(profiles)} customer profiles")


def get_customer_history(tracker, customer_name):
    """Hole die komplette Historie eines Kunden (PG-First, JSON-Fallback)"""
    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _get_customer_history_pg(customer_name)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"PG get_customer_history failed, falling back to JSON: {e}")

    # 2. JSON-Fallback
    return _get_customer_history_json(tracker, customer_name)


def _get_customer_history_pg(customer_name):
    """PG: Lade Kundenhistorie aus Booking + BookingOutcome + CustomerProfile"""
    from app.utils.db_utils import db_session_scope_no_commit
    with db_session_scope_no_commit() as session:
        # Bookings
        booking_rows = session.query(Booking).filter(
            Booking.customer.ilike(f"%{customer_name}%")
        ).order_by(Booking.date).all()

        # Outcomes
        outcome_rows = session.query(BookingOutcome).filter(
            BookingOutcome.customer.ilike(f"%{customer_name}%")
        ).order_by(BookingOutcome.date).all()

        if not booking_rows and not outcome_rows:
            return None

        history = {
            "customer": customer_name,
            "bookings": [],
            "outcomes": [],
            "stats": {
                "total_bookings": 0,
                "no_shows": 0,
                "completed": 0,
                "cancelled": 0,
                "no_show_rate": 0,
                "reliability_score": 0
            },
            "timeline": []
        }

        for b in booking_rows:
            history["bookings"].append({
                "booking_id": b.booking_id,
                "customer": b.customer,
                "date": str(b.date),
                "time": b.time,
                "user": b.username,
                "color_id": b.color_id,
                "potential_type": b.potential_type
            })
            history["stats"]["total_bookings"] += 1

        for o in outcome_rows:
            history["outcomes"].append({
                "outcome_id": o.outcome_id,
                "customer": o.customer,
                "date": str(o.date),
                "time": o.time,
                "outcome": o.outcome,
                "color_id": o.color_id
            })
            history["timeline"].append({
                "date": str(o.date),
                "time": o.time,
                "outcome": o.outcome,
                "color_id": o.color_id
            })
            if o.outcome == "no_show":
                history["stats"]["no_shows"] += 1
            elif o.outcome == "completed":
                history["stats"]["completed"] += 1
            elif o.outcome == "cancelled":
                history["stats"]["cancelled"] += 1

        history["timeline"].sort(key=lambda x: (x["date"], x["time"]))

        total_outcomes = history["stats"]["completed"] + history["stats"]["no_shows"] + history["stats"]["cancelled"]
        if total_outcomes > 0:
            history["stats"]["no_show_rate"] = round(
                history["stats"]["no_shows"] / total_outcomes * 100, 2
            )
            history["stats"]["reliability_score"] = round(
                history["stats"]["completed"] / total_outcomes * 100, 2
            )

        # Lade CustomerProfile
        profile = session.query(CustomerProfile).filter_by(customer=customer_name).first()
        if profile:
            history["profile"] = {
                "first_seen": profile.first_seen,
                "last_seen": profile.last_seen,
                "total_appointments": profile.total_appointments,
                "completed": profile.completed,
                "no_shows": profile.no_shows,
                "cancelled": profile.cancelled,
                "reliability_score": profile.reliability_score,
                "risk_level": profile.risk_level
            }

        return history


def _get_customer_history_json(tracker, customer_name):
    """JSON-Fallback: Lade Kundenhistorie aus JSONL-Dateien"""
    history = {
        "customer": customer_name,
        "bookings": [],
        "outcomes": [],
        "stats": {
            "total_bookings": 0,
            "no_shows": 0,
            "completed": 0,
            "cancelled": 0,
            "no_show_rate": 0,
            "reliability_score": 0
        },
        "timeline": []
    }

    if os.path.exists(tracker.bookings_file):
        with open(tracker.bookings_file, "r", encoding="utf-8") as f:
            for line in f:
                booking = json.loads(line)
                if customer_name.lower() in booking["customer"].lower():
                    history["bookings"].append(booking)
                    history["stats"]["total_bookings"] += 1

    if os.path.exists(tracker.outcomes_file):
        with open(tracker.outcomes_file, "r", encoding="utf-8") as f:
            for line in f:
                outcome = json.loads(line)
                if customer_name.lower() in outcome["customer"].lower():
                    history["outcomes"].append(outcome)
                    timeline_entry = {
                        "date": outcome["date"],
                        "time": outcome["time"],
                        "outcome": outcome["outcome"],
                        "color_id": outcome.get("color_id", "9")
                    }
                    history["timeline"].append(timeline_entry)
                    if outcome["outcome"] == "no_show":
                        history["stats"]["no_shows"] += 1
                    elif outcome["outcome"] == "completed":
                        history["stats"]["completed"] += 1
                    elif outcome["outcome"] == "cancelled":
                        history["stats"]["cancelled"] += 1

    history["timeline"].sort(key=lambda x: (x["date"], x["time"]))

    total_outcomes = history["stats"]["completed"] + history["stats"]["no_shows"] + history["stats"]["cancelled"]
    if total_outcomes > 0:
        history["stats"]["no_show_rate"] = round(
            history["stats"]["no_shows"] / total_outcomes * 100, 2
        )
        history["stats"]["reliability_score"] = round(
            history["stats"]["completed"] / total_outcomes * 100, 2
        )

    if os.path.exists(tracker.customer_file):
        with open(tracker.customer_file, "r", encoding="utf-8") as f:
            profiles = json.load(f)
            if customer_name in profiles:
                history["profile"] = profiles[customer_name]

    return history
