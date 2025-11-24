# -*- coding: utf-8 -*-
"""
T2 Availability Service
Scans Google Calendar for free 2-hour slots (09:00-22:00)
Caches availability for 6 weeks
"""

import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional
from app.core.google_calendar import get_google_calendar_service
from app.services.data_persistence import data_persistence

logger = logging.getLogger(__name__)

# T2 Closer configuration (synchronized with t2.py)
T2_CLOSERS = {
    "Alexander": {"calendar_id": "alexandernehm84@gmail.com"},
    "David": {"calendar_id": "david.nehm@googlemail.com"},
    "Jose": {"calendar_id": "jtldiw@gmail.com"}
}

# Time slots for 2-hour appointments (09:00-22:00, last slot 20:00-22:00)
TIME_SLOTS = [
    "09:00", "11:00", "13:00", "15:00", "17:00", "19:00", "20:00"
]


class T2AvailabilityService:
    """Service for scanning and caching T2 closer availability"""

    def __init__(self):
        self.calendar_service = get_google_calendar_service()

    def scan_all_closers_availability(self, days: int = 42) -> Dict:
        """
        Scan availability for all closers for next N days

        Args:
            days: Number of days to scan (default: 42 = 6 weeks)

        Returns:
            Dict with availability data
        """
        logger.info(f"Starting availability scan for all closers ({days} days)")

        availability = {}

        for closer_name in T2_CLOSERS.keys():
            try:
                closer_availability = self.scan_closer_availability(closer_name, days)
                availability[closer_name] = closer_availability
                logger.info(f"Scanned {closer_name}: {len(closer_availability)} days with data")
            except Exception as e:
                logger.error(f"Error scanning {closer_name}: {e}")
                availability[closer_name] = {}

        # Save to cache
        self.save_availability_cache(availability, days)

        return availability

    def scan_closer_availability(self, closer_name: str, days: int = 42) -> Dict[str, List[str]]:
        """
        Scan availability for single closer

        Args:
            closer_name: Closer name (e.g., "Alexander")
            days: Number of days to scan

        Returns:
            Dict mapping date strings to list of available time slots
            Example: {"2025-10-10": ["09:00", "11:00", "14:00"], ...}
        """
        if closer_name not in T2_CLOSERS:
            logger.error(f"Unknown closer: {closer_name}")
            return {}

        calendar_id = T2_CLOSERS[closer_name]["calendar_id"]

        # Calculate time range
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=days)

        # Get all events in range
        time_min = start_date.isoformat() + 'Z'
        time_max = end_date.isoformat() + 'Z'

        try:
            result = self.calendar_service.get_events(
                calendar_id=calendar_id,
                time_min=time_min,
                time_max=time_max,
                cache_duration=3600  # Cache for 1 hour
            )

            events = result.get('items', []) if result else []
            logger.info(f"{closer_name}: Found {len(events)} events in {days} days")

        except Exception as e:
            logger.error(f"Error fetching calendar events for {closer_name}: {e}")
            return {}

        # Process each day
        availability = {}
        current_date = start_date

        while current_date < end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            available_slots = self.find_free_2h_slots(events, date_str)
            availability[date_str] = available_slots
            current_date += timedelta(days=1)

        return availability

    def find_free_2h_slots(self, events: List[Dict], date_str: str) -> List[str]:
        """
        Find free 2-hour slots for a specific date

        Args:
            events: List of Google Calendar events
            date_str: Date in YYYY-MM-DD format

        Returns:
            List of available slot start times (e.g., ["09:00", "14:00"])
        """
        # Filter events for this date
        date_events = []
        for event in events:
            start = event.get('start', {})
            start_time = start.get('dateTime') or start.get('date')

            if not start_time:
                continue

            # Extract date
            event_date = start_time.split('T')[0] if 'T' in start_time else start_time

            if event_date == date_str:
                date_events.append(event)

        # Check each time slot
        available_slots = []

        for slot_start in TIME_SLOTS:
            if self._is_slot_available(date_str, slot_start, date_events):
                available_slots.append(slot_start)

        return available_slots

    def _is_slot_available(self, date_str: str, slot_start: str, events: List[Dict]) -> bool:
        """
        Check if a 2-hour slot is available

        Args:
            date_str: Date in YYYY-MM-DD format
            slot_start: Slot start time (e.g., "09:00")
            events: Events on that date

        Returns:
            True if slot is free
        """
        # Parse slot times
        slot_start_hour, slot_start_minute = map(int, slot_start.split(':'))
        slot_start_dt = datetime.strptime(date_str, '%Y-%m-%d').replace(
            hour=slot_start_hour, minute=slot_start_minute
        )
        slot_end_dt = slot_start_dt + timedelta(hours=2)

        # Check against all events
        for event in events:
            start = event.get('start', {})
            end = event.get('end', {})

            start_time = start.get('dateTime')
            end_time = end.get('dateTime')

            if not start_time or not end_time:
                continue

            # Parse event times
            try:
                event_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

                # Remove timezone for comparison (assume same timezone)
                event_start = event_start.replace(tzinfo=None)
                event_end = event_end.replace(tzinfo=None)

                # Check for overlap
                if self._times_overlap(slot_start_dt, slot_end_dt, event_start, event_end):
                    return False  # Slot is blocked

            except Exception as e:
                logger.warning(f"Error parsing event times: {e}")
                continue

        return True  # Slot is free

    def _times_overlap(self, start1, end1, start2, end2) -> bool:
        """Check if two time ranges overlap"""
        return start1 < end2 and start2 < end1

    def save_availability_cache(self, availability: Dict, days: int):
        """
        Save availability to persistent cache

        Args:
            availability: Dict mapping closer names to their availability
            days: Number of days scanned
        """
        cache_data = {
            'last_updated': datetime.now().isoformat(),
            'scan_duration_days': days,
            'availability': availability
        }

        try:
            data_persistence.save_data('t2_availability', cache_data)
            logger.info(f"Availability cache saved ({days} days, {len(availability)} closers)")
        except Exception as e:
            logger.error(f"Error saving availability cache: {e}")

    def get_cached_availability(self, closer_name: str = None, date: str = None) -> Dict:
        """
        Get availability from cache

        Args:
            closer_name: Optional closer name to filter
            date: Optional date to filter

        Returns:
            Cached availability data
        """
        try:
            cache = data_persistence.load_data('t2_availability', {})

            if not cache:
                logger.warning("No availability cache found")
                return {}

            availability = cache.get('availability', {})

            # Filter by closer if specified
            if closer_name:
                availability = {closer_name: availability.get(closer_name, {})}

            # Filter by date if specified
            if date and closer_name:
                closer_data = availability.get(closer_name, {})
                return {closer_name: {date: closer_data.get(date, [])}}

            return availability

        except Exception as e:
            logger.error(f"Error loading availability cache: {e}")
            return {}

    def is_date_available(self, closer_name: str, date: str) -> bool:
        """
        Check if closer has any availability on date

        Args:
            closer_name: Closer name
            date: Date in YYYY-MM-DD format

        Returns:
            True if closer has at least one free slot
        """
        availability = self.get_cached_availability(closer_name, date)
        closer_data = availability.get(closer_name, {})
        date_slots = closer_data.get(date, [])
        return len(date_slots) > 0

    def get_available_dates(self, closer_name: str, days: int = 42) -> List[str]:
        """
        Get list of dates where closer has availability

        Args:
            closer_name: Closer name
            days: Number of days to check

        Returns:
            List of date strings with availability
        """
        availability = self.get_cached_availability(closer_name)
        closer_data = availability.get(closer_name, {})

        available_dates = [
            date for date, slots in closer_data.items()
            if len(slots) > 0
        ]

        return sorted(available_dates)


# Global instance (lazy-loaded)
_availability_service_instance = None

def get_availability_service():
    """Get or create availability service instance"""
    global _availability_service_instance
    if _availability_service_instance is None:
        _availability_service_instance = T2AvailabilityService()
    return _availability_service_instance

# For backwards compatibility
availability_service = type('LazyService', (), {
    '__getattr__': lambda self, name: getattr(get_availability_service(), name)
})()


# CLI function for cron job
def scan_all_closers():
    """CLI function to scan all closers (for systemd timer)"""
    logger.info("=== T2 Availability Scan Started ===")
    try:
        service = get_availability_service()
        result = service.scan_all_closers_availability(days=42)
        logger.info(f"=== Scan Complete: {len(result)} closers processed ===")
        return result
    except Exception as e:
        logger.error(f"=== Scan Failed: {e} ===")
        return {}
