# -*- coding: utf-8 -*-
"""
T2 Dynamic 2-Hour Availability Service

Scannt Google Calendar für freie 2-Stunden-Slots in 30-Minuten-Schritten (Mo-Fr, 8-20 Uhr).
Nur nicht-überlappende Slots werden zurückgegeben, gruppiert nach Tageszeit.

=== ON-DEMAND SCANNING STRATEGY ===

Das System scannt NICHT via Cronjob, sondern nur wenn User aktiv bucht:

1. Step 2 (Monats-Kalender):
   - API: /t2/api/month-availability/<berater>/<year>/<month>
   - Funktion: get_month_availability()
   - Scannt alle Tage im Monat (max 31 Tage, nur Mo-Fr)
   - Cache: 10 Minuten pro Tag
   - Google API Calls: ~22 (Arbeitstage pro Monat)

2. Step 3 (Zeitslot-Auswahl):
   - API: /t2/api/day-slots/<berater>/<date>
   - Funktion: find_2h_slots_non_overlapping()
   - Scannt einen Tag (1 API-Call)
   - Cache: 10 Minuten
   - Google API Calls: 1

3. Buchung (Live-Check):
   - API: /t2/api/book-2h-slot
   - Funktion: is_2h_slot_free()
   - Live-Check OHNE Cache (verhindert Race Conditions!)
   - Google API Calls: 1

VORTEILE gegenüber Cronjob-Ansatz:
✅ Keine unnötigen API-Calls wenn niemand bucht
✅ Immer aktuelle Daten bei finaler Buchung (Live-Check)
✅ Reduziert Google Calendar Quota-Usage signifikant
✅ Skaliert automatisch mit User-Last
✅ Kein Server-Overhead für Background-Jobs

CACHE-INVALIDIERUNG:
- Automatisch nach 10 Minuten
- Manuell nach erfolgreicher Buchung (clear_cache_for_berater)
- Optional: Admin-Funktion zum kompletten Cache-Clear

QUOTA-USAGE Beispiel (1 Buchung):
- Monat-Scan: ~22 API-Calls (gecached 10 Min)
- Tag-Scan: 1 API-Call (gecached 10 Min)
- Live-Check: 1 API-Call (kein Cache)
- Total: ~24 API-Calls pro Buchung
- Google Limit: 10,000/Tag → ~416 Buchungen/Tag möglich
"""

import logging
from datetime import datetime, time, timedelta, date
from typing import Dict, List, Optional, Tuple
from dateutil import parser
import pytz
from app.core.google_calendar import GoogleCalendarService
from app.core.extensions import cache_manager

logger = logging.getLogger(__name__)


