# slot_booking_webapp.py
from flask import Flask, render_template, request, redirect, url_for
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, date
import pytz
import json
import os

app = Flask(__name__)

# Kalender Setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
TZ = pytz.timezone("Europe/Berlin")

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=creds)

CENTRAL_CALENDAR_ID = "zentralkalenderzfa@gmail.com"

# Zeithorizont: Mo–Fr dieser & nächster Woche
def get_week_days():
    today = datetime.now(TZ)
    start = today - timedelta(days=today.weekday())
    days = [start + timedelta(days=i) for i in range(10) if (start + timedelta(days=i)).weekday() < 5]
    return days

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_current_kw(d):
    return d.isocalendar()[1]

def load_availability():
    with open("availability.json", "r", encoding="utf-8") as f:
        return json.load(f)

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

@app.route("/day/<date_str>")
def day_view(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for("day_view", date=datetime.today().strftime("%Y-%m-%d")))

    # Slots simulieren (normalerweise hier: Kalenderabfrage)
    availability = load_availability()
    slots = {}
    for hour in ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]:
        key = f"{date_str} {hour}"
        events = []
        if key in availability:
            for idx, entry in enumerate(availability[key]):
                events.append({
                    "id": f"{key}-{idx}",
                    "booked": False,
                    "summary": ""
                })
        slots[hour] = {
            "events": events,
            "available_beraters": len(availability.get(key, []))
        }

    return render_template(
        "index.html",
        slots=slots,
        date=date_obj,
        days=get_week_days(),
        week_start=get_week_start(date_obj),
        current_kw=get_current_kw(date_obj),
        weekly_summary=extract_weekly_summary(availability),
        weekly_detailed=extract_detailed_summary(availability),
        timedelta=timedelta  # ✅ damit {% timedelta %} funktioniert
    )

@app.route("/")
def index():
    return redirect(url_for("day_view", date=datetime.today().strftime("%Y-%m-%d")))

@app.route("/book", methods=["POST"])
def book():
    # Buchung simuliert
    slot_id = request.form.get("slot_id")
    first = request.form.get("first_name")
    last = request.form.get("last_name")
    date = request.form.get("date")
    print(f"Buchung für {first} {last} in Slot {slot_id} am {date}")
    return redirect(url_for("day_view", date=date, success=True))

if __name__ == '__main__':
    app.run(debug=True)
