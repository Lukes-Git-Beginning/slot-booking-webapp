# -*- coding: utf-8 -*-
import datetime
import os
import json
import time
import shutil
from datetime import datetime, timedelta
import pytz
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(project_root)

# Load .env file explicitly for standalone execution
from dotenv import load_dotenv
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"✅ Loaded environment from {dotenv_path}")
else:
    print(f"⚠️ No .env file found at {dotenv_path}")

from app.core.google_calendar import get_google_calendar_service

# ----------------- Konfiguration -----------------
CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "primary")
TZ = pytz.timezone("Europe/Berlin")

# Google Calendar Farben die NICHT blockieren sollen
# Import vom Hauptverzeichnis (ein Level höher)
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
from app.utils.color_mapping import NON_BLOCKING_COLORS

weekday_map = {
    'Monday': 'Mo',
    'Tuesday': 'Di',
    'Wednesday': 'Mi',
    'Thursday': 'Do',
    'Friday': 'Fr',
    'Saturday': 'Sa',
    'Sunday': 'So'
}

# Import consultant configuration from central config
from app.config.base import ConsultantConfig
consultants = ConsultantConfig.get_consultants()

restricted_slots = {
    # Alle Zeitbeschränkungen entfernt - alle Berater verfügbar zu allen Zeiten
}

slots = {
    "Mo": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Di": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Mi": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Do": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Fr": ["09:00", "11:00", "14:00"]
}

# safe_api_call is now handled by GoogleCalendarService.safe_calendar_call()

def batch_fetch_events(consultant_calendars, start_date, end_date):
    """
    Hole Events für alle Berater mit Caching (30min)
    Nutzt GoogleCalendarService für Quota-Management und Rate-Limiting
    """
    calendar_service = get_google_calendar_service()
    if not calendar_service:
        print("❌ GoogleCalendarService konnte nicht initialisiert werden")
        return {}

    all_events = {}
    cache_duration = 1800  # 30 Minuten Cache

    for name, cal_id in consultant_calendars.items():
        print(f"📅 Hole Events für {name}...")

        # GoogleCalendarService mit Cache nutzen
        result = calendar_service.get_events(
            calendar_id=cal_id,
            time_min=start_date.isoformat(),
            time_max=end_date.isoformat(),
            max_results=2500,
            cache_duration=cache_duration
        )

        if result:
            events = result.get('items', [])
            all_events[name] = events
            print(f"  ✅ {len(events)} Events geladen (Cache: {cache_duration}s)")
        else:
            all_events[name] = []
            print(f"  ⚠️ Keine Events für {name} erhalten")

    # Quota-Status ausgeben
    print(f"\n📊 Quota-Status: {calendar_service._daily_quota_used}/{calendar_service._quota_limit} API-Calls heute")

    return all_events

def is_consultant_available(events, slot_start, slot_end):
    """Prüfe ob Berater verfügbar ist basierend auf Events und Farbcodes"""
    has_t1_bereit = False
    has_blocking_event = False

    for event in events:
        # Parse Event-Zeit
        event_start_str = event.get('start', {}).get('dateTime')
        event_end_str = event.get('end', {}).get('dateTime')

        if not event_start_str or not event_end_str:
            continue

        try:
            event_start = datetime.fromisoformat(event_start_str)
            event_end = datetime.fromisoformat(event_end_str)

            # Prüfe Überschneidung
            if event_start < slot_end and event_end > slot_start:
                summary = event.get('summary', '').strip().lower()
                color_id = event.get('colorId', None)

                # NEUE LOGIK: Erst Farbe prüfen, dann Titel
                # 1. Wenn Color ID in NON_BLOCKING_COLORS, dann ignorieren
                if color_id and str(color_id) in NON_BLOCKING_COLORS:
                    print(f"  ⚪ Non-blocking Event (Farbe {color_id}): '{event.get('summary', '')}'")
                    continue

                # 2. T1-bereit Events erkennen (sowohl Titel als auch ohne blockierende Farbe)
                if 't1' in summary and ('t1-bereit' in summary or 't1 bereit' in summary):
                    has_t1_bereit = True
                    print(f"  ✅ T1-bereit Event gefunden: '{event.get('summary', '')}' (Farbe: {color_id})")
                else:
                    # 3. Alle anderen Events sind blockierend (T2, T2.5, T3, Privat, etc.)
                    has_blocking_event = True
                    print(f"  🚫 Blockierender Event: '{event.get('summary', '')}' (Farbe: {color_id})")

        except Exception as e:
            print(f"⚠️ Fehler beim Parsen von Event: {e}")
            continue

    # Verfügbar nur wenn T1-bereit Event vorhanden UND keine blockierenden Events
    is_available = has_t1_bereit and not has_blocking_event
    if is_available:
        print(f"  ✅ Berater verfügbar (T1-bereit: {has_t1_bereit}, Blockierende Events: {has_blocking_event})")
    else:
        print(f"  🚫 Berater NICHT verfügbar (T1-bereit: {has_t1_bereit}, Blockierende Events: {has_blocking_event})")

    return is_available

def backup_availability():
    """Erstelle tägliches Backup"""
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    if os.path.exists("static/availability.json"):
        backup_name = f"backups/availability_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy2("static/availability.json", backup_name)
        print(f"💾 Backup erstellt: {backup_name}")
        
        # Behalte nur die letzten 7 Backups
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("availability_")])
        for old_backup in backups[:-7]:
            os.remove(os.path.join(backup_dir, old_backup))
            print(f"🗑️ Altes Backup gelöscht: {old_backup}")

