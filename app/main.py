import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import pytz
import time
from collections import defaultdict

# ===== NEUE IMPORT-PFADE =====
from features.tracking.system import BookingTracker
from core.persistence.data_manager import data_persistence
from features.gamification.levels import level_system
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response, make_response
import uuid
import logging
from logging import StreamHandler
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ===== NEUE IMPORT-PFADE =====
from core.auth.credentials import load_google_credentials
from core.persistence.cache_manager import cache_manager

# ===== NEUE IMPORT-PFADE =====
from features.gamification.weekly_points import (
    get_week_key,
    list_recent_weeks,
    is_in_commit_window,
    get_participants,
    set_participants,
    set_week_goal,
    record_activity,
    apply_pending,
    compute_week_stats,
    add_participant,
    remove_participant,
    set_on_vacation,
    get_week_audit,
)

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ----------------- Flask Setup -----------------
app = Flask(__name__)

# Rate Limiter
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour", "50 per minute"])

# ----------------- Sentry -----------------
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")),
        send_default_pii=False,
    )
    handler = StreamHandler()
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

app.secret_key = os.getenv("SECRET_KEY", "change-me-to-random-string-now")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,  # 2 MB request body limit
)

# ----------------- Request ID Middleware -----------------
@app.before_request
def attach_request_id():
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.environ["request_id"] = rid

@app.after_request
def add_request_id_header(response):
    rid = request.environ.get("request_id")
    if rid:
        response.headers.setdefault("X-Request-ID", rid)
    return response

# ----------------- Google Calendar API Setup -----------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = load_google_credentials(SCOPES)
service = build("calendar", "v3", credentials=creds)

CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")
TZ = pytz.timezone("Europe/Berlin")

# ----------------- Konfiguration -----------------
SLOTS_PER_BERATER = 4
EXCLUDE_CHAMPION_USERS = ["callcenter", "admin"]

