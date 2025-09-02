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
from datetime import datetime, timedelta, time
from collections import defaultdict
from googleapiclient.discovery import build
from creds_loader import load_google_credentials

# ----------------- Setup -----------------
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TZ = pytz.timezone("Europe/Berlin")
CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")

# Farben-Mapping
COLOR_OUTCOMES = {
    "11": "no_show",      # Tomate/Rot = Nicht erschienen
    "6": "cancelled",     # Mandarine/Orange = Abgesagt/Verschoben
    "2": "completed",     # Grün = Normal abgeschlossen
    "7": "completed",     # Blau = Top Potential abgeschlossen
    "5": "needs_followup", # Gelb = Closer nötig
    "3": "recall"         # Weintraube = Rückholung
}

class BookingTracker:
    def __init__(self):
        self.data_dir = "data/tracking"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Files für verschiedene Tracking-Arten
        self.bookings_file = os.path.join(self.data_dir, "bookings.jsonl")
        self.outcomes_file = os.path.join(self.data_dir, "outcomes.jsonl")
        self.metrics_file = os.path.join(self.data_dir, "daily_metrics.json")
        
        # Google Calendar Service
        creds = load_google_credentials(SCOPES)
        self.service = build("calendar", "v3", credentials=creds)
    
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
            "potential_type": self._get_potential_type(color_id),
            "color_id": color_id,
            "description_length": len(description) if description else 0,
            "has_description": bool(description),
            "booking_lead_time": (datetime.strptime(date, "%Y-%m-%d") - datetime.now(TZ).date()).days,
            "booked_at_hour": datetime.now(TZ).hour,
            "booked_on_weekday": datetime.now(TZ).strftime("%A")
        }
        
        # Append to JSONL file
        with open(self.bookings_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(booking_data, ensure_ascii=False) + "\n")
        
        print(f"✅ Booking tracked: {customer_name} on {date} at {time_slot}")
        return booking_data
    
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
        
        print(f"🔍 Checking outcomes for {check_date}...")
        
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
                # Skip Platzhalter
                if event.get("summary", "").isdigit():
                    continue
                
                # Extrahiere Daten
                customer_name = event.get("summary", "Unknown")
                color_id = event.get("colorId", "9")
                event_start = event.get("start", {}).get("dateTime")
                
                if not event_start:
                    continue
                
                event_time = datetime.fromisoformat(event_start).strftime("%H:%M")
                outcome = COLOR_OUTCOMES.get(color_id, "unknown")
                
                # Track outcome
                outcome_data = {
                    "id": f"{check_date}_{event_time}_{customer_name}".replace(" ", "_"),
                    "timestamp": datetime.now(TZ).isoformat(),
                    "customer": customer_name,
                    "date": str(check_date),
                    "time": event_time,
                    "outcome": outcome,
                    "color_id": color_id,
                    "checked_at": datetime.now(TZ).strftime("%H:%M"),
                    "description": event.get("description", "")
                }
                
                # Spezielle Behandlung für No-Shows
                if outcome == "no_show":
                    outcome_data["alert"] = "NO_SHOW_DETECTED"
                    print(f"⚠️ No-Show detected: {customer_name} at {event_time}")
                
                # Speichere Outcome
                with open(self.outcomes_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(outcome_data, ensure_ascii=False) + "\n")
                
                outcomes_tracked += 1
            
            print(f"✅ Tracked {outcomes_tracked} outcomes for {check_date}")
            
            # Berechne Tagesmetriken
            self._calculate_daily_metrics(check_date, events)
            
            return outcomes_tracked
            
        except Exception as e:
            print(f"❌ Error checking outcomes: {e}")
            return 0
    
    def _calculate_daily_metrics(self, date, events):
        """Berechne und speichere Tagesstatistiken"""
        metrics = {
            "date": str(date),
            "total_slots": len(events),
            "no_shows": 0,
            "completed": 0,
            "cancelled": 0,
            "by_hour": defaultdict(lambda: {"total": 0, "no_shows": 0}),
            "by_user": defaultdict(lambda: {"total": 0, "no_shows": 0}),
            "calculated_at": datetime.now(TZ).isoformat()
        }
        
        for event in events:
            if event.get("summary", "").isdigit():
                continue
            
            color_id = event.get("colorId", "9")
            outcome = COLOR_OUTCOMES.get(color_id, "unknown")
            
            # Zähle Outcomes
            if outcome == "no_show":
                metrics["no_shows"] += 1
            elif outcome in ["completed", "recall"]:
                metrics["completed"] += 1
            elif outcome == "cancelled":
                metrics["cancelled"] += 1
            
            # Nach Stunde
            event_start = event.get("start", {}).get("dateTime")
            if event_start:
                hour = datetime.fromisoformat(event_start).strftime("%H:00")
                metrics["by_hour"][hour]["total"] += 1
                if outcome == "no_show":
                    metrics["by_hour"][hour]["no_shows"] += 1
        
        # Berechne Raten
        if metrics["total_slots"] > 0:
            metrics["no_show_rate"] = round(metrics["no_shows"] / metrics["total_slots"] * 100, 2)
            metrics["completion_rate"] = round(metrics["completed"] / metrics["total_slots"] * 100, 2)
        else:
            metrics["no_show_rate"] = 0
            metrics["completion_rate"] = 0
        
        # Speichere Metriken
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    all_metrics = json.load(f)
            else:
                all_metrics = {}
            
            all_metrics[str(date)] = metrics
            
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(all_metrics, f, ensure_ascii=False, indent=2)
            
            print(f"📊 Daily metrics saved: {metrics['completed']} completed, {metrics['no_shows']} no-shows")
            
        except Exception as e:
            print(f"❌ Error saving metrics: {e}")
    
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
                "no_show_rate": 0
            }
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
                        if outcome["outcome"] == "no_show":
                            history["stats"]["no_shows"] += 1
                        elif outcome["outcome"] in ["completed", "recall"]:
                            history["stats"]["completed"] += 1
        
        # Berechne No-Show Rate
        if history["stats"]["total_bookings"] > 0:
            history["stats"]["no_show_rate"] = round(
                history["stats"]["no_shows"] / history["stats"]["total_bookings"] * 100, 2
            )
        
        return history
    
    def get_weekly_report(self, week_number=None):
        """Generiere Wochenbericht"""
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
                "by_day": defaultdict(lambda: {"bookings": 0, "no_shows": 0}),
                "by_user": defaultdict(lambda: {"bookings": 0, "no_shows": 0}),
                "top_no_show_times": [],
                "top_success_times": []
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
                    # Prüfe ob in der richtigen Woche
                    outcome_date = datetime.strptime(outcome["date"], "%Y-%m-%d")
                    if outcome_date.isocalendar()[1] == week_number:
                        report["metrics"]["total_outcomes"] += 1
                        if outcome["outcome"] == "no_show":
                            report["metrics"]["no_shows"] += 1
                        elif outcome["outcome"] in ["completed", "recall"]:
                            report["metrics"]["completed"] += 1
        
        return report
    
    def _get_potential_type(self, color_id):
        """Mappe Color ID zu Potential Type"""
        mapping = {
            "2": "normal",
            "7": "top",
            "5": "closer_needed",
            "3": "recall",
            "11": "no_show",
            "6": "cancelled"
        }
        return mapping.get(str(color_id), "unknown")

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
    
    print(f"✅ Daily outcome check completed at {datetime.now(TZ).strftime('%H:%M')}")
    
    # Sende Alert bei vielen No-Shows
    if outcomes > 0:
        metrics_file = os.path.join(tracker.data_dir, "daily_metrics.json")
        if os.path.exists(metrics_file):
            with open(metrics_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)
                today_metrics = metrics.get(str(today), {})
                
                if today_metrics.get("no_show_rate", 0) > 20:  # Mehr als 20% No-Shows
                    print(f"⚠️ ALERT: High no-show rate today: {today_metrics['no_show_rate']}%")
                    # Hier könnte eine Email/Slack Notification gesendet werden

# ----------------- Integration in slot_booking_webapp.py -----------------
"""
Füge diese Zeilen in slot_booking_webapp.py ein:

from tracking_system import BookingTracker

# In der book() Funktion nach erfolgreicher Buchung:
if result:
    # Tracking hinzufügen
    tracker = BookingTracker()
    tracker.track_booking(
        customer_name=f"{last}, {first}",
        date=date,
        time_slot=hour,
        user=user,
        color_id=color_id,
        description=description
    )
    
    # Rest der Funktion...
"""

if __name__ == "__main__":
    # Test: Führe täglichen Check aus
    run_daily_outcome_check()
    
    # Test: Hole Kundenhistorie
    tracker = BookingTracker()
    history = tracker.get_customer_history("Müller")
    print(json.dumps(history, indent=2, ensure_ascii=False))