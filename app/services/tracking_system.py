# -*- coding: utf-8 -*-
"""
Tracking System für Slot Booking Webapp
- Trackt alle Buchungen
- Erkennt No-Shows (rote Termine)
- Berechnet Success-Metriken
- Vorbereitung für Prediction Engine
"""

import os
import json
import pytz
import logging
from datetime import datetime, timedelta, time
from collections import defaultdict
from googleapiclient.discovery import build
from app.utils.credentials import load_google_credentials

# PostgreSQL Models
try:
    from app.models import Booking, is_postgres_enabled, get_db_session
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("PostgreSQL Models nicht verfügbar - Fallback zu JSON")

# ----------------- Setup -----------------
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TZ = pytz.timezone("Europe/Berlin")

# Logger setup
logger = logging.getLogger(__name__)
CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")

# ----------------- ZENTRALE COLOR-DEFINITION -----------------
from app.utils.color_mapping import get_outcome_from_color, get_potential_type

# Potential-Typ Mapping (für Analyse-Zwecke) - jetzt über color_mapping.py
POTENTIAL_TYPES = {
    "2": "normal",          # Grün = Normales Potential
    "7": "top",            # Blau = Top Potential
    "5": "closer_needed",  # Gelb = Closer nötig
    "3": "recall",         # Weintraube = Rückholung
    "9": "standard",       # Graphit = Standard
    "10": "standard",      # Flamingo = Standard
    "11": "no_show",       # Tomate = Nicht erschienen
    "6": "cancelled"       # Mandarine = Abgesagt
}

