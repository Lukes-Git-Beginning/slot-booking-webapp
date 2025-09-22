# -*- coding: utf-8 -*-
"""
Booking routes
Slot booking functionality and related endpoints
"""

import pytz
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, url_for, flash, session

from app.config.base import config, slot_config
from app.core.extensions import cache_manager, data_persistence, tracking_system
from app.core.google_calendar import get_google_calendar_service
from app.services.booking_service import get_effective_availability, get_slot_status, get_slot_points
from app.utils.decorators import require_login
from app.utils.helpers import is_admin
from error_handler import raise_validation_error
from request_deduplication import request_deduplicator, SlotLockContext
from app.utils.logging import booking_logger, log_request

booking_bp = Blueprint('booking', __name__)
TZ = pytz.timezone(slot_config.TIMEZONE)


def add_points_to_user(user, points):
    """
    Add points to user with Achievement System Integration
    Migrated from original slot_booking_webapp.py
    """
    try:
        # Load scores with robust persistence system
        scores = data_persistence.load_scores()

        month = datetime.now(TZ).strftime("%Y-%m")
        if user not in scores:
            scores[user] = {}

        scores[user][month] = scores[user].get(month, 0) + points
        data_persistence.save_scores(scores)

        # Achievement system integration
        new_badges = []
        try:
            from app.services.achievement_system import achievement_system
            if achievement_system:
                new_badges = achievement_system.process_user_achievements(user)
        except ImportError:
            pass
        except Exception as e:
            booking_logger.warning(f"Could not process achievements for user {user}: {e}")

        return new_badges

    except Exception as e:
        booking_logger.error(f"Error adding points to user {user}: {e}")
        return []


