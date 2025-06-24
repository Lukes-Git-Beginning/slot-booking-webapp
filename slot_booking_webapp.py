import os
from flask import Flask, render_template, request, redirect, url_for, flash
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
import uuid

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

# Zeitzone festlegen
TZ = pytz.timezone("Europe/Berlin")

# Login-Credentials aus Umgebungsvariablen
USERNAME = os.getenv("LOGIN_USERNAME", "admin")
PASSWORD = os.getenv("LOGIN_PASSWORD", "passwort")

# Slot-Times (konfigurierbar)
TIME_SLOTS = ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]

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

    # Tage von Mo–Fr anzeigen
    days = [today + timedelta(days=i) for i in range(10) if (today + timedelta(days=i)).weekday() < 5]

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
            booked = summary.startswith("T1 –")
            slot_list.append({
                'id': event['id'],
                'summary': summary,
                'booked': booked
            })
        slots[time_str] = slot_list

    return render_template('index.html', slots=slots, date=date, days=days)

@app.route('/book', methods=['POST'])
def book():
    slot_id = request.form['slot_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    date = request.form['date']

    try:
        event = calendar_service.events().get(calendarId=CALENDAR_ID, eventId=slot_id).execute()

        # Wenn bereits jemand gebucht hat, abbrechen
        if event.get('summary', '').startswith("T1 –"):
            flash("⚠️ Der Slot wurde gerade bereits gebucht.")
            return redirect(url_for('day_view', date=date))

        # Markiere den Slot sofort als gebucht
        event['summary'] = f"T1 – {last_name}, {first_name}"
        calendar_service.events().update(calendarId=CALENDAR_ID, eventId=slot_id, body=event).execute()

        return redirect(url_for('day_view', date=date, success=True))
    except Exception as e:
        flash(f"Fehler beim Buchen: {str(e)}")
        return redirect(url_for('day_view', date=date))

if __name__ == '__main__':
    app.run(debug=True)