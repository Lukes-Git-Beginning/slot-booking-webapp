# -*- coding: utf-8 -*-
"""Track bookings with dual-write pattern + failure queue."""

import os
import json
import logging
from datetime import datetime
from time import sleep as _sleep

from app.services.tracking_system.converters import _get_potential_type

logger = logging.getLogger(__name__)

# PostgreSQL Models
try:
    from app.models import Booking, is_postgres_enabled
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# Timezone
import pytz
TZ = pytz.timezone("Europe/Berlin")


def track_booking(tracker, customer_name, date, time_slot, user, color_id, description=""):
    """
    Tracke eine neue Buchung mit Dual-Write Pattern + Auto-Retry

    Schreibt in:
    1. PostgreSQL (wenn USE_POSTGRES=true und verfügbar)
    2. JSONL-Datei (immer als Fallback)

    Bei komplettem Failure: 3 Versuche mit Backoff, dann Failure-Queue.
    """
    booking_data = None
    try:
        booking_date = datetime.strptime(date, "%Y-%m-%d")
        booking_id = f"{date}_{time_slot}_{customer_name}".replace(" ", "_")

        booking_data = {
            "id": booking_id,
            "timestamp": datetime.now(TZ).isoformat(),
            "customer": customer_name,
            "date": date,
            "time": time_slot,
            "weekday": booking_date.strftime("%A"),
            "week_number": booking_date.isocalendar()[1],
            "user": user,
            "potential_type": _get_potential_type(color_id),
            "color_id": color_id,
            "description_length": len(description) if description else 0,
            "has_description": bool(description),
            "booking_lead_time": (booking_date.date() - datetime.now(TZ).date()).days,
            "booked_at_hour": datetime.now(TZ).hour,
            "booked_on_weekday": datetime.now(TZ).strftime("%A")
        }

        # ========== DUAL-WRITE with AUTO-RETRY ==========
        from app.config.base import DataPersistenceConfig
        max_retries = DataPersistenceConfig.DUAL_WRITE_MAX_RETRIES
        retry_delays = DataPersistenceConfig.DUAL_WRITE_RETRY_DELAYS

        for attempt in range(max_retries):
            postgres_error = None
            postgres_success = False

            # 1. PostgreSQL schreiben (wenn aktiviert)
            if POSTGRES_AVAILABLE and is_postgres_enabled():
                try:
                    from app.utils.db_utils import db_session_scope

                    with db_session_scope() as session:
                        existing = session.query(Booking).filter_by(booking_id=booking_id).first()
                        if existing:
                            existing.customer = customer_name
                            existing.username = user
                            existing.color_id = color_id
                            existing.booking_timestamp = datetime.now(TZ)
                        else:
                            booking = Booking(
                                booking_id=booking_id,
                                customer=customer_name,
                                date=booking_date.date(),
                                time=time_slot,
                                weekday=booking_data["weekday"],
                                week_number=booking_data["week_number"],
                                username=user,
                                potential_type=booking_data["potential_type"],
                                color_id=color_id,
                                description_length=booking_data["description_length"],
                                has_description=booking_data["has_description"],
                                booking_lead_time=booking_data["booking_lead_time"],
                                booked_at_hour=booking_data["booked_at_hour"],
                                booked_on_weekday=booking_data["booked_on_weekday"],
                                booking_timestamp=datetime.now(TZ)
                            )
                            session.add(booking)

                    postgres_success = True
                    logger.info(f"Booking tracked to PostgreSQL: {booking_id} ({customer_name})")
                except Exception as e:
                    postgres_error = str(e)
                    logger.error(f"PostgreSQL write failed for {booking_id} ({customer_name}): {e}")

            # 2. JSONL schreiben (immer, als Fallback)
            try:
                os.makedirs(os.path.dirname(tracker.bookings_file), exist_ok=True)
                with open(tracker.bookings_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(booking_data, ensure_ascii=False) + "\n")
            except Exception as json_error:
                if not postgres_success:
                    # Both writes failed — retry if attempts remain
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            f"Dual-write attempt {attempt + 1}/{max_retries} failed for {booking_id}, "
                            f"retrying in {delay}s (PG: {postgres_error}, JSONL: {json_error})"
                        )
                        _sleep(delay)
                        continue

                    # All retries exhausted
                    logger.error(
                        "Dual-write tracking failed after all retries",
                        extra={
                            'booking_id': booking_id,
                            'customer': customer_name,
                            'date': date,
                            'time_slot': time_slot,
                            'user': user,
                            'postgres_error': postgres_error or 'N/A',
                            'jsonl_error': str(json_error),
                            'attempts': max_retries
                        },
                        exc_info=True
                    )
                    _queue_failed_booking(tracker, booking_data)
                    return None
                else:
                    # PostgreSQL succeeded, JSONL failed - not critical
                    logger.warning(
                        f"JSONL write failed but PostgreSQL succeeded for {booking_id}: {json_error}"
                    )

            # At least one write succeeded
            try:
                msg = f"Booking tracked: {booking_id} ({customer_name}) [PG={'ok' if postgres_success else 'fail'}, JSONL=ok]"
                if attempt > 0:
                    msg += f" (attempt {attempt + 1})"
                logger.info(msg)
            except Exception:
                pass

            return booking_data

    except Exception as e:
        logger.error(
            f"Unexpected error in track_booking: {e}",
            extra={
                'customer': customer_name,
                'date': date,
                'time_slot': time_slot
            },
            exc_info=True
        )
        if booking_data:
            _queue_failed_booking(tracker, booking_data)
        return None


