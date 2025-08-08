import os
import json
import pytz
from collections import defaultdict
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from googleapiclient.discovery import build
from creds_loader import load_google_credentials

# ----------------- Flask Setup -----------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me")

# ----------------- Google Calendar API Setup -----------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = load_google_credentials(SCOPES)
service = build("calendar", "v3", credentials=creds)

CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")
TZ = pytz.timezone("Europe/Berlin")

# ----------------- Konfiguration -----------------
SLOTS_PER_BERATER = 4  # Slots pro Berater & Uhrzeit
EXCLUDE_CHAMPION_USERS = ["callcenter", "admin"]

# ----------------- Hilfsfunktionen -----------------
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
    return [start + timedelta(days=i) for i in range(10) if (start + timedelta(days=i)).weekday() < 5]

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_current_kw(d):
    return d.isocalendar()[1]

def load_availability():
    try:
        with open("static/availability.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ Warnung: availability.json nicht gefunden.")
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
        min_start = min(rng[0] for rng in week_dates.values())
        max_end = max(rng[1] for rng in week_dates.values()) + timedelta(days=1)
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
            "possible": possible,
            "booked": booked,
            "current": (
                current_date is not None and start.date() <= current_date <= end.date()
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
        by_week.setdefault(week, {}).setdefault(hour, {"booked": 0, "free": 0})
        if data:
            by_week[week][hour]["free"] += len(data)
        else:
            by_week[week][hour]["booked"] += 1
    return [{"label": label, "slots": slots} for label, slots in by_week.items()]

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

    # Filtere zweistellige Platzhalter wie "01"
    gebuchte = [ev for ev in events if not (ev.get("summary", "").isdigit() and len(ev.get("summary", "")) == 2)]
    taken_count = len(gebuchte)
    freie_count = max(0, max_slots - taken_count)
    overbooked = taken_count > max_slots

    slots = [{"id": f"SLOT-{i:02d}", "booked": False, "summary": ""} for i in range(1, freie_count + 1)]
    return slots, taken_count, max_slots, freie_count, overbooked

def get_slot_points(hour, slot_date):
    now = datetime.now(TZ).date()
    if (slot_date - now).days >= 28:
        return 0
    return {"18:00": 1, "20:00": 1, "11:00": 2, "14:00": 3, "16:00": 3}.get(hour, 0)

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

# ----------------- Punkte & Champion -----------------
def add_points_to_user(user, points):
    try:
        with open("static/scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
    except FileNotFoundError:
        scores = {}
    month = datetime.now(TZ).strftime("%Y-%m")
    scores.setdefault(user, {}).setdefault(month, 0)
    scores[user][month] += points
    with open("static/scores.json", "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

def check_and_set_champion():
    now = datetime.now(TZ)
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    try:
        with open("static/champions.json", "r", encoding="utf-8") as f:
            champions = json.load(f)
    except FileNotFoundError:
        champions = {}
    if last_month in champions:
        return champions[last_month]
    try:
        with open("static/scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
    except FileNotFoundError:
        scores = {}
    month_scores = [(u, v.get(last_month, 0)) for u, v in scores.items() if u.lower() not in EXCLUDE_CHAMPION_USERS]
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
            return json.load(f).get(month)
    except FileNotFoundError:
        return None

# ----------------- Routes -----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    userlist = get_userlist()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in userlist and password == userlist[username]:
            session.update({"logged_in": True, "user": username})
            champ = check_and_set_champion()
            session["is_champion"] = (champ == username)
            if champ == username:
                flash("🏆 Glückwunsch! Du warst Top-Telefonist des letzten Monats!", "success")
            return redirect(url_for("index"))
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
            "events": slot_list, "booked": booked, "total": total,
            "free_count": freie_count, "available_beraters": berater_count,
            "overbooked": overbooked,
        }
    return render_template(
        "index.html",
        slots=slots,
        date=date_obj,
        days=get_week_days(date_obj),
        week_start=get_week_start(date_obj),
        current_kw=get_current_kw(date_obj),
        weekly_summary=extract_weekly_summary(availability, current_date=date_obj),
        weekly_detailed=extract_detailed_summary(availability),
        timedelta=timedelta,
        get_week_start=get_week_start,
        slot_suggestions=get_slot_suggestions(availability)
    )

@app.route("/")
def index():
    return redirect(url_for("day_view", date_str=datetime.today().strftime("%Y-%m-%d")))

@app.route("/book", methods=["POST"])
def book():
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
    event_body = {
        "summary": f"{last}, {first}",
        "description": description,
        "start": {"dateTime": slot_start.isoformat()},
        "end": {"dateTime": slot_end.isoformat()},
        "colorId": color_id
    }
    service.events().insert(calendarId=CENTRAL_CALENDAR_ID, body=event_body).execute()
    if user and points > 0:
        add_points_to_user(user, points)
        flash(f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) erhalten.", "success")
    else:
        flash("Slot erfolgreich gebucht!", "success")
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
    ranking = sorted([(u, v.get(month, 0)) for u, v in scores.items()], key=lambda x: x[1], reverse=True)
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
        if "summary" in event and user.lower() in event["summary"].lower():
            start_dt = datetime.fromisoformat(event["start"]["dateTime"])
            hour = start_dt.strftime("%H:%M")
            points = get_slot_points(hour, start_dt.date())
            my_events.append({
                "date": start_dt.strftime("%A, %d.%m.%Y"),
                "hour": hour,
                "summary": event["summary"],
                "color_id": event.get("colorId", "9"),
                "points": points,
                "desc": event.get("description", "")
            })
    my_events.sort(key=lambda e: (e["date"], e["hour"]))
    return render_template("my_calendar.html", my_events=my_events, user=user)

@app.get("/api/calendar/events")
def api_calendar_events():
    """
    Liefert Events für FullCalendar.
    Erwartet Query-Params ?start=...&end=... (ISO-8601). Default: heute..+14 Tage.
    """
    start_param = request.args.get("start")
    end_param = request.args.get("end")

    def fix_iso(s):
        # FullCalendar sendet oft 'Z' -> Python mag '+00:00'
        return s.replace("Z", "+00:00") if s else s

    if start_param and end_param:
        try:
            start_iso = fix_iso(start_param)
            end_iso = fix_iso(end_param)
            # Wir geben einfach die Strings so weiter – Google API akzeptiert ISO8601
            time_min = start_iso
            time_max = end_iso
        except Exception:
            start = datetime.now(TZ)
            end = start + timedelta(days=14)
            time_min = start.isoformat()
            time_max = end.isoformat()
    else:
        start = datetime.now(TZ)
        end = start + timedelta(days=14)
        time_min = start.isoformat()
        time_max = end.isoformat()

    events_result = service.events().list(
        calendarId=CENTRAL_CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime',
        maxResults=2500
    ).execute()

    items = events_result.get("items", [])

    def map_event(ev):
        start = ev.get("start", {})
        end = ev.get("end", {})
        start_dt = start.get("dateTime") or start.get("date")  # all-day fallback
        end_dt = end.get("dateTime") or end.get("date")
        return {
            "id": ev.get("id"),
            "title": ev.get("summary", ""),
            "start": start_dt,
            "end": end_dt,
            # optionales Mapping: färbt Events nach Google colorId leicht ein
            "extendedProps": {
                "colorId": ev.get("colorId", "")
            }
        }

    return jsonify([map_event(e) for e in items])

if __name__ == '__main__':
    app.run(debug=True)