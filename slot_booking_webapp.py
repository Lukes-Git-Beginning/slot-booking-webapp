# slot_booking_webapp.py
from flask import Flask, render_template
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import re
import os

app = Flask(__name__)

# Kalender Setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
creds = Credentials.from_authorized_user_file('token.json', SCOPES)
service = build('calendar', 'v3', credentials=creds)

CENTRAL_CALENDAR_ID = "zentralkalenderzfa@gmail.com"
TZ = pytz.timezone("Europe/Berlin")

# Zeithorizont: Mo–Fr dieser & nächster Woche
def get_week_days():
    today = datetime.now(TZ)
    start = today - timedelta(days=today.weekday())  # Montag dieser Woche
    days = [start + timedelta(days=i) for i in range(10) if (start + timedelta(days=i)).weekday() < 5]
    return days

# Slots für ein Datum abrufen
def get_slots_for_date(target_date):
    start = TZ.localize(datetime.combine(target_date, datetime.min.time()))
    end = start + timedelta(days=1)

    events = service.events().list(
        calendarId=CENTRAL_CALENDAR_ID,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])

    slots = {}
    for event in events:
        title = event.get('summary', '').strip()
        if not re.fullmatch(r"T1 – [0-9]{2}", title):
            continue  # Nur Slots mit Format "T1 – 01" bis "T1 – 99"

        start_time = datetime.fromisoformat(event['start']['dateTime']).astimezone(TZ)
        key = start_time.strftime('%H:%M')

        if key not in slots:
            slots[key] = []

        slots[key].append({
            'id': event['id'],
            'summary': title,
            'start': start_time,
            'booked': bool(re.search(r'[A-Za-z]', title.replace("T1 –", "")))  # wenn kein Name = frei
        })

    return slots

# Oberfläche
@app.route("/")
def index():
    days = get_week_days()
    data = []

    for day in days:
        day_slots = get_slots_for_date(day)
        display = {}

        for time, slots in sorted(day_slots.items()):
            gebucht = sum(1 for s in slots if s['booked'])
            gesamt = len(slots)
            status = "✅ {}/{} gebucht".format(gebucht, gesamt) if gebucht < gesamt else "⚠️ voll"

            display[time] = {
                'slots': slots,
                'status': status
            }

        data.append({
            'date': day.strftime('%A, %d.%m.%Y'),
            'slots_by_time': display
        })

    return render_template("slots_overview.html", days=data)

if __name__ == "__main__":
    app.run(debug=True)
