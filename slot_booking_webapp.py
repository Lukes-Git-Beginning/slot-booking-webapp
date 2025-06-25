import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-key")

# Google Calendar API Setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

if not SERVICE_ACCOUNT_FILE:
    raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS Umgebungsvariable nicht gesetzt!")

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

calendar_service = build('calendar', 'v3', credentials=creds)
CALENDAR_ID = os.getenv("CALENDAR_ID", "primary")

# Zeitzone
TZ = pytz.timezone("Europe/Berlin")

# Login
USERNAME = os.getenv("LOGIN_USERNAME", "admin")
PASSWORD = os.getenv("LOGIN_PASSWORD", "passwort")

# Slot-Zeiten
TIME_SLOTS = ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]

# Verfügbarkeit aus JSON laden
try:
    with open("availability.json", encoding="utf-8") as f:
        availability_data = json.load(f)
except FileNotFoundError:
    availability_data = {}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            return redirect(url_for('day_view'))
        else:
            flash('❌ Falscher Benutzername oder Passwort')
    return render_template('login.html')

@app.route('/day/<date>', methods=['GET'])
@app.route('/day', methods=['GET'])
def day_view(date=None):
    today = datetime.now(TZ).date()
    if not date:
        date = today
    else:
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()

    start_of_week = date - timedelta(days=date.weekday())  # Montag der Woche des gewählten Datums
    days = [start_of_week + timedelta(days=i) for i in range(5)]  # Mo–Fr der Woche

    slots = {}
    for time_str in TIME_SLOTS:
        dt = TZ.localize(datetime.combine(date, datetime.strptime(time_str, "%H:%M").time()))
        start = dt.isoformat()
        end = (dt + timedelta(minutes=119)).isoformat()

        events = calendar_service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        slot_list = []
        for event in events.get('items', []):
            summary = event.get('summary', '')
            color = event.get('colorId', '')

            if color in ['11', '6']:
                booked = False
            else:
                booked = summary.startswith("T1 –")

            slot_list.append({
                'id': event['id'],
                'summary': summary,
                'booked': booked
            })

        key = f"{date.strftime('%Y-%m-%d')} {time_str}"
        available_beraters = len(availability_data.get(key, []))

        slots[time_str] = {
            'events': slot_list,
            'available_beraters': available_beraters
        }

    # 4-Wochen-Auslastung vorbereiten
    weekly_summary = []
    for offset in [0, 7, 14, 21]:
        week_start = today + timedelta(days=-today.weekday() + offset)
        total = 0
        booked = 0
        for i in range(5):
            day = week_start + timedelta(days=i)
            for time_str in TIME_SLOTS:
                key = f"{day.strftime('%Y-%m-%d')} {time_str}"
                total += len(availability_data.get(key, []))
                dt = TZ.localize(datetime.combine(day, datetime.strptime(time_str, "%H:%M").time()))
                start = dt.isoformat()
                end = (dt + timedelta(minutes=119)).isoformat()
                events = calendar_service.events().list(
                    calendarId=CALENDAR_ID,
                    timeMin=start,
                    timeMax=end,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                for event in events.get('items', []):
                    if event.get('summary', '').startswith("T1 –") and event.get('colorId') not in ['11', '6']:
                        booked += 1

        weekly_summary.append({
            'label': f"KW {week_start.isocalendar()[1]} ({week_start.strftime('%d.%m.')})",
            'free': total - booked,
            'booked': booked
        })

    return render_template('index.html', slots=slots, date=date, days=days, weekly_summary=weekly_summary)

@app.route('/book', methods=['POST'])
def book():
    slot_id = request.form['slot_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    date = request.form['date']

    try:
        event = calendar_service.events().get(calendarId=CALENDAR_ID, eventId=slot_id).execute()
        if event.get('summary', '').startswith("T1 –") and event.get('colorId') not in ['11', '6']:
            flash("⚠️ Der Slot wurde gerade bereits gebucht.")
            return redirect(url_for('day_view', date=date))

        event['summary'] = f"T1 – {last_name}, {first_name}"
        calendar_service.events().update(calendarId=CALENDAR_ID, eventId=slot_id, body=event).execute()
        return redirect(url_for('day_view', date=date, success=True))
    except Exception as e:
        flash(f"Fehler beim Buchen: {str(e)}")
        return redirect(url_for('day_view', date=date))

if __name__ == '__main__':
    app.run(debug=True)
