# -*- coding: utf-8 -*-
"""
T2 Calendar Parser Service
Parses Google Calendar events for T2/T3 appointment types
"""

import re
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class T2CalendarParser:
    """Parser for T2/T3 calendar events"""

    # Appointment type regex: T2, T2.5, T2.75, T3, T3.5, T3.75, etc.
    APPOINTMENT_TYPE_REGEX = r'T(\d+(?:\.\d+)?)'

    # Color mapping
    T2_TYPES = ['2', '2.25', '2.5', '2.75']  # Yellow
    T3_TYPES = ['3', '3.25', '3.5', '3.75']  # Purple

    @classmethod
    def parse_appointment_type(cls, title: str) -> Optional[str]:
        """
        Extract appointment type from event title

        Args:
            title: Event title (e.g., "T2.5 - Max Mustermann")

        Returns:
            Appointment type (e.g., "T2.5") or None
        """
        if not title:
            return None

        match = re.search(cls.APPOINTMENT_TYPE_REGEX, title, re.IGNORECASE)
        if match:
            return f"T{match.group(1)}"
        return None

    @classmethod
    def get_appointment_color(cls, appointment_type: str) -> str:
        """
        Get color for appointment type

        Args:
            appointment_type: Type string (e.g., "T2.5", "T3")

        Returns:
            Color: 'yellow' for T2.x, 'purple' for T3.x, 'gray' for unknown
        """
        if not appointment_type:
            return 'gray'

        # Extract number (e.g., "2.5" from "T2.5")
        match = re.search(r'(\d+(?:\.\d+)?)', appointment_type)
        if not match:
            return 'gray'

        type_number = match.group(1)

        if type_number in cls.T2_TYPES or type_number.startswith('2'):
            return 'yellow'
        elif type_number in cls.T3_TYPES or type_number.startswith('3'):
            return 'purple'
        else:
            return 'gray'

    @classmethod
    def extract_customer_from_title(cls, title: str) -> str:
        """
        Extract customer name from event title

        Args:
            title: Event title (e.g., "T2.5 - Max Mustermann")

        Returns:
            Customer name or original title if no pattern found
        """
        if not title:
            return "Unbekannt"

        # Try to remove T2/T3 prefix
        cleaned = re.sub(cls.APPOINTMENT_TYPE_REGEX, '', title, flags=re.IGNORECASE)

        # Remove common separators
        cleaned = re.sub(r'^[\s\-:]+', '', cleaned)
        cleaned = re.sub(r'[\s\-:]+$', '', cleaned)

        return cleaned.strip() if cleaned.strip() else title

    @classmethod
    def classify_appointment(cls, event: Dict) -> Dict:
        """
        Classify a calendar event

        Args:
            event: Google Calendar event dict

        Returns:
            Dict with: {type, color, customer, description, start, end}
        """
        title = event.get('summary', '')
        description = event.get('description', '')

        # Parse appointment type
        appointment_type = cls.parse_appointment_type(title)
        color = cls.get_appointment_color(appointment_type) if appointment_type else 'gray'
        customer = cls.extract_customer_from_title(title)

        # Get start/end times
        start = event.get('start', {})
        end = event.get('end', {})

        start_time = start.get('dateTime') or start.get('date')
        end_time = end.get('dateTime') or end.get('date')

        return {
            'type': appointment_type or 'Unknown',
            'color': color,
            'customer': customer,
            'description': description,
            'start': start_time,
            'end': end_time,
            'original_title': title
        }

    @classmethod
    def get_events_by_date(cls, events: List[Dict], target_date: str) -> List[Dict]:
        """
        Filter events by date and classify them

        Args:
            events: List of Google Calendar events
            target_date: Date string in YYYY-MM-DD format

        Returns:
            List of classified events for that date
        """
        filtered = []

        for event in events:
            start = event.get('start', {})
            start_time = start.get('dateTime') or start.get('date')

            if not start_time:
                continue

            # Extract date from datetime
            event_date = start_time.split('T')[0] if 'T' in start_time else start_time

            if event_date == target_date:
                classified = cls.classify_appointment(event)
                filtered.append(classified)

        return filtered

    @classmethod
    def get_date_colors(cls, events: List[Dict], date: str) -> List[str]:
        """
        Get all colors for events on a specific date

        Args:
            events: List of Google Calendar events
            date: Date string in YYYY-MM-DD format

        Returns:
            List of unique colors (e.g., ['yellow', 'purple'])
        """
        day_events = cls.get_events_by_date(events, date)
        colors = [e['color'] for e in day_events if e['color'] != 'gray']
        return list(set(colors))  # Unique colors


# Global instance
calendar_parser = T2CalendarParser()
