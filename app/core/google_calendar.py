# -*- coding: utf-8 -*-
"""
Google Calendar API service
Centralized calendar integration with aggressive caching
"""

import pytz
import time
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.utils.credentials import load_google_credentials
from app.config.base import config, slot_config
from app.utils.logging import calendar_logger


class GoogleCalendarService:
    """Singleton service for Google Calendar API interactions with rate limiting"""

    def __init__(self):
        self.service = None
        self.timezone = pytz.timezone(slot_config.TIMEZONE)
        self._event_cache = {}  # Cache: {cache_key: (data, expiry_time)}
        self._cache_duration = 1800  # 30 minutes default cache
        self._rate_limit_delay = 0.5  # 500ms between API calls
        self._last_api_call = 0
        self._daily_quota_used = 0
        self._quota_reset_time = time.time() + 86400  # Reset in 24h
        self._quota_limit = 180  # Conservative limit (90% of 200)
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

    def _check_and_enforce_quota(self) -> bool:
        """Check if we're within quota limits"""
        current_time = time.time()

        # Reset quota counter if 24h passed
        if current_time >= self._quota_reset_time:
            self._daily_quota_used = 0
            self._quota_reset_time = current_time + 86400
            calendar_logger.info("Daily quota counter reset")

        # Check if quota exceeded
        if self._daily_quota_used >= self._quota_limit:
            calendar_logger.error(f"Daily quota limit reached ({self._quota_limit}). Blocking further API calls.")
            return False

        return True

    def _enforce_rate_limit(self):
        """Enforce rate limiting between API calls"""
        current_time = time.time()
        time_since_last_call = current_time - self._last_api_call

        if time_since_last_call < self._rate_limit_delay:
            sleep_time = self._rate_limit_delay - time_since_last_call
            time.sleep(sleep_time)

        self._last_api_call = time.time()

    def _get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate cache key from function name and parameters"""
        import json
        params_str = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
        return f"{func_name}:{params_str}"

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if still valid"""
        if cache_key in self._event_cache:
            data, expiry = self._event_cache[cache_key]
            if time.time() < expiry:
                calendar_logger.debug(f"Cache HIT: {cache_key[:50]}...")
                return data
            else:
                # Expired, remove from cache
                del self._event_cache[cache_key]
                calendar_logger.debug(f"Cache EXPIRED: {cache_key[:50]}...")
        return None

    def _save_to_cache(self, cache_key: str, data: Dict, cache_duration: int = None):
        """Save data to cache with expiry time"""
        if cache_duration is None:
            cache_duration = self._cache_duration
        expiry = time.time() + cache_duration
        self._event_cache[cache_key] = (data, expiry)
        calendar_logger.debug(f"Cache SAVE: {cache_key[:50]}... (expires in {cache_duration}s)")

    def safe_calendar_call(self, func: Callable, *args: Any, cache_duration: int = None, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """
        Wrapper für sichere Google Calendar API-Aufrufe mit:
        - Rate limiting
        - Quota management
        - Retry logic
        - Aggressive caching
        """
        from googleapiclient.errors import HttpError

        # Generate cache key for GET operations
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        is_read_operation = 'list' in func_name or 'get' in func_name

        cache_key = None
        if is_read_operation:
            cache_key = self._get_cache_key(func_name, *args, **kwargs)
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # Check quota before making API call
        if not self._check_and_enforce_quota():
            calendar_logger.error("API call blocked due to quota limit")
            # Return cached data if available, even if expired
            if cache_key and cache_key in self._event_cache:
                data, _ = self._event_cache[cache_key]
                calendar_logger.warning("Returning expired cache due to quota limit")
                return data
            return None

        # Enforce rate limiting
        self._enforce_rate_limit()

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                self._daily_quota_used += 1
                calendar_logger.info(f"Calendar API call successful: {func_name} (quota: {self._daily_quota_used}/{self._quota_limit})")

                # Cache read operations
                if is_read_operation and cache_key:
                    self._save_to_cache(cache_key, result, cache_duration)

                return result
            except HttpError as e:
                if e.resp.status == 429:
                    # Rate limit hit - wait longer
                    wait_time = retry_delay * (2 ** attempt) * 2
                    calendar_logger.warning(f"Rate limit (429) hit, waiting {wait_time}s (attempt {attempt + 1})")
                    time.sleep(wait_time)
                    continue
                elif e.resp.status in [500, 502, 503, 504] and attempt < max_retries - 1:
                    calendar_logger.warning(f"Calendar API HTTP error (attempt {attempt + 1}): {e}")
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

    def get_events(self, calendar_id: str, time_min: str = None, time_max: str = None, max_results: int = None, cache_duration: int = 1800):
        """Get events from calendar with 30min default cache"""
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

        return self.safe_calendar_call(_get_events, cache_duration=cache_duration)

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
            calendar_logger.error(f"Could not initialize Google Calendar service", extra={'error': str(e)})
            return None
    return google_calendar_service