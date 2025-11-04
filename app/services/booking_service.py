# -*- coding: utf-8 -*-
"""
Booking service - Business logic for slot booking and availability
"""

import json
import os
import pytz
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

from app.config.base import slot_config, consultant_config
from app.core.extensions import cache_manager, data_persistence
from app.core.google_calendar import get_google_calendar_service
from app.utils.helpers import get_week_start, get_current_kw, week_key_from_date
# from color_mapping import determine_outcome_from_color  # Will be fixed later

# Logger setup
logger = logging.getLogger(__name__)

TZ = pytz.timezone(slot_config.TIMEZONE)


def is_t1_bereit_event(summary: str) -> bool:
    """Check if an event is a T1-bereit event (should not count as booked)"""
    summary_lower = summary.lower()
    return 't1-bereit' in summary_lower or 't1 bereit' in summary_lower


def load_availability() -> Dict[str, List[str]]:
    """Load availability data from persistent storage"""
    availability_file = "data/persistent/availability.json"

    # Fallback to old location for backwards compatibility
    if not os.path.exists(availability_file):
        availability_file = "static/availability.json"

    if os.path.exists(availability_file):
        try:
            with open(availability_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            from app.utils.logging import booking_logger
            booking_logger.error(f"Error loading availability from {availability_file}: {e}")
            return {}
    return {}


def get_default_availability(date_str: str, hour: str) -> List[str]:
    """Get default consultant availability for a time slot

    Standard-Verfügbarkeit greift nur wenn:
    1. Datum ist NACH AVAILABILITY_GENERATION_DAYS (56 Tage)
    2. Datum ist nicht geblockt (Feiertage)
    3. Zeitslot ist in STANDARD_AVAILABILITY_HOURS definiert

    Zeiten:
    - Mo-Do: 11:00, 14:00, 16:00, 18:00, 20:00
    - Fr: 09:00, 11:00, 14:00
    """
    # Check if date is blocked (holidays or custom blocks) first
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        from app.services.holiday_service import holiday_service

        # Check with time to respect time-range blocks
        if holiday_service.is_blocked_date(check_date, check_time=hour):
            return []  # No availability on blocked dates/times
    except Exception as e:
        # If there's any error checking holidays, log it but continue
        from app.utils.logging import booking_logger
        booking_logger.warning(f"Error checking holiday status for {date_str}: {e}")
        return []

    # Check if date is beyond availability generation days
    today = datetime.now(TZ).date()
    days_ahead = (check_date - today).days

    # Standard-Verfügbarkeit nur nach AVAILABILITY_GENERATION_DAYS
    if days_ahead <= slot_config.AVAILABILITY_GENERATION_DAYS:
        return []  # Noch innerhalb des generierten Zeitraums

    # Check if weekday and hour are in standard availability
    weekday = check_date.weekday()
    standard_hours = slot_config.STANDARD_AVAILABILITY_HOURS.get(weekday, [])

    if hour in standard_hours:
        return consultant_config.DEFAULT_STANDARD_CONSULTANTS

    # No Standard-Verfügbarkeit for this slot
    return []


# REMOVED: get_9am_availability_from_calendar()
# This function made 9 API calls per page load (1 per consultant)
# 9am slots now use pre-generated availability from availability.json only
# Performance improvement: Reduced API calls from 105 to ~10 per page load

def get_effective_availability(date_str: str, hour: str) -> List[str]:
    """Get effective availability combining loaded, calendar (for 9am), and default data"""
    # Check if date is blocked (holidays or custom blocks)
    try:
        from datetime import datetime
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        from app.services.holiday_service import holiday_service

        # Check with time to respect time-range blocks
        if holiday_service.is_blocked_date(check_date, check_time=hour):
            return []  # No availability on blocked dates/times
    except Exception as e:
        # If there's any error checking holidays, log it but continue
        from app.utils.logging import booking_logger
        booking_logger.warning(f"Error checking holiday status for {date_str}: {e}")

    availability = load_availability()

    # Try to get from loaded data first - handle old format "YYYY-MM-DD HH:MM"
    slot_key = f"{date_str} {hour}"
    if slot_key in availability:
        loaded_consultants = availability[slot_key]

        # 9am slots use pre-generated availability only (no live API checks)
        # This improves performance by reducing API calls from 105 to ~10 per page load
        return loaded_consultants

    # Also try new nested format for backwards compatibility
    if date_str in availability and hour in availability[date_str]:
        loaded_consultants = availability[date_str][hour]

        # For 9am slots: merge with live T1-bereit check
        if hour == "09:00":
            t1_consultants = get_9am_availability_from_calendar(date_str)
            combined = list(set(loaded_consultants + t1_consultants))
            return combined

        return loaded_consultants

    # For 9am slots without pre-generated data: Use default availability
    # (Live T1-bereit checking removed for performance - was 9 API calls)
    if hour == "09:00":
        return get_default_availability(date_str, hour)

    # Fall back to default availability for all other hours
    return get_default_availability(date_str, hour)


def extract_weekly_summary(availability, current_date=None):
    """Extract weekly summary using old working method - matches original calculation"""
    from collections import defaultdict
    from app.utils.color_mapping import blocks_availability

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

                    # Use different capacity for 9am slots
                    if hour == "09:00":
                        slots_per_consultant = slot_config.SLOTS_PER_BERATER_9AM
                    else:
                        slots_per_consultant = slot_config.SLOTS_PER_BERATER

                    key = week_key_from_date(dt)
                    week_possible[key] += len(consultants) * slots_per_consultant
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
                logger.info(f"Weekly summary: Fetched {len(events)} events from Google Calendar ({min_start_dt.date()} to {max_end_dt.date()})")
            except Exception as e:
                from app.utils.logging import booking_logger
                booking_logger.error(f"Error fetching calendar events: {e}")
                events = []
        else:
            logger.warning("Weekly summary: Google Calendar service not available")
            events = []

        # Process all events
        events_processed = 0
        events_counted = 0
        events_filtered_t1 = 0
        events_filtered_color = 0
        for event in events:
            if "start" in event and "dateTime" in event["start"]:
                try:
                    dt = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                    events_processed += 1
                    # Only count future events
                    if dt.date() >= today:
                        # Get event summary to check if it's T1-bereit
                        summary = event.get("summary", "")

                        # Don't count T1-bereit events as booked
                        if is_t1_bereit_event(summary):
                            events_filtered_t1 += 1
                            logger.debug(f"Event filtered (T1-bereit): {summary}")
                        else:
                            # IMPORTANT: Check if event blocks availability
                            color_id = event.get("colorId", "2")  # Default: Green
                            blocks = blocks_availability(color_id)
                            logger.debug(f"Event '{summary}' has colorId={color_id}, blocks_availability={blocks}")
                            if blocks:  # Only count blocking events
                                key = week_key_from_date(dt)
                                week_booked[key] += 1
                                events_counted += 1
                            else:
                                events_filtered_color += 1
                except Exception as e:
                    logger.error(f"Error parsing event time", extra={'error': str(e)})
                    continue

        logger.info(f"Weekly summary: Processed {events_processed} events, counted {events_counted} as booked (filtered: {events_filtered_t1} T1-bereit, {events_filtered_color} non-blocking colors)")

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
    """Get slot booking status for a specific time slot

    9am slots have reduced capacity: SLOTS_PER_BERATER_9AM (2) instead of SLOTS_PER_BERATER (3)
    """
    # Use different capacity for 9am slots
    if hour == "09:00":
        slots_per_consultant = slot_config.SLOTS_PER_BERATER_9AM
    else:
        slots_per_consultant = slot_config.SLOTS_PER_BERATER

    max_slots = berater_count * slots_per_consultant

    # Get events from Google Calendar
    calendar_service = get_google_calendar_service()
    if not calendar_service:
        # Calendar service unavailable - assume no bookings exist
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


def get_slot_points(hour, slot_date, date_str=None, berater_count=None, color_id=None):
    """Calculate points for a time slot based on availability and demand"""

    # If we have slot information, calculate dynamic points based on utilization
    if date_str and berater_count:
        try:
            slot_list, booked, total, freie_count, overbooked = get_slot_status(date_str, hour, berater_count)

            # Calculate utilization rate
            utilization = booked / total if total > 0 else 0

            # Base points based on utilization (incentivize booking less full slots)
            if utilization <= 0.33:  # 0-33% full
                points = 5
            elif utilization <= 0.66:  # 34-66% full
                points = 3
            else:  # 67-100% full
                points = 1

        except Exception:
            # Fallback to static points if dynamic calculation fails
            points = 3
    else:
        # Fallback base points when no slot data available
        points = 3

    # Time-based bonus for less popular slots
    if hour in ["11:00", "14:00"]:
        points += 2

    # Weekend bonus
    if slot_date.weekday() >= 5:
        points += 1

    # Rückholungs-Modifikator: Halbe Punkte für Rückholungen (Color ID "3")
    if color_id == "3":
        points = int(points * 0.5)
        # Mindestens 1 Punkt vergeben
        points = max(1, points)

    return points


def book_slot_for_user(user: str, date_str: str, time_str: str, berater: str,
                       first_name: str = "", last_name: str = "", description: str = "",
                       color_id: str = "9") -> Dict[str, Any]:
    """
    Book a slot for a user

    Args:
        user: Username who is booking
        date_str: Date in format YYYY-MM-DD
        time_str: Time in format HH:MM
        berater: Consultant name
        first_name: Customer first name (optional)
        last_name: Customer last name (optional)
        description: Booking description (optional)
        color_id: Calendar color ID (default 9)

    Returns:
        Dict with 'success' boolean and either 'message' or 'error'
    """
    try:
        # Validate inputs
        if not all([user, date_str, time_str]):
            return {'success': False, 'error': 'Missing required parameters'}

        # Parse datetime
        try:
            slot_start = TZ.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M"))
            slot_end = slot_start + timedelta(hours=2)
        except ValueError as e:
            return {'success': False, 'error': f'Invalid date/time format: {e}'}

        # Create booking description with [Booked by:] tag for tracking
        booking_description = description
        if user and user != "unknown":
            tag = f"[Booked by: {user}]"
            booking_description = f"{description}\n\n{tag}" if description else tag

        # Create event summary
        if first_name and last_name:
            summary = f"{last_name}, {first_name}"
        elif first_name:
            summary = first_name
        elif last_name:
            summary = last_name
        else:
            summary = "Buchung"

        # Create calendar event
        event_body = {
            "summary": summary,
            "description": booking_description,
            "start": {"dateTime": slot_start.isoformat()},
            "end": {"dateTime": slot_end.isoformat()},
            "colorId": color_id
        }

        # Book via Google Calendar
        calendar_service = get_google_calendar_service()
        if not calendar_service:
            return {'success': False, 'error': 'Calendar service not available'}

        from app.config.base import config
        result = calendar_service.create_event(
            calendar_id=config.CENTRAL_CALENDAR_ID,
            event_data=event_body
        )

        if not result:
            return {'success': False, 'error': 'Failed to create calendar event'}

        # Clear cache
        cache_manager.clear_all()

        # Track booking in bookings.jsonl for backfill script and analytics
        try:
            from app.services.tracking_system import tracking_system
            tracking_system.track_booking(
                customer_name=summary,
                date=date_str,
                time_slot=time_str,
                user=user,
                color_id=color_id,
                description=description
            )
            logger.debug(f"Booking tracked in bookings.jsonl: {summary} by {user}")
        except Exception as track_error:
            # Don't fail the booking if tracking fails
            logger.warning(f"Failed to track booking: {track_error}")

        logger.info(f"Slot booked successfully by {user}: {date_str} {time_str} - {summary}")

        return {
            'success': True,
            'message': 'Slot erfolgreich gebucht',
            'event_id': result.get('id') if isinstance(result, dict) else None
        }

    except Exception as e:
        logger.error(f"Error booking slot: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}