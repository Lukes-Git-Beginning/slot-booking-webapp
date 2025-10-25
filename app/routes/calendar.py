# -*- coding: utf-8 -*-
"""
Calendar routes
Calendar view and personal calendar functionality
"""

from flask import Blueprint, render_template, session, jsonify, request
from datetime import datetime, timedelta
import pytz
import json
import os

from app.config.base import slot_config
from app.core.extensions import data_persistence
from app.core.google_calendar import get_google_calendar_service
from app.utils.decorators import require_login

calendar_bp = Blueprint('calendar', __name__)
TZ = pytz.timezone(slot_config.TIMEZONE)


@calendar_bp.route("/my-calendar")
@require_login
def my_calendar():
    """Display user's personal calendar view with Table and Kanban modes"""
    from datetime import datetime as dt_module, date
    from app.utils.color_mapping import get_booking_status, get_column_stats
    from app.utils.helpers import get_username_variants
    from collections import defaultdict
    import logging

    logger = logging.getLogger(__name__)
    user = session.get("user")

    # Get view mode parameter (table or kanban)
    view_mode = request.args.get('view', 'table')

    # Get user's bookings from the past 30 days and next 30 days
    start_date = (dt_module.now(TZ) - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = (dt_module.now(TZ) + timedelta(days=30)).strftime("%Y-%m-%d")

    # Get events from Google Calendar
    google_calendar_service = get_google_calendar_service()
    if not google_calendar_service:
        logger.warning("Google Calendar service not available")
        return render_template("my_calendar.html",
                             my_events=[],
                             kanban_columns={},
                             stats={},
                             view_mode=view_mode,
                             user=user)

    from app.config.base import config
    events_result = google_calendar_service.get_events(
        calendar_id=config.CENTRAL_CALENDAR_ID,
        time_min=f"{start_date}T00:00:00+01:00",
        time_max=f"{end_date}T23:59:59+01:00",
        cache_duration=0  # No cache - always get fresh data
    )

    all_events = events_result.get('items', []) if events_result else []

    # Get all possible username variants for backward compatibility
    username_variants = get_username_variants(user)

    logger.info(f"MY-CALENDAR: Looking for bookings by user '{user}'")
    logger.info(f"MY-CALENDAR: Username variants: {username_variants}")
    logger.info(f"MY-CALENDAR: Total events in calendar: {len(all_events)}")

    # Initialize data structures
    my_events = []
    kanban_columns = defaultdict(list)
    today = date.today()

    # Week boundaries for weekly stats
    from app.utils.helpers import get_week_start
    current_week_start = get_week_start(today)
    last_week_start = current_week_start - timedelta(weeks=1)

    for event in all_events:
        summary = event.get('summary', '')
        description = event.get('description', '')

        # Skip placeholder events (nur Zahlen)
        if summary.isdigit():
            continue

        # Check if this user booked the event (via [Booked by: username] tag)
        is_booked_by_user = False
        matched_variant = None
        for variant in username_variants:
            booked_by_tag = f"[Booked by: {variant}]"
            if booked_by_tag in description:
                is_booked_by_user = True
                matched_variant = variant
                break

        if not is_booked_by_user:
            continue

        # Parse event data
        start_dt = event.get('start', {}).get('dateTime', '')
        color_id = event.get('colorId', '1')
        event_id = event.get('id', '')

        if not start_dt:
            continue

        try:
            dt = dt_module.fromisoformat(start_dt.replace('Z', '+00:00'))
            event_date = dt.date()
            date_str = dt.strftime('%d.%m.%Y')
            hour_str = dt.strftime('%H:%M')
        except Exception as e:
            logger.error(f"Error parsing datetime for event '{summary}': {e}")
            continue

        # Get status information using color_mapping
        status_info = get_booking_status(color_id, summary, event_date)

        # Extract customer name (remove status markers like "(Ghost)", "(Verschoben)", etc.)
        customer_name = summary
        for marker in [' ( Ghost )', ' (Ghost)', ' ( Verschoben )', ' (Verschoben)',
                      ' ( Abgesagt )', ' (Abgesagt)', ' ( nicht erschienen )',
                      ' (nicht erschienen)', ' ( erschienen )', ' (erschienen)']:
            customer_name = customer_name.replace(marker, '')
        customer_name = customer_name.strip()

        # Calculate customer_showed for compatibility
        if status_info['is_positive'] is True:
            customer_showed = True
        elif status_info['is_positive'] is False:
            customer_showed = False
        else:
            customer_showed = None  # Pending

        # Calculate week flags
        is_current_week = current_week_start <= event_date < (current_week_start + timedelta(weeks=1))
        is_last_week = last_week_start <= event_date < current_week_start

        # Calculate days ago/until
        days_diff = (today - event_date).days
        if days_diff > 0:
            days_ago = days_diff
            days_until = 0
        elif days_diff < 0:
            days_ago = 0
            days_until = abs(days_diff)
        else:
            days_ago = 0
            days_until = 0

        # Extract booked_by initials
        if matched_variant:
            parts = matched_variant.split('.')
            if len(parts) >= 2:
                booked_by_initials = f"{parts[0][0].upper()}{parts[1][0].upper()}"
            else:
                booked_by_initials = matched_variant[:2].upper()
        else:
            booked_by_initials = "??"

        # Determine potential type label
        potential_map = {
            '2': 'Normal',
            '7': 'Top',
            '5': 'Sonderkunde',
            '3': 'Rückholung',
            '11': 'No-Show',
            '6': 'Verschoben',
            '9': 'Standard',
            '10': 'Standard'
        }
        potential = potential_map.get(color_id, 'Sonstiges')

        # Calculate points (for gamification)
        points = 3
        if color_id == '7':  # Top Potential
            points = 5
        elif color_id == '5':  # Sonderkunde
            points = 4
        elif color_id == '3':  # Rückholung
            points = 3
        elif color_id in ['11', '6']:  # No-Show, Verschoben
            points = 0

        # Clean description (remove booked by tag)
        clean_desc = description
        for variant in username_variants:
            booked_by_tag = f"[Booked by: {variant}]"
            clean_desc = clean_desc.replace(f"\n\n{booked_by_tag}", "").replace(booked_by_tag, "")
        clean_desc = clean_desc.strip() or '-'

        # Build event dict
        event_dict = {
            'id': event_id,
            'summary': summary,
            'customer_name': customer_name,
            'date': date_str,
            'hour': hour_str,
            'date_obj': event_date,
            'color_id': color_id,
            'potential': potential,
            'points': points,
            'desc': clean_desc,
            'booked_by': matched_variant,
            'booked_by_initials': booked_by_initials,

            # Status information from color_mapping
            'status': status_info['status'],
            'status_label': status_info['label'],
            'badge_class': status_info['badge_class'],
            'row_bg_class': status_info['bg_class'],
            'status_icon': status_info['status_icon'],
            'is_positive': status_info['is_positive'],
            'column': status_info['column'],

            # Additional flags
            'customer_showed': customer_showed,
            'is_future': event_date >= today,
            'is_current_week': is_current_week,
            'is_last_week': is_last_week,
            'days_ago': days_ago,
            'days_until': days_until,
        }

        my_events.append(event_dict)

        # Add to kanban column
        kanban_columns[status_info['column']].append(event_dict)

    # Sort events by date (newest first for table view)
    my_events.sort(key=lambda x: x['date_obj'], reverse=True)

    # Sort kanban columns by date
    for column in kanban_columns.values():
        column.sort(key=lambda x: x['date_obj'], reverse=False)

    # Calculate statistics
    stats = get_column_stats(kanban_columns)

    logger.info(f"MY-CALENDAR: Found {len(my_events)} bookings for user '{user}'")
    logger.info(f"MY-CALENDAR: Stats - Total: {stats['total']}, Erschienen: {stats['erschienen']}, "
               f"No-Show: {stats['nicht_erschienen']}, Ghost: {stats['ghost']}")

    return render_template("my_calendar.html",
                         my_events=my_events,
                         kanban_columns=dict(kanban_columns),
                         stats=stats,
                         view_mode=view_mode,
                         user=user)


@calendar_bp.route("/my-customers")
@require_login
def my_customers():
    """Dashboard for telemarketers to see attendance rate of their customers"""
    from datetime import datetime as dt_module
    user = session.get("user")

    # Get user's bookings since September 1st (or 90 days back, whichever is earlier)
    september_first = datetime(2024, 9, 1).date()
    ninety_days_ago = (dt_module.now(TZ) - timedelta(days=90)).date()

    # Use the earlier date
    start_date_obj = september_first if september_first < ninety_days_ago else ninety_days_ago
    start_date = start_date_obj.strftime("%Y-%m-%d")
    end_date = (dt_module.now(TZ) + timedelta(days=30)).strftime("%Y-%m-%d")

    # Get events from Google Calendar
    google_calendar_service = get_google_calendar_service()
    if not google_calendar_service:
        return render_template("my_customers.html", customers=[], stats={}, user=user)

    from app.config.base import config
    events_result = google_calendar_service.get_events(
        calendar_id=config.CENTRAL_CALENDAR_ID,
        time_min=f"{start_date}T00:00:00+01:00",
        time_max=f"{end_date}T23:59:59+01:00",
        max_results=2500,
        cache_duration=0  # No cache - always get fresh data for customer analytics
    )

    all_events = events_result.get('items', []) if events_result else []

    # Filter events booked by this user and analyze outcomes
    from collections import defaultdict
    customer_data = defaultdict(lambda: {
        'name': '',
        'total': 0,
        'erschienen': 0,
        'no_show': 0,
        'cancelled': 0,
        'pending': 0,
        'events': []
    })

    outcome_map = {
        '2': 'erschienen',      # Sage/Green - Normal
        '7': 'erschienen',      # Peacock/Türkis - Top
        '11': 'no_show',        # Tomate/Red - No Show
        '6': 'cancelled',       # Mandarine/Orange - Cancelled
        '5': 'pending',         # Banana/Yellow - Closer needed (pending)
    }

    # Get all possible username variants for backward compatibility
    from app.utils.helpers import get_username_variants
    username_variants = get_username_variants(user)

    for event in all_events:
        description = event.get('description', '')

        # Only events booked by this user - check all username variants
        is_booked_by_user = False
        for variant in username_variants:
            booked_by_tag = f"[Booked by: {variant}]"
            if booked_by_tag in description:
                is_booked_by_user = True
                break

        if not is_booked_by_user:
            continue

        summary = event.get('summary', '').strip()
        if not summary:
            continue

        # Parse customer name (format: "Nachname, Vorname")
        customer_name = summary

        color_id = event.get('colorId', '1')
        outcome = outcome_map.get(color_id, 'pending')

        # Get event time
        start_dt = event.get('start', {}).get('dateTime', '')
        event_date = ''
        if start_dt:
            try:
                dt = dt_module.fromisoformat(start_dt.replace('Z', '+00:00'))
                event_date = dt.strftime('%d.%m.%Y')
            except:
                pass

        # Track customer stats
        customer_data[customer_name]['name'] = customer_name
        customer_data[customer_name]['total'] += 1
        customer_data[customer_name][outcome] += 1
        customer_data[customer_name]['events'].append({
            'date': event_date,
            'outcome': outcome,
            'color_id': color_id
        })

    # Calculate attendance rates
    customers = []
    for customer_name, data in customer_data.items():
        total = data['total']
        erschienen = data['erschienen']
        no_show = data['no_show']
        cancelled = data['cancelled']
        pending = data['pending']

        # Calculate rate (only from completed outcomes)
        completed = erschienen + no_show + cancelled
        attendance_rate = (erschienen / completed * 100) if completed > 0 else 0
        no_show_rate = (no_show / completed * 100) if completed > 0 else 0

        customers.append({
            'name': customer_name,
            'total': total,
            'erschienen': erschienen,
            'no_show': no_show,
            'cancelled': cancelled,
            'pending': pending,
            'attendance_rate': round(attendance_rate, 1),
            'no_show_rate': round(no_show_rate, 1),
            'events': data['events']
        })

    # Sort by total appointments descending
    customers.sort(key=lambda x: x['total'], reverse=True)

    # Calculate overall stats
    total_customers = len(customers)
    total_appointments = sum(c['total'] for c in customers)
    total_erschienen = sum(c['erschienen'] for c in customers)
    total_no_show = sum(c['no_show'] for c in customers)
    total_cancelled = sum(c['cancelled'] for c in customers)
    total_pending = sum(c['pending'] for c in customers)

    completed_total = total_erschienen + total_no_show + total_cancelled
    overall_attendance_rate = (total_erschienen / completed_total * 100) if completed_total > 0 else 0
    overall_no_show_rate = (total_no_show / completed_total * 100) if completed_total > 0 else 0

    stats = {
        'total_customers': total_customers,
        'total_appointments': total_appointments,
        'total_erschienen': total_erschienen,
        'total_no_show': total_no_show,
        'total_cancelled': total_cancelled,
        'total_pending': total_pending,
        'overall_attendance_rate': round(overall_attendance_rate, 1),
        'overall_no_show_rate': round(overall_no_show_rate, 1)
    }

    return render_template("my_customers.html", customers=customers, stats=stats, user=user)


@calendar_bp.route("/calendar-view")
@require_login
def calendar_view():
    """Display full calendar view with actual availability data"""
    # Get data for calendar view
    today = datetime.now(TZ).date()

    # Get week parameter from request (for navigation)
    week_param = request.args.get('week')
    if week_param:
        try:
            # Parse week parameter (format: YYYY-MM-DD)
            current_week = datetime.strptime(week_param, '%Y-%m-%d').date()
            # Ensure it's a Monday
            current_week = current_week - timedelta(days=current_week.weekday())
        except ValueError:
            # Fall back to current week if invalid date
            from app.utils.helpers import get_week_start
            current_week = get_week_start(today)
    else:
        # Calculate week navigation
        from app.utils.helpers import get_week_start
        current_week = get_week_start(today)

    prev_week = current_week - timedelta(weeks=1)
    next_week = current_week + timedelta(weeks=1)

    # Generate week dates for template
    week_start = current_week
    week_end = current_week + timedelta(days=6)

    # Load availability data from persistent storage
    availability_data = {}
    # Try persistent storage first
    availability_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'persistent', 'availability.json')

    # Fallback to old location
    if not os.path.exists(availability_path):
        availability_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'availability.json')

    try:
        with open(availability_path, 'r', encoding='utf-8') as f:
            availability_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        availability_data = {}

    # Generate weekdays data for calendar display
    weekdays_data = []
    for i in range(7):
        day = current_week + timedelta(days=i)
        day_availability = []

        # Process availability for this day
        for time_slot, consultants in availability_data.items():
            if time_slot.startswith(day.strftime('%Y-%m-%d')):
                # Extract time from slot key (format: "2025-09-22 20:00")
                time_part = time_slot.split(' ')[1]
                start_time = datetime.strptime(f"{day.strftime('%Y-%m-%d')} {time_part}", '%Y-%m-%d %H:%M')
                end_time = start_time + timedelta(hours=2)  # 2-hour blocks

                # Determine availability level based on consultant count
                slot_count = len(consultants)
                if slot_count >= 4:
                    availability_level = 'high'
                elif slot_count >= 1:
                    availability_level = 'medium'
                else:
                    availability_level = 'none'

                day_availability.append({
                    'time': time_part,
                    'start_time': start_time,
                    'end_time': end_time,
                    'slot_count': slot_count,
                    'available_consultants': consultants,
                    'availability_level': availability_level
                })

        weekdays_data.append({
            'date': day,
            'name': day.strftime('%A'),
            'is_today': day == today,
            'availability': day_availability
        })

    return render_template("calendar_view.html",
                         today=today,
                         availability=availability_data,
                         prev_week=prev_week,
                         next_week=next_week,
                         current_week=current_week,
                         week_start=week_start,
                         week_end=week_end,
                         weekdays_data=weekdays_data)