# ----------------- Hilfsfunktionen -----------------
def safe_calendar_call(func, *args, **kwargs):
    """Wrapper für Google Calendar API calls mit Retry und Error Handling"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            req_or_result = func(*args, **kwargs)
            if hasattr(req_or_result, "execute") and callable(req_or_result.execute):
                return req_or_result.execute()
            return req_or_result
        except HttpError as e:
            status = getattr(getattr(e, "resp", None), "status", None)
            if status == 429:  # Rate limit
                wait_time = (2 ** attempt) * 2
                print(f"[Calendar] Rate limit, retry in {wait_time}s")
                time.sleep(wait_time)
                continue
            elif status == 403:
                print(f"[Calendar] Permission denied: {e}")
                return None
            elif status == 404:
                print(f"[Calendar] Resource not found: {e}")
                return None
            elif status and status >= 500:
                wait_time = 2 ** attempt
                print(f"[Calendar] Server-Fehler {status}, retry in {wait_time}s")
                time.sleep(wait_time)
                continue
            else:
                print(f"[Calendar] HTTP-Fehler {status}: {e}")
                return None
        except (ConnectionError, TimeoutError) as e:
            print(f"[Calendar] Network error: {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt)
        except ValueError as e:
            print(f"[Calendar] Wertfehler: {e}")
            return None
        except Exception as e:
            print(f"[Calendar] Unerwarteter Fehler: {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt)
    return None

def is_admin(user):
    """Prüft ob User Admin-Rechte hat"""
    admin_env = os.environ.get("ADMIN_USERS", "")
    env_admins = [u.strip() for u in admin_env.split(",") if u.strip()]
    fallback_admins = ["admin", "Admin", "administrator", "Jose", "Simon", "Alex", "David"]
    admin_users = env_admins if env_admins else fallback_admins
    return user and user.lower() in [u.lower() for u in admin_users]

@app.after_request
def add_security_headers(response):
    """Setze grundlegende Security-Header"""
    try:
        csp = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "font-src 'self' data: https://cdn.jsdelivr.net;"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
    except Exception:
        pass
    return response

def get_app_runtime_days():
    """Berechnet wie lange die App schon läuft"""
    app_start_date = datetime(2025, 9, 1)
    app_start_localized = TZ.localize(app_start_date)
    days_running = (datetime.now(TZ) - app_start_localized).days
    return max(30, days_running)

def get_color_mapping_status():
    """Gebe Color-Mapping Status für Admin Dashboard zurück"""
    from core.mapping.colors import CALENDAR_COLORS
    
    blocking_colors = []
    non_blocking_colors = []
    
    for color_id, info in CALENDAR_COLORS.items():
        if info.get("blocks_availability", True):
            blocking_colors.append({
                "id": color_id,
                "name": info["name"],
                "description": info["description"]
            })
        else:
            non_blocking_colors.append({
                "id": color_id,
                "name": info["name"],
                "description": info["description"]
            })
    
    return {
        "blocking": blocking_colors,
        "non_blocking": non_blocking_colors,
        "total_colors": len(CALENDAR_COLORS)
    }

def get_userlist():
    userlist_raw = os.environ.get("USERLIST", "")
    userdict = {}
    for entry in userlist_raw.split(","):
        if ":" in entry:
            user, pw = entry.split(":", 1)
            userdict[user.strip()] = pw.strip()
    return userdict

def get_all_active_users():
    """Hole alle aktiven User aus verschiedenen Quellen"""
    active_users = set()
    
    # Users aus Scores
    try:
        scores = data_persistence.load_scores()
        active_users.update(scores.keys())
    except:
        pass
    
    # Users aus Badges
    try:
        from features.gamification.achievements import achievement_system
        badges_data = achievement_system.load_badges()
        active_users.update(badges_data.keys())
    except:
        pass
    
    # Users aus Tracking
    try:
        tracker = BookingTracker()
        if os.path.exists(tracker.bookings_file):
            with open(tracker.bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            booking = json.loads(line)
                            user = booking.get("user")
                            if user and user != "unknown":
                                active_users.add(user)
                        except:
                            continue
    except:
        pass
    
    return list(active_users)

def get_week_days(anchor_date):
    """Zeige 7 Tage (3 Tage vor und nach dem aktuellen Tag)"""
    days = []
    for i in range(-3, 4):
        check_date = anchor_date + timedelta(days=i)
        days.append(check_date)
    return days

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_current_kw(d):
    return d.isocalendar()[1]

def load_availability():
    """Lade availability.json mit Cache und robustem Error Handling"""
    cached_data = cache_manager.get("availability")
    if cached_data:
        return cached_data
    
    try:
        with open("static/availability.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            cache_manager.set("availability", "", data)
            return data
    except FileNotFoundError:
        print("Warnung: availability.json nicht gefunden.")
        return {}
    except json.JSONDecodeError:
        print("Warnung: availability.json ist korrupt.")
        return {}
    except Exception as e:
        print(f"Fehler beim Laden der availability.json: {e}")
        return {}

def week_key_from_date(dt):
    return f"{dt.year}-KW{dt.isocalendar()[1]}"

def extract_weekly_summary(availability, current_date=None):
    """Berechnet Wochenverfügbarkeit korrekt - zählt nur zukünftige Slots"""
    week_possible = defaultdict(int)
    week_booked = defaultdict(int)
    week_dates = {}
    
    today = datetime.now(TZ).date()
    
    for slot_time, beraterlist in availability.items():
        try:
            dt = datetime.strptime(slot_time, "%Y-%m-%d %H:%M")
            
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

    # Gebuchte Termine abrufen
    if week_dates:
        from core.mapping.colors import blocks_availability
        
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
                        if dt.date() >= today:
                            color_id = event.get("colorId", "2")
                            if blocks_availability(color_id):
                                key = week_key_from_date(dt)
                                week_booked[key] += 1
                    except Exception as e:
                        print(f"Fehler beim Parsen von Event-Zeit: {e}")
                        continue

    summary = []
    for key, possible in week_possible.items():
        booked = week_booked.get(key, 0)
        start, end = week_dates[key]
        
        usage = (booked / possible) if possible > 0 else 0
        
        summary.append({
            "label": key.replace("-", " "),
            "range": f"{start.strftime('%d.%m.')} — {end.strftime('%d.%m.')}",
            "start_date": start.strftime("%Y-%m-%d"),
            "usage_pct": min(100, int(round(usage * 100))),
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
    """Detaillierte Slot-Zusammenfassung nach Woche und Stunde"""
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
        return [], 0, max_slots, 0, False
    
    events = events_result.get('items', [])
    
    # Filtere Platzhalter-Events
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
    return {"14:00": 4, "16:00": 3, "11:00": 2, "18:00": 2, "09:00": 1, "20:00": 1}.get(hour, 0)

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
from features.gamification.achievements import achievement_system, ACHIEVEMENT_DEFINITIONS
from core.mapping.colors import blocks_availability

def add_points_to_user(user, points):
    """Erweiterte Punkte-Funktion mit Achievement System Integration"""
    try:
        scores = data_persistence.load_scores()
        
        month = datetime.now(TZ).strftime("%Y-%m")
        if user not in scores:
            scores[user] = {}
        if month not in scores[user]:
            scores[user][month] = 0
        
        old_points = scores[user][month]
        scores[user][month] += points
        
        data_persistence.save_scores(scores)
        
        print(f"Punkte gespeichert: {user} +{points} Punkte (Monat: {month}) - Gesamt: {old_points} → {scores[user][month]}")
        
    except Exception as e:
        print(f"Fehler beim Speichern der Punkte: {e}")
        return []
    
    # Achievement System Integration
    try:
        new_badges = achievement_system.add_points_and_check_achievements(user, points)
        if new_badges:
            print(f"{user} hat {len(new_badges)} neue Badge(s) erhalten!")
            return new_badges
    except Exception as e:
        print(f"Achievement System Fehler: {e}")
    
    return []

def check_and_set_champion():
    now = datetime.now(TZ)
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    
    champions = data_persistence.load_champions()
    
    if last_month in champions:
        return champions[last_month]
    
    scores = data_persistence.load_scores()
    
    month_scores = [(u, v.get(last_month, 0)) for u, v in scores.items() if u.lower() not in EXCLUDE_CHAMPION_USERS]
    month_scores = [x for x in month_scores if x[1] > 0]
    month_scores.sort(key=lambda x: x[1], reverse=True)
    
    if month_scores:
        champion_user = month_scores[0][0]
        champions[last_month] = champion_user
        data_persistence.save_champions(champions)
        return champion_user
    return None

def get_champion_for_month(month):
    champions = data_persistence.load_champions()
    return champions.get(month)

def check_for_updates():
    """Prüft auf neue Updates für Real-time Stream"""
    try:
        bookings = load_jsonl_data("data/tracking/bookings.jsonl")
        recent_bookings = [
            b for b in bookings 
            if (datetime.now(TZ) - datetime.fromisoformat(b.get("timestamp", ""))).seconds < 30
        ]
        
        outcomes = load_jsonl_data("data/tracking/outcomes.jsonl")
        recent_outcomes = [
            o for o in outcomes
            if (datetime.now(TZ) - datetime.fromisoformat(o.get("timestamp", ""))).seconds < 30
        ]
        
        updates = {}
        if recent_bookings:
            updates["new_bookings"] = len(recent_bookings)
        if recent_outcomes:
            updates["new_outcomes"] = len(recent_outcomes)
        
        return updates if updates else None
        
    except Exception as e:
        print(f"Update check error: {e}")
        return None

# ----------------- Analytics Functions -----------------
def load_jsonl_data(file_path):
    """Lade JSONL Daten sicher"""
    try:
        data = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data.append(json.loads(line))
                    except:
                        continue
        return data
    except:
        return []

def load_json_data(file_path):
    """Lade JSON Daten sicher"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

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
                flash("Glückwunsch! Du warst Top-Telefonist des letzten Monats!", "success")
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
    
    # Berechne Level-Daten für User
    user = session.get("user")
    user_level = None
    if user:
        user_level = level_system.calculate_user_level(user)
        user_level["progress_color"] = level_system.get_level_progress_color(user_level["progress_to_next"])
        if user_level["best_badge"]:
            user_level["best_badge_color"] = level_system.get_rarity_color(user_level["best_badge"]["rarity"])
    
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
        slot_suggestions=get_slot_suggestions(availability),
        user_level=user_level
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
    
    if result:
        # Tracking hinzufügen
        try:
            tracker = BookingTracker()
            tracker.track_booking(
                customer_name=f"{last}, {first}",
                date=date,
                time_slot=hour,
                user=user or "unknown",
                color_id=color_id,
                description=description
            )
        except Exception as e:
            print(f"Tracking error: {e}")
        
        # Achievement System Integration
        new_badges = []
        if user and user != "unknown" and points > 0:
            new_badges = add_points_to_user(user, points)
            flash(f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) erhalten.", "success")
        elif user and user != "unknown":
            new_badges = add_points_to_user(user, 0)
            flash("Slot erfolgreich gebucht!", "success")
        else:
            flash("Slot erfolgreich gebucht!", "success")

        # Spezielle Badge-Zähler
        try:
            if user and user != "unknown":
                daily_stats = data_persistence.load_daily_user_stats()
                today_key = datetime.now(TZ).strftime("%Y-%m-%d")
                if user not in daily_stats:
                    daily_stats[user] = {}
                if today_key not in daily_stats[user]:
                    daily_stats[user][today_key] = {"points": 0, "bookings": 0, "first_booking": False}
                h_int = int(hour.split(":")[0]) if isinstance(hour, str) and ":" in hour else 0
                if h_int >= 18:
                    daily_stats[user][today_key]["evening_bookings"] = daily_stats[user][today_key].get("evening_bookings", 0) + 1
                elif 9 <= h_int < 12:
                    daily_stats[user][today_key]["morning_bookings"] = daily_stats[user][today_key].get("morning_bookings", 0) + 1
                data_persistence.save_daily_user_stats(daily_stats)
        except Exception as e:
            print(f"Konnte Spezial-Badge-Zähler nicht aktualisieren: {e}")
        
        # Zeige neue Badges an
        if new_badges:
            badge_names = [badge["name"] for badge in new_badges]
            flash(f"Neue Badges erhalten: {', '.join(badge_names)}", "success")
    else:
        flash("Fehler beim Buchen des Slots. Bitte versuche es später erneut.", "danger")
    
    return redirect(url_for("day_view", date_str=date))

