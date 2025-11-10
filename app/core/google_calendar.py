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
        self._quota_limit = 5000  # Conservative daily limit (50% of 10,000 Google default)
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
                # Check if it's an SSL error (needs longer retry delay)
                import ssl
                is_ssl_error = isinstance(e, (ssl.SSLError, OSError)) or 'SSL' in str(e)

                if is_ssl_error:
                    wait_time = retry_delay * (2 ** attempt) * 3  # Longer wait for SSL errors
                    calendar_logger.error(f"SSL/Network error in calendar API call: {e}")
                    if attempt < max_retries - 1:
                        calendar_logger.warning(f"Retrying after SSL error, waiting {wait_time}s (attempt {attempt + 1})")
                        # CRITICAL FIX: Reinitialize service after SSL error to reset connection pool
                        try:
                            calendar_logger.info("Reinitializing Google Calendar service after SSL error")
                            self._initialize_service()
                        except Exception as reinit_error:
                            calendar_logger.error(f"Failed to reinitialize service: {reinit_error}")
                        time.sleep(wait_time)
                        continue
                else:
                    calendar_logger.error(f"Unexpected error in calendar API call: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue

                return None

        return None

    def get_events(self, calendar_id: str, time_min: str = None, time_max: str = None, max_results: int = None, cache_duration: int = 1800):
        """Get events from calendar with 30min default cache"""
        if not self.service:
            return None

        def _get_events(cal_id, t_min, t_max, max_res):
            params = {
                'calendarId': cal_id,
                'timeMin': t_min,
                'timeMax': t_max,
                'singleEvents': True,
                'orderBy': 'startTime',
                # CRITICAL: Request description field explicitly!
                'fields': 'items(id,summary,description,start,end,colorId,status),nextPageToken'
            }
            if max_res:
                params['maxResults'] = max_res

            return self.service.events().list(**params).execute()

        return self.safe_calendar_call(_get_events, calendar_id, time_min, time_max, max_results, cache_duration=cache_duration)

    def get_all_events_paginated(self, calendar_id: str, time_min: str = None, time_max: str = None, cache_duration: int = 1800):
        """
        Load ALL events using pagination (no limit).

        This method will loop through all pages returned by the Google Calendar API
        to ensure we get every single event in the time range.

        Args:
            calendar_id: Calendar ID to fetch from
            time_min: ISO 8601 timestamp (e.g., "2025-10-01T00:00:00+01:00")
            time_max: ISO 8601 timestamp (e.g., "2025-12-31T23:59:59+01:00")
            cache_duration: Cache duration in seconds (default: 1800 = 30min)

        Returns:
            dict: {'items': [all_events], 'total_pages': N, 'total_events': N}
        """
        if not self.service:
            calendar_logger.error("Calendar service not initialized")
            return {'items': [], 'total_pages': 0, 'total_events': 0}

        # Check cache first (cache key includes pagination flag)
        cache_key = self._get_cache_key('get_all_events_paginated', calendar_id, time_min, time_max)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            calendar_logger.info(f"PAGINATION: Returning cached data ({cached_data['total_events']} events)")
            return cached_data

        all_events = []
        page_token = None
        page_count = 0
        max_pages = 10  # Safety limit (2500 × 10 = 25,000 events max)

        calendar_logger.info(f"PAGINATION: Starting paginated fetch for {calendar_id} ({time_min} to {time_max})")

        while page_count < max_pages:
            # Check quota before each page
            if not self._check_and_enforce_quota():
                calendar_logger.error(f"PAGINATION: Quota limit reached after {page_count} pages ({len(all_events)} events)")
                break

            # Enforce rate limiting
            self._enforce_rate_limit()

            try:
                params = {
                    'calendarId': calendar_id,
                    'timeMin': time_min,
                    'timeMax': time_max,
                    'maxResults': 2500,  # Max per page
                    'singleEvents': True,
                    'orderBy': 'startTime',
                    'fields': 'items(id,summary,description,start,end,colorId,status),nextPageToken'
                }

                if page_token:
                    params['pageToken'] = page_token

                # Execute API call
                result = self.service.events().list(**params).execute()
                self._daily_quota_used += 1

                # Extract events from this page
                page_events = result.get('items', [])
                all_events.extend(page_events)
                page_count += 1

                calendar_logger.info(f"PAGINATION: Page {page_count} fetched - {len(page_events)} events (total: {len(all_events)})")

                # Check if there's a next page
                page_token = result.get('nextPageToken')
                if not page_token:
                    calendar_logger.info(f"PAGINATION: Completed - No more pages. Total: {len(all_events)} events from {page_count} pages")
                    break

            except HttpError as e:
                if e.resp.status == 429:
                    # Rate limit - wait and retry
                    calendar_logger.warning(f"PAGINATION: Rate limit hit on page {page_count + 1}, waiting 5s")
                    time.sleep(5)
                    continue
                else:
                    calendar_logger.error(f"PAGINATION: HTTP error on page {page_count + 1}: {e}")
                    break
            except Exception as e:
                calendar_logger.error(f"PAGINATION: Unexpected error on page {page_count + 1}: {e}")
                break

        # Build result
        result_data = {
            'items': all_events,
            'total_pages': page_count,
            'total_events': len(all_events)
        }

        # Cache the combined result
        if all_events:
            self._save_to_cache(cache_key, result_data, cache_duration)
            calendar_logger.info(f"PAGINATION: Cached {len(all_events)} events for {cache_duration}s")

        return result_data

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