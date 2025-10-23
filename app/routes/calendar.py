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
    """Display user's personal calendar view"""
    from datetime import datetime as dt_module
    user = session.get("user")

    # Get user's bookings from the past month and next month
    start_date = (dt_module.now(TZ) - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = (dt_module.now(TZ) + timedelta(days=30)).strftime("%Y-%m-%d")

    # Get events from Google Calendar
    google_calendar_service = get_google_calendar_service()
    if not google_calendar_service:
        # Return empty calendar if Google Calendar is not available
        return render_template("my_calendar.html", events=[], user=user)

    from app.config.base import config
    events_result = google_calendar_service.get_events(
        calendar_id=config.CENTRAL_CALENDAR_ID,
        time_min=f"{start_date}T00:00:00+01:00",
        time_max=f"{end_date}T23:59:59+01:00",
        cache_duration=0  # No cache - always get fresh data for personal calendar
    )

    all_events = events_result.get('items', []) if events_result else []

    # Filter events for this user (events they booked - based on [Booked by: username] tag)
    my_events = []

    # Get all possible username variants for backward compatibility
    from app.utils.helpers import get_username_variants
    username_variants = get_username_variants(user)

    # DEBUG: Log what we're searching for
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"MY-CALENDAR DEBUG: Looking for bookings by user '{user}'")
    logger.info(f"MY-CALENDAR DEBUG: Username variants: {username_variants}")
    logger.info(f"MY-CALENDAR DEBUG: Total events found: {len(all_events)}")

    for event in all_events:
        summary = event.get('summary', '')
        description = event.get('description', '')

        # Check if this user booked the event (via [Booked by: username] tag in description)
        # Check all username variants for backward compatibility
        is_booked_by_user = False
        for variant in username_variants:
            booked_by_tag = f"[Booked by: {variant}]"
            if booked_by_tag in description:
                is_booked_by_user = True
                break

        # DEBUG: Log each event
        if description and '[Booked by:' in description:
            logger.info(f"MY-CALENDAR DEBUG: Found event '{summary}' with tag in description")
            logger.info(f"MY-CALENDAR DEBUG: Description contains: {description[:200]}")
            logger.info(f"MY-CALENDAR DEBUG: Match: {is_booked_by_user}")

        if is_booked_by_user:
            # Parse event data for display
            start_dt = event.get('start', {}).get('dateTime', '')
            color_id = event.get('colorId', '1')

            # Extract date and hour
            date_str = ""
            hour_str = ""
            if start_dt:
                try:
                    dt = dt_module.fromisoformat(start_dt.replace('Z', '+00:00'))
                    date_str = dt.strftime('%d.%m.%Y')
                    hour_str = dt.strftime('%H:%M')
                except:
                    pass

            # Determine outcome/potential from color
            potential_map = {
                '2': 'Normales Potential',  # Sage/Green
                '7': 'Top Potential',        # Peacock/Türkis
                '5': 'Closer nötig',         # Banana/Yellow
                '11': 'Nicht erschienen',    # Tomate/Red
                '6': 'Storniert',            # Mandarine/Orange
            }
            potential = potential_map.get(color_id, 'Sonstiges')

            # Calculate points (simplified)
            points = 3
            if color_id == '7':  # Top Potential
                points = 5
            elif color_id == '5':  # Closer nötig
                points = 2

            # Clean description (remove booked by tag)
            clean_desc = description.replace(f"\n\n{booked_by_tag}", "").replace(booked_by_tag, "").strip()

            my_events.append({
                'summary': summary,
                'date': date_str,
                'hour': hour_str,
                'color_id': color_id,
                'potential': potential,
                'points': points,
                'desc': clean_desc or '-',
                'source': 'calendar'
            })

    return render_template("my_calendar.html", my_events=my_events, user=user)


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