@booking_bp.route("/book", methods=["POST"])
@require_login
def book():
    """Handle slot booking"""
    user = session.get("user")

    with log_request(booking_logger, "create_booking", user_id=user) as request_id:
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()
        description = request.form.get("description", "").strip()
        date = request.form.get("date", "")
        hour = request.form.get("hour", "")
        color_id = request.form.get("color", "9")

        # Input validation
        if not all([first, last, date, hour]):
            raise_validation_error(
                "Pflichtfelder fehlen",
                user_message="Bitte alle Pflichtfelder ausfüllen."
            )

        # Length validation
        if len(first) > 100 or len(last) > 100:
            raise_validation_error(
                "Name zu lang",
                user_message="Name darf nicht länger als 100 Zeichen sein."
            )

        if len(description) > 500:
            raise_validation_error(
                "Beschreibung zu lang",
                user_message="Beschreibung darf nicht länger als 500 Zeichen sein."
            )

        # Date format validation
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise_validation_error(
                "Ungültiges Datumsformat",
                user_message="Ungültiges Datum."
            )

        # Hour format validation
        valid_hours = ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]
        if hour not in valid_hours:
            raise_validation_error(
                "Ungültige Uhrzeit",
                user_message="Ungültige Uhrzeit gewählt."
            )

        # Request deduplication - prevents concurrent bookings
        with SlotLockContext(request_deduplicator, user, date, hour) as lock_id:
            if lock_id is None:
                flash("Slot wird gerade von einem anderen Nutzer bearbeitet. Bitte versuchen Sie es erneut.", "warning")
                return redirect(url_for("main.day_view", date_str=date))

        # Use effective availability (loaded data + fallback defaults)
        effective_beraters = get_effective_availability(date, hour)
        berater_count = len(effective_beraters)

        # Block booking if no consultants available (no Standard-Verfügbarkeit for this slot)
        if berater_count == 0:
            flash("Für diesen Zeitslot ist keine Standard-Verfügbarkeit konfiguriert.", "warning")
            return redirect(url_for("main.day_view", date_str=date))

        slot_list, booked, total, freie_count, overbooked = get_slot_status(date, hour, berater_count)

        try:
            slot_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise_validation_error(
                f"Ungültiges Datum: {date}",
                field="date",
                user_message="Das angegebene Datum ist ungültig."
            )

        points = get_slot_points(hour, slot_date)

        if overbooked or freie_count <= 0:
            flash("Slot ist bereits voll belegt.", "danger")
            return redirect(url_for("main.day_view", date_str=date))

        try:
            slot_start = TZ.localize(datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M"))
            slot_end = slot_start + timedelta(hours=2)
        except Exception as e:
            flash("Fehler beim Erstellen des Termins.", "danger")
            print(f"Fehler beim Parsen der Zeit: {e}")
            return redirect(url_for("main.day_view", date_str=date))

        event_body = {
            "summary": f"{last}, {first}",
            "description": description,
            "start": {"dateTime": slot_start.isoformat()},
            "end": {"dateTime": slot_end.isoformat()},
            "colorId": color_id
        }

        calendar_service = get_google_calendar_service()
        if not calendar_service:
            flash("Calendar service not available", "danger")
            return redirect(url_for("main.day_view", date_str=date))

        result = calendar_service.create_event(
            calendar_id=config.CENTRAL_CALENDAR_ID,
            event_data=event_body
        )

        if result:
            # Invalidate cache for this slot since we just booked it
            cache_key = f"{date}_{hour}"
            cache_manager.invalidate("calendar_events", cache_key)

            # Add tracking
            try:
                if tracking_system:
                    tracking_system.track_booking(
                        customer_name=f"{last}, {first}",
                        date=date,
                        time_slot=hour,
                        user=user or "unknown",
                        color_id=color_id,
                        description=description
                    )
            except Exception as e:
                booking_logger.warning(f"Tracking error for booking {last}, {first} on {date} {hour}: {e}")

            # Achievement System Integration
            new_badges = []
            if user and user != "unknown":
                new_badges = add_points_to_user(user, points)
                if points > 0:
                    flash(f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) erhalten.", "success")
                else:
                    flash("Slot erfolgreich gebucht!", "success")
            else:
                flash("Slot erfolgreich gebucht!", "success")

            # Quest Progress Integration
            if user and user != "unknown":
                try:
                    from gamification_routes import update_quest_progress_for_booking
                    booking_data = {
                        "has_description": bool(description),
                        "booking_time": int(hour.split(":")[0]) if isinstance(hour, str) and ":" in hour else 0,
                        "points_earned": points,
                        "date": date,
                        "hour": hour
                    }
                    update_quest_progress_for_booking(user, booking_data)
                except ImportError:
                    pass  # Enhanced features not available
                except Exception as e:
                    booking_logger.warning(f"Could not update quest progress for user {user}: {e}")

            # Store special badge counters (evening/morning) persistently
            try:
                if user and user != "unknown":
                    daily_stats = data_persistence.load_daily_user_stats()
                    today_key = datetime.now(TZ).strftime("%Y-%m-%d")
                    if user not in daily_stats:
                        daily_stats[user] = {}
                    if today_key not in daily_stats[user]:
                        daily_stats[user][today_key] = {"points": 0, "bookings": 0, "first_booking": False}
                    h_int = int(hour.split(":")[0]) if isinstance(hour, str) and ":" in hour else 0
                    if h_int >= 18:
                        daily_stats[user][today_key]["evening_bookings"] = daily_stats[user][today_key].get("evening_bookings", 0) + 1
                    elif 9 <= h_int < 12:
                        daily_stats[user][today_key]["morning_bookings"] = daily_stats[user][today_key].get("morning_bookings", 0) + 1
                    data_persistence.save_daily_user_stats(daily_stats)
            except Exception as e:
                print(f"Warning: Could not update special badge counters: {e}")

            # Show new badges
            if new_badges:
                badge_names = [badge["name"] for badge in new_badges]
                flash(f"Neue Badges erhalten: {', '.join(badge_names)}", "success")
        else:
            flash("Fehler beim Buchen des Slots. Bitte versuche es später erneut.", "danger")

        return redirect(url_for("main.day_view", date_str=date))