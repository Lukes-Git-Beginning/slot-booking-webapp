import os
import json
from datetime import datetime, timedelta
import pytz
from googleapiclient.discovery import build
from creds_loader import load_google_credentials

# ----------------- Google Calendar API Setup -----------------
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]  # nur lesen
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

availability = {}
availability_file = "static/availability.json"
today = datetime.now(TZ)
slot_count = 0

# Vorhandene Verfügbarkeiten laden
if os.path.exists(availability_file):
    try:
        with open(availability_file, "r", encoding="utf-8") as f:
            availability = json.load(f)
    except Exception as e:
        print(f"⚠️ Fehler beim Laden der alten availability.json: {e}")
        availability = {}

# Neue Slots berechnen
for day_offset in range(30):
    day = today + timedelta(days=day_offset)
    weekday_en = day.strftime('%A')
    weekday = weekday_map.get(weekday_en, None)

    if weekday not in slots:
        print(f"⏭️  {day.strftime('%Y-%m-%d')} ({weekday_en}) übersprungen (kein definierter Slot-Tag)")
        continue

    for time in slots[weekday]:
        start_naive = datetime.strptime(f"{day.strftime('%Y-%m-%d')} {time}", "%Y-%m-%d %H:%M")
        start = TZ.localize(start_naive)
        end = start + timedelta(hours=2)
        slot_key = f"{day.strftime('%Y-%m-%d')} {time}"

        available = []

        for name, cal_id in consultants.items():
            if name in restricted_slots and time not in restricted_slots[name]:
                print(f"🔒 {name} ausgeschlossen für {slot_key} (nicht in allowed times)")
                continue

            try:
                events_result = service.events().list(
                    calendarId=cal_id,
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    orderBy='startTime',
                    maxResults=10
                ).execute()
                events = events_result.get('items', [])

                has_conflict = True
                for event in events:
                    summary = event.get('summary', '').strip().lower()
                    if 't1-bereit' in summary or 't1 bereit' in summary:
                        has_conflict = False
                        print(f"✅ {name} hat Slot {slot_key} FREI mit Event: '{summary}'")
                        break
                    else:
                        print(f"⛔️ {name} blockiert Slot {slot_key} mit Event: '{summary}'")

                if not has_conflict:
                    available.append(name)

            except Exception as e:
                print(f"❌ Fehler bei {name} ({cal_id}): {e}")

        availability[slot_key] = available
        if not available:
            print(f"🚫 Slot {slot_key} hat KEINEN verfügbaren Berater!")
        slot_count += 1

# Alte Einträge älter als 7 Tage entfernen
cutoff_date = today - timedelta(days=6)
availability = {
    k: v for k, v in availability.items()
    if TZ.localize(datetime.strptime(k.split(" ")[0], "%Y-%m-%d")) >= cutoff_date
}

# Datei speichern
with open(availability_file, "w", encoding="utf-8") as f:
    json.dump(availability, f, ensure_ascii=False, indent=2)

print(f"\n✅ availability.json erfolgreich aktualisiert ({slot_count} neue Slots analysiert)")