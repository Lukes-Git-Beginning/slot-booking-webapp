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
    user = session.get("user")

    # Get user's bookings from the past month and next month
    start_date = (datetime.now(TZ) - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = (datetime.now(TZ) + timedelta(days=30)).strftime("%Y-%m-%d")

    # Get events from Google Calendar
    google_calendar_service = get_google_calendar_service()
    if not google_calendar_service:
        # Return empty calendar if Google Calendar is not available
        return render_template("my_calendar.html", events=[], user=user)

    from app.config.base import config
    events_result = google_calendar_service.get_events(
        calendar_id=config.CENTRAL_CALENDAR_ID,
        time_min=f"{start_date}T00:00:00+01:00",
        time_max=f"{end_date}T23:59:59+01:00"
    )

    all_events = events_result.get('items', []) if events_result else []

    # Filter events for this user (events they created)
    my_events = []
    for event in all_events:
        summary = event.get('summary', '')
        # Simple heuristic: if user is mentioned in summary or they created it
        if user.lower() in summary.lower() or event.get('creator', {}).get('email', '').startswith(user.lower()):
            my_events.append({
                'summary': summary,
                'start': event.get('start', {}),
                'end': event.get('end', {}),
                'description': event.get('description', ''),
                'colorId': event.get('colorId', '1')
            })

    return render_template("my_calendar.html", my_events=my_events, user=user)


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

    # Load availability data from static/availability.json
    availability_data = {}
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