@app.route("/scoreboard")
def scoreboard():
    user = session.get("user")
    scores = data_persistence.load_scores()
    
    month = datetime.now(TZ).strftime("%Y-%m")
    ranking = sorted([(u, v.get(month, 0)) for u, v in scores.items()], key=lambda x: x[1], reverse=True)
    user_score = scores.get(user, {}).get(month, 0) if user else 0
    champion = get_champion_for_month((datetime.now(TZ).replace(day=1) - timedelta(days=1)).strftime("%Y-%m"))
    
    try:
        badge_leaderboard = achievement_system.get_badge_leaderboard()
    except Exception as e:
        print(f"Badge Leaderboard Fehler: {e}")
        badge_leaderboard = []
    
    return render_template("scoreboard.html", 
                         ranking=ranking, 
                         user_score=user_score, 
                         month=month, 
                         current_user=user, 
                         champion=champion,
                         badge_leaderboard=badge_leaderboard)

@app.route("/badges")
def badges():
    """Badge-Übersicht für alle User"""
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    try:
        user_badges = achievement_system.get_user_badges(user)
        leaderboard = achievement_system.get_badge_leaderboard()
        total_badges = user_badges.get("total_badges", 0)
        available_badges = ACHIEVEMENT_DEFINITIONS
        badge_progress = achievement_system.get_badge_progress(user)
        
    except Exception as e:
        print(f"Badge System Fehler: {e}")
        user_badges = {"badges": [], "total_badges": 0}
        leaderboard = []
        total_badges = 0
        available_badges = ACHIEVEMENT_DEFINITIONS
        badge_progress = {}
    
    return render_template("badges.html", 
                         user_badges=user_badges,
                         leaderboard=leaderboard,
                         current_user=user,
                         total_badges=total_badges,
                         available_badges=available_badges,
                         badge_progress=badge_progress)

