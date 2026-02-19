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
from app.core.extensions import cache_manager, data_persistence, tracking_system
from app.core.google_calendar import get_google_calendar_service
from app.utils.helpers import get_week_start, get_current_kw, week_key_from_date
from app.utils.logging import booking_logger
from app.utils.memory_guard import safe_import, force_garbage_collection
# from color_mapping import determine_outcome_from_color  # Will be fixed later

# Logger setup
logger = logging.getLogger(__name__)

TZ = pytz.timezone(slot_config.TIMEZONE)


def load_special_bookings() -> Dict[str, Dict]:
    """Load special bookings (T1.5/UL) from persistent storage"""
    special_file = os.path.join("data", "persistent", "special_bookings.json")
    if os.path.exists(special_file):
        try:
            with open(special_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading special bookings: {e}")
            return {}
    return {}


def save_special_bookings(data: Dict) -> None:
    """Save special bookings (T1.5/UL) to persistent storage"""
    special_file = os.path.join("data", "persistent", "special_bookings.json")
    os.makedirs(os.path.dirname(special_file), exist_ok=True)
    try:
        with open(special_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving special bookings: {e}")
        raise


def check_special_booking_capacity(date_str: str, hour: str, opener_name: str) -> Dict[str, Any]:
    """Check if an opener can take a special booking (T1.5/UL) without causing undercapacity.

    Args:
        date_str: Date in YYYY-MM-DD format
        hour: Time slot e.g. "14:00"
        opener_name: Opener name as in availability.json (e.g. "Sara")

    Returns:
        Dict with 'allowed', 'reason', and capacity details
    """
    consultants = get_effective_availability(date_str, hour)

    if opener_name not in consultants:
        return {
            'allowed': False,
            'reason': f'{opener_name} ist in diesem Slot nicht eingeteilt.',
            'current_openers': len(consultants),
            'remaining_openers': len(consultants)
        }

    remaining_count = len(consultants) - 1
    weekday = datetime.strptime(date_str, '%Y-%m-%d').weekday()
    slots_per = get_slots_per_consultant(hour, weekday)
    remaining_capacity = remaining_count * slots_per

    # Get current bookings in this slot
    berater_count = len(consultants)
    _, booked, _, _, _ = get_slot_status(date_str, hour, berater_count)

    if remaining_capacity >= booked:
        return {
            'allowed': True,
            'reason': f'Kapazität reicht aus. {remaining_count} Opener verbleiben mit {remaining_capacity} Plätzen für {booked} Buchungen.',
            'current_openers': len(consultants),
            'remaining_openers': remaining_count,
            'remaining_capacity': remaining_capacity,
            'booked': booked
        }
    else:
        return {
            'allowed': False,
            'reason': f'Nicht genug Kapazität. {remaining_count} Opener hätten nur {remaining_capacity} Plätze für {booked} Buchungen.',
            'current_openers': len(consultants),
            'remaining_openers': remaining_count,
            'remaining_capacity': remaining_capacity,
            'booked': booked
        }


def remove_opener_from_availability(date_str: str, hour: str, opener_name: str) -> bool:
    """Remove an opener from availability.json for a specific slot.

    Args:
        date_str: Date in YYYY-MM-DD format
        hour: Time slot e.g. "14:00"
        opener_name: Opener name to remove

    Returns:
        True if successfully removed, False otherwise
    """
    availability_file = os.path.join("data", "persistent", "availability.json")
    if not os.path.exists(availability_file):
        availability_file = os.path.join("static", "availability.json")

    if not os.path.exists(availability_file):
        logger.error("availability.json not found")
        return False

    try:
        with open(availability_file, 'r', encoding='utf-8') as f:
            availability = json.load(f)

        slot_key = f"{date_str} {hour}"
        if slot_key in availability and opener_name in availability[slot_key]:
            availability[slot_key].remove(opener_name)
            with open(availability_file, 'w', encoding='utf-8') as f:
                json.dump(availability, f, ensure_ascii=False, indent=2)
            logger.info(f"Removed {opener_name} from availability slot {slot_key}")
            return True
        else:
            logger.warning(f"Opener {opener_name} not found in slot {slot_key}")
            return False
    except Exception as e:
        logger.error(f"Error removing opener from availability: {e}")
        return False


def get_slots_per_consultant(hour: str, weekday: int) -> int:
    """Kapazität pro Berater für einen Zeitslot.

    Args:
        hour: Zeitslot z.B. "09:00", "11:00"
        weekday: 0=Monday ... 4=Friday
    """
    if hour == "09:00":
        if weekday <= 3:  # Mo-Do
            return slot_config.SLOTS_PER_BERATER_9AM_MON_THU
        return slot_config.SLOTS_PER_BERATER_9AM
    elif hour == "20:00":
        return slot_config.SLOTS_PER_BERATER_8PM
    return slot_config.SLOTS_PER_BERATER


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

def get_day_availability(date_str: str) -> Dict[str, List[str]]:
    """
    Get all availability slots for a specific day
    Wrapper around get_effective_availability() for full day data
    Returns: Dict with time slots as keys, consultant lists as values
    """
    from app.services.holiday_service import holiday_service
    from datetime import datetime

    # Check if entire day is blocked
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if holiday_service.is_blocked_date(check_date):
            return {}  # No slots available on blocked dates
    except Exception:
        pass

    availability = load_availability()
    day_slots = {}

    # Standard time slots
    time_slots = ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]

    for hour in time_slots:
        # Use existing get_effective_availability for each slot
        # This respects holiday blocks, time-range blocks, etc.
        consultants = get_effective_availability(date_str, hour)
        if consultants:  # Only include non-empty slots
            day_slots[hour] = consultants

    return day_slots


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
        # If there's any error checking holidays, fail safe - no availability
        from app.utils.logging import booking_logger
        booking_logger.warning(f"Error checking holiday status for {date_str}: {e}")
        return []

    availability = load_availability()

    # Try to get from loaded data first - handle old format "YYYY-MM-DD HH:MM"
    slot_key = f"{date_str} {hour}"
    if slot_key in availability:
        loaded_consultants = availability[slot_key]

        # 9am slots use pre-generated availability only (no live API checks)
        # This improves performance by reducing API calls from 105 to ~10 per page load
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
    # Loop until we have 4 valid weeks (skip fully blocked weeks like Betriebsferien)
    valid_weeks_collected = 0
    week_offset = 0
    max_weeks_to_scan = 15  # Enough buffer to skip blocked weeks

    while valid_weeks_collected < 6 and week_offset < max_weeks_to_scan:
        week_start = get_week_start(today) + timedelta(weeks=week_offset)

        # Pre-check: Does this week have ANY availability? (Skip fully blocked weeks)
        week_has_availability = False
        for day_offset in range(5):  # Mo-Fr only for check
            date_obj = week_start + timedelta(days=day_offset)
            if date_obj < today:
                continue

            date_str = date_obj.strftime("%Y-%m-%d")

            # Check if ANY timeslot has availability
            for hour in ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]:
                consultants = get_effective_availability(date_str, hour)
                if consultants:
                    week_has_availability = True
                    break

            if week_has_availability:
                break

        # If week has no availability → skip to next week
        if not week_has_availability:
            week_offset += 1
            continue

        # Process this week fully (has availability)
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

                    slots_per_consultant = get_slots_per_consultant(hour, date_obj.weekday())

                    key = week_key_from_date(dt)
                    week_possible[key] += len(consultants) * slots_per_consultant
                    monday = dt - timedelta(days=dt.weekday())
                    friday = monday + timedelta(days=4)
                    week_dates[key] = (monday, friday)

        # Week processed successfully → increment counters
        valid_weeks_collected += 1
        week_offset += 1

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


