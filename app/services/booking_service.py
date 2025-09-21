# -*- coding: utf-8 -*-
"""
Booking service - Business logic for slot booking and availability
"""

import json
import os
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

from app.config.base import slot_config, consultant_config
from app.core.extensions import cache_manager, data_persistence
from app.core.google_calendar import get_google_calendar_service
from app.utils.helpers import get_week_start, get_current_kw, week_key_from_date
# from color_mapping import determine_outcome_from_color  # Will be fixed later


TZ = pytz.timezone(slot_config.TIMEZONE)


def load_availability() -> Dict[str, List[str]]:
    """Load availability data from static file"""
    availability_file = "static/availability.json"
    if os.path.exists(availability_file):
        try:
            with open(availability_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading availability: {e}")
            return {}
    return {}


def get_default_availability(date_str: str, hour: str) -> List[str]:
    """Get default consultant availability for a time slot"""
    # Basic availability logic - can be enhanced
    weekday = datetime.strptime(date_str, '%Y-%m-%d').weekday()

    # Weekend or evening hours get fewer consultants
    if weekday >= 5 or hour in ["20:00"]:  # Weekend or late evening
        return consultant_config.DEFAULT_STANDARD_CONSULTANTS[:2]
    else:
        return consultant_config.DEFAULT_STANDARD_CONSULTANTS


def get_effective_availability(date_str: str, hour: str) -> List[str]:
    """Get effective availability combining loaded and default data"""
    availability = load_availability()

    # Try to get from loaded data first
    if date_str in availability and hour in availability[date_str]:
        return availability[date_str][hour]

    # Fall back to default availability
    return get_default_availability(date_str, hour)


def extract_weekly_summary(availability, current_date=None):
    """Extract weekly summary from availability data - returns list for template compatibility"""
    from collections import defaultdict

    week_possible = defaultdict(int)
    week_dates = {}

    # Only count slots from today forward
    today = datetime.now(TZ).date()

    # Calculate possible slots for next 4 weeks
    for week_offset in range(4):
        week_start = get_week_start(today) + timedelta(weeks=week_offset)
        week_key = f"KW{week_start.isocalendar()[1]}"
        week_dates[week_key] = week_start

        # Count available slots for this week
        for day_offset in range(7):  # Monday to Sunday
            date_obj = week_start + timedelta(days=day_offset)
            date_str = date_obj.strftime("%Y-%m-%d")

            if date_obj >= today:  # Only future dates
                for hour in ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]:
                    if date_str in availability and hour in availability[date_str]:
                        consultants = availability[date_str][hour]
                        week_possible[week_key] += len(consultants) * 2  # 2 slots per consultant

    # Create summary list for template
    summary = []
    for week_key in sorted(week_dates.keys()):
        summary.append({
            "label": week_key,
            "start_date": week_dates[week_key],
            "possible": week_possible[week_key],
            "booked": 0  # TODO: Calculate actual bookings
        })

    return summary


def extract_detailed_summary(availability):
    """Extract detailed summary of availability patterns"""
    if not availability:
        return {}

    summary = {
        "total_slots": 0,
        "total_days": len(availability),
        "consultant_frequency": defaultdict(int),
        "hour_frequency": defaultdict(int),
        "weekday_frequency": defaultdict(int)
    }

    for date_str, date_slots in availability.items():
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            weekday = date_obj.strftime("%A")
            summary["weekday_frequency"][weekday] += len(date_slots)
        except ValueError:
            continue

        for hour, consultants in date_slots.items():
            summary["total_slots"] += 1
            summary["hour_frequency"][hour] += 1

            for consultant in consultants:
                summary["consultant_frequency"][consultant] += 1

    return dict(summary)


def get_slot_status(date_str: str, hour: str, berater_count: int) -> Tuple[List[Dict[str, Any]], int, int, int, bool]:
    """Get slot booking status for a specific time slot"""
    max_slots = berater_count * slot_config.SLOTS_PER_BERATER

    # Get events from Google Calendar
    calendar_service = get_google_calendar_service()
    if not calendar_service:
        return [], 0, 0, 0, False

    events_result = calendar_service.get_events(
        calendar_id='primary',
        time_min=f"{date_str}T{hour}:00+01:00",
        time_max=f"{date_str}T{hour}:59+01:00"
    )

    events = events_result.get('items', []) if events_result else []

    # Process events
    slot_list = []
    for event in events:
        summary = event.get('summary', 'Unbekannt')
        color_id = event.get('colorId', '1')

        slot_list.append({
            'summary': summary,
            'colorId': color_id,
            'outcome': 'unknown'  # Will be enhanced later
        })

    booked = len(slot_list)
    total = max_slots
    freie_count = max(0, total - booked)
    overbooked = booked > total

    return slot_list, booked, total, freie_count, overbooked


def get_slot_suggestions(availability, n=5):
    """Get suggested time slots based on availability"""
    suggestions = []
    today = datetime.now(TZ).date()

    # Look ahead for next few days
    for days_ahead in range(1, 15):  # Look 2 weeks ahead
        check_date = today + timedelta(days=days_ahead)
        date_str = check_date.strftime("%Y-%m-%d")

        if date_str in availability:
            for hour in ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]:
                if hour in availability[date_str]:
                    consultants = availability[date_str][hour]
                    if len(consultants) >= 2:  # Good availability
                        suggestions.append({
                            'date': date_str,
                            'hour': hour,
                            'consultants': len(consultants),
                            'weekday': check_date.strftime("%A")
                        })

                        if len(suggestions) >= n:
                            return suggestions

    return suggestions


def get_slot_points(hour, slot_date):
    """Calculate points for a time slot"""
    # Base points
    points = 10

    # Bonus for evening slots
    if hour in ["18:00", "20:00"]:
        points += 5

    # Bonus for weekend
    if slot_date.weekday() >= 5:
        points += 3

    return points