@app.route("/gamification")
def gamification_dashboard():
    """Gamification-Dashboard mit allen Statistiken"""
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    try:
        user_level = level_system.calculate_user_level(user)
        user_badges = achievement_system.get_user_badges(user)
        
        daily_stats = data_persistence.load_daily_user_stats()
        streak_info = achievement_system.calculate_advanced_streak(daily_stats.get(user, {}))
        next_goals = achievement_system.get_next_achievements(user)
        
        badge_stats = {
            "by_rarity": {
                "common": 0, "uncommon": 0, "rare": 0,
                "epic": 0, "legendary": 0, "mythic": 0
            },
            "total": len(user_badges.get("badges", []))
        }
        
        for badge in user_badges.get("badges", []):
            rarity = badge.get("rarity", "common")
            if rarity in badge_stats["by_rarity"]:
                badge_stats["by_rarity"][rarity] += 1
        
        rarity_colors = {
            "common": "#10b981", "uncommon": "#3b82f6", "rare": "#8b5cf6",
            "epic": "#f59e0b", "legendary": "#eab308", "mythic": "#ec4899"
        }
        
        scores = data_persistence.load_scores()
        month = datetime.now(TZ).strftime("%Y-%m")
        current_month_points = scores.get(user, {}).get(month, 0)
        
        month_ranking = sorted([(u, v.get(month, 0)) for u, v in scores.items()], key=lambda x: x[1], reverse=True)
        user_rank = next((i+1 for i, (u, _) in enumerate(month_ranking) if u == user), 0)
        
        return render_template("gamification.html",
                             user_level=user_level,
                             user_badges=user_badges,
                             badge_stats=badge_stats,
                             streak_info=streak_info,
                             next_goals=next_goals,
                             rarity_colors=rarity_colors,
                             current_user=user,
                             current_month_points=current_month_points,
                             user_rank=user_rank,
                             total_players=len(month_ranking))
    except Exception as e:
        print(f"Gamification Dashboard Fehler: {e}")
        # Fallback-Daten
        return render_template("gamification.html",
                             user_level={"level": 1, "level_title": "Anfänger"},
                             user_badges={"badges": [], "total_badges": 0},
                             current_user=user)