def extract_monthly_overview():
    """Slot-Level-Übersicht für die nächsten 3 Kalenderwochen.

    Returns list of weeks, each with days, each day with per-hour slot utilization.
    Color coding: success (<60%), warning (60-90%), error (>=90%)
    """
    from app.utils.color_mapping import blocks_availability

    today = datetime.now(TZ).date()
    # Always start from next Monday — current week is covered by weekly summary + day view
    week_start = get_week_start(today) + timedelta(weeks=1)

    time_slots = ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]
    weekday_names = ["Mo", "Di", "Mi", "Do", "Fr"]

    # Phase 1: Collect capacity data for all slots
    weeks_data = []
    all_dates_min = None
    all_dates_max = None

    for w in range(3):
        ws = week_start + timedelta(weeks=w)
        kw = ws.isocalendar()[1]
        friday = ws + timedelta(days=4)

        week_info = {
            "kw": kw,
            "range": f"{ws.strftime('%d.%m.')} - {friday.strftime('%d.%m.')}",
            "days": []
        }

        for day_offset in range(5):  # Mo-Fr
            date_obj = ws + timedelta(days=day_offset)
            date_str = date_obj.strftime("%Y-%m-%d")

            # Track date range for calendar API call
            if all_dates_min is None or date_obj < all_dates_min:
                all_dates_min = date_obj
            if all_dates_max is None or date_obj > all_dates_max:
                all_dates_max = date_obj

            day_info = {
                "date_str": date_str,
                "weekday_short": weekday_names[day_offset],
                "date_short": date_obj.strftime("%d.%m."),
                "slots": []
            }

            for hour in time_slots:
                consultants = get_effective_availability(date_str, hour)
                if consultants:
                    slots_per = get_slots_per_consultant(hour, date_obj.weekday())
                    total = len(consultants) * slots_per
                else:
                    total = 0

                day_info["slots"].append({
                    "hour": hour,
                    "booked": 0,  # Filled in phase 2
                    "total": total,
                    "pct": 0,
                    "color": "success"
                })

            week_info["days"].append(day_info)

        weeks_data.append(week_info)

    # Phase 2: Single Calendar API call for all events in the 3-week range
    if all_dates_min and all_dates_max:
        min_dt = TZ.localize(datetime.combine(all_dates_min, datetime.min.time()))
        max_dt = TZ.localize(datetime.combine(all_dates_max + timedelta(days=1), datetime.min.time()))

        calendar_service = get_google_calendar_service()
        events = []
        if calendar_service:
            try:
                from app.config.base import config
                events_result = calendar_service.get_events(
                    calendar_id=config.CENTRAL_CALENDAR_ID,
                    time_min=min_dt.isoformat(),
                    time_max=max_dt.isoformat(),
                    max_results=2500
                )
                events = events_result.get('items', []) if events_result else []
                logger.info(f"Monthly overview: Fetched {len(events)} events ({all_dates_min} to {all_dates_max})")
            except Exception as e:
                logger.error(f"Monthly overview: Error fetching calendar events: {e}")

        # Build lookup: (date_str, hour_bucket) -> booked_count
        booked_lookup = defaultdict(int)
        for event in events:
            if "start" not in event or "dateTime" not in event["start"]:
                continue
            try:
                dt = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                event_date = dt.strftime("%Y-%m-%d")
                # Bucket to the nearest even hour slot
                event_hour = f"{dt.hour:02d}:00"

                summary = event.get("summary", "")
                if is_t1_bereit_event(summary):
                    continue

                color_id = event.get("colorId", "2")
                if not blocks_availability(color_id):
                    continue

                booked_lookup[(event_date, event_hour)] += 1
            except Exception:
                continue

        # Phase 3: Fill in booked counts and calculate colors
        for week in weeks_data:
            for day in week["days"]:
                for slot in day["slots"]:
                    booked = booked_lookup.get((day["date_str"], slot["hour"]), 0)
                    slot["booked"] = booked
                    total = slot["total"]

                    if total > 0:
                        pct = int(round((booked / total) * 100))
                        slot["pct"] = min(pct, 100)
                    else:
                        slot["pct"] = 0

                    # Color logic: green <60%, yellow 60-90%, red >=90%
                    if total == 0:
                        slot["color"] = "ghost"
                    elif slot["pct"] < 60:
                        slot["color"] = "success"
                    elif slot["pct"] < 90:
                        slot["color"] = "warning"
                    else:
                        slot["color"] = "error"

    # Filter out days with no availability at all (e.g. holidays)
    for week in weeks_data:
        week["days"] = [
            day for day in week["days"]
            if any(s["total"] > 0 for s in day["slots"])
        ]

    # Remove empty weeks
    weeks_data = [w for w in weeks_data if w["days"]]

    return weeks_data


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

    from app.services.holiday_service import holiday_service

    for date_str, date_slots in availability.items():
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            if holiday_service.is_blocked_date(date_obj.date()):
                continue
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
    weekday = datetime.strptime(date_str, "%Y-%m-%d").weekday()
    slots_per_consultant = get_slots_per_consultant(hour, weekday)

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
    from app.services.holiday_service import holiday_service

    for days_ahead in range(1, 15):  # Look 2 weeks ahead
        check_date = today + timedelta(days=days_ahead)
        date_str = check_date.strftime("%Y-%m-%d")

        if holiday_service.is_blocked_date(check_date):
            continue

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


