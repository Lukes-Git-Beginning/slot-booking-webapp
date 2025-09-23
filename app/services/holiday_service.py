# -*- coding: utf-8 -*-
"""
Holiday service for German NRW holidays and custom blocked dates
"""

try:
    import holidays
    HOLIDAYS_AVAILABLE = True
except ImportError:
    HOLIDAYS_AVAILABLE = False
    print("WARNING: holidays package not available - holiday blocking disabled")
from datetime import datetime, date, timedelta
from typing import Dict, List, Set, Optional, Any
import pytz

from app.config.base import slot_config


TZ = pytz.timezone(slot_config.TIMEZONE)


class HolidayService:
    """Service for managing German NRW holidays and custom blocked dates"""

    def __init__(self):
        if HOLIDAYS_AVAILABLE:
            self.german_holidays = holidays.Germany(state='NW')  # Nordrhein-Westfalen
        else:
            self.german_holidays = {}
        self._blocked_dates_cache = None
        self._cache_timestamp = None

    def is_holiday(self, check_date: date) -> bool:
        """Check if a date is a German NRW holiday"""
        if not HOLIDAYS_AVAILABLE:
            return False
        return check_date in self.german_holidays

    def get_holiday_name(self, check_date: date) -> Optional[str]:
        """Get the name of the holiday for a given date"""
        if not HOLIDAYS_AVAILABLE:
            return None
        return self.german_holidays.get(check_date)

    def is_blocked_date(self, check_date: date) -> bool:
        """Check if a date is blocked (holiday or custom block)"""
        # Check if it's a German NRW holiday
        if self.is_holiday(check_date):
            return True

        # Check custom blocked dates
        blocked_dates = self._get_blocked_dates()
        date_str = check_date.strftime('%Y-%m-%d')
        return date_str in blocked_dates.get('custom_blocks', {})

    def get_blocked_reason(self, check_date: date) -> Optional[str]:
        """Get the reason why a date is blocked"""
        # Check holidays first
        holiday_name = self.get_holiday_name(check_date)
        if holiday_name:
            return f"Feiertag: {holiday_name}"

        # Check custom blocks
        blocked_dates = self._get_blocked_dates()
        date_str = check_date.strftime('%Y-%m-%d')
        custom_blocks = blocked_dates.get('custom_blocks', {})

        if date_str in custom_blocks:
            return custom_blocks[date_str].get('reason', 'Gesperrt')

        return None

    def add_custom_block(self, block_date: date, reason: str, user: str) -> bool:
        """Add a custom blocked date"""
        try:
            blocked_dates = self._get_blocked_dates()

            if 'custom_blocks' not in blocked_dates:
                blocked_dates['custom_blocks'] = {}

            date_str = block_date.strftime('%Y-%m-%d')
            blocked_dates['custom_blocks'][date_str] = {
                'reason': reason,
                'added_by': user,
                'added_at': datetime.now(TZ).isoformat()
            }

            return self._save_blocked_dates(blocked_dates)

        except Exception as e:
            print(f"Error adding custom block: {e}")
            return False

    def remove_custom_block(self, block_date: date) -> bool:
        """Remove a custom blocked date"""
        try:
            blocked_dates = self._get_blocked_dates()

            if 'custom_blocks' not in blocked_dates:
                return True  # Nothing to remove

            date_str = block_date.strftime('%Y-%m-%d')
            if date_str in blocked_dates['custom_blocks']:
                del blocked_dates['custom_blocks'][date_str]
                return self._save_blocked_dates(blocked_dates)

            return True  # Already not present

        except Exception as e:
            print(f"Error removing custom block: {e}")
            return False

    def get_upcoming_holidays(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get upcoming holidays within the next N days"""
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        upcoming = []
        current = today

        while current <= end_date:
            if self.is_holiday(current):
                upcoming.append({
                    'date': current,
                    'date_str': current.strftime('%Y-%m-%d'),
                    'formatted_date': current.strftime('%d.%m.%Y'),
                    'name': self.get_holiday_name(current),
                    'weekday': current.strftime('%A'),
                    'days_until': (current - today).days
                })
            current += timedelta(days=1)

        return upcoming

    def get_blocked_dates_overview(self, year: int = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get overview of all blocked dates for a year"""
        if year is None:
            year = datetime.now(TZ).year

        # Get holidays for the year
        year_holidays = []
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        current = start_date
        while current <= end_date:
            if self.is_holiday(current):
                year_holidays.append({
                    'date': current,
                    'date_str': current.strftime('%Y-%m-%d'),
                    'formatted_date': current.strftime('%d.%m.%Y'),
                    'name': self.get_holiday_name(current),
                    'weekday': current.strftime('%A'),
                    'type': 'holiday'
                })
            current += timedelta(days=1)

        # Get custom blocks for the year
        blocked_dates = self._get_blocked_dates()
        custom_blocks = []

        for date_str, block_info in blocked_dates.get('custom_blocks', {}).items():
            try:
                block_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if block_date.year == year:
                    custom_blocks.append({
                        'date': block_date,
                        'date_str': date_str,
                        'formatted_date': block_date.strftime('%d.%m.%Y'),
                        'name': block_info.get('reason', 'Gesperrt'),
                        'weekday': block_date.strftime('%A'),
                        'type': 'custom',
                        'added_by': block_info.get('added_by', 'Unbekannt'),
                        'added_at': block_info.get('added_at', '')
                    })
            except ValueError:
                continue  # Skip invalid dates

        # Sort both lists by date
        year_holidays.sort(key=lambda x: x['date'])
        custom_blocks.sort(key=lambda x: x['date'])

        return {
            'holidays': year_holidays,
            'custom_blocks': custom_blocks,
            'year': year
        }

    def _get_blocked_dates(self) -> Dict[str, Any]:
        """Load blocked dates with caching"""
        # Simple caching to avoid frequent file reads
        now = datetime.now()
        if (self._blocked_dates_cache is None or
            self._cache_timestamp is None or
            (now - self._cache_timestamp).seconds > 300):  # 5 min cache

            # Import here to avoid circular imports
            from app.core.extensions import data_persistence
            if data_persistence:
                self._blocked_dates_cache = data_persistence.load_data('blocked_dates', {})
            else:
                # Fallback to empty if data_persistence not available
                self._blocked_dates_cache = {}
            self._cache_timestamp = now

        return self._blocked_dates_cache

    def _save_blocked_dates(self, blocked_dates: Dict[str, Any]) -> bool:
        """Save blocked dates and clear cache"""
        # Import here to avoid circular imports
        from app.core.extensions import data_persistence
        if not data_persistence:
            return False

        success = data_persistence.save_data('blocked_dates', blocked_dates)
        if success:
            # Clear cache to force reload
            self._blocked_dates_cache = None
            self._cache_timestamp = None
        return success


# Global instance
holiday_service = HolidayService()