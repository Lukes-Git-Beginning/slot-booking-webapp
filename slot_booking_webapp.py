# slot_booking_webapp.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import pytz
import json
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "defaultsecret")

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
TZ = pytz.timezone("Europe/Berlin")

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=creds)

CENTRAL_CALENDAR_ID = "zentralkalenderzfa@gmail.com"

def get_week_days(anchor_date):
    start = anchor_date - timedelta(days=anchor_date.weekday())
    days = [start + timedelta(days=i) for i in range(10) if (start + timedelta(days=i)).weekday() < 5]
    return days

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_current_kw(d):
    return d.isocalendar()[1]

def load_availability():
    try:
        with open("static/availability.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ Warnung: availability.json nicht gefunden. Rückgabe: leeres Verzeichnis.")
        return {}

def extract_weekly_summary(availability):
    by_week = {}
    for slot_time, data in availability.items():
        dt = datetime.strptime(slot_time, "%Y-%m-%d %H:%M")
        week = dt.strftime("KW %V (%d.%m.)")
        if week not in by_week:
            by_week[week] = {"booked": 0, "free": 0}
        if data:
            by_week[week]["free"] += len(data)
        else:
            by_week[week]["booked"] += 1
    summary = []
    for label, values in by_week.items():
        summary.append({"label": label, "booked": values["booked"], "free": values["free"]})
    return summary

def extract_detailed_summary(availability):
    by_week = {}
    for slot_time, data in availability.items():
        dt = datetime.strptime(slot_time, "%Y-%m-%d %H:%M")
        week = dt.strftime("KW %V (%d.%m.)")
        hour = dt.strftime("%H:%M")
        if week not in by_week:
            by_week[week] = {}
        if hour not in by_week[week]:
            by_week[week][hour] = {"booked": 0, "free": 0}
        if data:
            by_week[week][hour]["free"] += len(data)
        else:
            by_week[week][hour]["booked"] += 1
    formatted = []
    for label, slots in by_week.items():
        formatted.append({"label": label, "slots": slots})
    return formatted

def get_booked_slot_count(date_str, hour):
    """Zählt die Anzahl T1-Termine im Kalender für einen Slot."""
    slot_start = TZ.localize(datetime.strptime(f"{date_str} {hour}", "%Y-%m-%d %H:%M"))
    slot_end = slot_start + timedelta(hours=2)
    events_result = service.events().list(
        calendarId=CENTRAL_CALENDAR_ID,
        timeMin=slot_start.isoformat(),
        timeMax=slot_end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    t1_events = [event for event in events if event.get("summary", "").strip().lower().startswith("t1")]
    return len(t1_events)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == os.environ.get("LOGIN_USER") and password == os.environ.get("LOGIN_PASS"):
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            flash("Falscher Benutzername oder Passwort.")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.before_request
def require_login():
    if request.endpoint not in ("login", "static") and not session.get("logged_in"):
        return redirect(url_for("login"))

@app.route("/day/<date_str>")
def day_view(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for("day_view", date_str=datetime.today().strftime("%Y-%m-%d")))

    availability = load_availability()
    slots = {}
    for hour in ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]:
        key = f"{date_str} {hour}"
        berater_count = len(availability.get(key, []))
        booked = get_booked_slot_count(date_str, hour)
        free = max(0, berater_count - booked)
        slots[hour] = {
            "booked": booked,
            "free": free,
            "total": berater_count,
        }

    return render_template(
        "index.html",
        slots=slots,
        date=date_obj,
        days=get_week_days(date_obj),
        week_start=get_week_start(date_obj),
        current_kw=get_current_kw(date_obj),
        weekly_summary=extract_weekly_summary(availability),
        weekly_detailed=extract_detailed_summary(availability),
        timedelta=timedelta,
        get_week_start=get_week_start   # <-- DAS WICHTIGE!
    )

@app.route("/")
def index():
    return redirect(url_for("day_view", date_str=datetime.today().strftime("%Y-%m-%d")))

@app.route("/book", methods=["POST"])
def book():
    first = request.form.get("first_name")
    last = request.form.get("last_name")
    date = request.form.get("date")
    hour = request.form.get("hour")

    key = f"{date} {hour}"
    berater_count = len(load_availability().get(key, []))
    booked = get_booked_slot_count(date, hour)
    if booked >= berater_count:
        flash("Slot ist bereits voll belegt.", "danger")
        return redirect(url_for("day_view", date_str=date))

    slot_num = booked + 1
    event_title = f"T1-{slot_num:02d} – {last}, {first}"
    slot_start = TZ.localize(datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M"))
    slot_end = slot_start + timedelta(hours=2)
    event_body = {
        "summary": event_title,
        "start": {"dateTime": slot_start.isoformat()},
        "end": {"dateTime": slot_end.isoformat()},
    }
    service.events().insert(calendarId=CENTRAL_CALENDAR_ID, body=event_body).execute()
    flash("Slot erfolgreich gebucht!", "success")
    return redirect(url_for("day_view", date_str=date))

if __name__ == '__main__':
    app.run(debug=True)