def award_booking_points(user, points):
    """Add points and coins to user, process achievements.

    Args:
        user: Username
        points: Points to award

    Returns:
        list: New badges earned (may be empty)
    """
    try:
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

        # Achievement system integration
        new_badges = []
        try:
            achievement_module = safe_import('app.services.achievement_system')

            if achievement_module and hasattr(achievement_module, 'achievement_system'):
                achievement_sys = achievement_module.achievement_system

                if achievement_sys:
                    new_badges = achievement_sys.process_user_achievements(user)
                    if isinstance(new_badges, list) and len(new_badges) > 20:
                        booking_logger.warning(f"Achievement system returned {len(new_badges)} badges, limiting to 20")
                        new_badges = new_badges[:20]

        except MemoryError:
            booking_logger.error(f"Memory error in achievement system for user {user}")
            force_garbage_collection()
        except Exception as e:
            booking_logger.error(f"Could not process achievements for user {user}: {e}", exc_info=True)

        return new_badges if isinstance(new_badges, list) else []

    except Exception as e:
        booking_logger.error(f"Error adding points to user {user}: {e}", exc_info=True)
        return []


def execute_post_booking_chain(user, customer_name, date, hour, color_id,
                                description, points, calendar_event_id):
    """Orchestrate the post-booking chain: Tracking -> Points -> Quests -> Stats -> Audit.

    Args:
        user: Username who booked
        customer_name: "Last, First" format
        date: Date string YYYY-MM-DD
        hour: Time slot e.g. "14:00"
        color_id: Calendar color ID
        description: Booking description
        points: Points to award
        calendar_event_id: Google Calendar event ID

    Returns:
        dict with keys: tracking_ok, new_badges, flash_messages
    """
    from app.utils.error_messages import get_error_message
    from app.utils.error_tracking import generate_error_id

    flash_messages = []
    tracking_successful = False
    new_badges = []

    # --- 1. Tracking ---
    try:
        if tracking_system:
            booking_data = tracking_system.track_booking(
                customer_name=customer_name,
                date=date,
                time_slot=hour,
                user=user or "unknown",
                color_id=color_id,
                description=description
            )
            if booking_data is None:
                error_id = generate_error_id("TRK")
                booking_logger.error(
                    f"Dual-write tracking failed {error_id}: "
                    f"customer={customer_name}, date={date}, hour={hour}, "
                    f"calendar_event_id={calendar_event_id}",
                    extra_fields={'error_id': error_id, 'calendar_event_id': calendar_event_id}
                )

                error_msg = get_error_message('TRACKING_FAILED')
                flash_messages.append((f"{error_msg['message']} (Fehler-ID: {error_id})", "warning"))
                flash_messages.append(("WICHTIG: Ihr Termin wurde erfolgreich im Kalender erstellt und ist gültig!", "success"))

                try:
                    from app.services.notification_service import notification_service
                    notification_service.create_notification(
                        roles=['admin'],
                        title='Tracking Failed - Action Required',
                        message=f'Booking created but tracking failed for {customer_name} on {date} {hour}. Error ID: {error_id}',
                        notification_type='warning',
                        show_popup=True
                    )
                except Exception:
                    pass
            else:
                tracking_successful = True
    except Exception as e:
        error_id = generate_error_id("TRK")
        booking_logger.error(
            f"Tracking exception {error_id}: {e}, customer={customer_name}, date={date}, hour={hour}",
            exc_info=True,
            extra_fields={'error_id': error_id}
        )

        error_msg = get_error_message('TRACKING_FAILED')
        flash_messages.append((f"{error_msg['message']} (Fehler-ID: {error_id})", "warning"))
        flash_messages.append(("WICHTIG: Ihr Termin wurde erfolgreich im Kalender erstellt und ist gültig!", "success"))

    # --- 2. Points & Achievements ---
    if user and user != "unknown":
        try:
            new_badges = award_booking_points(user, points)
            if points > 0 and tracking_successful:
                flash_messages.append((f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) und {points} Coins erhalten.", "success"))
            elif tracking_successful:
                flash_messages.append(("Slot erfolgreich gebucht!", "success"))
        except Exception as e:
            booking_logger.error(f"Critical error in achievement system for user {user}: {e}", exc_info=True)
            if tracking_successful:
                flash_messages.append(("Slot erfolgreich gebucht!", "success"))
    else:
        if tracking_successful:
            flash_messages.append(("Slot erfolgreich gebucht!", "success"))

    # --- 3. Quest Progress ---
    if user and user != "unknown":
        try:
            from app.routes.gamification.legacy_routes import update_quest_progress_for_booking
            quest_data = {
                "has_description": bool(description),
                "booking_time": int(hour.split(":")[0]) if isinstance(hour, str) and ":" in hour else 0,
                "points_earned": points,
                "date": date,
                "hour": hour
            }
            update_quest_progress_for_booking(user, quest_data)
        except ImportError:
            pass  # Enhanced features not available
        except Exception as e:
            booking_logger.warning(f"Could not update quest progress for user {user}: {e}")

    # --- 4. Daily Stats ---
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

    # --- 5. Badge flash messages ---
    if new_badges:
        badge_names = [badge["name"] for badge in new_badges]
        flash_messages.append((f"Neue Badges erhalten: {', '.join(badge_names)}", "success"))

    # --- 6. Audit log (per CLAUDE.md requirement) ---
    try:
        from app.services.audit_service import audit_service
        audit_service.log_event(
            event_type='booking',
            action='booking_created',
            details={
                'customer': customer_name,
                'date': date,
                'hour': hour,
                'color_id': color_id,
                'points': points,
                'calendar_event_id': calendar_event_id,
                'tracking_ok': tracking_successful,
                'badges_earned': len(new_badges)
            },
            user=user
        )
    except Exception as e:
        booking_logger.warning(f"Could not write audit log for booking: {e}")

    return {
        'tracking_ok': tracking_successful,
        'new_badges': new_badges,
        'flash_messages': flash_messages
    }