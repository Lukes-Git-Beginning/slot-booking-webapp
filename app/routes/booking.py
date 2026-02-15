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
from app.core.extensions import cache_manager, limiter
from app.core.google_calendar import get_google_calendar_service
from app.services.booking_service import (
    get_effective_availability, get_slot_status, get_slot_points,
    execute_post_booking_chain
)
from app.utils.decorators import require_login
from app.utils.error_handler import raise_validation_error
from app.utils.request_deduplication import request_deduplicator, SlotLockContext
from app.utils.logging import booking_logger, log_request
from app.utils.memory_guard import memory_guard

booking_bp = Blueprint('booking', __name__)
TZ = pytz.timezone(slot_config.TIMEZONE)


def apply_rate_limit(route_func):
    """Apply rate limiting decorator if limiter is available"""
    if limiter:
        return limiter.limit("20 per minute", methods=["POST"])(route_func)
    return route_func


def apply_csrf_exempt(route_func):
    """Apply CSRF exemption for JSON-API routes (uses session-based auth)"""
    if csrf:
        return csrf.exempt(route_func)
    return route_func


@booking_bp.route("/book", methods=["POST"])
@apply_csrf_exempt  # JSON-API uses session-based auth, CSRF exempt per CSRF_STRATEGY.md
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

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise_validation_error(
                "Ungültiges Datumsformat",
                user_message="Ungültiges Datum."
            )

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

        # Availability & capacity check
        effective_beraters = get_effective_availability(date, hour)
        berater_count = len(effective_beraters)

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

        # Build calendar event
        try:
            slot_start = TZ.localize(datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M"))
            slot_end = slot_start + timedelta(hours=2)
        except ValueError as e:
            from app.utils.error_tracking import generate_error_id
            error_id = generate_error_id("BOOK")
            booking_logger.error(f"Date parsing error {error_id}: date={date}, hour={hour}, error={e}")
            flash(
                f"Ungültiges Datums-/Zeitformat. Bitte verwenden Sie das Formular zur Auswahl. (Fehler-ID: {error_id})",
                "danger"
            )
            return redirect(url_for("main.day_view", date_str=date))
        except Exception as e:
            from app.utils.error_tracking import generate_error_id
            error_id = generate_error_id("BOOK")
            booking_logger.error(f"Timezone localization error {error_id}: {e}", exc_info=True)
            flash(
                f"Zeitzone-Konvertierung fehlgeschlagen. Bitte Support kontaktieren. (Fehler-ID: {error_id})",
                "danger"
            )
            return redirect(url_for("main.day_view", date_str=date))

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

        from app.utils.error_messages import get_error_message
        from app.utils.error_tracking import generate_error_id

        calendar_service = get_google_calendar_service()
        if not calendar_service:
            error_id = generate_error_id("CAL")
            booking_logger.critical(f"Calendar service initialization failed {error_id}")
            error_msg = get_error_message('CONFIGURATION')
            flash(
                f"{error_msg['title']}: {error_msg['message']} (Fehler-ID: {error_id})",
                "danger"
            )

            try:
                from app.services.notification_service import notification_service
                notification_service.create_notification(
                    roles=['admin'],
                    title='CRITICAL: Calendar Service Down',
                    message=f'Calendar service initialization failed. Error ID: {error_id}',
                    notification_type='error',
                    show_popup=True
                )
            except Exception:
                pass
            return redirect(url_for("main.day_view", date_str=date))

        result, error_context = calendar_service.create_event_with_context(
            calendar_id=config.CENTRAL_CALENDAR_ID,
            event_data=event_body
        )

        if not result:
            error_id = generate_error_id("CAL")
            error_category = error_context.get('category', 'CALENDAR_UNAVAILABLE')

            booking_logger.error(
                f"Calendar event creation failed {error_id}: "
                f"customer={last}, {first}, date={date}, hour={hour}, "
                f"category={error_category}, details={error_context}",
                extra_fields={'error_id': error_id, 'error_context': error_context}
            )

            error_msg = get_error_message(error_category)
            flash_message = f"{error_msg['title']}: {error_msg['message']}"
            if error_msg.get('show_error_id', False):
                flash_message += f" (Fehler-ID: {error_id})"

            flash(flash_message, "danger")
            return redirect(url_for("main.day_view", date_str=date))

        # Event created successfully — invalidate caches
        cache_manager.invalidate("calendar_events", f"{date}_{hour}")
        cache_manager.clear_all()

        # Post-booking chain: tracking, points, quests, stats, audit
        chain = execute_post_booking_chain(
            user=user,
            customer_name=f"{last}, {first}",
            date=date,
            hour=hour,
            color_id=color_id,
            description=description,
            points=points,
            calendar_event_id=result.get('id', 'unknown')
        )

        for msg, category in chain["flash_messages"]:
            flash(msg, category)

        return redirect(url_for("main.day_view", date_str=date))
