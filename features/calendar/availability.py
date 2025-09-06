# -*- coding: utf-8 -*-
import datetime
import os
import json
import time
import shutil
from datetime import datetime, timedelta
import pytz
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from core.auth.credentials import load_google_credentials

# ----------------- Google Calendar API Setup -----------------
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
creds = load_google_credentials(SCOPES)
service = build("calendar", "v3", credentials=creds)

# ----------------- Konfiguration -----------------
CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "primary")
TZ = pytz.timezone("Europe/Berlin")

# Google Calendar Farben die NICHT blockieren sollen
from core.mapping.colors import NON_BLOCKING_COLORS

weekday_map = {
    'Monday': 'Mo',
    'Tuesday': 'Di',
    'Wednesday': 'Mi',
    'Thursday': 'Do',
    'Friday': 'Fr',
    'Saturday': 'Sa',
    'Sunday': 'So'
}

consultants = {
    "Daniel": "daniel.herbort.zfa@gmail.com",
    "Simon": "simonmast9@gmail.com",
    "Ann-Kathrin": "a.welge.zfa@gmail.com",
    "Christian": "chmast95@gmail.com",
    "Tim": "tim.kreisel71@gmail.com",
    "Sara": "mastsara2@gmail.com",
    "Patrick": "0d5nq65ogpekomad34ti234h1g@group.calendar.google.com",
    "Dominik": "mikic.dom@gmail.com"
}

restricted_slots = {
    "Simon": ["20:00"],
}

slots = {
    "Mo": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Di": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Mi": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Do": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Fr": ["09:00", "11:00", "14:00"]
}

def safe_api_call(func, *args, **kwargs):
    """
    API-Call mit Retry-Logik, Error Handling und auto-execute() für Google-Requests.
    Gibt bei Erfolg immer ein dict (execute()-Result) zurück, sonst None.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req_or_result = func(*args, **kwargs)
            if hasattr(req_or_result, "execute") and callable(req_or_result.execute):
                return req_or_result.execute()
            return req_or_result
        except HttpError as e:
            status = getattr(getattr(e, "resp", None), "status", None)
            if status == 429:
                wait_time = (2 ** attempt) * 2
                print(f"⏳ Rate limit erreicht, warte {wait_time}s …")
                time.sleep(wait_time)
                continue
            if status and status >= 500:
                wait_time = 2 ** attempt
                print(f"⚠️ Server-Fehler {status}, Retry in {wait_time}s …")
                time.sleep(wait_time)
                continue
            print(f"❌ API-Fehler: {e}")
            return None
        except Exception as e:
            print(f"❌ Unerwarteter Fehler: {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt)
    return None

def batch_fetch_events(consultant_calendars, start_date, end_date):
    """Hole Events für alle Berater in einem optimierten Batch"""
    all_events = {}
    
    for name, cal_id in consultant_calendars.items():
        print(f"📅 Hole Events für {name}...")
        result = safe_api_call(
            service.events().list,
            calendarId=cal_id,
            timeMin=start_date.isoformat(),
            timeMax=end_date.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500
        )
        
        if result:
            all_events[name] = result.get('items', [])
        else:
            all_events[name] = []
            print(f"⚠️ Keine Events für {name} erhalten")
    
    return all_events

def is_consultant_available(events, slot_start, slot_end):
    """Prüfe ob Berater verfügbar ist basierend auf Events"""
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
                color_id = event.get('colorId', '')
                
                # NEU: Termine mit Tomate(11) oder Mandarine(6) blockieren NICHT
                if color_id in NON_BLOCKING_COLORS:
                    print(f"  🟠 Ignoriere Event (Farbe {color_id}): '{event.get('summary', '')}'")
                    continue  # Diesen Termin ignorieren, weiter zum nächsten
                
                # Berater ist verfügbar wenn "t1-bereit" im Titel
                if 't1-bereit' in summary or 't1 bereit' in summary:
                    return True
                else:
                    # Konflikt gefunden
                    return False
        except Exception as e:
            print(f"⚠️ Fehler beim Parsen von Event: {e}")
            continue
    
    # Keine blockierenden Konflikte = nicht verfügbar (kein t1-bereit Event)
    return False

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
    
    # Vorhandene Verfügbarkeiten laden
    if os.path.exists(availability_file):
        try:
            with open(availability_file, "r", encoding="utf-8") as f:
                availability = json.load(f)
            print(f"✅ Bestehende availability.json geladen ({len(availability)} Einträge)")
        except Exception as e:
            print(f"⚠️ Fehler beim Laden der alten availability.json: {e}")
            availability = {}
    
    # Zeitraum für Batch-Fetch (30 Tage) - aber ab jetzt
    start_date = TZ.localize(datetime.combine(now.date(), datetime.min.time()))
    end_date = start_date + timedelta(days=30)
    
    # PERFORMANCE-OPTIMIERUNG: Alle Events einmal holen
    print(f"\n🚀 Hole alle Events für {len(consultants)} Berater (30 Tage ab jetzt)...")
    all_consultant_events = batch_fetch_events(consultants, start_date, end_date)
    
    # Slots analysieren
    print(f"\n📊 Analysiere Slots...")
    print(f"ℹ️ Termine mit Farbe Tomate(11) oder Mandarine(6) werden ignoriert")
    print(f"🕒 Aktuelle Zeit: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"ℹ️ Nur zukünftige Slots werden berücksichtigt\n")
    
    slot_count = 0
    new_slots = 0
    skipped_past = 0
    
    for day_offset in range(30):
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
            
            # Skip wenn schon verarbeitet und noch zukünftig
            if slot_key in availability:
                slot_count += 1
                continue
            
            available = []
            
            # Prüfe jeden Berater (nutze gecachte Events)
            for name, cal_id in consultants.items():
                # Prüfe Einschränkungen
                if name in restricted_slots and time not in restricted_slots[name]:
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
            new_slots += 1
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
    print(f"   - Neue Slots: {new_slots}")
    print(f"   - Vergangene übersprungen: {skipped_past}")
    print(f"   - Alte entfernt: {removed_count}")
    print(f"   - Gesamt gespeichert: {len(availability)}")
    print(f"🕒 Nur Slots ab {now.strftime('%Y-%m-%d %H:%M')} berücksichtigt")

if __name__ == "__main__":
    start_time = time.time()
    main()
    backup_availability()  # Backup nach erfolgreicher Generierung
    duration = time.time() - start_time
    print(f"⏱️ Laufzeit: {duration:.2f} Sekunden")