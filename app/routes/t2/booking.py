# -*- coding: utf-8 -*-
"""
T2 Booking Routes - Calendly-Style 4-Step Booking Flow

Routes (23 total):
1. /t2/booking/calendly - Main booking UI
2. /t2/api/available-dates - Date picker API
3. /t2/api/available-times - Time slot API
4. /t2/api/book-appointment - Booking submission
5. /t2/my-bookings - User's appointments list
6. /t2/api/cancel-booking - Cancel appointment
7. /t2/api/reschedule-booking - Reschedule request
8. /t2/api/get-reschedule-slots - Reschedule time slots
9. /t2/booking/success - Success page
10. /t2/booking/error - Error page
11. /t2/api/booking-stats - Booking statistics
12. /t2/api/select-berater - Berater selection
13. /t2/api/my-2h-bookings - User's 2h bookings
14. /t2/api/month-availability/<berater>/<year>/<month> - Month availability
15. /t2/api/day-slots/<berater>/<date> - Day slots
16. /t2/api/book-2h-slot - Book 2h slot
17. /t2/api/check-coach-availability/<coach>/<year>/<month> - Coach availability
18. /t2/api/admin/2h-analytics - Admin analytics
19. /t2/api/availability-calendar/<closer> - 6-week availability (C.4)
20. /t2/api/availability/<closer>/<date> - Free slots for date (C.4)
21. /t2/api/my-calendar-events/<date> - Closer's own events (C.4)
22. /t2/api/my-upcoming-events - Closer's next 5 events (C.4)
23. /t2/api/my-upcoming-bookings - Opener's upcoming bookings (C.4)

Migration Status: Phase 2 - Stub created, implementation in Phase 5
"""

from flask import Blueprint, render_template, jsonify, request, session, flash, redirect, url_for
from app.utils.decorators import require_login
from app.utils.rate_limiting import rate_limit_api
from app.services.t2_dynamic_availability import t2_dynamic_availability
from app.services.data_persistence import data_persistence
from app.services.tracking_system import tracking_system
from app.services.t2_analytics_service import t2_analytics_service
from app.core.google_calendar import GoogleCalendarService, get_google_calendar_service
from app.services.t2_availability_service import availability_service
from app.services.t2_calendar_parser import calendar_parser
from .utils import (
    is_admin_user,
    is_closer,
    T2_CLOSERS,
    get_user_tickets_remaining,
    get_next_ticket_reset,
    get_user_t2_bookings,
    get_next_t2_appointments,
    load_t2_bookings,
    can_modify_booking,
    return_user_ticket,
    save_t2_booking,
    consume_user_ticket
)
import logging
import uuid
import pytz
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Create sub-blueprint
booking_bp = Blueprint('booking', __name__)


@booking_bp.route('/booking-calendly')
@require_login
def booking_calendly():
    """
    Neue Calendly-Style T2-Buchungsseite.

    Flow:
    1. Berater-Auswahl (nach Würfel)
    2. Monats-Kalender
    3. 2h-Slot-Auswahl (gruppiert)
    4. Kundeninfo-Formular

    MIGRATED FROM: t2_legacy.py line 182
    TEMPLATE: templates/t2/booking_calendly.html
    """
    user = session.get('user')

    # Check: Coach wurde gewürfelt?
    coach = session.get('t2_current_closer')
    logger.info(f"Booking access: user={user}, coach={coach}, session_keys={list(session.keys())}")

    if not coach or coach not in T2_CLOSERS:
        logger.warning(f"Missing/invalid coach in session: coach={coach}, in_T2_CLOSERS={coach in T2_CLOSERS if coach else False}")
        flash('Bitte ziehe zuerst einen Coach im Würfelsystem.', 'warning')
        return redirect(url_for('t2.draw_page'))

    # Check: Tickets verfügbar?
    tickets_remaining = get_user_tickets_remaining(user)
    if tickets_remaining <= 0:
        return render_template('t2/no_tickets.html',
                             user=user,
                             next_reset=get_next_ticket_reset())

    return render_template('t2/booking_calendly.html',
                         user=user,
                         coach=coach,
                         T2_CLOSERS=T2_CLOSERS,
                         tickets_remaining=tickets_remaining)


