# -*- coding: utf-8 -*-
"""
Feiertags-Service für deutsche NRW-Feiertage und benutzerdefinierte gesperrte Termine
"""

try:
    import holidays
    HOLIDAYS_AVAILABLE = True
except ImportError:
    HOLIDAYS_AVAILABLE = False
    logger.warning("holidays Package nicht verfügbar - Feiertags-Sperrung deaktiviert")
from datetime import datetime, date, timedelta
from typing import Dict, List, Set, Optional, Any
import pytz
import logging

from app.config.base import slot_config

# Logger setup
logger = logging.getLogger(__name__)


TZ = pytz.timezone(slot_config.TIMEZONE)


class HolidayService:
    """Service für Verwaltung deutscher NRW-Feiertage und benutzerdefinierter gesperrter Termine"""

    def __init__(self):
        if HOLIDAYS_AVAILABLE:
            self.german_holidays = holidays.Germany(state='NW')  # Nordrhein-Westfalen
        else:
            self.german_holidays = {}
        self._blocked_dates_cache = None
        self._cache_timestamp = None

    def is_holiday(self, check_date: date) -> bool:
        """Prüft, ob ein Datum ein deutscher NRW-Feiertag ist"""
        if not HOLIDAYS_AVAILABLE:
            return False
        return check_date in self.german_holidays

    def get_holiday_name(self, check_date: date) -> Optional[str]:
        """Gibt den Namen des Feiertags für ein gegebenes Datum zurück"""
        if not HOLIDAYS_AVAILABLE:
            return None
        return self.german_holidays.get(check_date)

    def is_blocked_date(self, check_date: date, check_time: str = None) -> bool:
        """
        Prüft, ob ein Datum (und optional eine Uhrzeit) gesperrt ist

        Args:
            check_date: Das zu prüfende Datum
            check_time: Optional - Uhrzeit im Format "HH:MM" (z.B. "14:30")

        Returns:
            True wenn das Datum (oder die Zeit) gesperrt ist
        """
        # Prüfen ob es ein deutscher NRW-Feiertag ist
        if self.is_holiday(check_date):
            return True

        # Benutzerdefinierte gesperrte Termine prüfen
        blocked_dates = self._get_blocked_dates()
        custom_blocks = blocked_dates.get('custom_blocks', {})
        date_str = check_date.strftime('%Y-%m-%d')

        # Check for full day blocks
        if date_str in custom_blocks:
            block = custom_blocks[date_str]
            if block.get('block_type', 'full_day') == 'full_day':
                return True

        # Check for date range blocks
        for key, block in custom_blocks.items():
            if block.get('block_type') == 'date_range':
                try:
                    start_date = datetime.strptime(block['start_date'], '%Y-%m-%d').date()
                    end_date = datetime.strptime(block['end_date'], '%Y-%m-%d').date()
                    if start_date <= check_date <= end_date:
                        return True
                except (KeyError, ValueError):
                    continue

        # Check for time range blocks (only if check_time is provided)
        if check_time:
            for key, block in custom_blocks.items():
                if block.get('block_type') == 'time_range' and block.get('date') == date_str:
                    try:
                        start_time = block['start_time']
                        end_time = block['end_time']
                        if start_time <= check_time <= end_time:
                            return True
                    except KeyError:
                        continue

        return False

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

    def add_custom_block(self, block_date: date, reason: str, user: str,
                        block_type: str = 'full_day', **kwargs) -> bool:
        """
        Add a custom blocked date with support for different block types

        Args:
            block_date: The date to block (for full_day and time_range)
            reason: Reason for blocking
            user: User who created the block
            block_type: 'full_day', 'time_range', or 'date_range'
            **kwargs: Additional parameters:
                - For time_range: start_time (str), end_time (str)
                - For date_range: end_date (date)
        """
        try:
            blocked_dates = self._get_blocked_dates()

            if 'custom_blocks' not in blocked_dates:
                blocked_dates['custom_blocks'] = {}

            date_str = block_date.strftime('%Y-%m-%d')

            # Base block data
            block_data = {
                'reason': reason,
                'added_by': user,
                'added_at': datetime.now(TZ).isoformat(),
                'block_type': block_type
            }

            # Generate key and add type-specific data
            if block_type == 'full_day':
                key = date_str

            elif block_type == 'time_range':
                start_time = kwargs.get('start_time')
                end_time = kwargs.get('end_time')
                if not start_time or not end_time:
                    logger.error("time_range requires start_time and end_time")
                    return False

                key = f"{date_str}_{start_time}-{end_time}"
                block_data['date'] = date_str
                block_data['start_time'] = start_time
                block_data['end_time'] = end_time

            elif block_type == 'date_range':
                end_date = kwargs.get('end_date')
                if not end_date:
                    logger.error("date_range requires end_date")
                    return False

                end_date_str = end_date.strftime('%Y-%m-%d')
                key = f"range_{date_str}_{end_date_str}"
                block_data['start_date'] = date_str
                block_data['end_date'] = end_date_str

            else:
                logger.error(f"Unknown block_type: {block_type}")
                return False

            blocked_dates['custom_blocks'][key] = block_data
            return self._save_blocked_dates(blocked_dates)

        except Exception as e:
            logger.error(f"Error adding custom block", extra={'error': str(e)})
            return False

    def remove_custom_block(self, block_key: str = None, block_date: date = None) -> bool:
        """
        Remove a custom blocked date by key or date

        Args:
            block_key: The exact key of the block to remove
            block_date: Alternative - remove by date (for backward compatibility)
        """
        try:
            blocked_dates = self._get_blocked_dates()

            if 'custom_blocks' not in blocked_dates:
                return True  # Nothing to remove

            # If key is provided, use it directly
            if block_key:
                if block_key in blocked_dates['custom_blocks']:
                    del blocked_dates['custom_blocks'][block_key]
                    return self._save_blocked_dates(blocked_dates)
                return True  # Already not present

            # Fallback to date-based removal for backward compatibility
            if block_date:
                date_str = block_date.strftime('%Y-%m-%d')
                if date_str in blocked_dates['custom_blocks']:
                    del blocked_dates['custom_blocks'][date_str]
                    return self._save_blocked_dates(blocked_dates)
                return True

            logger.error("Either block_key or block_date must be provided")
            return False

        except Exception as e:
            logger.error(f"Error removing custom block", extra={'error': str(e)})
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

        for block_key, block_info in blocked_dates.get('custom_blocks', {}).items():
            try:
                block_type = block_info.get('block_type', 'full_day')

                if block_type == 'full_day':
                    block_date = datetime.strptime(block_key, '%Y-%m-%d').date()
                    if block_date.year == year:
                        custom_blocks.append({
                            'key': block_key,
                            'date': block_date,
                            'date_str': block_key,
                            'formatted_date': block_date.strftime('%d.%m.%Y'),
                            'name': block_info.get('reason', 'Gesperrt'),
                            'weekday': block_date.strftime('%A'),
                            'type': 'custom',
                            'block_type': 'full_day',
                            'added_by': block_info.get('added_by', 'Unbekannt'),
                            'added_at': block_info.get('added_at', '')
                        })

                elif block_type == 'time_range':
                    block_date = datetime.strptime(block_info['date'], '%Y-%m-%d').date()
                    if block_date.year == year:
                        custom_blocks.append({
                            'key': block_key,
                            'date': block_date,
                            'date_str': block_info['date'],
                            'formatted_date': block_date.strftime('%d.%m.%Y'),
                            'name': block_info.get('reason', 'Gesperrt'),
                            'weekday': block_date.strftime('%A'),
                            'type': 'custom',
                            'block_type': 'time_range',
                            'start_time': block_info.get('start_time', ''),
                            'end_time': block_info.get('end_time', ''),
                            'time_display': f"{block_info.get('start_time', '')} - {block_info.get('end_time', '')}",
                            'added_by': block_info.get('added_by', 'Unbekannt'),
                            'added_at': block_info.get('added_at', '')
                        })

                elif block_type == 'date_range':
                    start_date = datetime.strptime(block_info['start_date'], '%Y-%m-%d').date()
                    end_date = datetime.strptime(block_info['end_date'], '%Y-%m-%d').date()
                    # Include if range overlaps with the year
                    if start_date.year <= year <= end_date.year:
                        custom_blocks.append({
                            'key': block_key,
                            'date': start_date,
                            'date_str': block_info['start_date'],
                            'formatted_date': f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}",
                            'name': block_info.get('reason', 'Gesperrt'),
                            'weekday': f"{start_date.strftime('%A')} - {end_date.strftime('%A')}",
                            'type': 'custom',
                            'block_type': 'date_range',
                            'start_date': block_info['start_date'],
                            'end_date': block_info['end_date'],
                            'days_count': (end_date - start_date).days + 1,
                            'added_by': block_info.get('added_by', 'Unbekannt'),
                            'added_at': block_info.get('added_at', '')
                        })

            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid block entry: {block_key} - {str(e)}")
                continue  # Skip invalid entries

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