class T2DynamicAvailability:
    """
    Service für dynamische 2h-Verfügbarkeits-Scans.

    Features:
    - 30-Minuten-Schritte (8:00, 8:30, 9:00, ..., 18:00)
    - Nur nicht-überlappende Slots
    - Gruppierung: Vormittag (8-12), Mittag (12-16), Abend (16-20)
    - 10-Minuten Cache pro Tag
    """

    def __init__(self):
        self.calendar_service = GoogleCalendarService()
        self.timezone = pytz.timezone('Europe/Berlin')
        self.cache_duration = 600  # 10 Minuten Cache

        # Arbeitszeiten
        self.work_start_hour = 8
        self.work_end_hour = 20
        self.slot_duration_hours = 2
        self.step_minutes = 30  # Schritte in 30-Minuten

        # Gruppierungs-Schwellwerte (Ende-Zeit des Slots)
        self.morning_end = 12  # Vormittag: Slots die vor 12:00 enden
        self.midday_end = 16   # Mittag: Slots die vor 16:00 enden
        # Abend: Rest (bis 20:00)

    def _get_cache_key(self, calendar_id: str, check_date: date) -> str:
        """Generiert Cache-Key für Tag-Verfügbarkeit"""
        return f"t2_2h_avail_{calendar_id}_{check_date.isoformat()}_v2"

    def _parse_event_times(self, event: dict) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Parst Event-Zeiten aus Google Calendar Event.

        Returns:
            (start_dt, end_dt) oder (None, None) bei Fehler
        """
        try:
            start_str = event.get('start', {}).get('dateTime')
            end_str = event.get('end', {}).get('dateTime')

            if not start_str or not end_str:
                # Ganztags-Event, blockiert gesamten Tag
                return (
                    datetime.combine(date.today(), time(self.work_start_hour, 0)),
                    datetime.combine(date.today(), time(self.work_end_hour, 0))
                )

            start_dt = parser.isoparse(start_str).astimezone(self.timezone)
            end_dt = parser.isoparse(end_str).astimezone(self.timezone)

            return (start_dt, end_dt)

        except Exception as e:
            logger.error(f"Error parsing event times: {e}")
            return (None, None)

    def _check_slot_overlap(
        self,
        slot_start: datetime,
        slot_end: datetime,
        events: List[dict]
    ) -> bool:
        """
        Prüft ob 2h-Slot mit existierenden Events überlappt.

        Args:
            slot_start: Start des zu prüfenden Slots
            slot_end: Ende des zu prüfenden Slots (slot_start + 2h)
            events: Liste von Google Calendar Events

        Returns:
            True wenn Slot frei ist, False wenn Überlappung existiert
        """
        for event in events:
            # Skip cancelled events
            if event.get('status') == 'cancelled':
                continue

            event_start, event_end = self._parse_event_times(event)

            if event_start is None or event_end is None:
                continue

            # Überlappungs-Check:
            # Slots überlappen wenn NICHT (slot_end <= event_start ODER slot_start >= event_end)
            if not (slot_end <= event_start or slot_start >= event_end):
                logger.debug(
                    f"Slot {slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')} "
                    f"überlappt mit Event {event.get('summary', 'Unknown')} "
                    f"({event_start.strftime('%H:%M')}-{event_end.strftime('%H:%M')})"
                )
                return False

        return True

    def _categorize_slot(self, slot_time_str: str) -> str:
        """
        Kategorisiert Slot nach Tageszeit basierend auf ENDE-Zeit.

        Args:
            slot_time_str: Start-Zeit als String (z.B. "08:00")

        Returns:
            "morning", "midday" oder "evening"
        """
        hour, minute = map(int, slot_time_str.split(':'))
        end_hour = hour + self.slot_duration_hours

        if end_hour <= self.morning_end:
            return "morning"
        elif end_hour <= self.midday_end:
            return "midday"
        else:
            return "evening"

    def find_2h_slots_non_overlapping(
        self,
        calendar_id: str,
        check_date: date
    ) -> Dict[str, List[str]]:
        """
        Findet alle freien 2h-Slots für einen Tag (nicht-überlappend).

        Algorithmus:
        1. Lade alle Events für Tag (8-20 Uhr)
        2. Iteriere durch alle möglichen Startzeiten (30-Min-Schritte)
        3. Prüfe ob 2h-Fenster komplett frei
        4. Wenn frei: Füge Slot hinzu UND springe 2h weiter (keine Überlappung!)
        5. Wenn belegt: Springe nur 30min weiter
        6. Gruppiere Slots nach Tageszeit

        Args:
            calendar_id: Google Calendar ID des Beraters
            check_date: Datum zum Prüfen

        Returns:
            {
                "morning": ["08:00", "10:30"],
                "midday": ["12:00", "14:00"],
                "evening": ["16:30", "18:00"]
            }
        """
        # Cache prüfen
        cache_key = self._get_cache_key(calendar_id, check_date)
        cached = cache_manager.get(cache_key)
        if cached is not None:
            logger.info(f"Cache HIT: {cache_key}")
            return cached

        logger.info(f"Scanning 2h availability for {calendar_id} on {check_date}")

        # Zeitfenster definieren (8-20 Uhr in Berlin-Zeit)
        day_start = datetime.combine(check_date, time(self.work_start_hour, 0))
        day_start = self.timezone.localize(day_start)

        day_end = datetime.combine(check_date, time(self.work_end_hour, 0))
        day_end = self.timezone.localize(day_end)

        # Events für Tag laden
        time_min = day_start.isoformat()
        time_max = day_end.isoformat()

        response = self.calendar_service.get_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            cache_duration=self.cache_duration
        )

        if response is None:
            logger.error(f"Failed to fetch events for {calendar_id}")
            return {"morning": [], "midday": [], "evening": []}

        events = response.get('items', [])
        logger.info(f"Found {len(events)} events for {check_date}")

        # Freie Slots finden (nicht-überlappend)
        slots = []
        current = day_start

        while current <= day_end - timedelta(hours=self.slot_duration_hours):
            slot_end = current + timedelta(hours=self.slot_duration_hours)

            # Prüfe ob 2h-Fenster komplett frei
            if self._check_slot_overlap(current, slot_end, events):
                time_str = current.strftime("%H:%M")
                slots.append(time_str)
                logger.debug(f"✓ Free slot found: {time_str} - {slot_end.strftime('%H:%M')}")

                # WICHTIG: Spring 2h weiter um Überlappung zu vermeiden!
                current += timedelta(hours=self.slot_duration_hours)
            else:
                # Slot belegt, nur 30min weiter
                current += timedelta(minutes=self.step_minutes)

        # Gruppieren nach Tageszeit
        grouped = {
            "morning": [],
            "midday": [],
            "evening": []
        }

        for slot_time in slots:
            category = self._categorize_slot(slot_time)
            grouped[category].append(slot_time)

        logger.info(
            f"Scan complete: {len(slots)} total slots "
            f"(morning: {len(grouped['morning'])}, "
            f"midday: {len(grouped['midday'])}, "
            f"evening: {len(grouped['evening'])})"
        )

        # Cache speichern
        cache_manager.set(cache_key, grouped, timeout=self.cache_duration)

        return grouped

    def get_month_availability(
        self,
        calendar_id: str,
        year: int,
        month: int
    ) -> Dict[str, int]:
        """
        Scannt Verfügbarkeit für ganzen Monat.

        Args:
            calendar_id: Google Calendar ID
            year: Jahr (z.B. 2025)
            month: Monat (1-12)

        Returns:
            {
                "2025-11-25": 3,  # 3 freie Slots
                "2025-11-26": 1,  # 1 freier Slot
                ...
            }
        """
        logger.info(f"Scanning month availability: {year}-{month:02d}")

        availability = {}

        # Alle Tage im Monat durchgehen (max 31)
        for day in range(1, 32):
            try:
                check_date = date(year, month, day)

                # Skip Wochenende (Samstag=5, Sonntag=6)
                if check_date.weekday() >= 5:
                    continue

                # Scan Tag
                slots = self.find_2h_slots_non_overlapping(calendar_id, check_date)
                total_slots = len(slots['morning']) + len(slots['midday']) + len(slots['evening'])

                if total_slots > 0:
                    availability[check_date.isoformat()] = total_slots

            except ValueError:
                # Ungültiger Tag (z.B. 31. Februar)
                continue

        logger.info(f"Month scan complete: {len(availability)} days with availability")
        return availability

    def is_2h_slot_free(
        self,
        calendar_id: str,
        check_date: date,
        time_str: str
    ) -> bool:
        """
        Live-Check ob spezifischer 2h-Slot noch frei ist.

        WICHTIG: Wird vor Buchung aufgerufen um Doppelbuchungen zu vermeiden!

        Args:
            calendar_id: Google Calendar ID
            check_date: Datum
            time_str: Start-Zeit als String (z.B. "14:00")

        Returns:
            True wenn Slot frei, False sonst
        """
        logger.info(f"Live-Check: {calendar_id} on {check_date} at {time_str}")

        # Parse Zeit
        try:
            hour, minute = map(int, time_str.split(':'))
            slot_start = datetime.combine(check_date, time(hour, minute))
            slot_start = self.timezone.localize(slot_start)
            slot_end = slot_start + timedelta(hours=self.slot_duration_hours)
        except Exception as e:
            logger.error(f"Invalid time format '{time_str}': {e}")
            return False

        # Events laden (KEIN Cache für Live-Check!)
        time_min = slot_start.isoformat()
        time_max = slot_end.isoformat()

        response = self.calendar_service.get_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            cache_duration=0  # Kein Cache!
        )

        if response is None:
            logger.error("Failed to fetch events for live check")
            return False

        events = response.get('items', [])

        # Prüfe Überlappung
        is_free = self._check_slot_overlap(slot_start, slot_end, events)

        logger.info(f"Live-Check result: {'FREE' if is_free else 'BLOCKED'}")
        return is_free

    def clear_cache_for_berater(self, calendar_id: str, check_date: date):
        """
        Löscht Cache für spezifischen Berater + Datum.

        Wird nach Buchung aufgerufen um Cache zu invalidieren.
        """
        cache_key = self._get_cache_key(calendar_id, check_date)
        cache_manager.delete(cache_key)
        logger.info(f"Cache cleared: {cache_key}")


# Singleton-Instanz
t2_dynamic_availability = T2DynamicAvailability()
