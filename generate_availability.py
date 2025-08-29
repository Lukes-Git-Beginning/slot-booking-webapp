import os
import json
import time
from datetime import datetime, timedelta
import pytz
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from creds_loader import load_google_credentials

# ----------------- Google Calendar API Setup -----------------
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
creds = load_google_credentials(SCOPES)
service = build("calendar", "v3", credentials=creds)

# ----------------- Konfiguration -----------------
CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "primary")
TZ = pytz.timezone("Europe/Berlin")

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
    """API Call mit Retry-Logic und Error Handling"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            if e.resp.status == 429:  # Rate limit
                wait_time = (2 ** attempt) * 2
                print(f"⏳ Rate limit erreicht, warte {wait_time}s...")
                time.sleep(wait_time)
            elif e.resp.status >= 500:
                wait_time = 2 ** attempt
                print(f"⚠️ Server-Fehler, Retry in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ API Fehler: {e}")
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
                
                # Berater ist verfügbar wenn "t1-bereit" im Titel
                if 't1-bereit' in summary or 't1 bereit' in summary:
                    return True
                else:
                    # Konflikt gefunden
                    return False
        except Exception as e:
            print(f"⚠️ Fehler beim Parsen von Event: {e}")
            continue
    
    # Keine Konflikte = nicht verfügbar (kein t1-bereit Event)
    return False

def main():
    availability = {}
    availability_file = "static/availability.json"
    today = datetime.now(TZ)
    
    # Vorhandene Verfügbarkeiten laden
    if os.path.exists(availability_file):
        try:
            with open(availability_file, "r", encoding="utf-8") as f:
                availability = json.load(f)
            print(f"✅ Bestehende availability.json geladen ({len(availability)} Einträge)")
        except Exception as e:
            print(f"⚠️ Fehler beim Laden der alten availability.json: {e}")
            availability = {}
    
    # Zeitraum für Batch-Fetch (30 Tage)
    start_date = TZ.localize(datetime.combine(today.date(), datetime.min.time()))
    end_date = start_date + timedelta(days=30)
    
    # PERFORMANCE-OPTIMIERUNG: Alle Events einmal holen
    print(f"\n🚀 Hole alle Events für {len(consultants)} Berater (30 Tage)...")
    all_consultant_events = batch_fetch_events(consultants, start_date, end_date)
    
    # Slots analysieren
    print(f"\n📊 Analysiere Slots...")
    slot_count = 0
    new_slots = 0
    
    for day_offset in range(30):
        day = today + timedelta(days=day_offset)
        weekday_en = day.strftime('%A')
        weekday = weekday_map.get(weekday_en, None)
        
        if weekday not in slots:
            continue
        
        for time in slots[weekday]:
            start_naive = datetime.strptime(f"{day.strftime('%Y-%m-%d')} {time}", "%Y-%m-%d %H:%M")
            slot_start = TZ.localize(start_naive)
            slot_end = slot_start + timedelta(hours=2)
            slot_key = f"{day.strftime('%Y-%m-%d')} {time}"
            
            # Skip wenn schon verarbeitet und noch aktuell
            if slot_key in availability and day.date() >= today.date():
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
    
    # Alte Einträge entfernen (älter als 7 Tage)
    cutoff_date = today - timedelta(days=7)
    old_count = len(availability)
    
    availability = {
        k: v for k, v in availability.items()
        if TZ.localize(datetime.strptime(k.split(" ")[0], "%Y-%m-%d")) >= cutoff_date
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
    print(f"   - Alte entfernt: {removed_count}")
    print(f"   - Gesamt gespeichert: {len(availability)}")

if __name__ == "__main__":
    start_time = time.time()
    main()
    duration = time.time() - start_time
    print(f"⏱️ Laufzeit: {duration:.2f} Sekunden")