def _queue_failed_booking(tracker, booking_data):
    """Speichere fehlgeschlagene Buchung in Failure-Queue für spätere Recovery"""
    try:
        failed_entry = {
            **booking_data,
            "failed_at": datetime.now(TZ).isoformat(),
            "recovered": False
        }
        os.makedirs(os.path.dirname(tracker.failed_bookings_file), exist_ok=True)
        with open(tracker.failed_bookings_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(failed_entry, ensure_ascii=False) + "\n")
        logger.warning(f"Queued failed booking for recovery: {booking_data.get('id', 'unknown')}")
    except Exception as e:
        logger.error(f"Could not queue failed booking: {e} — Data: {booking_data}")


def get_failed_bookings(tracker):
    """Lese alle unrecovered Failed Bookings aus der Queue"""
    failed = []
    if not os.path.exists(tracker.failed_bookings_file):
        return failed
    try:
        with open(tracker.failed_bookings_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if not entry.get("recovered", False):
                            failed.append(entry)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"Error reading failed bookings: {e}")
    return failed


def recover_failed_booking(tracker, booking_id):
    """Versuche eine fehlgeschlagene Buchung erneut zu tracken"""
    failed = []
    target = None

    if not os.path.exists(tracker.failed_bookings_file):
        return False, "No failed bookings file found"

    # Lese alle Einträge
    try:
        with open(tracker.failed_bookings_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        failed.append(entry)
                        if entry.get("id") == booking_id and not entry.get("recovered", False):
                            target = entry
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        return False, f"Error reading failed bookings: {e}"

    if not target:
        return False, f"Booking {booking_id} not found in failed queue"

    # Versuche erneut zu tracken
    result = tracker.track_booking(
        customer_name=target["customer"],
        date=target["date"],
        time_slot=target["time"],
        user=target["user"],
        color_id=target["color_id"],
        description=""
    )

    if result is None:
        return False, f"Retry failed for {booking_id}"

    # Markiere als recovered
    for entry in failed:
        if entry.get("id") == booking_id:
            entry["recovered"] = True
            entry["recovered_at"] = datetime.now(TZ).isoformat()

    try:
        with open(tracker.failed_bookings_file, "w", encoding="utf-8") as f:
            for entry in failed:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Could not update failed bookings file: {e}")

    logger.info(f"Successfully recovered failed booking: {booking_id}")
    return True, f"Booking {booking_id} recovered successfully"
