# -*- coding: utf-8 -*-
"""
Tracking System für Slot Booking Webapp - Optimiert
"""

import os
import json
import pytz
from datetime import datetime, timedelta, time
from collections import defaultdict
from googleapiclient.discovery import build
from core.auth.credentials import load_google_credentials
from core.mapping.colors import get_outcome_from_color, get_potential_type

# Setup
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TZ = pytz.timezone("Europe/Berlin")
CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")

class BookingTracker:
    def __init__(self):
        self.data_dir = "data/tracking"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Tracking Files
        self.files = {
            "bookings": os.path.join(self.data_dir, "bookings.jsonl"),
            "outcomes": os.path.join(self.data_dir, "outcomes.jsonl"),
            "metrics": os.path.join(self.data_dir, "daily_metrics.json"),
            "customers": os.path.join(self.data_dir, "customer_profiles.json"),
            "reports": os.path.join(self.data_dir, "latest_weekly_report.json")
        }
        
        # Google Calendar Service
        creds = load_google_credentials(SCOPES)
        self.service = build("calendar", "v3", credentials=creds)
    
    def _append_jsonl(self, file_key, data):
        """Generische JSONL-Append-Methode"""
        try:
            with open(self.files[file_key], "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            return True
        except Exception:
            return False
    
    def _load_json(self, file_key, default=None):
        """Generische JSON-Lade-Methode"""
        try:
            with open(self.files[file_key], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default or {}
    
    def _save_json(self, file_key, data):
        """Generische JSON-Speicher-Methode"""
        try:
            with open(self.files[file_key], "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def track_booking(self, customer_name, date, time_slot, user, color_id, description=""):
        """Tracke eine neue Buchung"""
        booking_data = {
            "id": f"{date}_{time_slot}_{customer_name}".replace(" ", "_"),
            "timestamp": datetime.now(TZ).isoformat(),
            "customer": customer_name,
            "date": date,
            "time": time_slot,
            "weekday": datetime.strptime(date, "%Y-%m-%d").strftime("%A"),
            "week_number": datetime.strptime(date, "%Y-%m-%d").isocalendar()[1],
            "user": user,
            "potential_type": get_potential_type(color_id),
            "color_id": color_id,
            "has_description": bool(description),
            "booking_lead_time": (datetime.strptime(date, "%Y-%m-%d") - datetime.now(TZ).date()).days,
            "booked_at_hour": datetime.now(TZ).hour
        }
        
        return self._append_jsonl("bookings", booking_data)
    
    def check_daily_outcomes(self, check_date=None):
        """Prüft alle Termine eines Tages auf Outcomes"""
        if check_date is None:
            check_date = datetime.now(TZ).date()
        elif isinstance(check_date, str):
            check_date = datetime.strptime(check_date, "%Y-%m-%d").date()
        
        # Hole Events des Tages
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
                # Skip Platzhalter
                if event.get("summary", "").isdigit():
                    continue
                
                customer_name = event.get("summary", "Unknown")
                color_id = event.get("colorId", "9")
                event_start = event.get("start", {}).get("dateTime")
                
                if not event_start:
                    continue
                
                event_time = datetime.fromisoformat(event_start).strftime("%H:%M")
                outcome = get_outcome_from_color(color_id)
                
                # Track outcome
                outcome_data = {
                    "id": f"{check_date}_{event_time}_{customer_name}".replace(" ", "_"),
                    "timestamp": datetime.now(TZ).isoformat(),
                    "customer": customer_name,
                    "date": str(check_date),
                    "time": event_time,
                    "outcome": outcome,
                    "color_id": color_id,
                    "potential_type": get_potential_type(color_id),
                    "checked_at": datetime.now(TZ).strftime("%H:%M")
                }
                
                if outcome == "no_show":
                    outcome_data["alert"] = "NO_SHOW_DETECTED"
                
                self._append_jsonl("outcomes", outcome_data)
                outcomes_tracked += 1
            
            # Berechne Tagesmetriken
            self._calculate_daily_metrics(check_date, events)
            self._update_customer_profiles()
            
            return outcomes_tracked
            
        except Exception:
            return 0
    
    def _calculate_daily_metrics(self, date, events):
        """Berechne und speichere Tagesstatistiken"""
        metrics = {
            "date": str(date),
            "total_slots": 0,
            "no_shows": 0,
            "completed": 0,
            "cancelled": 0,
            "calculated_at": datetime.now(TZ).isoformat()
        }
        
        for event in events:
            if event.get("summary", "").isdigit():
                continue
            
            metrics["total_slots"] += 1
            color_id = event.get("colorId", "9")
            outcome = get_outcome_from_color(color_id)
            
            if outcome == "no_show":
                metrics["no_shows"] += 1
            elif outcome == "completed":
                metrics["completed"] += 1
            elif outcome == "cancelled":
                metrics["cancelled"] += 1
        
        # Berechne Raten
        if metrics["total_slots"] > 0:
            metrics["no_show_rate"] = round(metrics["no_shows"] / metrics["total_slots"] * 100, 2)
            metrics["completion_rate"] = round(metrics["completed"] / metrics["total_slots"] * 100, 2)
            metrics["cancellation_rate"] = round(metrics["cancelled"] / metrics["total_slots"] * 100, 2)
        else:
            metrics["no_show_rate"] = metrics["completion_rate"] = metrics["cancellation_rate"] = 0
        
        # Speichere Metriken
        all_metrics = self._load_json("metrics", {})
        all_metrics[str(date)] = metrics
        self._save_json("metrics", all_metrics)
    
    def _update_customer_profiles(self):
        """Aktualisiere Kundenprofile"""
        profiles = self._load_json("customers", {})
        
        # Analysiere alle Outcomes
        try:
            with open(self.files["outcomes"], "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        outcome = json.loads(line)
                        customer = outcome["customer"]
                        
                        if customer not in profiles:
                            profiles[customer] = {
                                "first_seen": outcome["date"],
                                "total_appointments": 0,
                                "completed": 0,
                                "no_shows": 0,
                                "cancelled": 0
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
                        
                        # ZuverlÃ¤ssigkeits-Score
                        if profile["total_appointments"] > 0:
                            profile["reliability_score"] = round(
                                (profile["completed"] / profile["total_appointments"]) * 100, 2
                            )
                        
                        # Risk Level
                        if profile["no_shows"] >= 3:
                            profile["risk_level"] = "high"
                        elif profile["no_shows"] >= 1:
                            profile["risk_level"] = "medium"
                        else:
                            profile["risk_level"] = "low"
                    
                    except Exception:
                        continue
        except Exception:
            pass
        
        self._save_json("customers", profiles)
    
    def _calculate_period_metrics(self, days):
        """Generische Periode-Metriken-Berechnung"""
        today = datetime.now(TZ).date()
        date_range = [str(today - timedelta(days=i)) for i in range(days)]
        
        all_metrics = self._load_json("metrics", {})
        totals = {"total_slots": 0, "no_shows": 0, "completed": 0, "cancelled": 0}
        
        for date_str in date_range:
            if date_str in all_metrics:
                metrics = all_metrics[date_str]
                for key in totals:
                    totals[key] += metrics.get(key, 0)
        
        # Berechne Raten
        if totals["total_slots"] > 0:
            appearance_base = totals["completed"] + totals["no_shows"]
            appearance_rate = round((totals["completed"] / appearance_base) * 100, 2) if appearance_base > 0 else 0
            success_rate = round((totals["completed"] / totals["total_slots"]) * 100, 2)
            no_show_rate = round((totals["no_shows"] / totals["total_slots"]) * 100, 2)
        else:
            appearance_rate = success_rate = no_show_rate = 0
        
        return {
            "total_bookings": totals["total_slots"],
            "appearance_rate": appearance_rate,
            "success_rate": success_rate,
            "no_show_rate": no_show_rate
        }
    
    def get_performance_dashboard(self):
        """Performance Dashboard mit konsolidierten Berechnungen"""
        dashboard = {
            "generated_at": datetime.now(TZ).isoformat(),
            "current_week": {
                "number": datetime.now(TZ).isocalendar()[1],
                "year": datetime.now(TZ).year
            },
            "last_7_days": self._calculate_period_metrics(7),
            "last_30_days": self._calculate_period_metrics(30),
            "alerts": []
        }
        
        # Trend-Analyse (7 vs vorherige 7 Tage)
        current_week_metrics = self._calculate_period_metrics(7)
        previous_week_metrics = self._calculate_period_metrics_offset(7, 7)
        
        if previous_week_metrics and current_week_metrics:
            no_show_change = current_week_metrics["no_show_rate"] - previous_week_metrics["no_show_rate"]
            dashboard["trends"] = {
                "no_show_trend": {
                    "current": current_week_metrics["no_show_rate"],
                    "previous": previous_week_metrics["no_show_rate"],
                    "change": round(no_show_change, 2),
                    "direction": "up" if no_show_change > 0 else "down"
                }
            }
        
        # Alerts
        if dashboard["last_7_days"]["no_show_rate"] > 20:
            dashboard["alerts"].append({
                "type": "warning",
                "message": f"Hohe No-Show Rate: {dashboard['last_7_days']['no_show_rate']}%",
                "severity": "high"
            })
        
        return dashboard
    
    def _calculate_period_metrics_offset(self, days, offset):
        """Berechne Metriken für Periode mit Offset"""
        today = datetime.now(TZ).date()
        start_offset = offset
        end_offset = offset + days
        date_range = [str(today - timedelta(days=i)) for i in range(start_offset, end_offset)]
        
        all_metrics = self._load_json("metrics", {})
        totals = {"total_slots": 0, "no_shows": 0, "completed": 0, "cancelled": 0}
        
        for date_str in date_range:
            if date_str in all_metrics:
                metrics = all_metrics[date_str]
                for key in totals:
                    totals[key] += metrics.get(key, 0)
        
        if totals["total_slots"] > 0:
            return {
                "total_bookings": totals["total_slots"],
                "no_show_rate": round((totals["no_shows"] / totals["total_slots"]) * 100, 2),
                "success_rate": round((totals["completed"] / totals["total_slots"]) * 100, 2)
            }
        return None
    
    def get_weekly_report(self, week_number=None):
        """Generiere Wochenbericht"""
        if week_number is None:
            week_number = datetime.now(TZ).isocalendar()[1]
        
        report = {
            "week": week_number,
            "year": datetime.now(TZ).year,
            "metrics": self._calculate_week_aggregates(week_number)
        }
        
        self._save_json("reports", report)
        return report
    
    def _calculate_week_aggregates(self, week_number):
        """Berechne Wochen-Aggregate"""
        metrics = {
            "total_bookings": 0,
            "total_outcomes": 0,
            "no_shows": 0,
            "completed": 0,
            "cancelled": 0,
            "by_day": defaultdict(lambda: {"bookings": 0, "no_shows": 0, "completed": 0}),
            "by_user": defaultdict(lambda: {"bookings": 0, "completed": 0})
        }
        
        # Analysiere Outcomes für die Woche
        try:
            with open(self.files["outcomes"], "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        outcome = json.loads(line)
                        outcome_date = datetime.strptime(outcome["date"], "%Y-%m-%d")
                        
                        if outcome_date.isocalendar()[1] == week_number:
                            metrics["total_outcomes"] += 1
                            weekday = outcome_date.strftime("%A")
                            
                            if outcome["outcome"] == "no_show":
                                metrics["no_shows"] += 1
                                metrics["by_day"][weekday]["no_shows"] += 1
                            elif outcome["outcome"] == "completed":
                                metrics["completed"] += 1
                                metrics["by_day"][weekday]["completed"] += 1
                            elif outcome["outcome"] == "cancelled":
                                metrics["cancelled"] += 1
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Berechne Raten
        if metrics["total_outcomes"] > 0:
            metrics["overall_no_show_rate"] = round((metrics["no_shows"] / metrics["total_outcomes"]) * 100, 2)
            metrics["overall_completion_rate"] = round((metrics["completed"] / metrics["total_outcomes"]) * 100, 2)
        
        return metrics
    
    def get_customer_history(self, customer_name):
        """Hole Kundenhistorie"""
        history = {
            "customer": customer_name,
            "outcomes": [],
            "stats": {"total_bookings": 0, "no_shows": 0, "completed": 0, "cancelled": 0}
        }
        
        # Lade Outcomes
        try:
            with open(self.files["outcomes"], "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        outcome = json.loads(line)
                        if customer_name.lower() in outcome["customer"].lower():
                            history["outcomes"].append(outcome)
                            
                            if outcome["outcome"] == "no_show":
                                history["stats"]["no_shows"] += 1
                            elif outcome["outcome"] == "completed":
                                history["stats"]["completed"] += 1
                            elif outcome["outcome"] == "cancelled":
                                history["stats"]["cancelled"] += 1
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Berechne Raten
        total_outcomes = sum(history["stats"].values())
        if total_outcomes > 0:
            history["stats"]["no_show_rate"] = round((history["stats"]["no_shows"] / total_outcomes) * 100, 2)
            history["stats"]["reliability_score"] = round((history["stats"]["completed"] / total_outcomes) * 100, 2)
        
        return history
    
    def load_all_bookings(self):
        """Lade alle Buchungen"""
        bookings = []
        try:
            with open(self.files["bookings"], "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        bookings.append(json.loads(line))
                    except Exception:
                        continue
        except Exception:
            pass
        return bookings
    
    def get_user_bookings(self, user, start_date, end_date):
        """Hole User-Buchungen für Zeitraum"""
        bookings = []
        try:
            with open(self.files["bookings"], "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        booking = json.loads(line)
                        if (booking.get("user") == user and 
                            start_date <= booking.get("date", "") <= end_date):
                            bookings.append({
                                "date": booking["date"],
                                "time_slot": booking["time"],
                                "customer_name": booking["customer"],
                                "color_id": booking["color_id"],
                                "potential_type": booking.get("potential_type", "unknown")
                            })
                    except Exception:
                        continue
        except Exception:
            pass
        return bookings

# Utility Functions
def run_daily_outcome_check():
    """Täglicher Outcome-Check (für GitHub Actions)"""
    tracker = BookingTracker()
    
    today = datetime.now(TZ).date()
    outcomes = tracker.check_daily_outcomes(today)
    
    # Prüfe auch gestern (Fallback)
    yesterday = today - timedelta(days=1)
    tracker.check_daily_outcomes(yesterday)
    
    # Dashboard erstellen
    dashboard = tracker.get_performance_dashboard()
    
    # Alert bei hoher No-Show Rate
    if dashboard["last_7_days"].get("no_show_rate", 0) > 20:
        print(f"ALERT: High no-show rate: {dashboard['last_7_days']['no_show_rate']}%")
    
    # Wochenbericht am Montag
    if datetime.now(TZ).weekday() == 0:
        last_week = datetime.now(TZ).isocalendar()[1] - 1
        tracker.get_weekly_report(last_week)
    
    return outcomes

def recalculate_all_outcomes():
    """Neuberechnung aller Outcomes (Reparatur-Funktion)"""
    tracker = BookingTracker()
    
    # Backup alte Dateien
    for key in ["outcomes", "metrics"]:
        if os.path.exists(tracker.files[key]):
            os.rename(tracker.files[key], tracker.files[key] + ".backup")
    
    # Berechne letzte 30 Tage neu
    today = datetime.now(TZ).date()
    for i in range(30):
        check_date = today - timedelta(days=i)
        tracker.check_daily_outcomes(check_date)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--recalculate":
        recalculate_all_outcomes()
    else:
        run_daily_outcome_check()