@app.route("/my-calendar")
def my_calendar():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    today = datetime.now(TZ).date()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    
    my_events = []
    
    # Google Calendar Events
    events_result = safe_calendar_call(
        service.events().list,
        calendarId=CENTRAL_CALENDAR_ID,
        timeMin=TZ.localize(datetime.combine(start, datetime.min.time())).isoformat(),
        timeMax=TZ.localize(datetime.combine(end, datetime.max.time())).isoformat(),
        singleEvents=True,
        orderBy='startTime'
    )
    
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
                        "desc": event.get("description", ""),
                        "source": "calendar"
                    })
                except Exception as e:
                    print(f"Fehler beim Parsen von Event: {e}")
                    continue
    
    # Getrackte Buchungen
    try:
        tracker = BookingTracker()
        tracked_bookings = tracker.get_user_bookings(user, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        
        for booking in tracked_bookings:
            try:
                booking_date = datetime.strptime(booking["date"], "%Y-%m-%d")
                if start <= booking_date.date() <= end:
                    points = get_slot_points(booking["time_slot"], booking_date.date())
                    my_events.append({
                        "date": booking_date.strftime("%A, %d.%m.%Y"),
                        "hour": booking["time_slot"],
                        "summary": f"📞 {booking['customer_name']}",
                        "color_id": booking["color_id"],
                        "points": points,
                        "desc": booking.get("description", ""),
                        "source": "tracking"
                    })
            except Exception as e:
                print(f"Fehler beim Parsen von getrackter Buchung: {e}")
                continue
                
    except Exception as e:
        print(f"Fehler beim Laden getrackter Buchungen: {e}")
    
    my_events.sort(key=lambda e: (e["date"], e["hour"]))
    
    return render_template("my_calendar.html", my_events=my_events, user=user)

@app.route("/stream/updates")
def stream_updates():
    """Server-Sent Events für Real-time Updates"""
    def generate():
        while True:
            try:
                updates = check_for_updates()
                if updates:
                    yield f"data: {json.dumps(updates)}\n\n"
                time.sleep(5)
            except Exception as e:
                print(f"Stream error: {e}")
                break
    
    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )

