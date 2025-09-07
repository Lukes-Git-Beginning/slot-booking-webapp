import os
import json
import pytz
import time
from tracking_system import BookingTracker
from data_persistence import data_persistence
from level_system import level_system
from collections import defaultdict
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from creds_loader import load_google_credentials
from cache_manager import cache_manager
import matplotlib
matplotlib.use('Agg')  # Für Server ohne Display
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import io
import base64
from matplotlib.dates import DateFormatter
from collections import defaultdict
import numpy as np
from weekly_points import (
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

# ----------------- Flask Setup -----------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me-to-random-string-now")

# ----------------- Google Calendar API Setup -----------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = load_google_credentials(SCOPES)
service = build("calendar", "v3", credentials=creds)

CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")
TZ = pytz.timezone("Europe/Berlin")

# ----------------- Persistenz Bootstrap & Backup-Cleanup -----------------
# Stelle sicher, dass Persist-Daten vorhanden sind (Migration von static falls nötig)
try:
    data_persistence.bootstrap_from_static_if_missing()
    # Optional: altes Backup aufräumen beim Start
    data_persistence.auto_cleanup_backups()
except Exception as _e:
    print(f"⚠️ Persistenz-Init Hinweis: {_e}")

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
            elif status == 403:  # Permission denied
                print(f"[Calendar] Permission denied: {e}")
                return None
            elif status == 404:  # Not found
                print(f"[Calendar] Resource not found: {e}")
                return None
            elif status and status >= 500:  # Server error
                wait_time = 2 ** attempt
                print(f"[Calendar] Server-Fehler {status}, retry in {wait_time}s …")
                time.sleep(wait_time)
                continue
            else:  # andere HTTP Fehler
                print(f"[Calendar] HTTP-Fehler {status}: {e}")
                return None
        except ConnectionError as e:
            print(f"[Calendar] Verbindungsfehler: {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt)
        except TimeoutError as e:
            print(f"[Calendar] Timeout: {e}")
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
# 2. ADMIN-CHECK FUNKTIONEN

def is_admin(user):
    """Prüft ob User Admin-Rechte hat"""
    admin_users = ["admin", "Admin", "administrator", "Jose", "Simon", "Alex", "David"]  # <-- Adminliste erweitert
    return user and user.lower() in [u.lower() for u in admin_users]

def check_admin_access():
    """Decorator-ähnliche Funktion für Admin-Check"""
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return False
    return True

def get_app_runtime_days():
    """Berechnet wie lange die App schon läuft"""
    # Dashboard ist jetzt immer verfügbar - keine Zeitbeschränkung mehr
    app_start_date = datetime(2025, 9, 1)  # Früherer Start für mehr "Laufzeit"
    app_start_localized = TZ.localize(app_start_date)
    
    days_running = (datetime.now(TZ) - app_start_localized).days
    return max(30, days_running)  # Mindestens 30 Tage für vollständigen Zugriff

def get_color_mapping_status():
    """Gebe Color-Mapping Status für Admin Dashboard zurück"""
    from color_mapping import CALENDAR_COLORS, NON_BLOCKING_COLORS, BLOCKING_COLORS
    
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

def get_week_days(anchor_date):
    """Zeige 7 Tage (3 Tage vor und nach dem aktuellen Tag)"""
    days = []
    for i in range(-3, 4):  # -3 bis +3 Tage
        check_date = anchor_date + timedelta(days=i)
        days.append(check_date)
    return days

def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_current_kw(d):
    return d.isocalendar()[1]

def load_availability():
    """Lade availability.json mit Cache und robustem Error Handling"""
    # Prüfe Cache zuerst
    cached_data = cache_manager.get("availability")
    if cached_data:
        return cached_data
    
    try:
        with open("static/availability.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            # Cache die Daten
            cache_manager.set("availability", "", data)
            return data
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
                            # WICHTIG: Prüfe ob Event die Verfügbarkeit blockiert
                            color_id = event.get("colorId", "2")  # Default: Grün
                            if blocks_availability(color_id):  # Nur blockierende Events zählen
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
from achievement_system import achievement_system, ACHIEVEMENT_DEFINITIONS
from color_mapping import blocks_availability

def add_points_to_user(user, points):
    """
    Erweiterte Punkte-Funktion mit Achievement System Integration
    """
    try:
        # Speichere Scores mit robustem Persistenz-System
        scores = data_persistence.load_scores()
        
        month = datetime.now(TZ).strftime("%Y-%m")
        if user not in scores:
            scores[user] = {}
        if month not in scores[user]:
            scores[user][month] = 0
        
        old_points = scores[user][month]
        scores[user][month] += points
        
        # Speichere aktualisierte Scores mit Backup
        data_persistence.save_scores(scores)
        
        print(f"✅ Punkte gespeichert: {user} +{points} Punkte (Monat: {month}) - Gesamt: {old_points} → {scores[user][month]}")
        
    except Exception as e:
        print(f"❌ Fehler beim Speichern der Punkte: {e}")
        return []
    
    # NEU: Achievement System Integration
    try:
        new_badges = achievement_system.add_points_and_check_achievements(user, points)
        if new_badges:
            print(f"🎖️ {user} hat {len(new_badges)} neue Badge(s) erhalten!")
            return new_badges
    except Exception as e:
        print(f"⚠️ Achievement System Fehler: {e}")
    
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
def load_detailed_metrics():
    """Lade und berechne detaillierte Metriken"""
    try:
        metrics_file = "data/tracking/daily_metrics.json"
        if not os.path.exists(metrics_file):
            return {"no_show_trend": [], "completion_trend": [], "dates": []}
            
        with open(metrics_file, "r", encoding="utf-8") as f:
            all_metrics = json.load(f)
        
        # Prüfe ob all_metrics ein Dictionary ist
        if not isinstance(all_metrics, dict):
            return {"no_show_trend": [], "completion_trend": [], "dates": []}
        
        # Filtere nur Datums-Schlüssel (YYYY-MM-DD Format)
        date_keys = [key for key in all_metrics.keys() 
                    if isinstance(key, str) and len(key) == 10 and key.count('-') == 2]
        
        # Berechne Trends der letzten 14 Tage
        dates = sorted(date_keys)[-14:]
        
        trends = {
            "no_show_trend": [],
            "completion_trend": [],
            "dates": dates
        }
        
        for date in dates:
            if date in all_metrics and isinstance(all_metrics[date], dict):
                trends["no_show_trend"].append(all_metrics[date].get("no_show_rate", 0))
                trends["completion_trend"].append(all_metrics[date].get("completion_rate", 0))
            else:
                trends["no_show_trend"].append(0)
                trends["completion_trend"].append(0)
        
        return trends
        
    except Exception as e:
        print(f"❌ Error loading detailed metrics: {e}")
        return {"no_show_trend": [], "completion_trend": [], "dates": []}

def generate_dashboard_charts(tracker):
    """Generiere Chart-Daten für Frontend"""
    charts = {
        "time_series": {"dates": [], "no_show_rates": [], "completion_rates": []},
        "hourly_performance": {"hours": [], "no_show_rates": []},
        "risk_distribution": {"low": 0, "medium": 0, "high": 0}
    }
    
    try:
        # 1. Time Series Chart
        metrics_file = tracker.metrics_file
        if os.path.exists(metrics_file):
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)
            
            # Prüfe ob metrics ein Dictionary ist
            if not isinstance(metrics, dict):
                return charts
            
            # Filtere nur Datums-Schlüssel (YYYY-MM-DD Format)
            date_keys = [key for key in metrics.keys() 
                        if isinstance(key, str) and len(key) == 10 and key.count('-') == 2]
            dates = sorted(date_keys)[-30:]  # Letzte 30 Tage
            
            for date in dates:
                if date in metrics and isinstance(metrics[date], dict):
                    try:
                        charts["time_series"]["dates"].append(
                            datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m")
                        )
                        charts["time_series"]["no_show_rates"].append(
                            metrics[date].get("no_show_rate", 0)
                        )
                        charts["time_series"]["completion_rates"].append(
                            metrics[date].get("completion_rate", 0)
                        )
                    except ValueError as e:
                        print(f"❌ Error parsing date '{date}': {e}")
                        continue
        
        # 2. Hourly Performance
        if os.path.exists(tracker.outcomes_file):
            hour_performance = defaultdict(lambda: {"total": 0, "no_shows": 0})
            
            with open(tracker.outcomes_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        outcome = json.loads(line)
                        hour = outcome["time"][:2]
                        hour_performance[hour]["total"] += 1
                        if outcome["outcome"] == "no_show":
                            hour_performance[hour]["no_shows"] += 1
                    except:
                        continue
            
            hours = sorted(hour_performance.keys())
            for hour in hours:
                data = hour_performance[hour]
                if data["total"] > 0:  # Nur Stunden mit Daten
                    rate = (data["no_shows"] / data["total"] * 100)
                    charts["hourly_performance"]["hours"].append(f"{hour}:00")
                    charts["hourly_performance"]["no_show_rates"].append(round(rate, 1))
        
        # 3. Risk Distribution
        if os.path.exists(tracker.customer_file):
            with open(tracker.customer_file, "r", encoding="utf-8") as f:
                profiles = json.load(f)
            
            for profile in profiles.values():
                risk_level = profile.get("risk_level", "low")
                if risk_level in charts["risk_distribution"]:
                    charts["risk_distribution"][risk_level] += 1
        
    except Exception as e:
        print(f"❌ Error generating charts: {e}")
    
    return charts

def get_customer_risk_analysis(tracker):
    """Analysiere Kunden-Risiko Patterns"""
    risk_analysis = {
        "high_risk_customers": [],
        "improvement_candidates": [],
        "loyal_customers": [],
        "new_customers": []
    }
    
    try:
        if not os.path.exists(tracker.customer_file):
            return risk_analysis
            
        with open(tracker.customer_file, "r", encoding="utf-8") as f:
            profiles = json.load(f)
        
        for customer, profile in profiles.items():
            total_appointments = profile.get("total_appointments", 0)
            reliability_score = profile.get("reliability_score", 0)
            no_shows = profile.get("no_shows", 0)
            
            customer_data = {
                "name": customer[:50],  # Begrenzte Länge für UI
                "no_shows": no_shows,
                "total_appointments": total_appointments,
                "reliability_score": reliability_score
            }
            
            if no_shows >= 3:
                risk_analysis["high_risk_customers"].append(customer_data)
            elif total_appointments <= 2:
                risk_analysis["new_customers"].append(customer_data)
            elif reliability_score >= 80:
                risk_analysis["loyal_customers"].append(customer_data)
            elif 40 <= reliability_score < 80:
                risk_analysis["improvement_candidates"].append(customer_data)
        
        # Sortiere Listen
        risk_analysis["high_risk_customers"].sort(key=lambda x: x["no_shows"], reverse=True)
        risk_analysis["loyal_customers"].sort(key=lambda x: x["reliability_score"], reverse=True)
        
        # Limitiere für UI Performance
        for key in risk_analysis:
            risk_analysis[key] = risk_analysis[key][:20]  # Max 20 pro Kategorie
        
    except Exception as e:
        print(f"❌ Error in risk analysis: {e}")
    
    return risk_analysis

def prepare_ml_insights(tracker):
    """Vorbereitung für Machine Learning Insights"""
    ml_insights = {
        "data_readiness": check_data_readiness(tracker),
        "pattern_detection": detect_basic_patterns(tracker),
        "prediction_readiness": assess_prediction_readiness(tracker),
        "recommended_models": get_recommended_models()
    }
    
    return ml_insights

def check_data_readiness(tracker):
    """Prüfe ob genug Daten für ML vorhanden sind"""
    try:
        bookings_count = 0
        outcomes_count = 0
        
        if os.path.exists(tracker.bookings_file):
            bookings_count = sum(1 for _ in open(tracker.bookings_file, 'r', encoding='utf-8'))
        
        if os.path.exists(tracker.outcomes_file):
            outcomes_count = sum(1 for _ in open(tracker.outcomes_file, 'r', encoding='utf-8'))
        
        customers = 0
        if os.path.exists(tracker.customer_file):
            with open(tracker.customer_file, 'r', encoding='utf-8') as f:
                customers = len(json.load(f))
        
        days_with_data = 0
        if os.path.exists(tracker.metrics_file):
            with open(tracker.metrics_file, 'r', encoding='utf-8') as f:
                days_with_data = len(json.load(f))
        
        # Scoring basierend auf Datenmenge
        readiness_score = min(100, (
            min(bookings_count / 1000, 1) * 25 +  # Min 1000 Bookings für 25%
            min(outcomes_count / 800, 1) * 25 +    # Min 800 Outcomes für 25%
            min(customers / 200, 1) * 25 +         # Min 200 Customers für 25%
            min(days_with_data / 30, 1) * 25       # Min 30 Days für 25%
        ))
        
        return {
            "score": round(readiness_score, 1),
            "bookings": bookings_count,
            "outcomes": outcomes_count,
            "customers": customers,
            "days": days_with_data,
            "ready_for_ml": readiness_score >= 75
        }
        
    except Exception as e:
        print(f"❌ Error checking data readiness: {e}")
        return {"score": 0, "ready_for_ml": False, "bookings": 0, "outcomes": 0, "customers": 0, "days": 0}

def detect_basic_patterns(tracker):
    """Erkenne grundlegende Patterns in den Daten"""
    patterns = {
        "time_patterns": {},
        "day_patterns": {},
        "seasonal_patterns": {},
        "customer_patterns": {}
    }
    
    try:
        if not os.path.exists(tracker.outcomes_file):
            return patterns
            
        # Analysiere Outcomes nach Stunden
        hour_stats = defaultdict(lambda: {"total": 0, "no_shows": 0})
        day_stats = defaultdict(lambda: {"total": 0, "no_shows": 0})
        
        with open(tracker.outcomes_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    outcome = json.loads(line)
                    hour = int(outcome["time"][:2])
                    date_obj = datetime.strptime(outcome["date"], "%Y-%m-%d")
                    day_name = date_obj.strftime("%A")
                    
                    hour_stats[hour]["total"] += 1
                    day_stats[day_name]["total"] += 1
                    
                    if outcome["outcome"] == "no_show":
                        hour_stats[hour]["no_shows"] += 1
                        day_stats[day_name]["no_shows"] += 1
                except:
                    continue
        
        # Beste und schlechteste Stunden
        hour_rates = {}
        for hour, stats in hour_stats.items():
            if stats["total"] >= 5:  # Nur bei genug Daten
                rate = (stats["no_shows"] / stats["total"]) * 100
                hour_rates[hour] = round(rate, 1)
        
        if hour_rates:
            patterns["time_patterns"] = {
                "best_hour": min(hour_rates, key=hour_rates.get),
                "worst_hour": max(hour_rates, key=hour_rates.get),
                "hour_rates": hour_rates
            }
        
        # Tag-Pattern
        day_rates = {}
        for day, stats in day_stats.items():
            if stats["total"] >= 3:
                rate = (stats["no_shows"] / stats["total"]) * 100
                day_rates[day] = round(rate, 1)
        
        if day_rates:
            patterns["day_patterns"] = {
                "best_day": min(day_rates, key=day_rates.get),
                "worst_day": max(day_rates, key=day_rates.get),
                "day_rates": day_rates
            }
        
    except Exception as e:
        print(f"❌ Error detecting patterns: {e}")
    
    return patterns

def assess_prediction_readiness(tracker):
    """Bewerte wie bereit das System für Predictions ist"""
    try:
        if not os.path.exists(tracker.outcomes_file):
            return {
                "ready": False,
                "reason": "Keine Outcome-Daten verfügbar",
                "confidence": "low"
            }
        
        # Prüfe Datenqualität und -menge
        with open(tracker.outcomes_file, 'r', encoding='utf-8') as f:
            outcomes = []
            for line in f:
                try:
                    outcomes.append(json.loads(line))
                except:
                    continue
        
        if len(outcomes) < 100:
            return {
                "ready": False,
                "reason": f"Nicht genug Daten ({len(outcomes)} von mind. 100 Outcomes)",
                "confidence": "low"
            }
        
        # Prüfe Datenverteilung
        outcome_distribution = defaultdict(int)
        for outcome in outcomes:
            outcome_distribution[outcome["outcome"]] += 1
        
        total_outcomes = len(outcomes)
        no_show_rate = outcome_distribution["no_show"] / total_outcomes if total_outcomes > 0 else 0
        
        if no_show_rate < 0.05 or no_show_rate > 0.8:
            return {
                "ready": False,
                "reason": f"Unbalanced data (No-Show Rate: {no_show_rate*100:.1f}%)",
                "confidence": "medium",
                "data_points": total_outcomes,
                "no_show_rate": round(no_show_rate * 100, 1)
            }
        
        return {
            "ready": True,
            "confidence": "high" if len(outcomes) >= 500 else "medium",
            "data_points": len(outcomes),
            "no_show_rate": round(no_show_rate * 100, 1)
        }
        
    except Exception as e:
        return {"ready": False, "reason": f"Error: {str(e)}", "confidence": "low"}

def get_recommended_models():
    """Empfehle ML-Modelle basierend auf dem Use Case"""
    return [
        {
            "name": "Logistic Regression",
            "use_case": "No-Show Prediction",
            "complexity": "Low",
            "accuracy_expectation": "70-80%",
            "implementation_effort": "Easy"
        },
        {
            "name": "Random Forest",
            "use_case": "Customer Risk Classification",
            "complexity": "Medium",
            "accuracy_expectation": "75-85%",
            "implementation_effort": "Medium"
        },
        {
            "name": "XGBoost",
            "use_case": "Advanced Pattern Recognition",
            "complexity": "High",
            "accuracy_expectation": "80-90%",
            "implementation_effort": "High"
        }
    ]

# ----------------- Analytics & Prediction Functions -----------------
def analyze_time_patterns(tracker):
    """Analysiert Zeitmuster in Buchungen und Outcomes"""
    try:
        bookings = load_jsonl_data(tracker.bookings_file)
        outcomes = load_jsonl_data(tracker.outcomes_file)
        
        if not bookings and not outcomes:
            return {"status": "No data available", "patterns": {}}
        
        # Zeitmuster-Analyse
        hour_distribution = defaultdict(int)
        weekday_distribution = defaultdict(int)
        lead_time_distribution = defaultdict(int)
        
        for booking in bookings:
            hour = booking.get("booked_at_hour", 0)
            weekday = booking.get("booked_on_weekday", "Unknown")
            lead_time = booking.get("booking_lead_time", 0)
            
            hour_distribution[hour] += 1
            weekday_distribution[weekday] += 1
            lead_time_distribution[lead_time] += 1
        
        # Outcome-Zeitmuster
        outcome_by_hour = defaultdict(lambda: defaultdict(int))
        for outcome in outcomes:
            hour = int(outcome.get("time", "00:00").split(":")[0])
            outcome_type = outcome.get("outcome", "unknown")
            outcome_by_hour[hour][outcome_type] += 1
        
        return {
            "status": "success",
            "patterns": {
                "peak_hours": sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
                "peak_weekdays": sorted(weekday_distribution.items(), key=lambda x: x[1], reverse=True),
                "avg_lead_time": sum(lead_time_distribution.keys()) / len(lead_time_distribution) if lead_time_distribution else 0,
                "outcome_patterns": dict(outcome_by_hour)
            }
        }
    except Exception as e:
        return {"status": f"Error: {str(e)}", "patterns": {}}

def analyze_customer_behavior(tracker):
    """Analysiert Kundenverhalten und Kategorisierung"""
    try:
        customer_profiles = load_json_data(tracker.customer_file)
        
        if not customer_profiles:
            return {"champions_count": 0, "loyals_count": 0, "potential_count": 0, "risk_count": 0}
        
        champions = 0
        loyals = 0
        potential = 0
        risk = 0
        
        for customer, profile in customer_profiles.items():
            reliability = profile.get("reliability_score", 0)
            appointments = profile.get("total_appointments", 0)
            
            if reliability >= 90 and appointments >= 3:
                champions += 1
            elif reliability >= 80 and appointments >= 2:
                loyals += 1
            elif appointments >= 1:
                potential += 1
            else:
                risk += 1
        
        return {
            "champions_count": champions,
            "loyals_count": loyals, 
            "potential_count": potential,
            "risk_count": risk,
            "total_customers": len(customer_profiles)
        }
    except Exception as e:
        return {"status": f"Error: {str(e)}", "champions_count": 0, "loyals_count": 0, "potential_count": 0, "risk_count": 0}

def analyze_success_factors(tracker):
    """Analysiert Erfolgsfaktoren für Termine"""
    try:
        outcomes = load_jsonl_data(tracker.outcomes_file)
        
        if not outcomes:
            return {"status": "No data available", "factors": {}}
        
        # Erfolgsfaktoren-Analyse
        success_by_time = defaultdict(lambda: {"completed": 0, "total": 0})
        success_by_weekday = defaultdict(lambda: {"completed": 0, "total": 0})
        success_by_lead_time = defaultdict(lambda: {"completed": 0, "total": 0})
        
        for outcome in outcomes:
            time_slot = outcome.get("time", "00:00")
            weekday = datetime.strptime(outcome.get("date", "2025-01-01"), "%Y-%m-%d").strftime("%A")
            outcome_type = outcome.get("outcome", "unknown")
            
            # Gruppiere nach Zeit-Slots
            hour = int(time_slot.split(":")[0])
            time_group = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
            
            success_by_time[time_group]["total"] += 1
            if outcome_type == "completed":
                success_by_time[time_group]["completed"] += 1
            
            success_by_weekday[weekday]["total"] += 1
            if outcome_type == "completed":
                success_by_weekday[weekday]["completed"] += 1
        
        # Berechne Erfolgsraten
        time_success_rates = {}
        for time_group, data in success_by_time.items():
            if data["total"] > 0:
                time_success_rates[time_group] = round((data["completed"] / data["total"]) * 100, 1)
        
        weekday_success_rates = {}
        for weekday, data in success_by_weekday.items():
            if data["total"] > 0:
                weekday_success_rates[weekday] = round((data["completed"] / data["total"]) * 100, 1)
        
        return {
            "status": "success",
            "factors": {
                "time_success_rates": time_success_rates,
                "weekday_success_rates": weekday_success_rates,
                "best_time": max(time_success_rates.items(), key=lambda x: x[1]) if time_success_rates else None,
                "best_weekday": max(weekday_success_rates.items(), key=lambda x: x[1]) if weekday_success_rates else None
            }
        }
    except Exception as e:
        return {"status": f"Error: {str(e)}", "factors": {}}

def generate_predictions(tracker):
    """Generiert Vorhersagen basierend auf historischen Daten"""
    try:
        outcomes = load_jsonl_data(tracker.outcomes_file)
        customer_profiles = load_json_data(tracker.customer_file)
        
        if not outcomes:
            return {"status": "No data available", "predictions": {}}
        
        # Einfache Vorhersagen basierend auf historischen Daten
        total_outcomes = len(outcomes)
        completed = sum(1 for o in outcomes if o.get("outcome") == "completed")
        no_shows = sum(1 for o in outcomes if o.get("outcome") == "no_show")
        
        if total_outcomes == 0:
            return {"status": "No data available", "predictions": {}}
        
        # Berechne Raten
        completion_rate = (completed / total_outcomes) * 100
        no_show_rate = (no_shows / total_outcomes) * 100
        
        # Vorhersage für nächste Woche (basierend auf aktueller Rate)
        avg_daily_outcomes = total_outcomes / 30 if total_outcomes > 0 else 0  # Annahme: 30 Tage Daten
        
        return {
            "status": "success",
            "predictions": {
                "completion_rate": round(completion_rate, 1),
                "no_show_rate": round(no_show_rate, 1),
                "predicted_weekly_completions": round(avg_daily_outcomes * 7 * (completion_rate / 100), 1),
                "predicted_weekly_no_shows": round(avg_daily_outcomes * 7 * (no_show_rate / 100), 1),
                "confidence_level": "medium" if total_outcomes > 50 else "low"
            }
        }
    except Exception as e:
        return {"status": f"Error: {str(e)}", "predictions": {}}

def generate_recommendations(tracker):
    """Generiert Empfehlungen für Optimierung"""
    try:
        success_factors = analyze_success_factors(tracker)
        customer_behavior = analyze_customer_behavior(tracker)
        
        recommendations = []
        
        # Empfehlungen basierend auf Erfolgsfaktoren
        if success_factors.get("status") == "success":
            factors = success_factors.get("factors", {})
            
            best_time = factors.get("best_time")
            if best_time:
                recommendations.append(f"📅 Fokussiere auf {best_time[0]}-Termine (Erfolgsrate: {best_time[1]}%)")
            
            best_weekday = factors.get("best_weekday")
            if best_weekday:
                recommendations.append(f"📆 {best_weekday[0]} ist der erfolgreichste Wochentag ({best_weekday[1]}%)")
        
        # Empfehlungen basierend auf Kundenverhalten
        if customer_behavior:
            risk_count = customer_behavior.get("risk_count", 0)
            if risk_count > 0:
                recommendations.append(f"⚠️ {risk_count} Kunden mit hohem No-Show Risiko identifiziert")
            
            champions_count = customer_behavior.get("champions_count", 0)
            if champions_count > 0:
                recommendations.append(f"🏆 {champions_count} treue Kunden - Priorisiere diese für Premium-Slots")
        
        # Allgemeine Empfehlungen
        if len(recommendations) == 0:
            recommendations.append("📊 Sammle mehr Daten für präzisere Empfehlungen")
        
        return {
            "status": "success",
            "recommendations": recommendations,
            "priority": "high" if len(recommendations) > 2 else "medium"
        }
    except Exception as e:
        return {"status": f"Error: {str(e)}", "recommendations": ["❌ Fehler bei der Analyse"]}

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
    
    # Berechne Level-Daten für User
    user = session.get("user")
    user_level = None
    if user:
        user_level = level_system.calculate_user_level(user)
        # Füge Farben hinzu
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

@app.route("/export/bookings/<month>")
def export_bookings(month):
    """Exportiere Buchungen als CSV"""
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
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
            print(f"❌ Tracking error: {e}")
        
        # NEU: Achievement System Integration - IMMER Punkte vergeben wenn möglich
        new_badges = []
        if user and user != "unknown" and points > 0:
            new_badges = add_points_to_user(user, points)
            flash(f"Slot erfolgreich gebucht! Du hast {points} Punkt(e) erhalten.", "success")
        elif user and user != "unknown":
            # Auch bei 0 Punkten Achievement System aufrufen
            new_badges = add_points_to_user(user, 0)
            flash("Slot erfolgreich gebucht!", "success")
        else:
            flash("Slot erfolgreich gebucht!", "success")

        # Spezielle Badge-Zähler (Abend/Morgen) persistieren
        try:
            if user and user != "unknown":
                from data_persistence import data_persistence
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
            print(f"⚠️ Konnte Spezial-Badge-Zähler nicht aktualisieren: {e}")
        
        # Zeige neue Badges an
        if new_badges:
            badge_names = [badge["name"] for badge in new_badges]
            flash(f"🏆 Neue Badges erhalten: {', '.join(badge_names)}", "success")
    else:
        flash("Fehler beim Buchen des Slots. Bitte versuche es später erneut.", "danger")
    
    return redirect(url_for("day_view", date_str=date))
    
@app.route("/tracking/report/weekly")
def weekly_tracking_report():
    """Zeige Wochenbericht"""
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    tracker = BookingTracker()
    report = tracker.get_weekly_report()
    return jsonify(report)
    
@app.route("/scoreboard")
def scoreboard():
    user = session.get("user")
    scores = data_persistence.load_scores()
    
    month = datetime.now(TZ).strftime("%Y-%m")
    ranking = sorted([(u, v.get(month, 0)) for u, v in scores.items()], key=lambda x: x[1], reverse=True)
    user_score = scores.get(user, {}).get(month, 0) if user else 0
    champion = get_champion_for_month((datetime.now(TZ).replace(day=1) - timedelta(days=1)).strftime("%Y-%m"))
    
    # Hole Badge-Daten für das Leaderboard (persistent)
    try:
        badge_leaderboard = achievement_system.get_badge_leaderboard()
    except Exception as e:
        print(f"❌ Badge Leaderboard Fehler: {e}")
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
    
    # Hole Badge-Daten
    try:
        user_badges = achievement_system.get_user_badges(user)
        leaderboard = achievement_system.get_badge_leaderboard()
        
        # Bereite Template-Variablen vor
        total_badges = user_badges.get("total_badges", 0)
        available_badges = ACHIEVEMENT_DEFINITIONS
        badge_progress = achievement_system.get_badge_progress(user)
        
    except Exception as e:
        print(f"❌ Badge System Fehler: {e}")
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

@app.route("/stream/updates")
def stream_updates():
    """Server-Sent Events für Real-time Updates"""
    def generate():
        """Generiert Event-Stream"""
        while True:
            try:
                # Prüfe auf neue Updates (alle 5 Sekunden)
                updates = check_for_updates()
                if updates:
                    yield f"data: {json.dumps(updates)}\n\n"
                
                time.sleep(5)
            except Exception as e:
                print(f"❌ Stream error: {e}")
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

def check_for_updates():
    """Prüft auf neue Updates für Real-time Stream"""
    try:
        # Prüfe auf neue Buchungen
        bookings = load_jsonl_data("data/tracking/bookings.jsonl")
        now_ts = datetime.now(TZ)
        def parse_ts(ts):
            try:
                return datetime.fromisoformat(ts)
            except Exception:
                return None
        recent_bookings = []
        for b in bookings:
            ts = parse_ts(b.get("timestamp", ""))
            if ts and (now_ts - ts).total_seconds() < 30:
                recent_bookings.append(b)
        
        # Prüfe auf neue Outcomes
        outcomes = load_jsonl_data("data/tracking/outcomes.jsonl")
        recent_outcomes = []
        for o in outcomes:
            ts = parse_ts(o.get("timestamp", ""))
            if ts and (now_ts - ts).total_seconds() < 30:
                recent_outcomes.append(o)
        
        updates = {}
        if recent_bookings:
            updates["new_bookings"] = len(recent_bookings)
        if recent_outcomes:
            updates["new_outcomes"] = len(recent_outcomes)
        
        return updates if updates else None
        
    except Exception as e:
        print(f"❌ Update check error: {e}")
        return None

@app.route("/my-calendar")
def my_calendar():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    today = datetime.now(TZ).date()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    
    my_events = []
    
    # 1. Google Calendar Events
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
    
    # 2. Getrackte Buchungen aus dem Tracking System
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
        print(f"❌ Fehler beim Laden getrackter Buchungen: {e}")
    
    # Sortiere alle Events nach Datum und Uhrzeit
    my_events.sort(key=lambda e: (e["date"], e["hour"]))
    
    return render_template("my_calendar.html", my_events=my_events, user=user)



@app.route("/admin/dashboard")
def admin_dashboard():
    """Admin-only Dashboard mit Statistiken und ML-Vorbereitung"""
    user = session.get("user")
    
    # Admin-Check
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    # Dashboard ist jetzt immer verfügbar - keine Zeitbeschränkung
    days_running = get_app_runtime_days()
    
    try:
        # Initialisiere Tracking System
        tracker = BookingTracker()
        
        # Hole Dashboard Daten mit Fallback
        try:
            dashboard_data = tracker.get_enhanced_dashboard()
        except Exception as e:
            print(f"⚠️ Dashboard data error: {e}")
            dashboard_data = {
                "current": {
                    "last_7_days": {"total_bookings": 0, "appearance_rate": 0, "success_rate": 0},
                    "last_30_days": {"success_rate": 0, "appearance_rate": 0}
                },
                "historical": {"by_weekday": {}},
                "combined_insights": {"recommendations": []}
            }
        
        try:
            weekly_report = tracker.get_weekly_report()
        except Exception as e:
            print(f"⚠️ Weekly report error: {e}")
            weekly_report = {}
        
        # Lade detaillierte Metriken
        detailed_metrics = load_detailed_metrics()
        
        # Generiere Charts
        charts = generate_dashboard_charts(tracker)
        
        # Hole Customer Risk Analysis
        risk_analysis = get_customer_risk_analysis(tracker)
        
        # ML Insights (Vorbereitung)
        ml_insights = prepare_ml_insights(tracker)
        
        # Color-Mapping Status für Berater
        color_status = get_color_mapping_status()
        
        return render_template("admin_dashboard_enhanced.html",
                             dashboard=dashboard_data,
                             weekly_report=weekly_report,
                             detailed_metrics=detailed_metrics,
                             charts=charts,
                             risk_analysis=risk_analysis,
                             ml_insights=ml_insights,
                             days_running=days_running)
        
    except Exception as e:
        print(f"❌ Error in admin dashboard: {e}")
        flash(f"Fehler beim Laden des Dashboards: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.route("/admin/analytics/export")
def export_analytics():
    """Export aller Daten für ML-Analyse"""
    user = session.get("user")
    if not is_admin(user):
        return jsonify({"error": "Access denied"}), 403
    
    try:
        tracker = BookingTracker()
        
        # Sammle alle Daten
        export_data = {
            "bookings": load_jsonl_data(tracker.bookings_file),
            "outcomes": load_jsonl_data(tracker.outcomes_file),
            "customer_profiles": load_json_data(tracker.customer_file),
            "daily_metrics": load_json_data(tracker.metrics_file),
            "export_timestamp": datetime.now(TZ).isoformat(),
            "total_records": 0,
            "export_info": {
                "app_runtime_days": get_app_runtime_days(),
                "export_user": user,
                "system_version": "1.0"
            }
        }
        
        # Zähle Records
        export_data["total_records"] = (
            len(export_data["bookings"]) + 
            len(export_data["outcomes"]) + 
            len(export_data["customer_profiles"])
        )
        
        # Als JSON Download anbieten
        from flask import Response
        
        response = Response(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=ml_dataset_{datetime.now(TZ).strftime("%Y%m%d_%H%M%S")}.json'
            }
        )
        
        print(f"📁 Admin {user} exported {export_data['total_records']} records")
        return response
        
    except Exception as e:
        print(f"❌ Export error: {e}")
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

@app.route("/admin/export/csv")
def export_csv():
    """Export als CSV für Excel"""
    user = session.get("user")
    if not is_admin(user):
        return jsonify({"error": "Access denied"}), 403
    
    try:
        import csv
        from io import StringIO
        
        tracker = BookingTracker()
        
        # Lade Daten
        bookings = load_jsonl_data(tracker.bookings_file)
        outcomes = load_jsonl_data(tracker.outcomes_file)
        
        # Erstelle CSV für Buchungen
        bookings_csv = StringIO()
        if bookings:
            writer = csv.DictWriter(bookings_csv, fieldnames=bookings[0].keys())
            writer.writeheader()
            writer.writerows(bookings)
        
        # Erstelle CSV für Outcomes
        outcomes_csv = StringIO()
        if outcomes:
            writer = csv.DictWriter(outcomes_csv, fieldnames=outcomes[0].keys())
            writer.writeheader()
            writer.writerows(outcomes)
        
        # Kombiniere zu ZIP
        import zipfile
        from io import BytesIO
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('bookings.csv', bookings_csv.getvalue())
            zip_file.writestr('outcomes.csv', outcomes_csv.getvalue())
        
        zip_buffer.seek(0)
        
        return app.response_class(
            zip_buffer.getvalue(),
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename=slot_booking_export_{datetime.now(TZ).strftime("%Y%m%d")}.zip'}
        )
        
    except Exception as e:
        print(f"❌ CSV Export error: {e}")
        return jsonify({"error": f"CSV Export failed: {str(e)}"}), 500

@app.route("/admin/export/pdf")
def admin_export_pdf():
    """Export als PDF Report"""
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from flask import make_response
        
        # Erstelle PDF
        response = make_response()
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=slot_booking_report.pdf'
        
        # PDF Buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        
        # Titel
        elements.append(Paragraph("Slot Booking System - Report", title_style))
        elements.append(Spacer(1, 20))
        
        # Hole Daten
        tracker = BookingTracker()
        dashboard = tracker.get_performance_dashboard()
        
        # Dashboard Tabelle
        dashboard_data = [
            ['Metrik', 'Wert'],
            ['Gesamt Buchungen (7 Tage)', dashboard.get('last_7_days', {}).get('total_bookings', 0)],
            ['No-Show Rate (7 Tage)', f"{dashboard.get('last_7_days', {}).get('no_show_rate', 0)}%"],
            ['Erfolgsrate (7 Tage)', f"{dashboard.get('last_7_days', {}).get('success_rate', 0)}%"],
        ]
        
        dashboard_table = Table(dashboard_data)
        dashboard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(dashboard_table)
        elements.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        response.data = pdf
        return response
        
    except Exception as e:
        flash(f"❌ PDF Export Fehler: {e}", "danger")
        return redirect(url_for("admin_dashboard"))

@app.route("/admin/fix-points")
def admin_fix_points():
    """Admin Route um Punkte für bereits getrackte Buchungen zu vergeben"""
    try:
        from tracking_system import BookingTracker
        tracker = BookingTracker()
        
        # Lade alle Buchungen
        all_bookings = tracker.load_all_bookings()
        
        fixed_count = 0
        already_processed = set()  # Verhindere Doppelvergabe
        debug_info = []
        
        for booking in all_bookings:
            user_name = booking.get("user")
            if user_name and user_name != "unknown":
                # Erstelle eindeutige ID für diese Buchung
                booking_id = f"{booking.get('date')}_{booking.get('time')}_{user_name}"
                
                if booking_id in already_processed:
                    continue  # Bereits verarbeitet
                
                # Berechne Punkte für diese Buchung
                time_slot = booking.get("time")
                date = booking.get("date")
                if time_slot and date:
                    try:
                        booking_date = datetime.strptime(date, "%Y-%m-%d").date()
                        points = get_slot_points(time_slot, booking_date)
                        
                        debug_info.append({
                            "user": user_name,
                            "date": date,
                            "time": time_slot,
                            "points": points,
                            "booking_id": booking.get('id', 'unknown')
                        })
                        
                        if points > 0:
                            # Vergebe Punkte
                            new_badges = add_points_to_user(user_name, points)
                            fixed_count += 1
                            already_processed.add(booking_id)
                            print(f"✅ Punkte vergeben: {user_name} +{points} für {date} {time_slot}")
                            
                    except Exception as e:
                        print(f"❌ Fehler bei Buchung {booking.get('id', 'unknown')}: {e}")
        
        # Speichere Debug-Info
        with open("data/debug_points_fix.json", "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now(TZ).isoformat(),
                "total_bookings": len(all_bookings),
                "processed_bookings": len(debug_info),
                "fixed_count": fixed_count,
                "debug_info": debug_info
            }, f, ensure_ascii=False, indent=2)
        
        if fixed_count > 0:
            flash(f"✅ {fixed_count} Buchungen mit Punkten versehen! Debug-Info gespeichert.", "success")
        else:
            flash("ℹ️ Keine neuen Buchungen für Punkte-Vergabe gefunden. Debug-Info gespeichert.", "info")
        
    except Exception as e:
        flash(f"❌ Fehler beim Punkte-Fix: {e}", "danger")
    
    # Zurück zur Hauptseite statt zum gesperrten Dashboard
    return redirect(url_for("index"))
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    try:
        tracker = BookingTracker()
        
        # Lade alle Buchungen der letzten 30 Tage
        today = datetime.now(TZ).date()
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        
        # Lade alle Buchungen
        all_bookings = []
        if os.path.exists(tracker.bookings_file):
            with open(tracker.bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            booking = json.loads(line)
                            if start_date <= booking.get("date", "") <= end_date:
                                all_bookings.append(booking)
                        except json.JSONDecodeError:
                            continue
        
        # Prüfe welche Buchungen noch keine Punkte haben
        fixed_count = 0
        already_processed = set()  # Verhindere Doppelvergabe
        
        for booking in all_bookings:
            user_name = booking.get("user")
            if user_name and user_name != "unknown":
                # Erstelle eindeutige ID für diese Buchung
                booking_id = f"{booking.get('date')}_{booking.get('time')}_{user_name}"
                
                if booking_id in already_processed:
                    continue  # Bereits verarbeitet
                
                # Berechne Punkte für diese Buchung
                time_slot = booking.get("time")
                date = booking.get("date")
                if time_slot and date:
                    try:
                        booking_date = datetime.strptime(date, "%Y-%m-%d").date()
                        points = get_slot_points(time_slot, booking_date)
                        
                        if points > 0:
                            # Vergebe Punkte
                            new_badges = add_points_to_user(user_name, points)
                            fixed_count += 1
                            already_processed.add(booking_id)
                            print(f"✅ Punkte vergeben: {user_name} +{points} für {date} {time_slot}")
                            
                    except Exception as e:
                        print(f"❌ Fehler bei Buchung {booking.get('id', 'unknown')}: {e}")
        
        if fixed_count > 0:
            flash(f"✅ {fixed_count} Buchungen mit Punkten versehen!", "success")
        else:
            flash("ℹ️ Keine neuen Buchungen für Punkte-Vergabe gefunden.", "info")
        
    except Exception as e:
        flash(f"❌ Fehler beim Punkte-Fix: {e}", "danger")
    
    # Zurück zur Hauptseite statt zum gesperrten Dashboard
    return redirect(url_for("index"))

@app.route("/admin/debug-points")
def admin_debug_points():
    """Debug-Route um Punktevergabe-Logik zu testen"""
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    try:
        from tracking_system import BookingTracker
        tracker = BookingTracker()
        
        # Lade alle Buchungen
        all_bookings = tracker.load_all_bookings()
        
        # Lade aktuelle Scores
        scores = data_persistence.load_scores()
        current_month = datetime.now(TZ).strftime("%Y-%m")
        
        debug_data = {
            "timestamp": datetime.now(TZ).isoformat(),
            "current_month": current_month,
            "total_bookings": len(all_bookings),
            "slot_points_logic": {
                "18:00": get_slot_points("18:00", datetime.now(TZ).date()),
                "20:00": get_slot_points("20:00", datetime.now(TZ).date()),
                "11:00": get_slot_points("11:00", datetime.now(TZ).date()),
                "14:00": get_slot_points("14:00", datetime.now(TZ).date()),
                "16:00": get_slot_points("16:00", datetime.now(TZ).date()),
                "09:00": get_slot_points("09:00", datetime.now(TZ).date())
            },
            "user_scores": {},
            "booking_analysis": [],
            "points_summary": {
                "total_possible_points": 0,
                "total_awarded_points": 0,
                "users_with_points": 0,
                "users_without_points": 0
            }
        }
        
        # Analysiere User-Scores
        for username, user_scores in scores.items():
            current_points = user_scores.get(current_month, 0)
            debug_data["user_scores"][username] = {
                "current_month": current_points,
                "all_months": user_scores
            }
            if current_points > 0:
                debug_data["points_summary"]["users_with_points"] += 1
            else:
                debug_data["points_summary"]["users_without_points"] += 1
        
        # Analysiere ALLE Buchungen für vollständige Übersicht
        for booking in all_bookings:
            user_name = booking.get("user")
            time_slot = booking.get("time")
            date = booking.get("date")
            
            if user_name and time_slot and date:
                try:
                    booking_date = datetime.strptime(date, "%Y-%m-%d").date()
                    points = get_slot_points(time_slot, booking_date)
                    
                    debug_data["points_summary"]["total_possible_points"] += points
                    
                    # Prüfe ob User bereits Punkte für diese Buchung hat
                    user_month = booking_date.strftime("%Y-%m")
                    user_has_points = scores.get(user_name, {}).get(user_month, 0) > 0
                    
                    debug_data["booking_analysis"].append({
                        "user": user_name,
                        "date": date,
                        "time": time_slot,
                        "points": points,
                        "booking_id": booking.get('id', 'unknown'),
                        "user_has_points_for_month": user_has_points,
                        "user_month_points": scores.get(user_name, {}).get(user_month, 0)
                    })
                except Exception as e:
                    debug_data["booking_analysis"].append({
                        "user": user_name,
                        "date": date,
                        "time": time_slot,
                        "points": "ERROR",
                        "error": str(e)
                    })
        
        # Berechne vergebene Punkte
        debug_data["points_summary"]["total_awarded_points"] = sum(
            user_scores.get(current_month, 0) for user_scores in scores.values()
        )
        
        # Speichere Debug-Info
        with open("data/debug_points_analysis.json", "w", encoding="utf-8") as f:
            json.dump(debug_data, f, ensure_ascii=False, indent=2)
        
        flash(f"✅ Debug-Analyse gespeichert! {len(debug_data['booking_analysis'])} Buchungen analysiert. Mögliche Punkte: {debug_data['points_summary']['total_possible_points']}, Vergebene Punkte: {debug_data['points_summary']['total_awarded_points']}", "success")
        
    except Exception as e:
        flash(f"❌ Fehler bei Debug-Analyse: {e}", "danger")
    
    return redirect(url_for("admin_dashboard"))

# API Endpoints für Badge System
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

@app.route("/api/user/badges/mark-seen", methods=["POST"])
def api_mark_badges_seen():
    """Markiere neue Badges als gesehen"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Nicht eingeloggt"}), 401
    
    try:
        # Markiere alle neuen Badges als gesehen
        badges_data = achievement_system.load_badges()
        if user in badges_data:
            for badge in badges_data[user]["badges"]:
                badge["new"] = False
            
            achievement_system.save_badges(badges_data)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/user/badges/check-new")
def api_check_new_badges():
    """Prüfe auf neue Badges für User"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Nicht eingeloggt"}), 401
    
    try:
        user_badges = achievement_system.get_user_badges(user)
        new_badges = [badge for badge in user_badges.get("badges", []) if badge.get("new", False)]
        
        return jsonify({
            "new_badges": new_badges,
            "total_new": len(new_badges)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/gamification")
def gamification_dashboard():
    """Gamification-Dashboard mit allen Statistiken"""
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    
    try:
        # Level-Informationen
        user_level = level_system.calculate_user_level(user)
        
        # Badge-Statistiken
        user_badges = achievement_system.get_user_badges(user)
        
        # Streak-Informationen
        from data_persistence import data_persistence
        daily_stats = data_persistence.load_daily_user_stats()
        streak_info = achievement_system.calculate_advanced_streak(daily_stats.get(user, {}))
        
        # Nächste Ziele
        next_goals = achievement_system.get_next_achievements(user)
        
        # Badge-Statistiken berechnen
        badge_stats = {
            "by_rarity": {
                "common": 0,
                "uncommon": 0,
                "rare": 0,
                "epic": 0,
                "legendary": 0,
                "mythic": 0
            },
            "total": len(user_badges.get("badges", []))
        }
        
        # Zähle Badges nach Rarität
        for badge in user_badges.get("badges", []):
            rarity = badge.get("rarity", "common")
            if rarity in badge_stats["by_rarity"]:
                badge_stats["by_rarity"][rarity] += 1
        
        # Raritäts-Farben für Template
        rarity_colors = {
            "common": "#10b981",
            "uncommon": "#3b82f6",
            "rare": "#8b5cf6",
            "epic": "#f59e0b",
            "legendary": "#eab308",
            "mythic": "#ec4899"
        }
        
        # Aktuelle Monatspunkte
        scores = data_persistence.load_scores()
        month = datetime.now(TZ).strftime("%Y-%m")
        current_month_points = scores.get(user, {}).get(month, 0)
        
        # Ranking-Position
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
        print(f"❌ Gamification Dashboard Fehler: {e}")
        # Fallback-Daten bei Fehlern
        fallback_data = {
            "user_level": {
                "level": 1,
                "level_title": "Anfänger",
                "xp": 0,
                "next_level_xp": 100,
                "progress_to_next": 0,
                "progress_color": "#10b981",
                "total_badges": 0,
                "level_up": None
            },
            "user_badges": {"badges": [], "total_badges": 0},
            "badge_stats": {
                "by_rarity": {"common": 0, "uncommon": 0, "rare": 0, "epic": 0, "legendary": 0, "mythic": 0},
                "total": 0
            },
            "streak_info": {
                "work_streak": 0,
                "booking_streak": 0,
                "points_streak": 0,
                "best_streak": 0
            },
            "next_goals": [],
            "rarity_colors": {
                "common": "#10b981",
                "uncommon": "#3b82f6",
                "rare": "#8b5cf6",
                "epic": "#f59e0b",
                "legendary": "#eab308",
                "mythic": "#ec4899"
            },
            "current_month_points": 0,
            "user_rank": 0,
            "total_players": 0
        }
        
        return render_template("gamification.html",
                             user_level=fallback_data["user_level"],
                             user_badges=fallback_data["user_badges"],
                             badge_stats=fallback_data["badge_stats"],
                             streak_info=fallback_data["streak_info"],
                             next_goals=fallback_data["next_goals"],
                             rarity_colors=fallback_data["rarity_colors"],
                             current_user=user,
                             current_month_points=fallback_data["current_month_points"],
                             user_rank=fallback_data["user_rank"],
                             total_players=fallback_data["total_players"])

@app.route("/api/badges/check-new")
def check_new_badges():
    """API-Endpoint für Badge-Updates"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Nicht eingeloggt"})
    
    try:
        # Prüfe auf neue Badges seit letztem Check
        last_check = session.get("last_badge_check", "1970-01-01")
        new_badges = achievement_system.get_new_badges_since(user, last_check)
        
        # Update Session
        session["last_badge_check"] = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({
            "new_badges": new_badges,
            "total_badges": len(achievement_system.get_user_badges(user)["badges"])
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/level/check-up")
def check_level_up():
    """API-Endpoint für Level-Up-Checks"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Nicht eingeloggt"})
    
    try:
        # Berechne aktuelles Level
        user_level = level_system.calculate_user_level(user)
        
        return jsonify({
            "level_up": user_level.get("level_up"),
            "current_level": user_level["level"],
            "current_xp": user_level["xp"]
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/admin/badges/backfill")
def admin_badges_backfill():
    """Reparaturroutine: Vergibt persistente Badges rückwirkend."""
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))

    try:
        result = achievement_system.backfill_persistent_badges()
        cnt = result.get("badges_awarded", 0)
        users = result.get("users_processed", 0)
        flash(f"✅ Backfill abgeschlossen: {cnt} Badges neu vergeben (über {users} Nutzer).", "success")
    except Exception as e:
        flash(f"❌ Backfill-Fehler: {e}", "danger")
    return redirect(url_for("scoreboard"))

@app.route("/admin/insights")
def admin_insights():
    """Detaillierte Insights und Predictions"""
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    # Insights sind jetzt immer verfügbar - keine Zeitbeschränkung
    days_running = get_app_runtime_days()
    
    try:
        tracker = BookingTracker()
        
        # Erweiterte Analysen
        insights = {
            "time_patterns": analyze_time_patterns(tracker),
            "customer_behavior": analyze_customer_behavior(tracker),
            "success_factors": analyze_success_factors(tracker),
            "predictions": generate_predictions(tracker),
            "recommendations": generate_recommendations(tracker)
        }
        
        return render_template("admin_insights.html", insights=insights)
        
    except Exception as e:
        print(f"❌ Error in insights: {e}")
        flash(f"Fehler beim Laden der Insights: {str(e)}", "danger")
        return redirect(url_for("admin_dashboard"))

# ----------------- Telefonie Punkte Backend -----------------
@app.route("/admin/telefonie", methods=["GET", "POST"])
def admin_telefonie():
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))

    # Woche auswählen
    selected_week = request.args.get("week") or get_week_key()
    recent_weeks = list_recent_weeks(12)

    # Teilnehmerliste
    participants = get_participants()

    # POST: Ziele/Aktivitäten setzen
    if request.method == "POST":
        action = request.form.get("action")
        target_week = request.form.get("week") or selected_week
        target_user = request.form.get("user")

        try:
            if action == "set_goal":
                raw_goal = request.form.get("goal_points", 0)
                try:
                    goal_points = int(raw_goal)
                except ValueError:
                    flash("Ungültiger Zielwert.", "danger")
                    return redirect(url_for("admin_telefonie", week=target_week))
                if goal_points > 100:
                    goal_points = 100
                    flash("Ziel auf 100 begrenzt.", "warning")
                if goal_points > 30:
                    flash("Warnung: Ziel über 30 Punkten.", "warning")
                set_week_goal(target_week, target_user, goal_points, set_by=user)
                flash("Ziel gespeichert (ggf. als wartend, wenn außerhalb 18–21 Uhr).", "success")

            elif action == "add_activity":
                kind = request.form.get("kind")  # T1/T2/telefonie/extra
                raw_points = request.form.get("points", 0)
                try:
                    points = int(raw_points)
                except ValueError:
                    flash("Ungültige Punktzahl.", "danger")
                    return redirect(url_for("admin_telefonie", week=target_week))
                if points > 100:
                    points = 100
                    flash("Punkte auf 100 begrenzt.", "warning")
                if points > 30:
                    flash("Warnung: Punkte über 30.", "warning")
                note = request.form.get("note", "")
                record_activity(target_week, target_user, kind, points, set_by=user, note=note)
                flash("Aktivität erfasst (ggf. als wartend, wenn außerhalb 18–21 Uhr).", "success")

            elif action == "apply_pending":
                goals_applied, acts_applied = apply_pending(target_week)
                if goals_applied or acts_applied:
                    flash(f"Verbucht: {goals_applied} Ziele, {acts_applied} Aktivitäten.", "success")
                else:
                    flash("Keine Pending-Einträge oder außerhalb des 18–21 Uhr Fensters.", "info")

            elif action == "add_participant":
                name = request.form.get("name", "").strip()
                if name:
                    add_participant(name)
                    flash(f"Teilnehmer hinzugefügt: {name}", "success")
                else:
                    flash("Name darf nicht leer sein.", "warning")

            elif action == "remove_participant":
                name = request.form.get("name", "").strip()
                if name:
                    remove_participant(name)
                    flash(f"Teilnehmer entfernt: {name}", "success")
                else:
                    flash("Name darf nicht leer sein.", "warning")

            elif action == "set_vacation":
                on_vacation = request.form.get("on_vacation") == "1"
                set_on_vacation(target_week, target_user, on_vacation)
                flash("Urlaubsstatus aktualisiert.", "success")

            return redirect(url_for("admin_telefonie", week=target_week))
        except Exception as e:
            flash(f"❌ Fehler: {str(e)}", "danger")
            return redirect(url_for("admin_telefonie", week=target_week))

    # GET: Daten anzeigen
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

