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

def get_slot_status(date_str, hour, berater_count):
    """
    Für einen Slot (Tag+Uhrzeit) wird gezählt, wie viele echte Termine schon im Kalender sind.
    Die Zahl der maximal möglichen Slots ergibt sich aus berater_count * 4.
    Buchungsformulare gibt es nur für die noch freien Slots.
    """
    max_slots = berater_count * 4
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

    # Zähle alle Events, deren Summary NICHT exakt zwei Ziffern ist (keine Platzhalter)
    gebuchte = [event for event in events if not (event.get("summary", "").strip().isdigit() and len(event.get("summary", "").strip()) == 2)]
    taken_count = len(gebuchte)
    freie_count = max(0, max_slots - taken_count)

    # Für das Template: Dummy-Slots für noch freie Plätze
    slots = []
    for i in range(1, freie_count + 1):
        slots.append({"id": f"SLOT-{i:02d}", "booked": False, "summary": ""})

    overbooked = taken_count > max_slots
    return slots, taken_count, max_slots, freie_count, overbooked

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
        slot_list, booked, total, freie_count, overbooked = get_slot_status(date_str, hour, berater_count)
        slots[hour] = {
            "events": slot_list,
            "booked": booked,
            "total": total,
            "free_count": freie_count,
            "available_beraters": berater_count,
            "overbooked": overbooked,
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
        get_week_start=get_week_start   # <- Für das KW-Dropdown im Template!
    )

@app.route("/")
def index():
    return redirect(url_for("day_view", date_str=datetime.today().strftime("%Y-%m-%d")))

@app.route("/book", methods=["POST"])
def book():
    slot_id = request.form.get("slot_id")
    first = request.form.get("first_name")
    last = request.form.get("last_name")
    date = request.form.get("date")
    hour = request.form.get("hour")
    color_id = request.form.get("color", "9")  # Default: blau

    key = f"{date} {hour}"
    berater_count = len(load_availability().get(key, []))
    slot_list, booked, total, freie_count, overbooked = get_slot_status(date, hour, berater_count)

    # Überbuchung prüfen
    if overbooked or freie_count <= 0:
        flash("Slot ist bereits voll belegt.", "danger")
        return redirect(url_for("day_view", date_str=date))

    # Slot jetzt mit Name buchen (neues Event anlegen)
    slot_start = TZ.localize(datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M"))
    slot_end = slot_start + timedelta(hours=2)
    event_title = f"{last}, {first}"
    event_body = {
        "summary": event_title,
        "start": {"dateTime": slot_start.isoformat()},
        "end": {"dateTime": slot_end.isoformat()},
        "colorId": color_id
    }
    service.events().insert(calendarId=CENTRAL_CALENDAR_ID, body=event_body).execute()
    flash("Slot erfolgreich gebucht!", "success")
    return redirect(url_for("day_view", date_str=date))

if __name__ == '__main__':
    app.run(debug=True)
