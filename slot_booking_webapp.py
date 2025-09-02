import os
import json
import pytz
import time
from tracking_system import BookingTracker
from collections import defaultdict
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from creds_loader import load_google_credentials

# ----------------- Flask Setup -----------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me-to-random-string-now")

# ----------------- Google Calendar API Setup -----------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = load_google_credentials(SCOPES)
service = build("calendar", "v3", credentials=creds)

CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")
TZ = pytz.timezone("Europe/Berlin")

# ----------------- Konfiguration -----------------
SLOTS_PER_BERATER = 4  # Slots pro Berater & Uhrzeit
EXCLUDE_CHAMPION_USERS = ["callcenter", "admin"]

# ----------------- Hilfsfunktionen mit Error Handling -----------------
def safe_calendar_call(func, *args, **kwargs):
    """
    Wrapper für Google Calendar API calls mit Retry, Error Handling
    und auto-execute(): Wenn das Ergebnis eine .execute()-Methode hat,
    wird sie aufgerufen und ein dict zurückgegeben.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req_or_result = func(*args, **kwargs)  # z.B. service.events().list(...)
            # WICHTIG: Wenn es ein HttpRequest ist → execute()
            if hasattr(req_or_result, "execute") and callable(req_or_result.execute):
                return req_or_result.execute()
            # Falls bereits ein fertiges dict/Result übergeben wurde
            return req_or_result
        except HttpError as e:
            status = getattr(getattr(e, "resp", None), "status", None)
            if status == 429:  # Rate limit
                wait_time = (2 ** attempt) * 2
                print(f"[Calendar] Rate limit, retry in {wait_time}s …")
                time.sleep(wait_time)
                continue
            if status and status >= 500:  # Server error
                wait_time = 2 ** attempt
                print(f"[Calendar] Server-Fehler {status}, retry in {wait_time}s …")
                time.sleep(wait_time)
                continue
            # andere Fehler nicht retryn
            print(f"[Calendar] API-Fehler: {e}")
            return None
        except Exception as e:
            print(f"[Calendar] Unerwarteter Fehler: {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt)
    return None

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
    """Lade availability.json mit robustem Error Handling"""
    try:
        with open("static/availability.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ Warnung: availability.json nicht gefunden.")
        return {}
    except json.JSONDecodeError:
        print("⚠️ Warnung: availability.json ist korrupt.")
        return {}
    except Exception as e:
        print(f"⚠️ Fehler beim Laden der availability.json: {e}")
        return {}

def week_key_from_date(dt):
    return f"{dt.year}-KW{dt.isocalendar()[1]}"

def extract_weekly_summary(availability, current_date=None):
    """GEFIXT: Berechnet Wochenverfügbarkeit korrekt - zählt nur zukünftige Slots"""
    week_possible = defaultdict(int)
    week_booked = defaultdict(int)
    week_dates = {}
    
    # WICHTIGER FIX: Nur Slots ab heute zählen
    today = datetime.now(TZ).date()
    
    for slot_time, beraterlist in availability.items():
        try:
            dt = datetime.strptime(slot_time, "%Y-%m-%d %H:%M")
            
            # Skip vergangene Slots für korrekte Prozentberechnung
            if dt.date() < today:
                continue
                
            key = week_key_from_date(dt)
            week_possible[key] += len(beraterlist) * SLOTS_PER_BERATER
            monday = dt - timedelta(days=dt.weekday())
            friday = monday + timedelta(days=4)
            week_dates[key] = (monday, friday)
        except ValueError as e:
            print(f"Fehler beim Parsen von Slot-Zeit {slot_time}: {e}")
            continue

    # Gebuchte Termine abrufen mit Error Handling
    if week_dates:
        min_start = min(rng[0] for rng in week_dates.values())
        max_end = max(rng[1] for rng in week_dates.values()) + timedelta(days=1)
        
        events_result = safe_calendar_call(
            service.events().list,
            calendarId=CENTRAL_CALENDAR_ID,
            timeMin=TZ.localize(datetime.combine(min_start.date(), datetime.min.time())).isoformat(),
            timeMax=TZ.localize(datetime.combine(max_end.date(), datetime.max.time())).isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=2500
        )
        
        if events_result:
            events = events_result.get('items', [])
            for event in events:
                if "start" in event and "dateTime" in event["start"]:
                    try:
                        dt = datetime.fromisoformat(event["start"]["dateTime"])
                        # Nur zukünftige Events zählen
                        if dt.date() >= today:
                            key = week_key_from_date(dt)
                            week_booked[key] += 1
                    except Exception as e:
                        print(f"Fehler beim Parsen von Event-Zeit: {e}")
                        continue

    summary = []
    for key, possible in week_possible.items():
        booked = week_booked.get(key, 0)
        start, end = week_dates[key]
        
        # Verhindere Division durch 0
        usage = (booked / possible) if possible > 0 else 0
        
        summary.append({
            "label": key.replace("-", " "),
            "range": f"{start.strftime('%d.%m.')} – {end.strftime('%d.%m.')}",
            "start_date": start.strftime("%Y-%m-%d"),
            "usage_pct": min(100, int(round(usage * 100))),  # Cap bei 100%
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
        try:
            dt = datetime.strptime(slot_time, "%Y-%m-%d %H:%M")
            week = dt.strftime("KW %V (%d.%m.)")
            hour = dt.strftime("%H:%M")
            by_week.setdefault(week, {}).setdefault(hour, {"booked": 0, "free": 0})
            if data:
                by_week[week][hour]["free"] += len(data)
            else:
                by_week[week][hour]["booked"] += 1
        except Exception as e:
            print(f"Fehler in detailed_summary: {e}")
            continue
    return [{"label": label, "slots": slots} for label, slots in by_week.items()]

def get_slot_status(date_str, hour, berater_count):
    """Hole Slot-Status mit Error Handling"""
    max_slots = berater_count * SLOTS_PER_BERATER
    try:
        slot_start = TZ.localize(datetime.strptime(f"{date_str} {hour}", "%Y-%m-%d %H:%M"))
        slot_end = slot_start + timedelta(hours=2)
    except Exception as e:
        print(f"Fehler beim Parsen der Slot-Zeit: {e}")
        return [], 0, max_slots, 0, False

    events_result = safe_calendar_call(
        service.events().list,
        calendarId=CENTRAL_CALENDAR_ID,
        timeMin=slot_start.isoformat(),
        timeMax=slot_end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    )
    
    if not events_result:
        # Bei API-Fehler: Sicherheitsmodus - keine neuen Buchungen
        return [], 0, max_slots, 0, False
    
    events = events_result.get('items', [])
    
    # Filtere Platzhalter-Events (zweistellige Zahlen)
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
    return {"18:00": 1, "20:00": 1, "11:00": 2, "14:00": 3, "16:00": 3, "09:00": 2}.get(hour, 0)

def get_slot_suggestions(availability, n=5):
    now = datetime.now(TZ).date()
    slot_list = []
    for slot_time, beraterlist in availability.items():
        try:
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
        except Exception as e:
            print(f"Fehler in slot_suggestions: {e}")
            continue
    
    slot_list.sort(key=lambda s: (-s["punkte"], s["date_raw"], -s["freie"], s["hour"]))
    return [s for s in slot_list if s["punkte"] > 0][:n]

# ----------------- Punkte & Champion -----------------
def add_points_to_user(user, points):
    try:
        with open("static/scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        scores = {}
    
    month = datetime.now(TZ).strftime("%Y-%m")
    scores.setdefault(user, {}).setdefault(month, 0)
    scores[user][month] += points
    
    try:
        with open("static/scores.json", "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Fehler beim Speichern der Punkte: {e}")

def check_and_set_champion():
    now = datetime.now(TZ)
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    
    try:
        with open("static/champions.json", "r", encoding="utf-8") as f:
            champions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        champions = {}
    
    if last_month in champions:
        return champions[last_month]
    
    try:
        with open("static/scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        scores = {}
    
    month_scores = [(u, v.get(last_month, 0)) for u, v in scores.items() if u.lower() not in EXCLUDE_CHAMPION_USERS]
    month_scores = [x for x in month_scores if x[1] > 0]
    month_scores.sort(key=lambda x: x[1], reverse=True)
    
    if month_scores:
        champion_user = month_scores[0][0]
        champions[last_month] = champion_user
        try:
            with open("static/champions.json", "w", encoding="utf-8") as f:
                json.dump(champions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern des Champions: {e}")
        return champion_user
    return None

def get_champion_for_month(month):
    try:
        with open("static/champions.json", "r", encoding="utf-8") as f:
            return json.load(f).get(month)
    except (FileNotFoundError, json.JSONDecodeError):
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
        weekly_summary=extract_weekly_summary(availability, current_date=date_obj),
        weekly_detailed=extract_detailed_summary(availability),
        timedelta=timedelta,
        get_week_start=get_week_start,
        slot_suggestions=get_slot_suggestions(availability)
    )

@app.route("/")
def index():
    return redirect(url_for("day_view", date_str=datetime.today().strftime("%Y-%m-%d")))

@app.route("/export/bookings/<month>")
def export_bookings(month):
    """Exportiere Buchungen als CSV"""
    if session.get("user") != "admin":
        return redirect(url_for("login"))
    
    # Hole alle Buchungen des Monats
    # Erstelle CSV
    # Return als Download

@app.route("/book", methods=["POST"])
def book():
    first = request.form.get("first_name")
    last = request.form.get("last_name")
    description = request.form.get("description", "")
    date = request.form.get("date")
    hour = request.form.get("hour")
    color_id = request.form.get("color", "9")
    user = session.get("user")

    # Validierung
    if not all([first, last, date, hour]):
        flash("Bitte alle Pflichtfelder ausfüllen.", "danger")
        return redirect(url_for("day_view", date_str=date))

    key = f"{date} {hour}"
    berater_count = len(load_availability().get(key, []))
    slot_list, booked, total, freie_count, overbooked = get_slot_status(date, hour, berater_count)
    
    try:
        slot_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        flash("Ungültiges Datum.", "danger")
        return redirect(url_for("index"))
    
    points = get_slot_points(hour, slot_date)

    if overbooked or freie_count <= 0:
        flash("Slot ist bereits voll belegt.", "danger")
        return redirect(url_for("day_view", date_str=date))

    try:
        slot_start = TZ.localize(datetime.strptime(f"{date} {hour}", "%Y-%m-%d %H:%M"))
        slot_end = slot_start + timedelta(hours=2)
    except Exception as e:
        flash("Fehler beim Erstellen des Termins.", "danger")
        print(f"Fehler beim Parsen der Zeit: {e}")
        return redirect(url_for("day_view", date_str=date))
    
    event_body = {
        "summary": f"{last}, {first}",
        "description": description,
        "start": {"dateTime": slot_start.isoformat()},
        "end": {"dateTime": slot_end.isoformat()},
        "colorId": color_id
    }
    
    result = safe_calendar_call(
        service.events().insert,
        calendarId=CENTRAL_CALENDAR_ID,
        body=event_body
    )
    
    if result:  # ZEILE 457 - KEINE EXTRA EINRÜCKUNG!
        if user and points > 0:
            add_points_to_user(user, points)
            flash(f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) erhalten.", "success")
        else:
            flash("Slot erfolgreich gebucht!", "success")
    else:
        flash("Fehler beim Buchen des Slots. Bitte versuche es später erneut.", "danger")
    
    return redirect(url_for("day_view", date_str=date))       
        if user and points > 0:
            add_points_to_user(user, points)
            flash(f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) erhalten.", "success")
        else:
            flash("Slot erfolgreich gebucht!", "success")
    if result:
        if user and points > 0:
            add_points_to_user(user, points)
            flash(f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) erhalten.", "success")
        else:
            flash("Slot erfolgreich gebucht!", "success")
    else:
        flash("Fehler beim Buchen des Slots. Bitte versuche es später erneut.", "danger")
    
    return redirect(url_for("day_view", date_str=date))
@app.route("/tracking/customer/<customer_name>")
def customer_tracking(customer_name):
    """Zeige Kundenhistorie"""
    if session.get("user") != "admin":
        return redirect(url_for("login"))
    
    history = tracker.get_customer_history(customer_name)
    return jsonify(history)

@app.route("/tracking/report/weekly")
def weekly_tracking_report():
    """Zeige Wochenbericht"""
    if session.get("user") != "admin":
        return redirect(url_for("login"))
    
    report = tracker.get_weekly_report()
    return jsonify(report)
    
@app.route("/scoreboard")
def scoreboard():
    user = session.get("user")
    try:
        with open("static/scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        scores = {}
    
    month = datetime.now(TZ).strftime("%Y-%m")
    ranking = sorted([(u, v.get(month, 0)) for u, v in scores.items()], key=lambda x: x[1], reverse=True)
    user_score = scores.get(user, {}).get(month, 0) if user else 0
    champion = get_champion_for_month((datetime.now(TZ).replace(day=1) - timedelta(days=1)).strftime("%Y-%m"))
    
    return render_template("scoreboard.html", 
                         ranking=ranking, 
                         user_score=user_score, 
                         month=month, 
                         current_user=user, 
                         champion=champion)

@app.route("/my-calendar")
def my_calendar():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    today = datetime.now(TZ).date()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    
    events_result = safe_calendar_call(
        service.events().list,
        calendarId=CENTRAL_CALENDAR_ID,
        timeMin=TZ.localize(datetime.combine(start, datetime.min.time())).isoformat(),
        timeMax=TZ.localize(datetime.combine(end, datetime.max.time())).isoformat(),
        singleEvents=True,
        orderBy='startTime'
    )
    
    my_events = []
    if events_result:
        events = events_result.get('items', [])
        for event in events:
            if "summary" in event and user.lower() in event["summary"].lower():
                try:
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
                except Exception as e:
                    print(f"Fehler beim Parsen von Event: {e}")
                    continue
    
    my_events.sort(key=lambda e: (e["date"], e["hour"]))
    return render_template("my_calendar.html", my_events=my_events, user=user)

if __name__ == '__main__':
    app.run(debug=False)  # Debug auf False für Produktion!