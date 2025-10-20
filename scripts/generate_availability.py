# -*- coding: utf-8 -*-
"""
Availability Generator - DIREKTE Google API (kein Cache-Bug!)
Basierend auf bewährter Render-Logik mit direktem API-Zugriff
"""
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

# Load .env file
from dotenv import load_dotenv
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"✅ Loaded environment from {dotenv_path}")
else:
    print(f"⚠️ No .env file found at {dotenv_path}")

# DIRECT Google API - kein GoogleCalendarService!
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.utils.credentials import load_google_credentials

# Konfiguration
TZ = pytz.timezone("Europe/Berlin")

# Berater-Konfiguration aus .env
consultants_str = os.getenv("CONSULTANTS", "")
consultants = {}
for entry in consultants_str.split(','):
    if ':' in entry:
        name, cal_id = entry.split(':', 1)
        consultants[name.strip()] = cal_id.strip()

# Zeitslots pro Wochentag
slots = {
    "Mo": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Di": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Mi": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Do": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Fr": ["09:00", "11:00", "14:00"]
}

weekday_map = {
    'Monday': 'Mo',
    'Tuesday': 'Di',
    'Wednesday': 'Mi',
    'Thursday': 'Do',
    'Friday': 'Fr',
    'Saturday': 'Sa',
    'Sunday': 'So'
}


def init_google_calendar_service():
    """Initialisiere DIREKTE Google Calendar API"""
    try:
        scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        creds = load_google_credentials(scopes)
        service = build('calendar', 'v3', credentials=creds)
        print("✅ Google Calendar API direkt initialisiert (KEIN CACHE!)")
        return service
    except Exception as e:
        print(f"❌ FEHLER beim Initialisieren der Google API: {e}")
        return None


def is_berater_available(service, cal_id, berater_name, slot_start, slot_end):
    """
    Prüfe ob Berater verfügbar ist - DIREKTE API, kein Cache

    Regel: Berater ist verfügbar wenn T1-bereit Event gefunden wird.
    """
    try:
        # DIREKTE API-Abfrage - KEIN CACHE!
        events_result = service.events().list(
            calendarId=cal_id,
            timeMin=slot_start.isoformat(),
            timeMax=slot_end.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=10
        ).execute()

        events = events_result.get('items', [])
        print(f"  📋 {berater_name}: {len(events)} events gefunden")

        # Suche T1-bereit Event
        for event in events:
            summary = event.get('summary', '').strip().lower()

            # T1-bereit gefunden? → Berater verfügbar!
            if 't1' in summary and 'bereit' in summary:
                print(f"  ✅ {berater_name}: T1-bereit gefunden: '{event.get('summary', '')}'")
                return True

        # Kein T1-bereit Event
        if len(events) > 0:
            print(f"  ⚪ {berater_name}: Kein T1-bereit Event ({len(events)} andere Events)")
        else:
            print(f"  ⚪ {berater_name}: Keine Events")
        return False

    except Exception as e:
        print(f"  ❌ {berater_name}: API-Fehler: {e}")
        return False


def backup_availability():
    """Erstelle Backup"""
    backup_dir = "data/persistent/backups"
    os.makedirs(backup_dir, exist_ok=True)

    availability_file = "data/persistent/availability.json"
    if os.path.exists(availability_file):
        backup_name = f"{backup_dir}/availability_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy2(availability_file, backup_name)
        print(f"💾 Backup: {backup_name}")

        # Behalte nur die letzten 7 Backups
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("availability_")])
        for old_backup in backups[:-7]:
            os.remove(os.path.join(backup_dir, old_backup))


def main():
    """Hauptfunktion"""
    availability = {}
    availability_file = "data/persistent/availability.json"
    now = datetime.now(TZ)

    print(f"\n🚀 Availability-Generator (DIREKTE API, kein Cache-Bug!)")
    print(f"🕒 Gestartet: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"👥 {len(consultants)} Berater konfiguriert\n")

    # Sicherstellen dass Verzeichnis existiert
    os.makedirs("data/persistent", exist_ok=True)

    # Google Calendar Service DIREKT initialisieren
    service = init_google_calendar_service()
    if not service:
        print("❌ ABBRUCH: Keine Google API Verbindung")
        return

    # Vorhandene Daten laden
    if os.path.exists(availability_file):
        try:
            with open(availability_file, "r", encoding="utf-8") as f:
                availability = json.load(f)
            print(f"📂 Bestehende Daten geladen ({len(availability)} Einträge)\n")
        except Exception as e:
            print(f"⚠️ Fehler beim Laden: {e}\n")
            availability = {}

    slot_count = 0
    skipped_past = 0

    # Slots für 56 Tage generieren
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

            # Skip vergangene Slots
            if slot_start <= now:
                if slot_key in availability:
                    del availability[slot_key]
                skipped_past += 1
                continue

            # Verfügbare Berater finden
            available = []

            print(f"🔍 Slot: {slot_key}")
            for name, cal_id in consultants.items():
                if is_berater_available(service, cal_id, name, slot_start, slot_end):
                    available.append(name)

            availability[slot_key] = available
            slot_count += 1

            if not available:
                print(f"  🚫 Ergebnis: Keine Berater verfügbar\n")
            else:
                print(f"  ✅ Ergebnis: {len(available)} Berater: {', '.join(available)}\n")

    # Alte Einträge entfernen
    old_count = len(availability)
    availability = {
        k: v for k, v in availability.items()
        if TZ.localize(datetime.strptime(k, "%Y-%m-%d %H:%M")) > now
    }
    removed_count = old_count - len(availability)

    # Datei speichern
    with open(availability_file, "w", encoding="utf-8") as f:
        json.dump(availability, f, ensure_ascii=False, indent=2)

    print(f"✅ Fertig!")
    print(f"📊 Statistik:")
    print(f"   - Analysiert: {slot_count}")
    print(f"   - Übersprungen: {skipped_past}")
    print(f"   - Entfernt: {removed_count}")
    print(f"   - Gespeichert: {len(availability)}")


if __name__ == "__main__":
    start_time = time.time()
    main()
    backup_availability()
    duration = time.time() - start_time
    print(f"⏱️ Laufzeit: {duration:.2f}s")