@app.route("/admin/telefonie/export")
def admin_telefonie_export():
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))

    week = request.args.get("week") or get_week_key()
    participants = get_participants()
    stats = compute_week_stats(week, participants)

    # PDF generieren (tabellarisch + Legende + Mini-Chart)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from flask import Response

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title = Paragraph(f"Wochenbilanz Telefonie – Woche {week} (Export: {datetime.now(TZ).strftime('%d.%m.%Y %H:%M')})", styles['Heading2'])
        elements.append(title)
        elements.append(Spacer(1, 12))

        # Tabelle
        table_data = [["Person", "Ziel", "Erreicht", "Offen", "Bilanz", "Urlaub"]]
        for u in stats["users"]:
            table_data.append([
                u["user"],
                u["goal"],
                u["achieved"],
                u["remaining"],
                u["balance"],
                "Ja" if u["on_vacation"] else "Nein",
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
        ]))
        elements.append(table)

        # Farblegende
        elements.append(Spacer(1, 12))
        legend = Table([
            ["Ziel", ""],
            ["Erreicht", ""],
            ["Offen", ""],
        ], colWidths=[80, 30])
        legend.setStyle(TableStyle([
            ('BACKGROUND', (1, 0), (1, 0), colors.yellow),
            ('BACKGROUND', (1, 1), (1, 1), colors.green),
            ('BACKGROUND', (1, 2), (1, 2), colors.red),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        elements.append(legend)

        # Summary
        elements.append(Spacer(1, 12))
        summary = stats["summary"]
        elements.append(Paragraph(
            f"Gesamt: Ziel {summary['total_goal']} | Erreicht {summary['total_achieved']} | Offen {summary['total_remaining']} | Bilanz {summary['total_balance']}",
            styles['Normal']
        ))

        # Mini-Chart Seite
        elements.append(PageBreak())
        elements.append(Paragraph("Übersicht als Mini-Chart", styles['Heading3']))
        # Matplotlib Diagramm erzeugen
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            names = [u["user"] for u in stats["users"]]
            goals = [u["goal"] for u in stats["users"]]
            achieved = [u["achieved"] for u in stats["users"]]
            remaining = [u["remaining"] for u in stats["users"]]

            x = np.arange(len(names))
            width = 0.25

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.bar(x - width, goals, width, label='Ziel', color='#eab308')
            ax.bar(x, achieved, width, label='Erreicht', color='#10b981')
            ax.bar(x + width, remaining, width, label='Offen', color='#ef4444')
            ax.set_xticks(x)
            ax.set_xticklabels(names, rotation=20, ha='right')
            ax.set_ylabel('Punkte')
            ax.set_title(f'Woche {week}')
            ax.legend()
            ax.grid(axis='y', alpha=0.2)

            img_buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(img_buf, format='png', dpi=140)
            plt.close(fig)
            img_buf.seek(0)

            elements.append(Image(img_buf, width=520, height=220))
        except Exception as chart_err:
            elements.append(Paragraph(f"Chart konnte nicht erzeugt werden: {chart_err}", styles['Italic']))

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        return Response(pdf, mimetype='application/pdf', headers={
            'Content-Disposition': f"attachment; filename=telefonie_week_{week}_{datetime.now(TZ).strftime('%Y%m%d_%H%M')}.pdf"
        })
    except Exception as e:
        flash(f"❌ PDF Export Fehler: {e}", "danger")
        return redirect(url_for("admin_telefonie", week=week))

def run_achievement_check():
    """
    Prüfe und vergebe Achievement Badges
    Sollte täglich laufen
    """
    try:
        achievement_system.check_and_award_mvp_badges()
        print("✅ Achievement check completed")
    except Exception as e:
        print(f"❌ Achievement check error: {e}")

@app.route("/admin/users")
def admin_users():
    """Admin Route um alle aktiven User anzuzeigen"""
    user = session.get("user")
    if not is_admin(user):
        flash("❌ Zugriff verweigert. Nur für Administratoren.", "danger")
        return redirect(url_for("login"))
    
    try:
        # Hole alle aktiven User (aus Scores und Tracking abgeleitet)
        scores = data_persistence.load_scores()
        active_users = set(scores.keys())
        try:
            from tracking_system import BookingTracker
            tracker = BookingTracker()
            if os.path.exists(tracker.bookings_file):
                with open(tracker.bookings_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                booking = json.loads(line)
                                if booking.get("user"):
                                    active_users.add(booking.get("user"))
                            except json.JSONDecodeError:
                                continue
        except Exception:
            pass
        active_users = sorted(active_users)
        base_users = get_userlist()
        
        # Erstelle User-Liste mit Details
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
            
            # Prüfe Buchungen und Punkte
            try:
                from tracking_system import BookingTracker
                tracker = BookingTracker()
                
                # Zähle Buchungen
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
                
                # Hole aktuelle Monatspunkte
                scores = data_persistence.load_scores()
                month = datetime.now(TZ).strftime("%Y-%m")
                user_info["current_month_points"] = scores.get(username, {}).get(month, 0)
                
            except Exception as e:
                print(f"❌ Fehler beim Laden der User-Daten für {username}: {e}")
            
            users_info.append(user_info)
        
        # Sortiere nach Punkten (absteigend)
        users_info.sort(key=lambda x: x["current_month_points"], reverse=True)
        
        return render_template("admin_users.html", 
                             users=users_info,
                             total_users=len(users_info),
                             base_users_count=len(base_users))
        
    except Exception as e:
        flash(f"❌ Fehler beim Laden der User-Liste: {e}", "danger")
        return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=False)  # Debug auf False für Produktion!