# ============================================================================
# MY CALENDAR - PHASE 2 API ENDPOINTS (Drag & Drop, Reschedule)
# ============================================================================

@calendar_bp.route('/api/update-event-status', methods=['POST'])
@require_login
def api_update_event_status():
    """
    Update event status via drag & drop (changes color in Google Calendar)

    Request JSON:
        {
            "event_id": "abc123",
            "new_status": "erschienen" | "ghost" | "verschoben" | etc.
        }

    Returns:
        {"success": True, "message": "Status updated"}
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        data = request.get_json()
        event_id = data.get('event_id')
        new_status = data.get('new_status')
        user = session.get('user')

        if not event_id or not new_status:
            return jsonify({'success': False, 'error': 'Missing event_id or new_status'}), 400

        # Map status to Google Calendar colorId
        status_to_color = {
            'pending': '1',         # Lavendel (future events)
            'erschienen': '2',      # Grün (appeared)
            'rückholung': '3',      # Weintraube (recall)
            'sonderkunde': '5',     # Gelb (special customer)
            'verschoben': '6',      # Orange (rescheduled/cancelled)
            'nicht_erschienen': '11', # Rot (no-show)
            'ghost': '11'           # Rot (ghost - will add marker to title)
        }

        color_id = status_to_color.get(new_status)
        if not color_id:
            return jsonify({'success': False, 'error': f'Invalid status: {new_status}'}), 400

        # Get Google Calendar service
        calendar_service = get_google_calendar_service()
        if not calendar_service:
            return jsonify({'success': False, 'error': 'Calendar service not available'}), 503

        from app.config.base import config

        # Get event to check permissions
        try:
            event = calendar_service.service.events().get(
                calendarId=config.CENTRAL_CALENDAR_ID,
                eventId=event_id
            ).execute()
        except Exception as e:
            logger.error(f"Error fetching event {event_id}: {e}")
            return jsonify({'success': False, 'error': 'Event not found'}), 404

        # Update event color
        update_body = {'colorId': color_id}

        # Special handling for "ghost" status - add marker to summary
        if new_status == 'ghost':
            current_summary = event.get('summary', '')
            if '( Ghost )' not in current_summary and '(Ghost)' not in current_summary:
                # Remove other status markers first
                clean_summary = current_summary
                for marker in [' ( Verschoben )', ' (Verschoben)', ' ( Abgesagt )', ' (Abgesagt)',
                              ' ( nicht erschienen )', ' (nicht erschienen)', ' ( erschienen )', ' (erschienen)']:
                    clean_summary = clean_summary.replace(marker, '')
                update_body['summary'] = f"{clean_summary.strip()} ( Ghost )"

        # Execute update
        try:
            calendar_service.service.events().patch(
                calendarId=config.CENTRAL_CALENDAR_ID,
                eventId=event_id,
                body=update_body
            ).execute()

            logger.info(f"MY-CALENDAR: Status updated for event {event_id} to {new_status} by {user}")

            # Invalidate cache
            from app.core.extensions import cache_manager
            cache_manager.clear_pattern('calendar_events_*')

            return jsonify({
                'success': True,
                'message': f'Status updated to {new_status}',
                'new_color_id': color_id
            })

        except Exception as e:
            logger.error(f"Error updating event {event_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    except Exception as e:
        logger.error(f"API error in update-event-status: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@calendar_bp.route('/api/get-available-slots', methods=['GET'])
@require_login
def api_get_available_slots():
    """
    Get available time slots for a specific date (for reschedule modal)

    Query params:
        date: YYYY-MM-DD (optional, defaults to tomorrow)

    Returns:
        {
            "success": True,
            "date": "2025-10-26",
            "slots": [
                {"time": "14:00", "consultants": ["christian.mast", "luke.hoppe"], "count": 2},
                ...
            ]
        }
    """
    import logging
    from datetime import datetime as dt_module, date as date_class
    from app.services.booking_service import get_effective_availability

    logger = logging.getLogger(__name__)

    try:
        # Get date parameter or use tomorrow
        date_param = request.args.get('date')
        if date_param:
            try:
                check_date = dt_module.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format (use YYYY-MM-DD)'}), 400
        else:
            check_date = dt_module.now(TZ).date() + timedelta(days=1)

        # Get availability for common time slots
        time_slots = ['09:00', '11:00', '14:00', '16:00', '18:00', '20:00']
        available_slots = []

        date_str = check_date.strftime('%Y-%m-%d')

        for time_slot in time_slots:
            consultants = get_effective_availability(date_str, time_slot)

            if consultants:  # Only include slots with availability
                available_slots.append({
                    'time': time_slot,
                    'consultants': consultants,
                    'count': len(consultants)
                })

        return jsonify({
            'success': True,
            'date': date_str,
            'slots': available_slots
        })

    except Exception as e:
        logger.error(f"API error in get-available-slots: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@calendar_bp.route('/api/reschedule-booking', methods=['POST'])
@require_login
def api_reschedule_booking():
    """
    Reschedule a booking (mark old as verschoben, create new)

    Request JSON:
        {
            "old_event_id": "abc123",
            "customer_name": "Müller, Hans",
            "new_date": "2025-10-26",
            "new_time": "14:00",
            "consultant": "christian.mast",  # optional, auto-select if empty
            "note": "Kunde hat angerufen"    # optional
        }

    Returns:
        {"success": True, "new_event_id": "xyz789", "message": "..."}
    """
    import logging
    from datetime import datetime as dt_module
    from app.services.booking_service import book_slot_for_user, get_effective_availability

    logger = logging.getLogger(__name__)

    try:
        data = request.get_json()
        old_event_id = data.get('old_event_id')
        customer_name = data.get('customer_name')
        new_date = data.get('new_date')
        new_time = data.get('new_time')
        consultant = data.get('consultant', '')
        note = data.get('note', '')
        user = session.get('user')

        # Validation
        if not all([old_event_id, customer_name, new_date, new_time]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Parse customer name (format: "Nachname, Vorname" or "Vorname Nachname")
        if ',' in customer_name:
            parts = customer_name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ''
        else:
            parts = customer_name.split(' ', 1)
            first_name = parts[0].strip()
            last_name = parts[1].strip() if len(parts) > 1 else ''

        # Auto-select consultant if not provided
        if not consultant:
            available_consultants = get_effective_availability(new_date, new_time)
            if not available_consultants:
                return jsonify({'success': False, 'error': f'No availability at {new_date} {new_time}'}), 400
            consultant = available_consultants[0]  # Pick first available

        # Step 1: Mark old event as "Verschoben"
        calendar_service = get_google_calendar_service()
        if calendar_service:
            try:
                from app.config.base import config

                # Get old event
                old_event = calendar_service.service.events().get(
                    calendarId=config.CENTRAL_CALENDAR_ID,
                    eventId=old_event_id
                ).execute()

                # Update to verschoben (Orange colorId=6)
                old_summary = old_event.get('summary', '')
                if '( Verschoben )' not in old_summary:
                    new_summary = f"{old_summary.strip()} ( Verschoben )"
                else:
                    new_summary = old_summary

                calendar_service.service.events().patch(
                    calendarId=config.CENTRAL_CALENDAR_ID,
                    eventId=old_event_id,
                    body={
                        'colorId': '6',  # Orange
                        'summary': new_summary
                    }
                ).execute()

                logger.info(f"MY-CALENDAR: Marked old event {old_event_id} as verschoben by {user}")

            except Exception as e:
                logger.warning(f"Could not update old event {old_event_id}: {e}")
                # Continue anyway

        # Step 2: Book new slot
        reschedule_note = f"Umbuchung von altem Termin.\n{note}" if note else "Umbuchung von altem Termin."

        booking_result = book_slot_for_user(
            user=user,
            date_str=new_date,
            time_str=new_time,
            berater=consultant,
            first_name=first_name,
            last_name=last_name,
            description=reschedule_note,
            color_id='2'  # Normal (Grün) for new booking
        )

        if booking_result.get('success'):
            logger.info(f"MY-CALENDAR: Rescheduled booking for {customer_name} to {new_date} {new_time} by {user}")

            # Invalidate cache
            from app.core.extensions import cache_manager
            cache_manager.clear_pattern('calendar_events_*')

            return jsonify({
                'success': True,
                'message': f'Termin erfolgreich umgebucht auf {new_date} {new_time}',
                'new_event_id': booking_result.get('event_id'),
                'consultant': consultant
            })
        else:
            return jsonify({
                'success': False,
                'error': booking_result.get('error', 'Booking failed')
            }), 400

    except Exception as e:
        logger.error(f"API error in reschedule-booking: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500