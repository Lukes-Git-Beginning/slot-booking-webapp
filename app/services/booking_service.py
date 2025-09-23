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


def is_t1_bereit_event(summary: str) -> bool:
    """Check if an event is a T1-bereit event (should not count as booked)"""
    summary_lower = summary.lower()
    return 't1-bereit' in summary_lower or 't1 bereit' in summary_lower


def load_availability() -> Dict[str, List[str]]:
    """Load availability data from static file"""
    availability_file = "static/availability.json"
    if os.path.exists(availability_file):
        try:
            with open(availability_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            from app.utils.logging import booking_logger
            booking_logger.error(f"Error loading availability: {e}")
            return {}
    return {}


def get_default_availability(date_str: str, hour: str) -> List[str]:
    """Get default consultant availability for a time slot

    Only provides Standard-Verfügbarkeit for:
    - Tuesday 9am
    - Thursday 9am
    - Friday 4pm, 6pm, 8pm
    """
    # Check if date is blocked (holidays or custom blocks) first
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        from app.services.holiday_service import holiday_service

        if holiday_service.is_blocked_date(check_date):
            return []  # No availability on blocked dates
    except Exception as e:
        # If there's any error checking holidays, log it but continue
        from app.utils.logging import booking_logger
        booking_logger.warning(f"Error checking holiday status for {date_str}: {e}")

    weekday = datetime.strptime(date_str, '%Y-%m-%d').weekday()

    # Standard-Verfügbarkeit only for specific slots
    if weekday == 1 and hour == "09:00":  # Tuesday 9am
        return consultant_config.DEFAULT_STANDARD_CONSULTANTS
    elif weekday == 3 and hour == "09:00":  # Thursday 9am
        return consultant_config.DEFAULT_STANDARD_CONSULTANTS
    elif weekday == 4 and hour in ["16:00", "18:00", "20:00"]:  # Friday 4pm, 6pm, 8pm
        return consultant_config.DEFAULT_STANDARD_CONSULTANTS

    # No Standard-Verfügbarkeit for all other times
    return []


def get_effective_availability(date_str: str, hour: str) -> List[str]:
    """Get effective availability combining loaded and default data"""
    # Check if date is blocked (holidays or custom blocks)
    try:
        from datetime import datetime
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        from app.services.holiday_service import holiday_service

        if holiday_service.is_blocked_date(check_date):
            return []  # No availability on blocked dates
    except Exception as e:
        # If there's any error checking holidays, log it but continue
        from app.utils.logging import booking_logger
        booking_logger.warning(f"Error checking holiday status for {date_str}: {e}")

    availability = load_availability()

    # Try to get from loaded data first - handle old format "YYYY-MM-DD HH:MM"
    slot_key = f"{date_str} {hour}"
    if slot_key in availability:
        return availability[slot_key]

    # Also try new nested format for backwards compatibility
    if date_str in availability and hour in availability[date_str]:
        return availability[date_str][hour]

    # Fall back to default availability
    return get_default_availability(date_str, hour)


def extract_weekly_summary(availability, current_date=None):
    """Extract weekly summary using old working method - matches original calculation"""
    from collections import defaultdict
    from color_mapping import blocks_availability

    week_possible = defaultdict(int)
    week_booked = defaultdict(int)
    week_dates = {}

    # IMPORTANT FIX: Only count slots from today forward
    today = datetime.now(TZ).date()

    # Process availability data - need to convert from new nested structure to old format
    # New structure: {"YYYY-MM-DD": {"HH:MM": [consultants]}}
    # Old format needed: {"YYYY-MM-DD HH:MM": [consultants]}

    # First, also include availability from effective_availability (loaded + defaults)
    for week_offset in range(5):
        week_start = get_week_start(today) + timedelta(weeks=week_offset)

        for day_offset in range(7):  # Monday to Sunday
            date_obj = week_start + timedelta(days=day_offset)
            if date_obj < today:  # Skip past dates
                continue

            date_str = date_obj.strftime("%Y-%m-%d")

            for hour in ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]:
                # Get effective availability (includes defaults)
                consultants = get_effective_availability(date_str, hour)
                if consultants:  # Only process if we have consultants
                    slot_time = f"{date_str} {hour}"
                    dt = datetime.strptime(slot_time, "%Y-%m-%d %H:%M")

                    key = week_key_from_date(dt)
                    week_possible[key] += len(consultants) * slot_config.SLOTS_PER_BERATER
                    monday = dt - timedelta(days=dt.weekday())
                    friday = monday + timedelta(days=4)
                    week_dates[key] = (monday, friday)

    # Get booked appointments from Google Calendar with error handling and caching
    if week_dates:
        min_start = min(rng[0] for rng in week_dates.values())
        max_end = max(rng[1] for rng in week_dates.values()) + timedelta(days=1)

        # Convert to proper datetime objects with timezone
        min_start_dt = TZ.localize(datetime.combine(min_start, datetime.min.time()))
        max_end_dt = TZ.localize(datetime.combine(max_end, datetime.max.time()))

        # Get calendar service
        calendar_service = get_google_calendar_service()
        if calendar_service:
            try:
                from app.config.base import config
                events_result = calendar_service.get_events(
                    calendar_id=config.CENTRAL_CALENDAR_ID,
                    time_min=min_start_dt.isoformat(),
                    time_max=max_end_dt.isoformat(),
                    max_results=2500
                )
                events = events_result.get('items', []) if events_result else []
            except Exception as e:
                from app.utils.logging import booking_logger
                booking_logger.error(f"Error fetching calendar events: {e}")
                events = []
        else:
            events = []

        # Process all events
        for event in events:
            if "start" in event and "dateTime" in event["start"]:
                try:
                    dt = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                    # Only count future events
                    if dt.date() >= today:
                        # Get event summary to check if it's T1-bereit
                        summary = event.get("summary", "")

                        # Don't count T1-bereit events as booked
                        if not is_t1_bereit_event(summary):
                            # IMPORTANT: Check if event blocks availability
                            color_id = event.get("colorId", "2")  # Default: Green
                            if blocks_availability(color_id):  # Only count blocking events
                                key = week_key_from_date(dt)
                                week_booked[key] += 1
                except Exception as e:
                    print(f"Error parsing event time: {e}")
                    continue

    summary = []
    for key, possible in week_possible.items():
        booked = week_booked.get(key, 0)
        start, end = week_dates[key]

        # Prevent division by 0
        usage = (booked / possible) if possible > 0 else 0

        summary.append({
            "label": key.replace("-", " "),
            "range": f"{start.strftime('%d.%m.')} – {end.strftime('%d.%m.')}",
            "start_date": start.strftime('%Y-%m-%d'),  # Format for URL
            "usage_pct": min(100, int(round(usage * 100))),  # Cap at 100%
            "usage": usage,
            "possible": possible,
            "booked": booked,
            "current": (
                current_date is not None and start.date() <= current_date <= end.date()
            )
        })

    summary.sort(key=lambda s: s["start_date"])
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
        # Calendar service unavailable - assume no bookings exist
        # Calculate available slots based on consultant count
        slots_per_consultant = getattr(slot_config, 'SLOTS_PER_BERATER', 4)
        total_capacity = berater_count * slots_per_consultant
        return [], 0, total_capacity, total_capacity, False

    from app.config.base import config
    events_result = calendar_service.get_events(
        calendar_id=config.CENTRAL_CALENDAR_ID,
        time_min=f"{date_str}T{hour}:00+01:00",
        time_max=f"{date_str}T{hour}:59+01:00"
    )

    events = events_result.get('items', []) if events_result else []

    # Process events
    slot_list = []
    booked_count = 0

    for event in events:
        summary = event.get('summary', 'Unbekannt')
        color_id = event.get('colorId', '1')

        slot_list.append({
            'summary': summary,
            'colorId': color_id,
            'outcome': 'unknown'  # Will be enhanced later
        })

        # Only count as booked if it's NOT a T1-bereit event
        if not is_t1_bereit_event(summary):
            booked_count += 1

    booked = booked_count
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