<<<<<<< HEAD
from flask import Flask, render_template, request, redirect, url_for, session, flash
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import pytz
import json
import os
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "defaultsecret")

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
TZ = pytz.timezone("Europe/Berlin")

# Hier anpassen: Wie viele Slots gibt es pro Berater und Uhrzeit?
SLOTS_PER_BERATER = 4  # <-- einfach auf 3 ändern, wenn gewünscht

# Welche User sollen beim Monats-Champion ausgeschlossen werden?
EXCLUDE_CHAMPION_USERS = ["callcenter", "admin"]

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=creds)

CENTRAL_CALENDAR_ID = "zentralkalenderzfa@gmail.com"

def get_userlist():
    userlist_raw = os.environ.get("USERLIST", "")
    userdict = {}
    for entry in userlist_raw.split(","):
        if ":" in entry:
            user, pw = entry.split(":", 1)
            userdict[user.strip()] = pw.strip()
    return userdict

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

def week_key_from_date(dt):
    return f"{dt.year}-KW{dt.isocalendar()[1]}"

def extract_weekly_summary(availability, current_date=None):
    week_possible = defaultdict(int)
    week_booked = defaultdict(int)
    week_dates = {}

    for slot_time, beraterlist in availability.items():
        dt = datetime.strptime(slot_time, "%Y-%m-%d %H:%M")
        key = week_key_from_date(dt)
        week_possible[key] += len(beraterlist) * SLOTS_PER_BERATER
        monday = dt - timedelta(days=dt.weekday())
        friday = monday + timedelta(days=4)
        week_dates[key] = (monday, friday)

    if week_dates:
        min_start = min([rng[0] for rng in week_dates.values()])
        max_end = max([rng[1] for rng in week_dates.values()]) + timedelta(days=1)
        events_result = service.events().list(
            calendarId=CENTRAL_CALENDAR_ID,
            timeMin=TZ.localize(datetime.combine(min_start.date(), datetime.min.time())).isoformat(),
            timeMax=TZ.localize(datetime.combine(max_end.date(), datetime.max.time())).isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        for event in events:
            if "start" in event and "dateTime" in event["start"]:
                dt = datetime.fromisoformat(event["start"]["dateTime"])
                key = week_key_from_date(dt)
                week_booked[key] += 1

    summary = []
    for key, possible in week_possible.items():
        booked = week_booked.get(key, 0)
        start, end = week_dates[key]
        usage = booked / (possible + 1e-5) if possible > 0 else 0
        summary.append({
            "label": key.replace("-", " "),
            "range": f"{start.strftime('%d.%m.')} – {end.strftime('%d.%m.')}",
            "start_date": start.strftime("%Y-%m-%d"),
            "usage_pct": int(round(usage * 100)),
            "usage": usage,
            "possible": possible,   # Immer aus availability.json!
            "booked": booked,
            "current": (
                current_date is not None and
                start.date() <= current_date <= end.date()
            )
        })
    summary.sort(key=lambda s: s["start_date"])
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
    max_slots = berater_count * SLOTS_PER_BERATER
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

    gebuchte = []
    for event in events:
        summary = event.get("summary", "").strip()
        # Filter: Nur echte Buchungen zählen (keine Dummy-Platzhalter wie '01')
        if summary.isdigit() and len(summary) == 2:
            continue
        gebuchte.append(event)

    taken_count = len(gebuchte)

    if taken_count > max_slots:
        print(f"⚠️ Überbuchung erkannt: {taken_count} gebucht bei max {max_slots} – {date_str} {hour}")

    freie_count = max(0, max_slots - taken_count)

    slots = []
    for i in range(1, freie_count + 1):
        slots.append({"id": f"SLOT-{i:02d}", "booked": False, "summary": ""})

    overbooked = taken_count > max_slots

    return slots, taken_count, max_slots, freie_count, overbooked

def get_slot_points(hour, slot_date):
    now = datetime.now(TZ).date()
    if (slot_date - now).days >= 28:
        return 0
    if hour in ["18:00", "20:00"]:
        return 1
    elif hour == "11:00":
        return 2
    elif hour in ["14:00", "16:00"]:
        return 3
    return 0

def get_slot_suggestions(availability, n=5):
    now = datetime.now(TZ).date()
    slot_list = []
    for slot_time, beraterlist in availability.items():
        dt = datetime.strptime(slot_time, "%Y-%m-%d %H:%M")
        slot_date = dt.date()
        hour = dt.strftime("%H:%M")
        if slot_date < now:
            continue
        freie = len(beraterlist) * SLOTS_PER_BERATER
        if freie > 0:
            punkte = get_slot_points(hour, slot_date)
            slot_list.append({
                "date": dt.strftime("%a, %d.%m."),
                "date_raw": slot_date,
                "hour": hour,
                "punkte": punkte,
                "freie": freie
            })
    slot_list.sort(key=lambda s: (-s["punkte"], s["date_raw"], -s["freie"], s["hour"]))
    return [s for s in slot_list if s["punkte"] > 0][:n]

def add_points_to_user(user, points):
    try:
        with open("static/scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
    except FileNotFoundError:
        scores = {}

    month = datetime.now(TZ).strftime("%Y-%m")
    if user not in scores:
        scores[user] = {}
    if month not in scores[user]:
        scores[user][month] = 0
    scores[user][month] += points

    with open("static/scores.json", "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

def check_and_set_champion():
    now = datetime.now(TZ)
    this_month = now.strftime("%Y-%m")
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    try:
        with open("static/champions.json", "r", encoding="utf-8") as f:
            champions = json.load(f)
    except FileNotFoundError:
        champions = {}

    # Bereits gespeichert?
    if last_month in champions:
        return champions[last_month]

    # Ranking auslesen
    try:
        with open("static/scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
    except FileNotFoundError:
        scores = {}

    # Sieger bestimmen, EXKLUDIERE bestimmte User
    month_scores = [
        (user, user_scores.get(last_month, 0))
        for user, user_scores in scores.items()
        if user.lower() not in EXCLUDE_CHAMPION_USERS
    ]
    month_scores = [x for x in month_scores if x[1] > 0]
    month_scores.sort(key=lambda x: x[1], reverse=True)

    if month_scores:
        champion_user = month_scores[0][0]
        champions[last_month] = champion_user
        with open("static/champions.json", "w", encoding="utf-8") as f:
            json.dump(champions, f, ensure_ascii=False, indent=2)
        return champion_user
    return None

def get_champion_for_month(month):
    try:
        with open("static/champions.json", "r", encoding="utf-8") as f:
            champions = json.load(f)
        return champions.get(month)
    except FileNotFoundError:
        return None

@app.route("/login", methods=["GET", "POST"])
def login():
    userlist = get_userlist()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in userlist and password == userlist[username]:
            session["logged_in"] = True
            session["user"] = username
            # --- Champion-Check für den letzten Monat:
            champ = check_and_set_champion()
            if champ == username:
                flash("🏆 Glückwunsch! Du warst Top-Telefonist des letzten Monats!", "success")
                session["is_champion"] = True
            else:
                session["is_champion"] = False
            return redirect(url_for("index"))
        else:
            flash("Falscher Benutzername oder Passwort.", "danger")
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

    weekly_summary = extract_weekly_summary(availability, current_date=date_obj)
    slot_suggestions = get_slot_suggestions(availability)

    return render_template(
        "index.html",
        slots=slots,
        date=date_obj,
        days=get_week_days(date_obj),
        week_start=get_week_start(date_obj),
        current_kw=get_current_kw(date_obj),
        weekly_summary=weekly_summary,
        weekly_detailed=extract_detailed_summary(availability),
        timedelta=timedelta,
        get_week_start=get_week_start,
        slot_suggestions=slot_suggestions
    )

@app.route("/")
def index():
    return redirect(url_for("day_view", date_str=datetime.today().strftime("%Y-%m-%d")))

@app.route("/book", methods=["POST"])
def book():
    slot_id = request.form.get("slot_id")
    first = request.form.get("first_name")
    last = request.form.get("last_name")
    description = request.form.get("description", "")
    date = request.form.get("date")
    hour = request.form.get("hour")
    color_id = request.form.get("color", "9")
    user = session.get("user")

    key = f"{date} {hour}"
    berater_count = len(load_availability().get(key, []))
    slot_list, booked, total, freie_count, overbooked = get_slot_status(date, hour, berater_count)

    slot_date = datetime.strptime(date, "%Y-%m-%d").date()
    points = get_slot_points(hour, slot_date)

    if overbooked or freie_count <= 0:
        flash("Slot ist bereits voll belegt.", "danger")
        return redirect(url_for("day_view", date_str=date))

    slot_start = TZ.localize(datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M"))
    slot_end = slot_start + timedelta(hours=2)
    event_title = f"{last}, {first}"
    event_body = {
        "summary": event_title,
        "description": description,
        "start": {"dateTime": slot_start.isoformat()},
        "end": {"dateTime": slot_end.isoformat()},
        "colorId": color_id
    }
    service.events().insert(calendarId=CENTRAL_CALENDAR_ID, body=event_body).execute()

    if user and points > 0:
        add_points_to_user(user, points)
        feedback = f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) erhalten."
    elif user and points == 0:
        feedback = "Slot erfolgreich gebucht! Für weit entfernte Termine werden keine Punkte vergeben."
    else:
        feedback = "Slot erfolgreich gebucht!"

    flash(feedback, "success")
    return redirect(url_for("day_view", date_str=date))

@app.route("/scoreboard")
def scoreboard():
    user = session.get("user")
    try:
        with open("static/scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
    except FileNotFoundError:
        scores = {}
    month = datetime.now(TZ).strftime("%Y-%m")
    ranking = [(u, v.get(month, 0)) for u, v in scores.items()]
    ranking.sort(key=lambda x: x[1], reverse=True)
    user_score = scores.get(user, {}).get(month, 0) if user else 0
    champion = get_champion_for_month((datetime.now(TZ).replace(day=1) - timedelta(days=1)).strftime("%Y-%m"))
    return render_template("scoreboard.html", ranking=ranking, user_score=user_score, month=month, current_user=user, champion=champion)

@app.route("/my-calendar")
def my_calendar():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    today = datetime.now(TZ).date()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)

    events_result = service.events().list(
        calendarId=CENTRAL_CALENDAR_ID,
        timeMin=TZ.localize(datetime.combine(start, datetime.min.time())).isoformat(),
        timeMax=TZ.localize(datetime.combine(end, datetime.max.time())).isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    my_events = []
    for event in events:
        if "summary" in event:
            summary = event["summary"]
            if user.lower() in summary.lower():
                start_dt = datetime.fromisoformat(event["start"]["dateTime"])
                color_id = event.get("colorId", "9")
                hour = start_dt.strftime("%H:%M")
                slot_date = start_dt.date()
                points = get_slot_points(hour, slot_date)
                my_events.append({
                    "date": start_dt.strftime("%A, %d.%m.%Y"),
                    "hour": hour,
                    "summary": summary,
                    "color_id": color_id,
                    "points": points,
                    "desc": event.get("description", ""),
                })

    my_events.sort(key=lambda e: (e["date"], e["hour"]))

    return render_template("my_calendar.html", my_events=my_events, user=user)

if __name__ == '__main__':
=======
# slot_booking_webapp.py
from flask import Flask, render_template
from google.oauth2.credentials import Credentials
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
>>>>>>> 9d7aa2b (Initial commit)
    app.run(debug=True)