def main():
    availability = {}
    availability_file = "static/availability.json"
    now = datetime.now(TZ)  # WICHTIG: Mit Timezone für Uhrzeitvergleich

    print(f"🚀 Availability-Generator gestartet um {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"🔧 Nutzt GoogleCalendarService mit Caching & Quota-Management\n")

    # Vorhandene Verfügbarkeiten laden
    if os.path.exists(availability_file):
        try:
            with open(availability_file, "r", encoding="utf-8") as f:
                availability = json.load(f)
            print(f"✅ Bestehende availability.json geladen ({len(availability)} Einträge)")
        except Exception as e:
            print(f"⚠️ Fehler beim Laden der alten availability.json: {e}")
            availability = {}

    # Zeitraum für Batch-Fetch (56 Tage = 8 Wochen) - aber ab jetzt
    start_date = TZ.localize(datetime.combine(now.date(), datetime.min.time()))
    end_date = start_date + timedelta(days=56)

    # PERFORMANCE-OPTIMIERUNG: Alle Events einmal holen (mit 30min Cache)
    print(f"🚀 Hole alle Events für {len(consultants)} Berater (56 Tage ab jetzt)...")
    print(f"💾 Cache-Dauer: 30 Minuten (reduziert API-Calls drastisch)")
    all_consultant_events = batch_fetch_events(consultants, start_date, end_date)
    
    # Slots analysieren
    print(f"\n📊 Analysiere Slots...")
    print(f"ℹ️ Termine mit Farbe Tomate(11) oder Mandarine(6) werden ignoriert")
    print(f"🕒 Aktuelle Zeit: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"ℹ️ Nur zukünftige Slots werden berücksichtigt\n")
    
    slot_count = 0
    new_slots = 0
    skipped_past = 0
    
    for day_offset in range(56):
        day = now + timedelta(days=day_offset)
        weekday_en = day.strftime('%A')
        weekday = weekday_map.get(weekday_en, None)
        
        if weekday not in slots:
            continue
        
        for time in slots[weekday]:
            start_naive = datetime.strptime(f"{day.strftime('%Y-%m-%d')} {time}", "%Y-%m-%d %H:%M")
            slot_start = TZ.localize(start_naive)
            slot_end = slot_start + timedelta(hours=2)
            slot_key = f"{day.strftime('%Y-%m-%d')} {time}"
            
            # KRITISCHER FIX: Skip vergangene Slots (auch heute!)
            if slot_start <= now:
                if slot_key in availability:
                    del availability[slot_key]  # Entferne vergangene Slots
                skipped_past += 1
                print(f"⏭️ Vergangener Slot übersprungen: {slot_key}")
                continue

            # WICHTIG: Slots werden bei jedem Durchlauf neu berechnet (keine Skip-Logik)
            # Dies stellt sicher, dass Änderungen im Google Calendar sofort reflektiert werden

            available = []
            
            # Prüfe jeden Berater (nutze gecachte Events)
            for name, cal_id in consultants.items():
                # Prüfe Einschränkungen: Wenn ein Berater für bestimmte Uhrzeiten gesperrt ist,
                # dann überspringe genau diese Uhrzeiten für diesen Berater
                if name in restricted_slots and time in restricted_slots[name]:
                    continue
                
                # Nutze die vorher geholten Events
                consultant_events = all_consultant_events.get(name, [])
                
                # Filtere relevante Events für diesen Slot
                relevant_events = [
                    e for e in consultant_events
                    if e.get('start', {}).get('dateTime')
                ]
                
                if is_consultant_available(relevant_events, slot_start, slot_end):
                    available.append(name)
            
            availability[slot_key] = available
            slot_count += 1
            
            if not available:
                print(f"🚫 {slot_key}: Keine Berater verfügbar")
            else:
                print(f"✅ {slot_key}: {len(available)} Berater verfügbar ({', '.join(available)})")
    
    # Alte Einträge entfernen (älter als heute)
    old_count = len(availability)
    today_start = TZ.localize(datetime.combine(now.date(), datetime.min.time()))
    
    availability = {
        k: v for k, v in availability.items()
        if TZ.localize(datetime.strptime(k.split(" ")[0] + " " + k.split(" ")[1], "%Y-%m-%d %H:%M")) > now
    }
    
    removed_count = old_count - len(availability)
    
    # Datei speichern
    os.makedirs("static", exist_ok=True)
    with open(availability_file, "w", encoding="utf-8") as f:
        json.dump(availability, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Fertig!")
    print(f"📊 Statistik:")
    print(f"   - Slots analysiert: {slot_count}")
    print(f"   - Vergangene übersprungen: {skipped_past}")
    print(f"   - Alte entfernt: {removed_count}")
    print(f"   - Gesamt gespeichert: {len(availability)}")
    print(f"🕒 Nur Slots ab {now.strftime('%Y-%m-%d %H:%M')} berücksichtigt")
    print(f"♻️ Alle Slots werden bei jedem Durchlauf neu berechnet (dynamische Updates)")

if __name__ == "__main__":
    start_time = time.time()
    main()
    backup_availability()  # Backup nach erfolgreicher Generierung
    duration = time.time() - start_time
    print(f"⏱️ Laufzeit: {duration:.2f} Sekunden")