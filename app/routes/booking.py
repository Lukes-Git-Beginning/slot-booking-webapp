# -*- coding: utf-8 -*-
"""
Booking routes
Slot booking functionality and related endpoints
"""

import pytz
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, url_for, flash, session

from app.config.base import config, slot_config
from app.core.extensions import csrf
from app.core.extensions import cache_manager, data_persistence, tracking_system, limiter
from app.core.google_calendar import get_google_calendar_service
from app.services.booking_service import get_effective_availability, get_slot_status, get_slot_points
from app.utils.decorators import require_login
from app.utils.helpers import is_admin
from app.utils.error_handler import raise_validation_error
from app.utils.request_deduplication import request_deduplicator, SlotLockContext
from app.utils.logging import booking_logger, log_request
from app.utils.memory_guard import memory_guard, safe_import, force_garbage_collection

booking_bp = Blueprint('booking', __name__)
TZ = pytz.timezone(slot_config.TIMEZONE)


def apply_rate_limit(route_func):
    """Apply rate limiting decorator if limiter is available"""
    if limiter:
        return limiter.limit("20 per minute", methods=["POST"])(route_func)
    return route_func


def add_points_to_user(user, points):
    """
    Add points to user with Achievement System Integration
    Migrated from original slot_booking_webapp.py
    Enhanced with memory-safe error handling to prevent SIGSEGV crashes

    Coins System Integration:
    - Points are added to scores.json (permanent, never reduced)
    - Equal amount of coins added to user_coins.json (can be spent in shop)
    - Coins separate from points to preserve scoreboard integrity
    """
    try:
        # Load scores with robust persistence system
        scores = data_persistence.load_scores()

        month = datetime.now(TZ).strftime("%Y-%m")
        if user not in scores:
            scores[user] = {}

        scores[user][month] = scores[user].get(month, 0) + points
        data_persistence.save_scores(scores)

        # Add equal amount of coins for cosmetics shop
        try:
            from app.services.daily_quests import daily_quest_system
            coins_data = daily_quest_system.load_user_coins()
            current_coins = coins_data.get(user, 0)
            coins_data[user] = current_coins + points
            daily_quest_system.save_user_coins(coins_data)
            booking_logger.info(f"Added {points} coins to user {user} (total: {coins_data[user]})")
        except Exception as e:
            booking_logger.error(f"Error adding coins to user {user}: {e}", exc_info=True)
            # Continue even if coins fail - points are still awarded

        # Achievement system integration with memory-safe guards
        new_badges = []
        try:
            # Safe import with memory protection
            achievement_module = safe_import('app.services.achievement_system')

            if achievement_module and hasattr(achievement_module, 'achievement_system'):
                achievement_system = achievement_module.achievement_system

                if achievement_system:
                    # Process achievements with size limits to prevent memory overflow
                    new_badges = achievement_system.process_user_achievements(user)
                    # Limit badge list size to prevent memory issues
                    if isinstance(new_badges, list) and len(new_badges) > 20:
                        booking_logger.warning(f"Achievement system returned {len(new_badges)} badges, limiting to 20")
                        new_badges = new_badges[:20]

        except MemoryError:
            booking_logger.error(f"Memory error in achievement system for user {user}")
            force_garbage_collection()  # Versuche Speicher freizugeben
            pass
        except Exception as e:
            booking_logger.error(f"Could not process achievements for user {user}: {e}", exc_info=True)
            pass

        return new_badges if isinstance(new_badges, list) else []

    except Exception as e:
        booking_logger.error(f"Error adding points to user {user}: {e}", exc_info=True)
        return []


@booking_bp.route("/book", methods=["POST"])
@csrf.exempt  # CSRF exempt for booking endpoint (legacy form without token)
@require_login
@apply_rate_limit
@memory_guard(max_retries=1, cleanup_on_error=True)
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

        points = get_slot_points(hour, slot_date, date, berater_count, color_id)

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

        # Add "Booked by" tag to description for tracking who created the booking
        # Normalize username to ensure consistency across all systems
        from app.utils.helpers import normalize_username
        normalized_user = normalize_username(user) if user else user

        booking_description = description
        if normalized_user and normalized_user != "unknown":
            booking_description = f"{description}\n\n[Booked by: {normalized_user}]" if description else f"[Booked by: {normalized_user}]"

        event_body = {
            "summary": f"{last}, {first}",
            "description": booking_description,
            "start": {"dateTime": slot_start.isoformat()},
            "end": {"dateTime": slot_end.isoformat()},
            "colorId": color_id
        }

        calendar_service = get_google_calendar_service()
        if not calendar_service:
            flash("Kalender-Service nicht verfügbar", "danger")
            return redirect(url_for("main.day_view", date_str=date))

        result = calendar_service.create_event(
            calendar_id=config.CENTRAL_CALENDAR_ID,
            event_data=event_body
        )

        if result:
            # Invalidate cache for this slot since we just booked it
            cache_key = f"{date}_{hour}"
            cache_manager.invalidate("calendar_events", cache_key)

            # Invalidate personal calendar cache for immediate visibility in my-calendar
            cache_manager.clear_all()  # Clear all calendar caches to ensure fresh data

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

            # Achievement System Integration with Enhanced Error Handling
            new_badges = []
            if user and user != "unknown":
                try:
                    new_badges = add_points_to_user(user, points)
                    if points > 0:
                        flash(f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) und {points} Coins erhalten.", "success")
                    else:
                        flash("Slot erfolgreich gebucht!", "success")
                except Exception as e:
                    booking_logger.error(f"Critical error in achievement system for user {user}: {e}", exc_info=True)
                    # Continue with success message but without achievement processing
                    flash("Slot erfolgreich gebucht!", "success")
            else:
                flash("Slot erfolgreich gebucht!", "success")

            # Quest Progress Integration
            if user and user != "unknown":
                try:
                    from app.routes.gamification.legacy_routes import update_quest_progress_for_booking
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
                booking_logger.warning(f"Could not update special badge counters for user {user}: {e}", exc_info=True)

            # Show new badges
            if new_badges:
                badge_names = [badge["name"] for badge in new_badges]
                flash(f"Neue Badges erhalten: {', '.join(badge_names)}", "success")
        else:
            flash("Fehler beim Buchen des Slots. Bitte versuche es später erneut.", "danger")

        return redirect(url_for("main.day_view", date_str=date))