# ----------------- Admin Routes -----------------
@app.route("/admin/dashboard")
def admin_dashboard():
    """Admin Dashboard mit Statistiken"""
    user = session.get("user")
    if not is_admin(user):
        flash("Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    try:
        tracker = BookingTracker()
        dashboard_data = tracker.get_enhanced_dashboard()
        
        return render_template("admin_dashboard_enhanced.html",
                             dashboard=dashboard_data,
                             days_running=get_app_runtime_days())
        
    except Exception as e:
        print(f"Error in admin dashboard: {e}")
        flash(f"Fehler beim Laden des Dashboards: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.route("/admin/insights")
def admin_insights():
    """Detaillierte Insights und Predictions"""
    user = session.get("user")
    if not is_admin(user):
        flash("Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    try:
        tracker = BookingTracker()
        
        insights = {
            "time_patterns": {"status": "success", "patterns": {}},
            "customer_behavior": {"champions_count": 0, "loyals_count": 0},
            "success_factors": {"status": "success", "factors": {}},
            "predictions": {"status": "success", "predictions": {}},
            "recommendations": {"status": "success", "recommendations": []}
        }
        
        return render_template("admin_insights.html", insights=insights)
        
    except Exception as e:
        print(f"Error in insights: {e}")
        flash(f"Fehler beim Laden der Insights: {str(e)}", "danger")
        return redirect(url_for("admin_dashboard"))

@app.route("/admin/users")
def admin_users():
    """Admin Route um alle aktiven User anzuzeigen"""
    user = session.get("user")
    if not is_admin(user):
        flash("Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    try:
        active_users = get_all_active_users()
        base_users = get_userlist()
        
        users_info = []
        for username in active_users:
            user_info = {
                "username": username,
                "in_userlist": username in base_users,
                "password": base_users.get(username, "Auto-generiert"),
                "has_bookings": False,
                "total_bookings": 0,
                "current_month_points": 0
            }
            
            try:
                tracker = BookingTracker()
                if os.path.exists(tracker.bookings_file):
                    with open(tracker.bookings_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    booking = json.loads(line)
                                    if booking.get("user") == username:
                                        user_info["has_bookings"] = True
                                        user_info["total_bookings"] += 1
                                except json.JSONDecodeError:
                                    continue
                
                scores = data_persistence.load_scores()
                month = datetime.now(TZ).strftime("%Y-%m")
                user_info["current_month_points"] = scores.get(username, {}).get(month, 0)
                
            except Exception as e:
                print(f"Fehler beim Laden der User-Daten für {username}: {e}")
            
            users_info.append(user_info)
        
        users_info.sort(key=lambda x: x["current_month_points"], reverse=True)
        
        return render_template("admin_users.html", 
                             users=users_info,
                             total_users=len(users_info),
                             base_users_count=len(base_users))
        
    except Exception as e:
        flash(f"Fehler beim Laden der User-Liste: {e}", "danger")
        return redirect(url_for("index"))

@app.route("/admin/fix-points")
def admin_fix_points():
    """Admin Route um Punkte für bereits getrackte Buchungen zu vergeben"""
    user = session.get("user")
    if not is_admin(user):
        flash("Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    try:
        tracker = BookingTracker()
        all_bookings = tracker.load_all_bookings()
        
        fixed_count = 0
        already_processed = set()
        
        for booking in all_bookings:
            user_name = booking.get("user")
            if user_name and user_name != "unknown":
                booking_id = f"{booking.get('date')}_{booking.get('time')}_{user_name}"
                
                if booking_id in already_processed:
                    continue
                
                time_slot = booking.get("time")
                date = booking.get("date")
                if time_slot and date:
                    try:
                        booking_date = datetime.strptime(date, "%Y-%m-%d").date()
                        points = get_slot_points(time_slot, booking_date)
                        
                        if points > 0:
                            add_points_to_user(user_name, points)
                            fixed_count += 1
                            already_processed.add(booking_id)
                            print(f"Punkte vergeben: {user_name} +{points} für {date} {time_slot}")
                            
                    except Exception as e:
                        print(f"Fehler bei Buchung {booking.get('id', 'unknown')}: {e}")
        
        if fixed_count > 0:
            flash(f"✅ {fixed_count} Buchungen mit Punkten versehen!", "success")
        else:
            flash("ℹ️ Keine neuen Buchungen für Punkte-Vergabe gefunden.", "info")
        
    except Exception as e:
        flash(f"Fehler beim Punkte-Fix: {e}", "danger")
    
    return redirect(url_for("index"))

# ----------------- Telefonie Punkte Backend -----------------
@app.route("/admin/telefonie", methods=["GET", "POST"])
def admin_telefonie():
    user = session.get("user")
    if not is_admin(user):
        flash("Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))

    selected_week = request.args.get("week") or get_week_key()
    recent_weeks = list_recent_weeks(12)
    participants = get_participants()

    if request.method == "POST":
        action = request.form.get("action")
        target_week = request.form.get("week") or selected_week
        target_user = request.form.get("user")

        try:
            if action == "set_goal":
                goal_points = int(request.form.get("goal_points", 0))
                set_week_goal(target_week, target_user, goal_points, set_by=user)
                flash("Ziel gespeichert.", "success")
            elif action == "add_activity":
                kind = request.form.get("kind")
                points = int(request.form.get("points", 0))
                note = request.form.get("note", "")
                record_activity(target_week, target_user, kind, points, set_by=user, note=note)
                flash("Aktivität erfasst.", "success")
            elif action == "add_participant":
                name = request.form.get("name", "").strip()
                if name:
                    add_participant(name)
                    flash(f"Teilnehmer hinzugefügt: {name}", "success")
                    
            return redirect(url_for("admin_telefonie", week=target_week))
        except Exception as e:
            flash(f"Fehler: {str(e)}", "danger")
            return redirect(url_for("admin_telefonie", week=target_week))

    stats = compute_week_stats(selected_week, participants)
    audit_entries = get_week_audit(selected_week)
    in_window = is_in_commit_window()

    return render_template(
        "admin_telefonie.html",
        week=selected_week,
        recent_weeks=recent_weeks,
        participants=participants,
        stats=stats,
        audit=audit_entries,
        in_window=in_window,
        now=datetime.now(TZ),
    )

# ----------------- API Endpoints -----------------
@app.route("/api/user/badges")
def api_user_badges():
    """API Endpoint für User Badges"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Nicht eingeloggt"}), 401
    
    try:
        user_badges = achievement_system.get_user_badges(user)
        return jsonify(user_badges)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/badges/backfill")
def admin_badges_backfill():
    """Reparaturroutine: Vergibt persistente Badges rückwirkend"""
    user = session.get("user")
    if not is_admin(user):
        flash("Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))

    try:
        result = achievement_system.backfill_persistent_badges()
        achievement_system.auto_check_mvp_badges()
        cnt = result.get("badges_awarded", 0)
        users = result.get("users_processed", 0)
        flash(f"Backfill abgeschlossen: {cnt} Badges neu vergeben (über {users} Nutzer).", "success")
    except Exception as e:
        flash(f"Backfill-Fehler: {e}", "danger")
    return redirect(url_for("scoreboard"))

@app.route("/admin/maintenance/run")
@limiter.limit("6 per hour; 2 per minute")
def admin_run_maintenance():
    """Geschützter Endpoint für tägliche Maintenance (Cron)"""
    token = request.headers.get("X-CRON-TOKEN") or request.args.get("token")
    expected = os.environ.get("CRON_TOKEN")
    if not expected or token != expected:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data_persistence.auto_cleanup_backups()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/healthz")
def healthz():
    """Health-Check"""
    try:
        ok, issues = data_persistence.validate_data_integrity()
        statvfs = os.statvfs(".")
        free_mb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 * 1024)
        return jsonify({
            "status": "ok" if ok else "degraded",
            "free_disk_mb": round(free_mb, 1),
            "issues": issues
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)