from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import json

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'service_account.json'
TZ = pytz.timezone('Europe/Berlin')

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=creds)

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
    "Christian": ["11:00", "16:00", "18:00"],
    "Tim": ["11:00", "16:00", "18:00"]
}

slots = {
    "Mo": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Di": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Mi": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Do": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Fr": ["09:00", "11:00", "14:00"]
}

availability = {}
today = datetime.now(TZ)
slot_count = 0

for day_offset in range(30):
    day = today + timedelta(days=day_offset)
    weekday = day.strftime('%a')[:2]
    if weekday in slots:
        for time in slots[weekday]:
            start_naive = datetime.strptime(f"{day.strftime('%Y-%m-%d')} {time}", "%Y-%m-%d %H:%M")
            start = TZ.localize(start_naive)
            end = start + timedelta(hours=2)
            slot_key = f"{day.strftime('%Y-%m-%d')} {time}"

            available = []

            for name, cal_id in consultants.items():
                if name in restricted_slots and time not in restricted_slots[name]:
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

                    # prüfen ob blockiert
                    has_conflict = False
                    for event in events:
                        summary = event.get('summary', '').lower()
                        if any(block in summary for block in ['t2', 't1,5', 't2,5', 't3', 't3,5']):
                            has_conflict = True
                            break
                    if not has_conflict:
                        available.append(name)

                except Exception as e:
                    print(f"❌ Fehler bei {name} ({cal_id}): {e}")

            availability[slot_key] = available
            print(f"{slot_key}: {len(available)} verfügbar → {', '.join(available)}")
            slot_count += 1

with open("static/availability.json", "w", encoding="utf-8") as f:
    json.dump(availability, f, ensure_ascii=False, indent=2)

print(f"\n✅ availability.json erfolgreich generiert ({slot_count} Slots analysiert)")