@booking_bp.route('/api/available-dates', methods=['POST'])
@require_login
@rate_limit_api
def available_dates():
    """
    Get available dates for selected consultant (POST variant)

    Request JSON:
        {"berater": "Christian", "year": 2025, "month": 11}

    Response:
        {"success": true, "days": {"2025-11-25": 3, ...}}

    MIGRATED FROM: t2_legacy.py line 945
    """
    try:
        data = request.get_json() or {}
        berater = data.get('berater')
        year = data.get('year')
        month = data.get('month')

        if not berater or not year or not month:
            return jsonify({'success': False, 'error': 'berater, year, and month required'}), 400

        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        year = int(year)
        month = int(month)
        if month < 1 or month > 12:
            return jsonify({'success': False, 'error': 'Invalid month'}), 400

        calendar_id = T2_CLOSERS[berater]['calendar_id']
        availability = t2_dynamic_availability.get_month_availability(calendar_id, year, month)

        return jsonify({
            'success': True,
            'days': availability,
            'total_days': len(availability)
        })

    except Exception as e:
        logger.error(f"Error loading available dates: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/available-times', methods=['POST'])
@require_login
@rate_limit_api
def available_times():
    """
    Get available time slots for selected date (POST variant)

    Request JSON:
        {"berater": "Christian", "date": "2025-11-25"}

    Response:
        {"success": true, "slots": {"morning": [...], "midday": [...], "evening": [...]}}

    MIGRATED FROM: t2_legacy.py line 998
    """
    try:
        data = request.get_json() or {}
        berater = data.get('berater')
        date_str = data.get('date')

        if not berater or not date_str:
            return jsonify({'success': False, 'error': 'berater and date required'}), 400

        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        try:
            check_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400

        calendar_id = T2_CLOSERS[berater]['calendar_id']
        slots = t2_dynamic_availability.find_2h_slots_non_overlapping(calendar_id, check_date)
        total_slots = len(slots['morning']) + len(slots['midday']) + len(slots['evening'])

        return jsonify({
            'success': True,
            'slots': slots,
            'total_slots': total_slots
        })

    except Exception as e:
        logger.error(f"Error loading available times: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/book-appointment', methods=['POST'])
@require_login
@rate_limit_api
def book_appointment():
    """
    Submit booking and create Google Calendar event (alias for book-2h-slot)

    Delegates to api_book_2h_slot() logic. This endpoint exists for backward
    compatibility with the legacy booking flow.

    Request JSON: Same as /api/book-2h-slot

    MIGRATED FROM: t2_legacy.py line 1056
    """
    return api_book_2h_slot()


@booking_bp.route('/my-bookings')
@require_login
def my_bookings():
    """
    My T2 2-Hour Bookings Management Page
    View, cancel, and reschedule 2-hour appointments

    MIGRATED FROM: t2_legacy.py line 1056
    TEMPLATE: templates/t2/my_bookings.html
    """
    user = session.get('user')

    return render_template('t2/my_bookings.html',
                         user=user,
                         is_admin=is_admin_user(user))


@booking_bp.route('/api/cancel-booking', methods=['POST'])
@require_login
@rate_limit_api
def api_cancel_booking():
    """
    API: Storniert eine T2-Buchung.

    Auth: User = Booker ODER User = Admin
    Ticket wird zurückgegeben.

    Request JSON:
        {"booking_id": "T2-ABC12345"}

    Response:
        {"success": true, "message": "Buchung storniert. Ticket zurückgegeben."}

    MIGRATED FROM: t2_legacy.py line 1784
    """
    try:
        user = session.get('user')
        data = request.json

        if not data or 'booking_id' not in data:
            return jsonify({'success': False, 'error': 'booking_id required'}), 400

        booking_id = data['booking_id']

        # Lade alle Buchungen (PostgreSQL-first, JSON fallback)
        all_bookings = load_t2_bookings()

        # Finde Buchung
        booking = None
        booking_index = None
        for i, b in enumerate(all_bookings):
            if b.get('id') == booking_id:
                booking = b
                booking_index = i
                break

        if not booking:
            return jsonify({'success': False, 'error': 'Buchung nicht gefunden'}), 404

        # Auth-Check
        if not can_modify_booking(booking, user):
            return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

        # Bereits storniert?
        if booking.get('status') == 'cancelled':
            return jsonify({'success': False, 'error': 'Buchung bereits storniert'}), 400

        # 1. Google Calendar Event löschen (wenn vorhanden)
        event_id = booking.get('event_id')
        calendar_id = booking.get('calendar_id')
        berater = booking.get('berater')

        if event_id and calendar_id:
            try:
                from app.core.google_calendar import GoogleCalendarService
                calendar_service = GoogleCalendarService()
                success, error = calendar_service.delete_event(calendar_id, event_id)

                if success:
                    logger.info(f"Successfully deleted calendar event {event_id} for booking {booking_id}")
                else:
                    logger.error(f"Failed to delete calendar event {event_id}: {error}")
                    # Continue with cancellation anyway - calendar failure shouldn't block booking cancellation
            except Exception as e:
                logger.error(f"Exception deleting calendar event: {e}")
                # Continue with cancellation anyway
        elif berater and berater in T2_CLOSERS and T2_CLOSERS[berater].get('can_write', False):
            logger.warning(f"Booking {booking_id} has no event_id - manual calendar cleanup required")
        else:
            logger.info(f"Skipping calendar deletion for {berater} (no write access or mock)")

        # 2. Status auf cancelled setzen
        all_bookings[booking_index]['status'] = 'cancelled'
        all_bookings[booking_index]['cancelled_at'] = datetime.now().isoformat()
        all_bookings[booking_index]['cancelled_by'] = user

        # 3. PostgreSQL Update (if enabled)
        from app.models import T2Booking, get_db_session, is_postgres_enabled
        if is_postgres_enabled():
            try:
                db_session = get_db_session()
                if db_session:
                    db_booking = db_session.query(T2Booking).filter_by(booking_id=booking_id).first()
                    if db_booking:
                        db_booking.status = 'cancelled'
                        db_session.commit()
                        logger.info(f"✅ Updated T2 booking status in PostgreSQL: {booking_id}")
                    db_session.close()
            except Exception as e:
                logger.error(f"⚠️ PostgreSQL update failed for T2 booking {booking_id}: {e}")
                # Continue with JSON update anyway

        # 4. Speichern (JSON Backup)
        data_persistence.save_data('t2_bookings', {'bookings': all_bookings})

        # 5. Ticket zurückgeben
        booking_user = booking.get('user')
        if booking_user:
            return_user_ticket(booking_user)

        # 6. Cache invalidieren
        booking_date_str = booking.get('date')
        if booking_date_str and berater and berater in T2_CLOSERS:
            try:
                booking_date = datetime.fromisoformat(booking_date_str).date()
                calendar_id = T2_CLOSERS[berater]['calendar_id']
                t2_dynamic_availability.clear_cache_for_berater(calendar_id, booking_date)
            except Exception as e:
                logger.warning(f"Cache clear failed: {e}")

        logger.info(f"User {user}: Cancelled booking {booking_id}")

        return jsonify({
            'success': True,
            'message': 'Buchung storniert. Ticket zurückgegeben.'
        })

    except Exception as e:
        logger.error(f"Error cancelling booking: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/reschedule-booking', methods=['POST'])
@require_login
@rate_limit_api
def api_reschedule_booking():
    """
    API: Bucht T2-Termin um.

    Auth: User = Booker ODER User = Admin
    Ticket wird NICHT zurückgegeben (bleibt verbraucht).

    Request JSON:
        {
            "booking_id": "T2-ABC12345",
            "new_date": "2025-11-26",
            "new_time": "16:00"
        }

    Response:
        {
            "success": true,
            "new_booking_id": "T2-XYZ67890",
            "message": "Buchung erfolgreich umgebucht."
        }

    MIGRATED FROM: t2_legacy.py line 1908
    """
    try:
        user = session.get('user')
        data = request.json

        # Validation
        required = ['booking_id', 'new_date', 'new_time']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} required'}), 400

        booking_id = data['booking_id']
        new_date_str = data['new_date']
        new_time_str = data['new_time']

        # Lade alle Buchungen (PostgreSQL-first, JSON fallback)
        all_bookings = load_t2_bookings()

        # Finde Buchung
        booking = None
        booking_index = None
        for i, b in enumerate(all_bookings):
            if b.get('id') == booking_id:
                booking = b
                booking_index = i
                break

        if not booking:
            return jsonify({'success': False, 'error': 'Buchung nicht gefunden'}), 404

        # Auth-Check
        if not can_modify_booking(booking, user):
            return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

        # Bereits storniert/umgebucht?
        if booking.get('status') in ['cancelled', 'rescheduled']:
            return jsonify({'success': False, 'error': 'Buchung wurde bereits storniert/umgebucht'}), 400

        # Parse new date/time
        try:
            new_date = datetime.fromisoformat(new_date_str).date()
            hour, minute = map(int, new_time_str.split(':'))
            new_datetime = datetime.combine(new_date, datetime.min.time().replace(hour=hour, minute=minute))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date or time format'}), 400

        # Live Slot-Check
        berater = booking.get('berater')
        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        calendar_id = T2_CLOSERS[berater]['calendar_id']
        is_free = t2_dynamic_availability.is_2h_slot_free(calendar_id, new_date, new_time_str)

        if not is_free:
            return jsonify({
                'success': False,
                'error': f'{berater} ist am {new_date_str} um {new_time_str} nicht verfügbar.'
            }), 409

        # 1. Alte Buchung auf 'rescheduled' setzen
        all_bookings[booking_index]['status'] = 'rescheduled'
        all_bookings[booking_index]['rescheduled_at'] = datetime.now().isoformat()
        all_bookings[booking_index]['rescheduled_by'] = user
        all_bookings[booking_index]['rescheduled_to'] = new_date_str

        # 1a. PostgreSQL Update für alte Buchung (if enabled)
        from app.models import T2Booking, get_db_session, is_postgres_enabled
        if is_postgres_enabled():
            try:
                db_session = get_db_session()
                if db_session:
                    old_booking = db_session.query(T2Booking).filter_by(booking_id=booking_id).first()
                    if old_booking:
                        old_booking.status = 'rescheduled'
                        db_session.commit()
                        logger.info(f"✅ Updated old T2 booking status in PostgreSQL: {booking_id}")
                    db_session.close()
            except Exception as e:
                logger.error(f"⚠️ PostgreSQL update failed for old booking {booking_id}: {e}")
                # Continue anyway

        # 2. Neue Buchung erstellen
        coach = booking.get('coach')
        customer = booking.get('customer')
        topic = booking.get('topic', '')
        email = booking.get('email', '')

        new_booking_id = f"T2-{uuid.uuid4().hex[:8].upper()}"
        end_datetime = new_datetime + timedelta(hours=2)

        # Event-Titel
        if coach == berater:
            event_title = f"T2 - Kunde: {customer} | Coach: {coach}"
        else:
            event_title = f"T2 - Kunde: {customer} | Coach: {coach}"

        # Description
        berlin_tz = pytz.timezone('Europe/Berlin')
        start_iso = berlin_tz.localize(new_datetime).isoformat()
        end_iso = berlin_tz.localize(end_datetime).isoformat()

        event_body = {
            'summary': event_title,
            'description': f"T2-Termin (UMGEBUCHT)\n\nKunde: {customer}\nCoach: {coach}\nBerater: {berater}\nThema: {topic}\nEmail: {email}\n\n[Booked by: {booking.get('user')}]\n[Rescheduled by: {user}]",
            'start': {'dateTime': start_iso, 'timeZone': 'Europe/Berlin'},
            'end': {'dateTime': end_iso, 'timeZone': 'Europe/Berlin'},
            'colorId': '5'  # Banana (Gelb - T2-Farbe für visuelle Unterscheidung von T1)
        }

        # Google Calendar Event erstellen (wenn Schreibrechte)
        reschedule_event_id = None
        reschedule_calendar_id = None

        if T2_CLOSERS[berater].get('can_write', False):
            try:
                from app.utils.error_messages import get_error_message
                from app.utils.error_tracking import generate_error_id

                calendar_service = GoogleCalendarService()
                result, error_context = calendar_service.create_event_with_context(calendar_id, event_body)

                if result:
                    reschedule_event_id = result.get('id')
                    reschedule_calendar_id = calendar_id
                    logger.info(f"New calendar event created for rescheduled booking: {reschedule_event_id}")
                else:
                    error_id = generate_error_id("CAL")
                    error_category = error_context.get('category', 'CALENDAR_UNAVAILABLE')
                    error_msg = get_error_message(error_category)
                    logger.error(f"Calendar event creation failed for reschedule {error_id}: category={error_category}, details={error_context}")
                    # Continue with booking anyway (calendar failure doesn't stop reschedule)
            except Exception as e:
                from app.utils.error_tracking import generate_error_id
                error_id = generate_error_id("CAL")
                logger.error(f"Calendar write failed {error_id}: {e}")
                # Continue with booking anyway
        else:
            logger.info(f"Mock reschedule for {berater} (no write access)")

        # Neue Buchung speichern
        new_booking = {
            'id': new_booking_id,
            'coach': coach,
            'berater': berater,
            'customer': customer,
            'date': new_date_str,
            'time': new_time_str,
            'topic': topic,
            'email': email,
            'user': booking.get('user'),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'is_rescheduled_from': booking_id,
            # NEW: Store event_id for deletion
            'event_id': reschedule_event_id,
            'calendar_id': reschedule_calendar_id
        }

        # 3. Neue Buchung speichern (DUAL-WRITE: PostgreSQL + JSON)
        save_t2_booking(new_booking)

        # 3a. Alte Buchung JSON Update (nur für Rescheduled-Status)
        data_persistence.save_data('t2_bookings', {'bookings': all_bookings})

        # Tracking (PostgreSQL + JSONL)
        tracking_system.track_booking(
            customer_name=customer,
            date=new_date_str,
            time_slot=new_time_str,
            user=booking.get('user'),
            color_id='4',
            description=f"T2 - Coach: {coach} | Berater: {berater} | {topic} (UMGEBUCHT)"
        )

        # Cache invalidieren (alte + neue Slots)
        try:
            # Alte Buchung
            old_date = datetime.fromisoformat(booking['date']).date()
            t2_dynamic_availability.clear_cache_for_berater(calendar_id, old_date)
            # Neue Buchung
            t2_dynamic_availability.clear_cache_for_berater(calendar_id, new_date)
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")

        logger.info(f"User {user}: Rescheduled booking {booking_id} → {new_booking_id}")

        return jsonify({
            'success': True,
            'new_booking_id': new_booking_id,
            'message': 'Buchung erfolgreich umgebucht.'
        })

    except Exception as e:
        logger.error(f"Error rescheduling booking: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/get-reschedule-slots', methods=['POST'])
@require_login
@rate_limit_api
def get_reschedule_slots():
    """
    Get available slots for rescheduling an existing booking

    Request JSON:
        {"booking_id": "T2-ABC12345", "date": "2025-11-26"}

    Response:
        {"success": true, "slots": {"morning": [...], "midday": [...], "evening": [...]}}

    MIGRATED FROM: t2_legacy.py line 1298
    """
    try:
        user = session.get('user')
        data = request.get_json() or {}
        booking_id = data.get('booking_id')
        date_str = data.get('date')

        if not booking_id:
            return jsonify({'success': False, 'error': 'booking_id required'}), 400

        # Find booking
        all_bookings = load_t2_bookings()
        booking = None
        for b in all_bookings:
            if b.get('id') == booking_id:
                booking = b
                break

        if not booking:
            return jsonify({'success': False, 'error': 'Buchung nicht gefunden'}), 404

        if not can_modify_booking(booking, user):
            return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

        berater = booking.get('berater')
        if not berater or berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        calendar_id = T2_CLOSERS[berater]['calendar_id']

        if date_str:
            # Return slots for specific date
            try:
                check_date = datetime.fromisoformat(date_str).date()
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format'}), 400

            slots = t2_dynamic_availability.find_2h_slots_non_overlapping(calendar_id, check_date)
            total_slots = len(slots['morning']) + len(slots['midday']) + len(slots['evening'])

            return jsonify({
                'success': True,
                'slots': slots,
                'total_slots': total_slots,
                'berater': berater,
                'date': date_str
            })
        else:
            # Return month availability (next 14 days)
            today = datetime.now().date()
            availability = t2_dynamic_availability.get_month_availability(
                calendar_id, today.year, today.month
            )

            return jsonify({
                'success': True,
                'days': availability,
                'berater': berater
            })

    except Exception as e:
        logger.error(f"Error loading reschedule slots: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/booking/success')
@require_login
def booking_success():
    """
    Booking success page

    MIGRATED FROM: t2_legacy.py line 1378
    """
    # Stub
    return render_template('t2/booking_success.html', active_page='t2')


@booking_bp.route('/booking/error')
@require_login
def booking_error():
    """
    Booking error page

    MIGRATED FROM: t2_legacy.py line 1412
    """
    # Stub
    return render_template('t2/booking_error.html', active_page='t2')


# ============================================================================
# CALENDLY BOOKING API ROUTES (Phase 2)
# ============================================================================

@booking_bp.route('/api/select-berater', methods=['POST'])
@require_login
@rate_limit_api
def api_select_berater():
    """
    API: Speichert Berater-Auswahl nach Würfel.

    Request JSON:
        {"berater": "Christian"}

    Response:
        {"success": true}

    MIGRATED FROM: t2_legacy.py line 1203
    """
    try:
        user = session.get('user')
        data = request.json

        if not data or 'berater' not in data:
            return jsonify({'success': False, 'error': 'Berater required'}), 400

        berater = data['berater']

        # Validation
        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        # Coach aus Session holen (vom Würfel)
        coach = session.get('t2_current_closer')

        if not coach:
            return jsonify({'success': False, 'error': 'No coach assigned. Please roll first.'}), 400

        # Session speichern
        session['t2_booking_coach'] = coach
        session['t2_booking_berater'] = berater

        logger.info(f"User {user}: Selected berater {berater} for coach {coach}")

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error selecting berater: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/my-2h-bookings')
@require_login
@rate_limit_api
def api_my_2h_bookings():
    """
    API: Lädt alle 2h-Buchungen für aktuellen User.

    Response:
        {
            "success": true,
            "bookings": [
                {
                    "id": "T2-ABC12345",
                    "date": "2025-11-25",
                    "time": "14:00",
                    "customer": "Mustermann, Max",
                    "coach": "David",
                    "berater": "Christian",
                    "status": "active",
                    "topic": "...",
                    "created_at": "..."
                }
            ]
        }

    MIGRATED FROM: t2_legacy.py line 1722
    """
    try:
        user = session.get('user')

        # Lade User-Buchungen
        bookings = get_user_t2_bookings(user)

        # Filter: Nur Buchungen mit allen nötigen Feldern
        valid_bookings = []
        for booking in bookings:
            if all(k in booking for k in ['id', 'date', 'time', 'customer']):
                valid_bookings.append({
                    'id': booking['id'],
                    'date': booking['date'],
                    'time': booking['time'],
                    'customer': booking['customer'],
                    'coach': booking.get('coach', 'Unknown'),
                    'berater': booking.get('berater', 'Unknown'),
                    'status': booking.get('status', 'active'),
                    'topic': booking.get('topic', ''),
                    'email': booking.get('email', ''),
                    'created_at': booking.get('created_at', '')
                })

        logger.info(f"User {user}: Loaded {len(valid_bookings)} T2 bookings")

        return jsonify({
            'success': True,
            'bookings': valid_bookings,
            'count': len(valid_bookings)
        })

    except Exception as e:
        logger.error(f"Error loading user bookings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/month-availability/<berater>/<int:year>/<int:month>')
@require_login
@rate_limit_api
def api_month_availability(berater, year, month):
    """
    API: Lädt Verfügbarkeit für ganzen Monat.

    URL Params:
        berater: Berater-Name (z.B. "Christian")
        year: Jahr (z.B. 2025)
        month: Monat 1-12 (z.B. 11)

    Response:
        {
            "success": true,
            "days": {
                "2025-11-25": 3,  # 3 freie Slots
                "2025-11-26": 1
            }
        }

    MIGRATED FROM: t2_legacy.py line 1248
    """
    try:
        user = session.get('user')

        # Validation
        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        if month < 1 or month > 12:
            return jsonify({'success': False, 'error': 'Invalid month'}), 400

        calendar_id = T2_CLOSERS[berater]['calendar_id']

        logger.info(f"User {user}: Loading month availability for {berater} ({year}-{month:02d})")

        # Scan Monat
        availability = t2_dynamic_availability.get_month_availability(calendar_id, year, month)

        return jsonify({
            'success': True,
            'days': availability,
            'total_days': len(availability)
        })

    except Exception as e:
        logger.error(f"Error loading month availability: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/day-slots/<berater>/<date_str>')
@require_login
@rate_limit_api
def api_day_slots(berater, date_str):
    """
    API: Lädt gruppierte 2h-Slots für einen Tag.

    URL Params:
        berater: Berater-Name (z.B. "Christian")
        date_str: Datum im ISO-Format (z.B. "2025-11-25")

    Response:
        {
            "success": true,
            "slots": {
                "morning": ["08:00", "10:30"],
                "midday": ["12:00", "14:00"],
                "evening": ["16:30", "18:00"]
            }
        }

    MIGRATED FROM: t2_legacy.py line 1297
    """
    try:
        user = session.get('user')

        # Validation
        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        # Parse Date
        try:
            check_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400

        calendar_id = T2_CLOSERS[berater]['calendar_id']

        logger.info(f"User {user}: Loading day slots for {berater} on {date_str}")

        # Scan Tag
        slots = t2_dynamic_availability.find_2h_slots_non_overlapping(calendar_id, check_date)

        total_slots = len(slots['morning']) + len(slots['midday']) + len(slots['evening'])

        return jsonify({
            'success': True,
            'slots': slots,
            'total_slots': total_slots
        })

    except Exception as e:
        logger.error(f"Error loading day slots: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/book-2h-slot', methods=['POST'])
@require_login
@rate_limit_api
def api_book_2h_slot():
    """
    API: Führt 2h-Slot-Buchung durch.

    Request JSON:
        {
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max@example.com",  # optional
            "topic": "Verkaufsgespräch",  # optional
            "date": "2025-11-25",
            "time": "14:00"
        }

    Response:
        {
            "success": true,
            "booking_id": "T2-ABC12345",
            "redirect": "/t2/"
        }

    MIGRATED FROM: t2_legacy.py line 1352
    """
    try:
        user = session.get('user')
        data = request.json

        # Validation
        required_fields = ['first_name', 'last_name', 'date', 'time']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} required'}), 400

        # Primär aus Request-Body lesen (session-unabhängig), Session als Fallback
        coach = data.get('coach') or session.get('t2_booking_coach')
        berater = data.get('berater') or session.get('t2_booking_berater')

        if not coach or not berater:
            return jsonify({
                'success': False,
                'error': 'Booking-Daten fehlen. Bitte starten Sie den Buchungsprozess neu.'
            }), 400

        # Validation: Coach und Berater müssen in T2_CLOSERS existieren
        if coach not in T2_CLOSERS or berater not in T2_CLOSERS:
            return jsonify({
                'success': False,
                'error': 'Ungültiger Coach oder Berater.'
            }), 400

        # 1. Ticket-Check
        tickets_remaining = get_user_tickets_remaining(user)
        if tickets_remaining <= 0:
            return jsonify({
                'success': False,
                'error': 'Keine Tickets verfügbar. Sie haben bereits alle 4 T2-Termine diesen Monat gebucht.'
            }), 403

        # 2. Parse Date + Time
        try:
            booking_date = datetime.fromisoformat(data['date']).date()
            hour, minute = map(int, data['time'].split(':'))
            booking_datetime = datetime.combine(booking_date, datetime.min.time().replace(hour=hour, minute=minute))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date or time format'}), 400

        # 3. Live Slot-Check
        calendar_id = T2_CLOSERS[berater]['calendar_id']

        is_free = t2_dynamic_availability.is_2h_slot_free(calendar_id, booking_date, data['time'])

        if not is_free:
            # Spezifische Error-Message je nach Situation
            if coach == berater:
                # Coach wollte selbst ausführen, aber hat Konflikt in eigenem Kalender
                error_msg = (
                    f"{coach} hat zu diesem Zeitpunkt bereits einen Termin im Kalender. "
                    f"Bitte wählen Sie einen anderen Zeitpunkt oder übertragen Sie den Termin "
                    f"an Christian, Daniel oder Tim."
                )
            else:
                # Berater ist belegt
                error_msg = (
                    f"{berater} ist zu diesem Zeitpunkt nicht verfügbar. "
                    f"Bitte wählen Sie einen anderen Zeitpunkt oder einen anderen Berater."
                )

            logger.warning(f"Slot conflict for {berater} at {booking_date} {data['time']}: Coach={coach}, Berater={berater}")

            return jsonify({
                'success': False,
                'error': error_msg
            }), 409

        # 4. Google Calendar Event erstellen
        customer_name = f"{data['last_name']}, {data['first_name']}"
        end_datetime = booking_datetime + timedelta(hours=2)

        # Event-Titel
        if coach == berater:
            event_title = f"T2 - Kunde: {customer_name} | Coach: {coach}"
        else:
            event_title = f"T2 - Kunde: {customer_name} | Coach: {coach}"

        # Description
        description_parts = [
            "T2-Termin",
            "",
            f"Kunde: {customer_name}",
            f"Coach: {coach}",
            f"Berater: {berater}",
        ]

        if data.get('topic'):
            description_parts.append(f"Thema: {data['topic']}")

        if data.get('email'):
            description_parts.append(f"Email: {data['email']}")

        description_parts.append("")
        description_parts.append(f"[Booked by: {user}]")

        event_description = "\n".join(description_parts)

        # Timezone-aware datetime (Europe/Berlin)
        berlin_tz = pytz.timezone('Europe/Berlin')
        start_iso = berlin_tz.localize(booking_datetime).isoformat()
        end_iso = berlin_tz.localize(end_datetime).isoformat()

        event_body = {
            'summary': event_title,
            'description': event_description,
            'start': {'dateTime': start_iso, 'timeZone': 'Europe/Berlin'},
            'end': {'dateTime': end_iso, 'timeZone': 'Europe/Berlin'},
            'colorId': '5'  # Banana (Gelb - T2-Farbe für visuelle Unterscheidung von T1)
        }

        # Nur schreiben wenn can_write=True
        event_id = None
        event_calendar_id = None

        if T2_CLOSERS[berater].get('can_write', False):
            try:
                from app.utils.error_messages import get_error_message
                from app.utils.error_tracking import generate_error_id

                calendar_service = GoogleCalendarService()
                result, error_context = calendar_service.create_event_with_context(calendar_id, event_body)

                if result:
                    event_id = result.get('id')
                    event_calendar_id = calendar_id
                    logger.info(f"Google Calendar event created: {event_id}")
                else:
                    error_id = generate_error_id("CAL")
                    error_category = error_context.get('category', 'CALENDAR_UNAVAILABLE')
                    error_msg = get_error_message(error_category)
                    logger.error(f"Google Calendar event creation failed {error_id}: category={error_category}, details={error_context}")
                    return jsonify({'success': False, 'error': error_msg['message'], 'error_id': error_id}), 500

            except Exception as e:
                from app.utils.error_tracking import generate_error_id
                error_id = generate_error_id("CAL")
                logger.error(f"Google Calendar write failed {error_id}: {e}")
                return jsonify({'success': False, 'error': f'Calendar-Fehler', 'error_id': error_id}), 500
        else:
            logger.info(f"Mock booking for {berater} (no write access yet)")

        # 5. Tracking (Dual-Write)

        # A) T2-JSON speichern
        booking_id = f"T2-{uuid.uuid4().hex[:8].upper()}"

        t2_booking_data = {
            'id': booking_id,
            'coach': coach,
            'berater': berater,
            'customer': customer_name,
            'date': data['date'],
            'time': data['time'],
            'topic': data.get('topic', ''),
            'email': data.get('email', ''),
            'user': user,
            'created_at': datetime.now().isoformat(),
            # NEW: Store event_id for deletion
            'event_id': event_id,
            'calendar_id': event_calendar_id
        }

        save_t2_booking(t2_booking_data)

        # B) PostgreSQL + JSONL via tracking_system
        tracking_system.track_booking(
            customer_name=customer_name,
            date=data['date'],
            time_slot=data['time'],
            user=user,
            color_id='4',  # T2-Farbe
            description=f"T2 - Coach: {coach} | Berater: {berater} | {data.get('topic', '')}"
        )

        # 6. Ticket verbrauchen
        consume_user_ticket(user)

        # 7. Cache invalidieren
        t2_dynamic_availability.clear_cache_for_berater(calendar_id, booking_date)

        # 8. Session clearen
        session.pop('t2_current_closer', None)
        session.pop('t2_booking_coach', None)
        session.pop('t2_booking_berater', None)

        logger.info(f"T2 booking successful: {booking_id} by {user}")

        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'redirect': url_for('t2.dashboard')
        })

    except Exception as e:
        logger.error(f"Error booking 2h slot: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/booking-stats', methods=['GET'])
@require_login
def booking_stats():
    """
    Booking statistics API

    Response:
        {
            "total_bookings": 42,
            "upcoming": 10,
            "completed": 25,
            "cancelled": 7,
            "by_coach": {...},
            "by_berater": {...}
        }

    MIGRATED FROM: t2_legacy.py line 1534
    """
    try:
        all_bookings = load_t2_bookings()
        now = datetime.now()

        total = len(all_bookings)
        upcoming = 0
        completed = 0
        cancelled = 0
        by_coach = {}
        by_berater = {}

        for b in all_bookings:
            status = b.get('status', 'active')

            if status == 'cancelled':
                cancelled += 1
            elif status == 'rescheduled':
                pass  # Don't count rescheduled originals
            else:
                # Check if upcoming or completed
                try:
                    booking_date = datetime.fromisoformat(b['date'])
                    booking_time = b.get('time', '00:00')
                    hour, minute = map(int, booking_time.split(':'))
                    booking_dt = booking_date.replace(hour=hour, minute=minute)
                    if booking_dt > now:
                        upcoming += 1
                    else:
                        completed += 1
                except (ValueError, KeyError):
                    completed += 1

            # Count by coach/berater
            coach = b.get('coach', 'Unknown')
            berater = b.get('berater', 'Unknown')
            by_coach[coach] = by_coach.get(coach, 0) + 1
            by_berater[berater] = by_berater.get(berater, 0) + 1

        return jsonify({
            'total_bookings': total,
            'upcoming': upcoming,
            'completed': completed,
            'cancelled': cancelled,
            'by_coach': by_coach,
            'by_berater': by_berater
        })

    except Exception as e:
        logger.error(f"Error loading booking stats: {e}")
        return jsonify({
            'total_bookings': 0,
            'upcoming': 0,
            'completed': 0,
            'cancelled': 0,
            'error': str(e)
        }), 500


# ============================================================================
# ROUTE 10: Check Coach Availability (Month View)
# ============================================================================

@booking_bp.route('/api/check-coach-availability/<coach>/<int:year>/<int:month>', methods=['GET'])
@require_login
@rate_limit_api
def api_check_coach_availability(coach: str, year: int, month: int):
    """
    API: Prüft Coach-Verfügbarkeit für einen Monat (für Modal/Debug).

    Args:
        coach: Coach-Name (z.B. "David", "Alex", "Jose")
        year: Jahr (z.B. 2025)
        month: Monat 1-12

    Returns:
        JSON mit verfügbaren Tagen:
        {
            "available_dates": ["2025-11-25", "2025-11-26", ...],
            "coach": "David",
            "month": "2025-11"
        }

    MIGRATED FROM: t2_legacy.py line 1579
    """
    try:
        if coach not in T2_CLOSERS:
            return jsonify({'error': 'Invalid coach'}), 400

        # Alle verfügbaren Daten für diesen Monat scannen
        available_dates = []
        calendar_id = T2_CLOSERS[coach]['calendar_id']

        # Ersten und letzten Tag des Monats
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, last_day).date()

        # Jeden Tag scannen
        current_date = start_date
        while current_date <= end_date:
            # Skip Wochenenden
            if current_date.weekday() >= 5:  # 5 = Samstag, 6 = Sonntag
                current_date += timedelta(days=1)
                continue

            # Prüfe ob mind. 1 Slot verfügbar
            has_free_slot = False
            for hour in range(8, 20):  # 8:00 - 19:00 Uhr (2h Slots)
                time_str = f"{hour:02d}:00"
                if t2_dynamic_availability.is_2h_slot_free(calendar_id, current_date, time_str):
                    has_free_slot = True
                    break

            if has_free_slot:
                available_dates.append(current_date.isoformat())

            current_date += timedelta(days=1)

        return jsonify({
            'available_dates': available_dates,
            'coach': coach,
            'month': f"{year}-{month:02d}"
        })

    except Exception as e:
        logger.error(f"Error checking coach availability: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ROUTE 11: Admin Analytics (2h Bookings)
# ============================================================================

@booking_bp.route('/api/admin/2h-analytics', methods=['GET'])
@require_login
@rate_limit_api
def api_admin_2h_analytics():
    """
    API: Admin-Analytics für 2h-Buchungssystem.

    Query Params:
        - start_date: ISO-Format (YYYY-MM-DD)
        - end_date: ISO-Format (YYYY-MM-DD)

    Returns:
        JSON mit Statistiken:
        {
            "total_bookings": 42,
            "by_coach": {"David": 15, "Alex": 12, ...},
            "by_berater": {"Christian": 20, "Daniel": 15, ...},
            "by_user": {"luke.hoppe": 4, ...},
            "by_status": {"active": 30, "cancelled": 5, ...}
        }

    MIGRATED FROM: t2_legacy.py line 1658
    """
    try:
        user = session.get('user')
        if not is_admin_user(user):
            return jsonify({'error': 'Admin access required'}), 403

        # Query Params
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Statistiken generieren
        stats = t2_analytics_service.get_2h_booking_stats(
            start_date=start_date_str,
            end_date=end_date_str
        )

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error fetching 2h analytics: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# C.4 — Restliche Legacy-Routen (migrated from t2_legacy.py)
# ============================================================================

@booking_bp.route('/api/availability-calendar/<closer_name>')
@require_login
def api_availability_calendar(closer_name):
    """
    Get 6-week availability calendar for a closer.
    Returns dates with available slots (for green dots).

    MIGRATED FROM: t2_legacy.py line 822
    """
    try:
        if closer_name not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Unknown closer'}), 400

        # Get available dates (dates with at least one free slot)
        available_dates = availability_service.get_available_dates(closer_name, days=42)

        return jsonify({
            'success': True,
            'closer': closer_name,
            'available_dates': available_dates
        })

    except Exception as e:
        logger.error(f"Error getting availability calendar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/availability/<closer_name>/<date_str>')
@require_login
def api_availability_by_date(closer_name, date_str):
    """
    Get available time slots for specific closer and date.
    Returns list of free 2h slots (09:00-22:00).

    MIGRATED FROM: t2_legacy.py line 849
    """
    try:
        if closer_name not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Unknown closer'}), 400

        # Get cached availability
        availability = availability_service.get_cached_availability(closer_name, date_str)
        closer_data = availability.get(closer_name, {})
        slots = closer_data.get(date_str, [])

        return jsonify({
            'success': True,
            'closer': closer_name,
            'date': date_str,
            'available_slots': slots
        })

    except Exception as e:
        logger.error(f"Error getting availability: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/my-calendar-events/<date_str>')
@require_login
def api_my_calendar_events(date_str):
    """
    Get closer's own calendar events for specific date.
    Only accessible by closers.

    MIGRATED FROM: t2_legacy.py line 879
    """
    try:
        user = session.get('user')

        if not is_closer(user):
            return jsonify({'success': False, 'error': 'Not authorized - Closers only'}), 403

        calendar_service = get_google_calendar_service()
        if not calendar_service:
            return jsonify({'success': False, 'error': 'Calendar service unavailable'}), 500

        # Get calendar ID for this closer
        closer_data = T2_CLOSERS.get(user)
        if not closer_data:
            return jsonify({'success': False, 'error': 'Closer calendar not found'}), 404

        calendar_id = closer_data['calendar_id']

        # Get events for this date
        start_time = f"{date_str}T00:00:00Z"
        end_time = f"{date_str}T23:59:59Z"

        result = calendar_service.get_events(
            calendar_id=calendar_id,
            time_min=start_time,
            time_max=end_time,
            cache_duration=1800  # 30min cache
        )

        events = result.get('items', []) if result else []

        # Classify events
        classified_events = [calendar_parser.classify_appointment(event) for event in events]

        return jsonify({
            'success': True,
            'date': date_str,
            'events': classified_events
        })

    except Exception as e:
        logger.error(f"Error getting calendar events: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/my-upcoming-events')
@require_login
def api_my_upcoming_events():
    """
    Get closer's next 5 upcoming appointments.
    Only accessible by closers.

    MIGRATED FROM: t2_legacy.py line 933
    """
    try:
        user = session.get('user')

        if not is_closer(user):
            return jsonify({'success': False, 'error': 'Not authorized - Closers only'}), 403

        calendar_service = get_google_calendar_service()
        if not calendar_service:
            return jsonify({'success': False, 'error': 'Calendar service unavailable'}), 500

        # Get calendar ID
        closer_data = T2_CLOSERS.get(user)
        if not closer_data:
            return jsonify({'success': False, 'error': 'Closer calendar not found'}), 404

        calendar_id = closer_data['calendar_id']

        # Get next 14 days of events
        start_time = datetime.now().isoformat() + 'Z'
        end_time = (datetime.now() + timedelta(days=14)).isoformat() + 'Z'

        result = calendar_service.get_events(
            calendar_id=calendar_id,
            time_min=start_time,
            time_max=end_time,
            max_results=10,
            cache_duration=1800
        )

        events = result.get('items', []) if result else []

        # Classify and limit to 5
        classified_events = [calendar_parser.classify_appointment(event) for event in events]
        upcoming = classified_events[:5]

        return jsonify({
            'success': True,
            'upcoming_events': upcoming
        })

    except Exception as e:
        logger.error(f"Error getting upcoming events: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@booking_bp.route('/api/my-upcoming-bookings')
@require_login
def api_my_upcoming_bookings():
    """
    Get next 5 upcoming bookings for current user (opener).

    MIGRATED FROM: t2_legacy.py line 1011
    """
    try:
        user = session.get('user')

        # Get upcoming appointments
        upcoming = get_next_t2_appointments(user)

        return jsonify({
            'success': True,
            'upcoming_bookings': upcoming
        })

    except Exception as e:
        logger.error(f"Error getting upcoming bookings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
