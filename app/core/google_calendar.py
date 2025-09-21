# -*- coding: utf-8 -*-
"""
Google Calendar API service
Centralized calendar integration
"""

import pytz
from typing import Callable, Any, Optional, Dict
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from creds_loader import load_google_credentials
from app.config.base import config, slot_config
from structured_logger import calendar_logger


class GoogleCalendarService:
    """Singleton service for Google Calendar API interactions"""

    def __init__(self):
        self.service = None
        self.timezone = pytz.timezone(slot_config.TIMEZONE)
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Calendar API service"""
        try:
            creds = load_google_credentials(config.SCOPES)
            self.service = build("calendar", "v3", credentials=creds)
            calendar_logger.info("Google Calendar service initialized successfully")
        except Exception as e:
            calendar_logger.error(f"Failed to initialize Google Calendar service: {e}")
            raise

    def safe_calendar_call(self, func: Callable, *args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """
        Wrapper für sichere Google Calendar API-Aufrufe mit Retry-Logik
        Migrated from original slot_booking_webapp.py
        """
        import time
        from googleapiclient.errors import HttpError

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                calendar_logger.debug(f"Calendar API call successful: {func.__name__}")
                return result
            except HttpError as e:
                calendar_logger.warning(f"Calendar API HTTP error (attempt {attempt + 1}): {e}")
                if e.resp.status in [500, 502, 503, 504] and attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    calendar_logger.error(f"Calendar API call failed permanently: {e}")
                    return None
            except Exception as e:
                calendar_logger.error(f"Unexpected error in calendar API call: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    return None

        return None

    def get_events(self, calendar_id: str, time_min: str = None, time_max: str = None, max_results: int = None):
        """Get events from calendar"""
        if not self.service:
            return None

        def _get_events():
            params = {
                'calendarId': calendar_id,
                'timeMin': time_min,
                'timeMax': time_max,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            if max_results:
                params['maxResults'] = max_results

            return self.service.events().list(**params).execute()

        return self.safe_calendar_call(_get_events)

    def create_event(self, calendar_id: str, event_data: dict):
        """Create a new calendar event"""
        if not self.service:
            return None

        def _create_event():
            return self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()

        return self.safe_calendar_call(_create_event)

    def update_event(self, calendar_id: str, event_id: str, event_data: dict):
        """Update an existing calendar event"""
        if not self.service:
            return None

        def _update_event():
            return self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event_data
            ).execute()

        return self.safe_calendar_call(_update_event)

    def delete_event(self, calendar_id: str, event_id: str):
        """Delete a calendar event"""
        if not self.service:
            return None

        def _delete_event():
            return self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

        return self.safe_calendar_call(_delete_event)


# Global instance - lazy-loaded
google_calendar_service = None


def get_google_calendar_service():
    """Get or create Google Calendar service instance"""
    global google_calendar_service
    if google_calendar_service is None:
        try:
            google_calendar_service = GoogleCalendarService()
        except Exception as e:
            print(f"WARNING: Could not initialize Google Calendar service: {e}")
            return None
    return google_calendar_service