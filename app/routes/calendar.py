# -*- coding: utf-8 -*-
"""
Calendar routes
Calendar view and personal calendar functionality
"""

from flask import Blueprint, render_template, session, jsonify
from datetime import datetime, timedelta
import pytz

from app.config.base import slot_config
from app.core.extensions import data_persistence
from app.core.google_calendar import google_calendar_service
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
    events_result = google_calendar_service.get_events(
        calendar_id=google_calendar_service.service.calendarId if hasattr(google_calendar_service.service, 'calendarId') else 'primary',
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
    """Display full calendar view"""
    # Get data for calendar view
    today = datetime.now(TZ).date()

    # Get weekly availability data
    availability = {}  # This would be loaded from your availability system

    return render_template("calendar_view.html",
                         today=today,
                         availability=availability)