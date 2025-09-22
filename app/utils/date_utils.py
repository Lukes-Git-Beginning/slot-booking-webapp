# -*- coding: utf-8 -*-
"""
Date Utilities für Slot Booking Webapp
- Zentrale Datums-Formatierung
- Konsistente Zeitstempel
- Zeitzonen-Handling
"""

import pytz
from datetime import datetime, timedelta
from typing import Union, Optional

# Zentrale Zeitzone
TZ = pytz.timezone("Europe/Berlin")

class DateFormatter:
    """Zentrale Klasse für Datums-Formatierung"""
    
    @staticmethod
    def now() -> datetime:
        """Aktuelle Zeit in Berlin-Zeitzone"""
        return datetime.now(TZ)
    
    @staticmethod
    def today() -> datetime:
        """Heute in Berlin-Zeitzone"""
        return datetime.now(TZ).date()
    
    @staticmethod
    def format_date(date_obj: Union[datetime, str], format_str: str = "%Y-%m-%d") -> str:
        """Formatiert ein Datum konsistent"""
        if isinstance(date_obj, str):
            try:
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_obj, "%Y-%m-%d %H:%M")
                except ValueError:
                    raise ValueError(f"Unbekanntes Datumsformat: {date_obj}")
        
        if date_obj.tzinfo is None:
            date_obj = TZ.localize(date_obj)
        
        return date_obj.strftime(format_str)
    
    @staticmethod
    def parse_date(date_str: str, format_str: str = "%Y-%m-%d") -> datetime:
        """Parst ein Datum konsistent"""
        try:
            date_obj = datetime.strptime(date_str, format_str)
            if date_obj.tzinfo is None:
                date_obj = TZ.localize(date_obj)
            return date_obj
        except ValueError as e:
            raise ValueError(f"Fehler beim Parsen von '{date_str}': {e}")
    
    @staticmethod
    def format_datetime(datetime_obj: Union[datetime, str], format_str: str = "%Y-%m-%d %H:%M") -> str:
        """Formatiert eine DateTime konsistent"""
        if isinstance(datetime_obj, str):
            datetime_obj = DateFormatter.parse_datetime(datetime_obj)
        
        if datetime_obj.tzinfo is None:
            datetime_obj = TZ.localize(datetime_obj)
        
        return datetime_obj.strftime(format_str)
    
    @staticmethod
    def parse_datetime(datetime_str: str, format_str: str = "%Y-%m-%d %H:%M") -> datetime:
        """Parst eine DateTime konsistent"""
        try:
            datetime_obj = datetime.strptime(datetime_str, format_str)
            if datetime_obj.tzinfo is None:
                datetime_obj = TZ.localize(datetime_obj)
            return datetime_obj
        except ValueError as e:
            raise ValueError(f"Fehler beim Parsen von '{datetime_str}': {e}")
    
    @staticmethod
    def get_week_start(date_obj: Union[datetime, str]) -> datetime:
        """Gibt den Montag der Woche zurück"""
        if isinstance(date_obj, str):
            date_obj = DateFormatter.parse_date(date_obj)
        
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        monday = date_obj - timedelta(days=date_obj.weekday())
        return datetime.combine(monday, datetime.min.time())
    
    @staticmethod
    def get_week_end(date_obj: Union[datetime, str]) -> datetime:
        """Gibt den Sonntag der Woche zurück"""
        if isinstance(date_obj, str):
            date_obj = DateFormatter.parse_date(date_obj)
        
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        sunday = date_obj + timedelta(days=6-date_obj.weekday())
        return datetime.combine(sunday, datetime.max.time())
    
    @staticmethod
    def get_month_start(date_obj: Union[datetime, str]) -> datetime:
        """Gibt den ersten Tag des Monats zurück"""
        if isinstance(date_obj, str):
            date_obj = DateFormatter.parse_date(date_obj)
        
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        month_start = date_obj.replace(day=1)
        return datetime.combine(month_start, datetime.min.time())
    
    @staticmethod
    def get_month_end(date_obj: Union[datetime, str]) -> datetime:
        """Gibt den letzten Tag des Monats zurück"""
        if isinstance(date_obj, str):
            date_obj = DateFormatter.parse_date(date_obj)
        
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        if date_obj.month == 12:
            next_month = date_obj.replace(year=date_obj.year + 1, month=1, day=1)
        else:
            next_month = date_obj.replace(month=date_obj.month + 1, day=1)
        
        month_end = next_month - timedelta(days=1)
        return datetime.combine(month_end, datetime.max.time())
    
    @staticmethod
    def format_week_key(date_obj: Union[datetime, str]) -> str:
        """Formatiert einen Wochen-Schlüssel (YYYY-KWXX)"""
        if isinstance(date_obj, str):
            date_obj = DateFormatter.parse_date(date_obj)
        
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        year, week, _ = date_obj.isocalendar()
        return f"{year}-KW{week:02d}"
    
    @staticmethod
    def format_month_key(date_obj: Union[datetime, str]) -> str:
        """Formatiert einen Monats-Schlüssel (YYYY-MM)"""
        if isinstance(date_obj, str):
            date_obj = DateFormatter.parse_date(date_obj)
        
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        return f"{date_obj.year}-{date_obj.month:02d}"
    
    @staticmethod
    def is_same_day(date1: Union[datetime, str], date2: Union[datetime, str]) -> bool:
        """Prüft ob zwei Daten am gleichen Tag sind"""
        if isinstance(date1, str):
            date1 = DateFormatter.parse_date(date1)
        if isinstance(date2, str):
            date2 = DateFormatter.parse_date(date2)
        
        if isinstance(date1, datetime):
            date1 = date1.date()
        if isinstance(date2, datetime):
            date2 = date2.date()
        
        return date1 == date2
    
    @staticmethod
    def days_between(date1: Union[datetime, str], date2: Union[datetime, str]) -> int:
        """Berechnet die Tage zwischen zwei Daten"""
        if isinstance(date1, str):
            date1 = DateFormatter.parse_date(date1)
        if isinstance(date2, str):
            date2 = DateFormatter.parse_date(date2)
        
        if isinstance(date1, datetime):
            date1 = date1.date()
        if isinstance(date2, datetime):
            date2 = date2.date()
        
        return (date2 - date1).days

# Globale Instanz
date_formatter = DateFormatter()