class BookingTracker:
    def __init__(self):
        self.data_dir = "data/tracking"
        os.makedirs(self.data_dir, exist_ok=True)

        # Persistent storage following dual-write pattern
        self.persistent_dir = "data/persistent"
        os.makedirs(self.persistent_dir, exist_ok=True)

        # Files für verschiedene Tracking-Arten (primary storage)
        self.bookings_file = os.path.join(self.data_dir, "bookings.jsonl")
        self.outcomes_file = os.path.join(self.data_dir, "outcomes.jsonl")
        self.metrics_file = os.path.join(self.data_dir, "daily_metrics.json")
        self.customer_file = os.path.join(self.data_dir, "customer_profiles.json")

        # Persistent files (secondary storage for compatibility)
        self.persistent_metrics_file = os.path.join(self.persistent_dir, "tracking_metrics.json")
        self.persistent_customer_file = os.path.join(self.persistent_dir, "customer_tracking.json")
        
        # Google Calendar Service
        creds = load_google_credentials(SCOPES)
        self.service = build("calendar", "v3", credentials=creds)
    
    def track_booking(self, customer_name, date, time_slot, user, color_id, description=""):
        """
        Tracke eine neue Buchung mit Dual-Write Pattern

        Schreibt in:
        1. PostgreSQL (wenn USE_POSTGRES=true und verfügbar)
        2. JSONL-Datei (immer als Fallback)
        """
        try:
            booking_date = datetime.strptime(date, "%Y-%m-%d")
            booking_id = f"{date}_{time_slot}_{customer_name}".replace(" ", "_")

            booking_data = {
                "id": booking_id,
                "timestamp": datetime.now(TZ).isoformat(),
                "customer": customer_name,
                "date": date,
                "time": time_slot,
                "weekday": booking_date.strftime("%A"),
                "week_number": booking_date.isocalendar()[1],
                "user": user,
                "potential_type": self._get_potential_type(color_id),
                "color_id": color_id,
                "description_length": len(description) if description else 0,
                "has_description": bool(description),
                "booking_lead_time": (booking_date.date() - datetime.now(TZ).date()).days,
                "booked_at_hour": datetime.now(TZ).hour,
                "booked_on_weekday": datetime.now(TZ).strftime("%A")
            }

            # ========== DUAL-WRITE: PostgreSQL + JSON ==========

            # 1. PostgreSQL schreiben (wenn aktiviert)
            if POSTGRES_AVAILABLE and is_postgres_enabled():
                try:
                    session = get_db_session()
                    booking = Booking(
                        booking_id=booking_id,
                        customer=customer_name,
                        date=booking_date.date(),
                        time=time_slot,
                        weekday=booking_data["weekday"],
                        week_number=booking_data["week_number"],
                        username=user,
                        potential_type=booking_data["potential_type"],
                        color_id=color_id,
                        description_length=booking_data["description_length"],
                        has_description=booking_data["has_description"],
                        booking_lead_time=booking_data["booking_lead_time"],
                        booked_at_hour=booking_data["booked_at_hour"],
                        booked_on_weekday=booking_data["booked_on_weekday"],
                        booking_timestamp=datetime.now(TZ)
                    )
                    session.merge(booking)  # Update if exists
                    session.commit()
                    session.close()
                    logger.debug(f"Booking tracked to PostgreSQL: {booking_id}")
                except Exception as e:
                    logger.error(f"PostgreSQL write failed, using JSON fallback: {e}")

            # 2. JSONL schreiben (immer, als Fallback)
            os.makedirs(os.path.dirname(self.bookings_file), exist_ok=True)
            with open(self.bookings_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(booking_data, ensure_ascii=False) + "\n")

            logger.info(f"Booking tracked: {customer_name} on {date} at {time_slot}")
            return booking_data

        except Exception as e:
            logger.error(f"Error tracking booking: {e}")
            return None
    
    def check_daily_outcomes(self, check_date=None):
        """
        Prüft alle Termine eines Tages auf No-Shows/Outcomes
        Standardmäßig prüft es den aktuellen Tag
        Sollte täglich um 21:00 Uhr laufen
        """
        if check_date is None:
            check_date = datetime.now(TZ).date()
        else:
            check_date = datetime.strptime(check_date, "%Y-%m-%d").date() if isinstance(check_date, str) else check_date
        
        logger.debug(f"Checking outcomes for {check_date}")
        
        # Hole alle Events des Tages
        start_time = TZ.localize(datetime.combine(check_date, time.min))
        end_time = TZ.localize(datetime.combine(check_date, time.max))
        
        try:
            events_result = self.service.events().list(
                calendarId=CENTRAL_CALENDAR_ID,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime',
                maxResults=100
            ).execute()
            
            events = events_result.get('items', [])
            outcomes_tracked = 0
            
            for event in events:
                # Skip Platzhalter (nur Zahlen)
                if event.get("summary", "").isdigit():
                    continue
                
                # Extrahiere Daten
                customer_name = event.get("summary", "Unknown")
                color_id = event.get("colorId", "9")  # Default: Graphit
                event_start = event.get("start", {}).get("dateTime")
                
                if not event_start:
                    continue
                
                event_time = datetime.fromisoformat(event_start).strftime("%H:%M")

                # WICHTIG: Nutze titel-basierte Outcome-Bestimmung
                outcome = self._get_outcome_from_title_and_color(customer_name, color_id)
                
                # Track outcome
                outcome_data = {
                    "id": f"{check_date}_{event_time}_{customer_name}".replace(" ", "_"),
                    "timestamp": datetime.now(TZ).isoformat(),
                    "customer": customer_name,
                    "date": str(check_date),
                    "time": event_time,
                    "outcome": outcome,
                    "color_id": color_id,
                    "potential_type": self._get_potential_type(color_id),
                    "checked_at": datetime.now(TZ).strftime("%H:%M"),
                    "description": event.get("description", "")
                }
                
                # Spezielle Behandlung für No-Shows
                if outcome == "no_show":
                    outcome_data["alert"] = "NO_SHOW_DETECTED"
                    logger.warning(f"No-Show detected: {customer_name} at {event_time}")
                elif outcome == "cancelled":
                    logger.info(f"Cancelled: {customer_name} at {event_time}")
                elif outcome == "completed":
                    logger.info(f"Completed: {customer_name} at {event_time} (Color: {color_id})")
                
                # Speichere Outcome
                with open(self.outcomes_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(outcome_data, ensure_ascii=False) + "\n")
                
                outcomes_tracked += 1
            
            logger.info(f"Tracked {outcomes_tracked} outcomes for {check_date}")
            
            # Berechne Tagesmetriken
            self._calculate_daily_metrics(check_date, events)
            
            # Update Kundenprofile
            self._update_customer_profiles()
            
            return outcomes_tracked
            
        except Exception as e:
            logger.error(f"Error checking outcomes: {e}")
            return 0
    
    def _calculate_daily_metrics(self, date, events):
        """Berechne und speichere Tagesstatistiken"""
        metrics = {
            "date": str(date),
            "total_slots": 0,
            "no_shows": 0,
            "completed": 0,
            "cancelled": 0,
            "rescheduled": 0,
            "by_hour": defaultdict(lambda: {"total": 0, "no_shows": 0, "completed": 0, "cancelled": 0, "rescheduled": 0}),
            "by_user": defaultdict(lambda: {"total": 0, "no_shows": 0, "completed": 0}),
            "by_potential": defaultdict(lambda: {"total": 0, "completed": 0}),
            "calculated_at": datetime.now(TZ).isoformat()
        }

        for event in events:
            # Skip Platzhalter
            if event.get("summary", "").isdigit():
                continue

            metrics["total_slots"] += 1

            color_id = event.get("colorId", "9")
            customer_name = event.get("summary", "Unknown")
            outcome = self._get_outcome_from_title_and_color(customer_name, color_id)
            potential_type = self._get_potential_type(color_id)

            # Zähle Outcomes
            if outcome == "no_show":
                metrics["no_shows"] += 1
            elif outcome == "completed":
                metrics["completed"] += 1
            elif outcome == "cancelled":
                metrics["cancelled"] += 1
            elif outcome == "rescheduled":
                metrics["rescheduled"] += 1
            
            # Nach Stunde
            event_start = event.get("start", {}).get("dateTime")
            if event_start:
                hour = datetime.fromisoformat(event_start).strftime("%H:00")
                metrics["by_hour"][hour]["total"] += 1
                if outcome == "no_show":
                    metrics["by_hour"][hour]["no_shows"] += 1
                elif outcome == "completed":
                    metrics["by_hour"][hour]["completed"] += 1
                elif outcome == "cancelled":
                    metrics["by_hour"][hour]["cancelled"] += 1
                elif outcome == "rescheduled":
                    metrics["by_hour"][hour]["rescheduled"] += 1
            
            # Nach Potential-Typ
            if potential_type not in ["no_show", "cancelled"]:
                metrics["by_potential"][potential_type]["total"] += 1
                if outcome == "completed":
                    metrics["by_potential"][potential_type]["completed"] += 1
        
        # Berechne Raten
        if metrics["total_slots"] > 0:
            metrics["no_show_rate"] = round(metrics["no_shows"] / metrics["total_slots"] * 100, 2)
            metrics["completion_rate"] = round(metrics["completed"] / metrics["total_slots"] * 100, 2)
            metrics["cancellation_rate"] = round(metrics["cancelled"] / metrics["total_slots"] * 100, 2)
        else:
            metrics["no_show_rate"] = 0
            metrics["completion_rate"] = 0
            metrics["cancellation_rate"] = 0
        
        # Speichere Metriken (dual-write pattern)
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    all_metrics = json.load(f)
            else:
                all_metrics = {}

            all_metrics[str(date)] = metrics

            # Primary storage
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(all_metrics, f, ensure_ascii=False, indent=2)

            # Secondary persistent storage
            try:
                with open(self.persistent_metrics_file, "w", encoding="utf-8") as f:
                    json.dump(all_metrics, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Could not write to persistent metrics: {e}")
            
            logger.debug("Daily metrics saved")
            logger.debug(f"Completed: {metrics['completed']} ({metrics['completion_rate']}%)")
            logger.debug(f"No-Shows: {metrics['no_shows']} ({metrics['no_show_rate']}%)")
            logger.debug(f"Cancelled: {metrics['cancelled']} ({metrics['cancellation_rate']}%)")
            
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    def _update_customer_profiles(self):
        """Aktualisiere Kundenprofile mit aggregierten Daten"""
        profiles = {}
        
        # Lade bestehende Profile
        if os.path.exists(self.customer_file):
            try:
                with open(self.customer_file, "r", encoding="utf-8") as f:
                    profiles = json.load(f)
            except:
                profiles = {}
        
        # Analysiere alle Outcomes
        if os.path.exists(self.outcomes_file):
            with open(self.outcomes_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        outcome = json.loads(line)
                        customer = outcome["customer"]
                        
                        if customer not in profiles:
                            profiles[customer] = {
                                "first_seen": outcome["date"],
                                "last_seen": outcome["date"],
                                "total_appointments": 0,
                                "completed": 0,
                                "no_shows": 0,
                                "cancelled": 0,
                                "reliability_score": 100.0
                            }
                        
                        profile = profiles[customer]
                        profile["total_appointments"] += 1
                        profile["last_seen"] = outcome["date"]
                        
                        if outcome["outcome"] == "completed":
                            profile["completed"] += 1
                        elif outcome["outcome"] == "no_show":
                            profile["no_shows"] += 1
                        elif outcome["outcome"] == "cancelled":
                            profile["cancelled"] += 1
                        
                        # Berechne Zuverlässigkeits-Score
                        if profile["total_appointments"] > 0:
                            profile["reliability_score"] = round(
                                (profile["completed"] / profile["total_appointments"]) * 100, 2
                            )
                        
                        # Klassifiziere Kunde
                        if profile["no_shows"] >= 3:
                            profile["risk_level"] = "high"
                        elif profile["no_shows"] >= 1:
                            profile["risk_level"] = "medium"
                        else:
                            profile["risk_level"] = "low"
                    
                    except Exception as e:
                        logger.error(f"Error processing outcome: {e}")
                        continue
        
        # Speichere aktualisierte Profile (dual-write pattern)
        with open(self.customer_file, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)

        # Secondary persistent storage
        try:
            with open(self.persistent_customer_file, "w", encoding="utf-8") as f:
                json.dump(profiles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Could not write to persistent customers: {e}")

        logger.info(f"Updated {len(profiles)} customer profiles")
    
    def get_customer_history(self, customer_name):
        """Hole die komplette Historie eines Kunden"""
        history = {
            "customer": customer_name,
            "bookings": [],
            "outcomes": [],
            "stats": {
                "total_bookings": 0,
                "no_shows": 0,
                "completed": 0,
                "cancelled": 0,
                "no_show_rate": 0,
                "reliability_score": 0
            },
            "timeline": []
        }
        
        # Lade Buchungen
        if os.path.exists(self.bookings_file):
            with open(self.bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    booking = json.loads(line)
                    if customer_name.lower() in booking["customer"].lower():
                        history["bookings"].append(booking)
                        history["stats"]["total_bookings"] += 1
        
        # Lade Outcomes
        if os.path.exists(self.outcomes_file):
            with open(self.outcomes_file, "r", encoding="utf-8") as f:
                for line in f:
                    outcome = json.loads(line)
                    if customer_name.lower() in outcome["customer"].lower():
                        history["outcomes"].append(outcome)
                        
                        # Erstelle Timeline-Eintrag
                        timeline_entry = {
                            "date": outcome["date"],
                            "time": outcome["time"],
                            "outcome": outcome["outcome"],
                            "color_id": outcome.get("color_id", "9")
                        }
                        history["timeline"].append(timeline_entry)
                        
                        # Update Stats
                        if outcome["outcome"] == "no_show":
                            history["stats"]["no_shows"] += 1
                        elif outcome["outcome"] == "completed":
                            history["stats"]["completed"] += 1
                        elif outcome["outcome"] == "cancelled":
                            history["stats"]["cancelled"] += 1
        
        # Sortiere Timeline
        history["timeline"].sort(key=lambda x: (x["date"], x["time"]))
        
        # Berechne Raten
        total_outcomes = history["stats"]["completed"] + history["stats"]["no_shows"] + history["stats"]["cancelled"]
        if total_outcomes > 0:
            history["stats"]["no_show_rate"] = round(
                history["stats"]["no_shows"] / total_outcomes * 100, 2
            )
            history["stats"]["reliability_score"] = round(
                history["stats"]["completed"] / total_outcomes * 100, 2
            )
        
        # Lade Kundenprofil wenn vorhanden
        if os.path.exists(self.customer_file):
            with open(self.customer_file, "r", encoding="utf-8") as f:
                profiles = json.load(f)
                if customer_name in profiles:
                    history["profile"] = profiles[customer_name]
        
        return history
    
    def get_weekly_report(self, week_number=None):
        """Generiere erweiterten Wochenbericht"""
        if week_number is None:
            week_number = datetime.now(TZ).isocalendar()[1]
        
        report = {
            "week": week_number,
            "year": datetime.now(TZ).year,
            "metrics": {
                "total_bookings": 0,
                "total_outcomes": 0,
                "no_shows": 0,
                "completed": 0,
                "cancelled": 0,
                "by_day": defaultdict(lambda: {
                    "bookings": 0, 
                    "no_shows": 0, 
                    "completed": 0,
                    "cancelled": 0
                }),
                "by_user": defaultdict(lambda: {
                    "bookings": 0, 
                    "no_shows": 0,
                    "completed": 0,
                    "success_rate": 0
                }),
                "by_hour": defaultdict(lambda: {
                    "total": 0,
                    "no_shows": 0,
                    "completed": 0
                }),
                "top_no_show_times": [],
                "top_success_times": [],
                "high_risk_customers": []
            }
        }
        
        # Analysiere Buchungen
        if os.path.exists(self.bookings_file):
            with open(self.bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    booking = json.loads(line)
                    if booking.get("week_number") == week_number:
                        report["metrics"]["total_bookings"] += 1
                        weekday = booking["weekday"]
                        report["metrics"]["by_day"][weekday]["bookings"] += 1
                        if booking.get("user"):
                            report["metrics"]["by_user"][booking["user"]]["bookings"] += 1
        
        # Analysiere Outcomes
        if os.path.exists(self.outcomes_file):
            with open(self.outcomes_file, "r", encoding="utf-8") as f:
                for line in f:
                    outcome = json.loads(line)
                    outcome_date = datetime.strptime(outcome["date"], "%Y-%m-%d")
                    
                    if outcome_date.isocalendar()[1] == week_number:
                        report["metrics"]["total_outcomes"] += 1
                        weekday = outcome_date.strftime("%A")
                        hour = outcome["time"][:2] + ":00"
                        
                        # Nach Outcome-Typ
                        if outcome["outcome"] == "no_show":
                            report["metrics"]["no_shows"] += 1
                            report["metrics"]["by_day"][weekday]["no_shows"] += 1
                            report["metrics"]["by_hour"][hour]["no_shows"] += 1
                        elif outcome["outcome"] == "completed":
                            report["metrics"]["completed"] += 1
                            report["metrics"]["by_day"][weekday]["completed"] += 1
                            report["metrics"]["by_hour"][hour]["completed"] += 1
                        elif outcome["outcome"] == "cancelled":
                            report["metrics"]["cancelled"] += 1
                            report["metrics"]["by_day"][weekday]["cancelled"] += 1
                        
                        report["metrics"]["by_hour"][hour]["total"] += 1
        
        # Berechne Success-Raten nach User
        for user, data in report["metrics"]["by_user"].items():
            if data["bookings"] > 0:
                data["success_rate"] = round(
                    (data.get("completed", 0) / data["bookings"]) * 100, 2
                )
        
        # Finde beste/schlechteste Zeiten
        hour_stats = []
        for hour, data in report["metrics"]["by_hour"].items():
            if data["total"] > 0:
                no_show_rate = (data["no_shows"] / data["total"]) * 100
                success_rate = (data["completed"] / data["total"]) * 100
                hour_stats.append({
                    "hour": hour,
                    "no_show_rate": round(no_show_rate, 2),
                    "success_rate": round(success_rate, 2),
                    "total": data["total"]
                })
        
        # Top No-Show Zeiten
        hour_stats.sort(key=lambda x: x["no_show_rate"], reverse=True)
        report["metrics"]["top_no_show_times"] = hour_stats[:3]
        
        # Top Success Zeiten
        hour_stats.sort(key=lambda x: x["success_rate"], reverse=True)
        report["metrics"]["top_success_times"] = hour_stats[:3]
        
        # Berechne Gesamt-Raten
        if report["metrics"]["total_outcomes"] > 0:
            report["metrics"]["overall_no_show_rate"] = round(
                (report["metrics"]["no_shows"] / report["metrics"]["total_outcomes"]) * 100, 2
            )
            report["metrics"]["overall_completion_rate"] = round(
                (report["metrics"]["completed"] / report["metrics"]["total_outcomes"]) * 100, 2
            )
            report["metrics"]["overall_cancellation_rate"] = round(
                (report["metrics"]["cancelled"] / report["metrics"]["total_outcomes"]) * 100, 2
            )
        
        return report
    
    def get_performance_dashboard(self):
        """Generiere Dashboard-Daten für Visualisierung"""
        dashboard = {
            "generated_at": datetime.now(TZ).isoformat(),
            "current_week": {
                "number": datetime.now(TZ).isocalendar()[1],
                "year": datetime.now(TZ).year
            },
            "last_7_days": {
                "total_bookings": 0,
                "appearance_rate": 0,
                "success_rate": 0,
                "no_show_rate": 0
            },
            "last_30_days": {
                "total_bookings": 0,
                "appearance_rate": 0,
                "success_rate": 0,
                "no_show_rate": 0
            },
            "current_totals": {
                "total_slots": 0,
                "total_appeared": 0,
                "total_not_appeared": 0,
                "total_cancelled": 0,
                "appearance_rate": 0,
                "days_tracked": 0
            },
            "trends": {},
            "alerts": []
        }
        
        try:
            # Lade Metriken
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    all_metrics = json.load(f)
                    
                    # Berechne 7-Tage Statistik
                    today = datetime.now(TZ).date()
                    last_7_days_list = [str(today - timedelta(days=i)) for i in range(7)]

                    total_slots = 0
                    total_no_shows = 0
                    total_completed = 0
                    total_cancelled = 0

                    for date_str in last_7_days_list:
                        if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                            metrics = all_metrics[date_str]
                            total_slots += metrics.get("total_slots", 0)
                            total_no_shows += metrics.get("no_shows", 0)
                            total_completed += metrics.get("completed", 0)
                            total_cancelled += metrics.get("cancelled", 0)

                    if total_slots > 0:
                        # Auftauchquote = Erschienene / Alle gelegten Termine
                        # Abgesagt und Verschoben zählen als "nicht erschienen"
                        appearance_rate = min(100, round((total_completed / total_slots) * 100, 2))
                        success_rate = min(100, round((total_completed / total_slots) * 100, 2))
                        no_show_rate = min(100, round((total_no_shows / total_slots) * 100, 2))

                        dashboard["last_7_days"] = {
                            "total_bookings": total_slots,
                            "appearance_rate": appearance_rate,
                            "success_rate": success_rate,
                            "no_show_rate": no_show_rate
                        }
                    else:
                        # Fallback wenn keine Daten vorhanden
                        dashboard["last_7_days"] = {
                            "total_bookings": 0,
                            "appearance_rate": 0,
                            "success_rate": 0,
                            "no_show_rate": 0
                        }
                    
                    # Berechne Statistik ab 01.09.2025
                    start_date = datetime(2025, 9, 1).date()
                    days_since_start = (today - start_date).days + 1
                    date_range = [str(start_date + timedelta(days=i)) for i in range(days_since_start) if start_date + timedelta(days=i) <= today]
                    
                    total_slots_30 = 0
                    total_no_shows_30 = 0
                    total_completed_30 = 0
                    total_cancelled_30 = 0
                    
                    for date_str in date_range:
                        if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                            metrics = all_metrics[date_str]
                            total_slots_30 += metrics.get("total_slots", 0)
                            total_no_shows_30 += metrics.get("no_shows", 0)
                            total_completed_30 += metrics.get("completed", 0)
                            total_cancelled_30 += metrics.get("cancelled", 0)
                    
                    if total_slots_30 > 0:
                        # Auftauchquote = Erschienene / Alle gelegten Termine
                        # Abgesagt und Verschoben zählen als "nicht erschienen"
                        appearance_rate_30 = min(100, round((total_completed_30 / total_slots_30) * 100, 2))
                        success_rate_30 = min(100, round((total_completed_30 / total_slots_30) * 100, 2))
                        no_show_rate_30 = min(100, round((total_no_shows_30 / total_slots_30) * 100, 2))

                        dashboard["since_september"] = {
                            "total_bookings": total_slots_30,
                            "appearance_rate": appearance_rate_30,
                            "success_rate": success_rate_30,
                            "no_show_rate": no_show_rate_30
                        }

                    # Calculate current totals from data since 01.09.2025
                    tracking_start_date = datetime(2025, 9, 1).date()
                    all_total_slots = 0
                    all_total_completed = 0
                    all_total_no_shows = 0
                    all_total_cancelled = 0
                    days_tracked = 0

                    for date_str, metrics in all_metrics.items():
                        try:
                            # Only count data from 01.09.2025 onwards
                            metric_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            if metric_date >= tracking_start_date and isinstance(metrics, dict) and 'total_slots' in metrics:
                                all_total_slots += metrics.get("total_slots", 0)
                                all_total_completed += metrics.get("completed", 0)
                                all_total_no_shows += metrics.get("no_shows", 0)
                                all_total_cancelled += metrics.get("cancelled", 0)
                                days_tracked += 1
                        except:
                            pass

                    if all_total_slots > 0:
                        # Auftauchquote = Erschienene / Alle gelegten Termine
                        # Abgesagt und Verschoben zählen als "nicht erschienen"
                        all_appearance_rate = round((all_total_completed / all_total_slots) * 100, 2)

                        dashboard["current_totals"] = {
                            "total_slots": all_total_slots,
                            "total_appeared": all_total_completed,
                            "total_not_appeared": all_total_no_shows,
                            "total_cancelled": all_total_cancelled,
                            "appearance_rate": all_appearance_rate,
                            "days_tracked": days_tracked
                        }
                    
                    # Trend-Analyse
                    if len(all_metrics) >= 14:
                        # Vergleiche letzte 7 Tage mit vorherigen 7 Tagen
                        prev_7_days = [str(today - timedelta(days=i)) for i in range(7, 14)]
                        
                        prev_no_show_rate = 0
                        prev_count = 0
                        
                        for date_str in prev_7_days:
                            if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                                metrics = all_metrics[date_str]
                                if metrics.get("total_slots", 0) > 0:
                                    prev_no_show_rate += metrics.get("no_show_rate", 0)
                                    prev_count += 1
                        
                        if prev_count > 0:
                            prev_no_show_rate = prev_no_show_rate / prev_count
                            current_no_show_rate = dashboard["last_7_days"].get("no_show_rate", 0)
                            
                            dashboard["trends"]["no_show_trend"] = {
                                "current": current_no_show_rate,
                                "previous": round(prev_no_show_rate, 2),
                                "change": round(current_no_show_rate - prev_no_show_rate, 2),
                                "direction": "up" if current_no_show_rate > prev_no_show_rate else "down"
                            }
                    
                    # Alerts
                    if dashboard["last_7_days"].get("no_show_rate", 0) > 20:
                        dashboard["alerts"].append({
                            "type": "warning",
                            "message": f"Hohe No-Show Rate: {dashboard['last_7_days']['no_show_rate']}%",
                            "severity": "high"
                        })
                        
        except Exception as e:
            logger.error(f"Fehler beim Laden der Dashboard-Daten: {e}")
            # Fallback-Werte beibehalten
        
        return dashboard
    
    def _get_potential_type(self, color_id):
        """Mappe Color ID zu Potential Type"""
        return POTENTIAL_TYPES.get(str(color_id), "unknown")

    def _get_outcome_from_title_and_color(self, title, color_id):
        """
        Bestimme Outcome basierend auf Titel-Keywords (Priorität) und Farbe (Fallback)

        Args:
            title: Event-Titel (Kundenname)
            color_id: Google Calendar Color ID

        Returns:
            str: 'completed', 'no_show', 'cancelled', 'rescheduled'
        """
        title_lower = title.lower() if title else ""

        # 1. Priorität: Titel-basierte Erkennung
        if "nicht erschienen" in title_lower or "ghost" in title_lower:
            return "no_show"
        elif "abgesagt" in title_lower:
            return "cancelled"
        elif "verschoben" in title_lower:
            return "rescheduled"

        # 2. Fallback: Color-basierte Erkennung
        return get_outcome_from_color(color_id)

    def get_user_bookings(self, user, start_date, end_date):
        """
        Hole alle Buchungen eines Users für einen bestimmten Zeitraum
        """
        try:
            bookings = []
            
            if not os.path.exists(self.bookings_file):
                return bookings
            
            with open(self.bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            booking = json.loads(line)
                            if booking.get("user") == user:
                                booking_date = booking.get("date")
                                if start_date <= booking_date <= end_date:
                                    bookings.append({
                                        "date": booking["date"],
                                        "time_slot": booking["time"],
                                        "customer_name": booking["customer"],
                                        "color_id": booking["color_id"],
                                        "description": booking.get("description", ""),
                                        "potential_type": booking.get("potential_type", "unknown")
                                    })
                        except json.JSONDecodeError:
                            continue
            
            return bookings
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der User-Buchungen: {e}")
            return []
    
    def load_all_bookings(self):
        """
        Lade alle Buchungen aus der JSONL-Datei
        """
        try:
            bookings = []
            
            if not os.path.exists(self.bookings_file):
                return bookings
            
            with open(self.bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            booking = json.loads(line)
                            bookings.append(booking)
                        except json.JSONDecodeError:
                            continue
            
            return bookings
            
        except Exception as e:
            logger.error(f"Fehler beim Laden aller Buchungen: {e}")
            return []
    
    def load_historical_data(self):
        """Lädt historische Daten für erweiterte Analysen"""
        try:
            historical_stats_file = "data/historical/historical_stats.json"
            historical_bookings_file = "data/historical/historical_bookings.jsonl"
            historical_outcomes_file = "data/historical/historical_outcomes.jsonl"
            
            historical_data = {
                "stats": {},
                "bookings": [],
                "outcomes": []
            }
            
            # Lade Statistiken
            if os.path.exists(historical_stats_file):
                with open(historical_stats_file, "r", encoding="utf-8") as f:
                    historical_data["stats"] = json.load(f)
            
            # Lade historische Buchungen
            if os.path.exists(historical_bookings_file):
                with open(historical_bookings_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                booking = json.loads(line)
                                historical_data["bookings"].append(booking)
                            except json.JSONDecodeError:
                                continue
            
            # Lade historische Outcomes
            if os.path.exists(historical_outcomes_file):
                with open(historical_outcomes_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                outcome = json.loads(line)
                                historical_data["outcomes"].append(outcome)
                            except json.JSONDecodeError:
                                continue
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der historischen Daten: {e}")
            return {"stats": {}, "bookings": [], "outcomes": []}
    
    def get_enhanced_dashboard(self):
        """Erweiterte Dashboard-Daten mit historischen Daten"""
        try:
            # Hole aktuelle Dashboard-Daten
            current_dashboard = self.get_performance_dashboard()
            
            # Lade historische Daten
            historical_data = self.load_historical_data()
            
            # Kombiniere die Daten
            enhanced_dashboard = {
                "current": current_dashboard,
                "historical": historical_data["stats"],
                "combined_insights": self._generate_combined_insights(current_dashboard, historical_data)
            }
            
            return enhanced_dashboard
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des erweiterten Dashboards: {e}")
            return self.get_performance_dashboard()
    
    def _generate_combined_insights(self, current_dashboard, historical_data):
        """Generiert kombinierte Erkenntnisse aus aktuellen und historischen Daten"""
        try:
            insights = {
                "trends": {},
                "comparisons": {},
                "recommendations": []
            }
            
            # Vergleiche aktuelle vs. historische Quoten
            if historical_data["stats"]:
                hist_stats = historical_data["stats"]
                
                # Auftauchquote Vergleich (neue Klassifizierung)
                # Both rates should be in decimal format for comparison
                current_appearance = current_dashboard.get("last_30_days", {}).get("appearance_rate", 0) / 100.0  # Convert percentage to decimal
                hist_appearance = hist_stats.get("appearance_rate", 0)  # Already in decimal format
                
                insights["comparisons"]["appearance_rate"] = {
                    "current": current_appearance,
                    "historical": hist_appearance,
                    "difference": current_appearance - hist_appearance,
                    "trend": "improving" if current_appearance > hist_appearance else "declining"
                }
                
                # Beste Zeiten basierend auf historischen Daten
                best_times = []
                if "by_time" in hist_stats:
                    time_stats = hist_stats["by_time"]
                    sorted_times = sorted(time_stats.items(), 
                                        key=lambda x: x[1]["appearance_rate"], 
                                        reverse=True)
                    best_times = [time for time, _ in sorted_times[:3]]
                
                # Beste Wochentage basierend auf historischen Daten
                best_weekdays = []
                if "by_weekday" in hist_stats:
                    weekday_stats = hist_stats["by_weekday"]
                    sorted_weekdays = sorted(weekday_stats.items(), 
                                           key=lambda x: x[1]["appearance_rate"], 
                                           reverse=True)
                    best_weekdays = [day for day, _ in sorted_weekdays[:3]]
                
                insights["recommendations"] = [
                    f"Beste historische Auftauchquoten nach Uhrzeit: {', '.join(best_times)}",
                    f"Beste historische Auftauchquoten nach Wochentag: {', '.join(best_weekdays)}",
                    f"Historische Auftauchquote: {hist_appearance:.1%}",
                    f"Aktuelle Auftauchquote: {current_appearance:.1%}"
                ]
            
            return insights

        except Exception as e:
            logger.error(f"Fehler bei der Generierung von Erkenntnissen: {e}")
            return {"trends": {}, "comparisons": {}, "recommendations": []}

    def get_last_n_workdays_stats(self, n=5):
        """
        Hole Statistiken für die letzten N Werktage (Mo-Fr)
        Für Admin Tracking-Dashboard

        Args:
            n: Anzahl der Werktage

        Returns:
            Liste mit Tages-Statistiken (neueste zuerst)
        """
        try:
            if not os.path.exists(self.metrics_file):
                return []

            with open(self.metrics_file, "r", encoding="utf-8") as f:
                all_metrics = json.load(f)

            # Finde letzte N Werktage
            today = datetime.now(TZ).date()
            workdays = []
            current_date = today

            while len(workdays) < n:
                # Prüfe ob Werktag (0=Montag, 6=Sonntag)
                if current_date.weekday() < 5:  # Mo-Fr
                    workdays.append(current_date)
                current_date -= timedelta(days=1)

                # Sicherheit: Max 20 Tage zurück
                if (today - current_date).days > 20:
                    break

            # Hole Metriken für diese Tage
            stats = []
            for date in workdays:
                date_str = str(date)
                if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                    metrics = all_metrics[date_str]

                    # Berechne Auftauchquote
                    total_slots = metrics.get("total_slots", 0)
                    completed = metrics.get("completed", 0)
                    no_shows = metrics.get("no_shows", 0)
                    cancelled = metrics.get("cancelled", 0)
                    rescheduled = metrics.get("rescheduled", 0)

                    # Auftauchquote = Erschienene / Alle gelegten Termine
                    # Abgesagt und Verschoben zählen als "nicht erschienen"
                    if total_slots > 0:
                        appearance_rate = round((completed / total_slots) * 100, 1)
                    else:
                        appearance_rate = 0.0

                    stats.append({
                        "date": date_str,
                        "weekday": date.strftime("%A"),
                        "weekday_de": self._get_german_weekday(date.weekday()),
                        "total_slots": total_slots,
                        "completed": completed,
                        "no_shows": no_shows,
                        "cancelled": cancelled,
                        "rescheduled": rescheduled,
                        "appearance_rate": appearance_rate
                    })
                else:
                    # Keine Daten für diesen Tag
                    stats.append({
                        "date": date_str,
                        "weekday": date.strftime("%A"),
                        "weekday_de": self._get_german_weekday(date.weekday()),
                        "total_slots": 0,
                        "completed": 0,
                        "no_shows": 0,
                        "cancelled": 0,
                        "rescheduled": 0,
                        "appearance_rate": 0.0
                    })

            return stats

        except Exception as e:
            logger.error(f"Fehler beim Laden der Werktags-Statistiken: {e}")
            return []

    def get_stats_since_date(self, start_date_str="2025-09-01"):
        """
        Hole Gesamt-Statistiken seit einem bestimmten Datum
        Für Admin Tracking-Dashboard (seit Go-Live)

        Args:
            start_date_str: Start-Datum im Format YYYY-MM-DD

        Returns:
            Dict mit aggregierten Statistiken
        """
        try:
            if not os.path.exists(self.metrics_file):
                return {
                    "start_date": start_date_str,
                    "days_tracked": 0,
                    "total_slots": 0,
                    "completed": 0,
                    "no_shows": 0,
                    "cancelled": 0,
                    "rescheduled": 0,
                    "appearance_rate": 0.0,
                    "completion_rate": 0.0,
                    "no_show_rate": 0.0,
                    "daily_data": []
                }

            with open(self.metrics_file, "r", encoding="utf-8") as f:
                all_metrics = json.load(f)

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            today = datetime.now(TZ).date()

            # Aggregierte Werte
            total_slots = 0
            total_completed = 0
            total_no_shows = 0
            total_cancelled = 0
            total_rescheduled = 0
            days_with_data = 0
            daily_data = []

            # Iteriere über alle Tage seit Start
            current_date = start_date
            while current_date <= today:
                date_str = str(current_date)

                if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                    metrics = all_metrics[date_str]
                    slots = metrics.get("total_slots", 0)

                    if slots > 0:  # Nur Tage mit Daten zählen
                        completed = metrics.get("completed", 0)
                        no_shows = metrics.get("no_shows", 0)
                        cancelled = metrics.get("cancelled", 0)
                        rescheduled = metrics.get("rescheduled", 0)

                        total_slots += slots
                        total_completed += completed
                        total_no_shows += no_shows
                        total_cancelled += cancelled
                        total_rescheduled += rescheduled
                        days_with_data += 1

                        # Für Trend-Chart
                        # Auftauchquote = Erschienene / Alle gelegten Termine
                        if slots > 0:
                            appearance_rate = round((completed / slots) * 100, 1)
                        else:
                            appearance_rate = 0.0

                        # Nur Werktage (Mo-Fr) zum Chart hinzufügen, keine Wochenenden
                        # current_date.weekday(): 0=Montag, 4=Freitag, 5=Samstag, 6=Sonntag
                        if current_date.weekday() < 5:  # Nur Mo-Fr
                            daily_data.append({
                                "date": date_str,
                                "total_slots": slots,
                                "completed": completed,
                                "no_shows": no_shows,
                                "appearance_rate": appearance_rate
                            })

                current_date += timedelta(days=1)

            # Berechne Raten
            # Auftauchquote = Erschienene / Alle gelegten Termine
            # Abgesagt und Verschoben zählen als "nicht erschienen"
            if total_slots > 0:
                appearance_rate = round((total_completed / total_slots) * 100, 1)
            else:
                appearance_rate = 0.0

            if total_slots > 0:
                completion_rate = round((total_completed / total_slots) * 100, 1)
                no_show_rate = round((total_no_shows / total_slots) * 100, 1)
            else:
                completion_rate = 0.0
                no_show_rate = 0.0

            return {
                "start_date": start_date_str,
                "end_date": str(today),
                "days_tracked": days_with_data,
                "total_days": (today - start_date).days + 1,
                "total_slots": total_slots,
                "completed": total_completed,
                "no_shows": total_no_shows,
                "cancelled": total_cancelled,
                "rescheduled": total_rescheduled,
                "appearance_rate": appearance_rate,
                "completion_rate": completion_rate,
                "no_show_rate": no_show_rate,
                "daily_data": daily_data  # Für Charts
            }

        except Exception as e:
            logger.error(f"Fehler beim Laden der Statistiken seit {start_date_str}: {e}")
            return {
                "start_date": start_date_str,
                "days_tracked": 0,
                "total_slots": 0,
                "completed": 0,
                "no_shows": 0,
                "cancelled": 0,
                "rescheduled": 0,
                "appearance_rate": 0.0,
                "completion_rate": 0.0,
                "no_show_rate": 0.0,
                "daily_data": []
            }

    def _get_german_weekday(self, weekday_index):
        """Helper: Englischer Wochentag-Index zu deutschem Namen"""
        weekdays_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        return weekdays_de[weekday_index]

# ----------------- Utility Funktionen -----------------
def recalculate_all_outcomes():
    """
    Neuberechnung aller Outcomes mit korrigiertem Mapping
    Nützlich nach Änderung der Farb-Logik
    """
    tracker = BookingTracker()
    
    # Lösche alte Outcomes
    if os.path.exists(tracker.outcomes_file):
        os.rename(tracker.outcomes_file, tracker.outcomes_file + ".backup")
    
    # Lösche alte Metriken
    if os.path.exists(tracker.metrics_file):
        os.rename(tracker.metrics_file, tracker.metrics_file + ".backup")
    
    logger.info("Recalculating all outcomes with new color mapping...")
    
    # Berechne die letzten 30 Tage neu
    today = datetime.now(TZ).date()
    for i in range(30):
        check_date = today - timedelta(days=i)
        tracker.check_daily_outcomes(check_date)
    
    logger.info("Recalculation complete!")

def backfill_september_data():
    """
    Backfill tracking data from September 2nd, 2025 to today
    This will scan the Google Calendar and process all historical appointments
    """
    from app.config.base import config
    from app.core.google_calendar import get_google_calendar_service

    service = get_google_calendar_service()
    CENTRAL_CALENDAR_ID = config.CENTRAL_CALENDAR_ID

    logger.info("Starting September data backfill...")

    tracker = BookingTracker()

    # Set start date to September 2nd, 2025
    start_date = datetime(2025, 9, 2).date()
    today = datetime.now(TZ).date()

    # Calculate total days
    total_days = (today - start_date).days + 1
    processed_days = 0

    logger.info(f"Backfilling from {start_date} to {today} ({total_days} days)")

    # Process each day
    current_date = start_date
    while current_date <= today:
        try:
            logger.debug(f"Processing {current_date} ({processed_days + 1}/{total_days})")
            tracker.check_daily_outcomes(current_date)
            processed_days += 1

        except Exception as e:
            logger.error(f"Error processing {current_date}: {e}")

        current_date += timedelta(days=1)

    logger.info(f"Backfill complete! Processed {processed_days} days")
    logger.info("Dashboard will now show data from September 2nd onwards")

# ----------------- Cron Job Function -----------------
def run_daily_outcome_check():
    """
    Diese Funktion sollte täglich um 21:00 Uhr laufen
    Kann in GitHub Actions oder als Cron Job eingerichtet werden
    """
    tracker = BookingTracker()
    
    # Prüfe heutigen Tag
    today = datetime.now(TZ).date()
    outcomes = tracker.check_daily_outcomes(today)
    
    # Optional: Prüfe auch gestern (falls der Job mal ausfällt)
    yesterday = today - timedelta(days=1)
    tracker.check_daily_outcomes(yesterday)
    
    logger.info(f"Daily outcome check completed at {datetime.now(TZ).strftime('%H:%M')}")
    
    # Generiere Dashboard
    dashboard = tracker.get_performance_dashboard()
    
    # Sende Alert bei vielen No-Shows
    if dashboard["last_7_days"].get("no_show_rate", 0) > 20:
        logger.warning(f"ALERT: High no-show rate (7 days): {dashboard['last_7_days']['no_show_rate']}%")
        # Hier könnte eine Email/Slack Notification gesendet werden
    
    # Generiere Wochenbericht am Montag
    if datetime.now(TZ).weekday() == 0:  # Montag
        last_week = datetime.now(TZ).isocalendar()[1] - 1
        report = tracker.get_weekly_report(last_week)
        
        report_file = os.path.join(tracker.data_dir, f"weekly_report_{last_week}.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Weekly report generated: {report_file}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--recalculate":
        # Neuberechnung aller Outcomes
        recalculate_all_outcomes()
    else:
        # Normaler täglicher Check
        run_daily_outcome_check()
        
        # Test: Hole Kundenhistorie
        tracker = BookingTracker()
        
        # Beispiel: Dashboard anzeigen
        dashboard = tracker.get_performance_dashboard()
        logger.debug("Performance Dashboard:")
        logger.debug(json.dumps(dashboard, indent=2, ensure_ascii=False))