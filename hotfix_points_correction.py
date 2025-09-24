#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hotfix Script: Korrektur der Punkte für die letzten 3 Tage
Behebt das Problem mit zu vielen Punkten pro Buchung (10 statt korrekte Anzahl)
"""

import json
import os
import pytz
from datetime import datetime, timedelta
from collections import defaultdict

# Import app modules
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from app.core.extensions import data_persistence  # Import issue
from app.core.google_calendar import get_google_calendar_service
from app.services.booking_service import get_effective_availability, get_slot_status
from app.config.base import config, slot_config

TZ = pytz.timezone(slot_config.TIMEZONE)

def calculate_correct_points(hour, slot_date, utilization_rate=0.5):
    """
    Calculate correct points based on new system
    Since we can't know exact historical utilization, use estimated average
    """
    # Base points based on estimated utilization
    if utilization_rate <= 0.33:
        points = 5
    elif utilization_rate <= 0.66:
        points = 3
    else:
        points = 1

    # Time bonus for less popular slots
    if hour in ["11:00", "14:00"]:
        points += 2

    # Weekend bonus
    if slot_date.weekday() >= 5:
        points += 1

    return points

def analyze_recent_bookings():
    """Analyze bookings from the last 3 days"""
    print("Analysiere Buchungen der letzten 3 Tage...")

    # Calculate date range
    today = datetime.now(TZ).date()
    start_date = today - timedelta(days=3)
    end_date = today

    print(f"Zeitraum: {start_date} bis {end_date}")

    # Get Google Calendar service
    calendar_service = get_google_calendar_service()
    if not calendar_service:
        print("FEHLER: Google Calendar Service nicht verfügbar")
        return []

    # Fetch events from the last 3 days
    start_dt = TZ.localize(datetime.combine(start_date, datetime.min.time()))
    end_dt = TZ.localize(datetime.combine(end_date, datetime.max.time()))

    try:
        events_result = calendar_service.get_events(
            calendar_id=config.CENTRAL_CALENDAR_ID,
            time_min=start_dt.isoformat(),
            time_max=end_dt.isoformat(),
            max_results=500
        )
        events = events_result.get('items', []) if events_result else []
    except Exception as e:
        print(f"FEHLER beim Abrufen der Kalender-Events: {e}")
        return []

    print(f"{len(events)} Events gefunden")

    # Analyze events and calculate corrections
    corrections = defaultdict(lambda: defaultdict(int))  # user -> date -> points_correction

    for event in events:
        if "start" in event and "dateTime" in event["start"]:
            try:
                dt = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                event_date = dt.date()
                event_hour = dt.strftime("%H:%M")

                # Skip T1-bereit events
                summary = event.get("summary", "")
                if 't1-bereit' in summary.lower() or 't1 bereit' in summary.lower():
                    continue

                # Only process standard booking hours
                if event_hour not in ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]:
                    continue

                print(f"Event: {summary} am {event_date} um {event_hour}")

                # Calculate what points should have been awarded (vs the 10 that were given)
                old_points = 10  # What was wrongly awarded

                # For correction, assume moderate utilization (0.5) as we can't reconstruct exact historical data
                correct_points = calculate_correct_points(event_hour, event_date, 0.5)

                points_diff = old_points - correct_points

                if points_diff != 0:
                    # Try to extract user from booking tracking or assume from current session
                    # For now, we'll need to manually identify or ask for user mapping
                    print(f"   Alte Punkte: {old_points}, Korrekte Punkte: {correct_points}, Differenz: {points_diff}")

                    # Add to corrections (we'll need to map customers to users manually)
                    date_str = event_date.strftime("%Y-%m-%d")
                    corrections[f"EVENT_{summary}_{date_str}_{event_hour}"] = {
                        'summary': summary,
                        'date': date_str,
                        'hour': event_hour,
                        'old_points': old_points,
                        'correct_points': correct_points,
                        'points_to_subtract': points_diff
                    }

            except Exception as e:
                print(f"FEHLER beim Verarbeiten des Events: {e}")
                continue

    return corrections

def get_user_booking_mapping():
    """
    Get user to booking mapping from tracking data or ask for manual mapping
    """
    # Try to load from tracking system
    try:
        # Load from daily_metrics file directly
        metrics_file = "data/tracking/daily_metrics.json"
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
        else:
            tracking_data = {}

        user_mappings = {}

        # Look through recent metrics to find user bookings
        today = datetime.now(TZ).date()

        for days_back in range(4):  # Last 4 days
            check_date = today - timedelta(days=days_back)
            date_str = check_date.strftime("%Y-%m-%d")

            if date_str in tracking_data and 'by_user' in tracking_data[date_str]:
                for user, user_data in tracking_data[date_str]['by_user'].items():
                    if user not in user_mappings:
                        user_mappings[user] = []
                    user_mappings[user].append({
                        'date': date_str,
                        'bookings': user_data.get('bookings', [])
                    })

        return user_mappings
    except Exception as e:
        print(f"WARNUNG: Konnte Benutzer-Mapping nicht automatisch laden: {e}")
        return {}

def load_scores_direct():
    """Load scores directly from JSON file"""
    scores_file = "data/persistent/persistent_data.json"
    if os.path.exists(scores_file):
        try:
            with open(scores_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('scores', {})
        except Exception as e:
            print(f"FEHLER beim Laden von {scores_file}: {e}")
            return {}
    else:
        print(f"Scores-Datei nicht gefunden: {scores_file}")
        return {}

def save_scores_direct(scores):
    """Save scores directly to JSON file"""
    scores_file = "data/persistent/persistent_data.json"
    try:
        # Load existing data
        data = {}
        if os.path.exists(scores_file):
            with open(scores_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # Update scores
        data['scores'] = scores

        # Save back
        with open(scores_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"FEHLER beim Speichern von {scores_file}: {e}")
        return False

def apply_corrections():
    """Apply point corrections to user scores"""
    print("\nStarte Punkte-Korrektur...")

    # Load current scores
    try:
        scores = load_scores_direct()
        print(f"Aktuelle Scores geladen: {len(scores)} Benutzer")
    except Exception as e:
        print(f"FEHLER beim Laden der Scores: {e}")
        return False

    # Get corrections
    corrections = analyze_recent_bookings()

    if not corrections:
        print("Keine Korrekturen erforderlich")
        return True

    print(f"{len(corrections)} Events benoetigen Korrektur")

    # Show what would be corrected
    total_points_to_subtract = 0
    print("\nKorrekturen die angewendet werden wuerden:")
    for event_key, correction in corrections.items():
        print(f"  - {correction['summary']}: {correction['date']} {correction['hour']}")
        print(f"    Alt: {correction['old_points']} → Neu: {correction['correct_points']} (Differenz: -{correction['points_to_subtract']})")
        total_points_to_subtract += correction['points_to_subtract']

    print(f"\nGesamt zu subtrahierende Punkte: {total_points_to_subtract}")

    # Manual user assignment needed
    print("\nACHTUNG: Automatische Benutzer-Zuordnung nicht moeglich.")
    print("Die Punkte-Korrektur muss manuell pro Benutzer angewendet werden.")
    print("\nSchritte:")
    print("1. Prüfe welcher Benutzer welche Termine gebucht hat")
    print("2. Führe dieses Script erneut aus mit --apply-user-corrections")

    return True

def manual_correction_mode():
    """Interactive mode for manual corrections"""
    print("\nManueller Korrektur-Modus")
    print("Format: Benutzername:Punkte_abziehen")
    print("Beispiel: Ladislav:27")
    print("Beenden mit 'done'")

    corrections_applied = False

    while True:
        user_input = input("\nKorrektur eingeben (oder 'done'): ").strip()

        if user_input.lower() == 'done':
            break

        if ':' not in user_input:
            print("FEHLER: Ungueltiges Format. Verwende: Benutzername:Punkte")
            continue

        try:
            username, points_str = user_input.split(':', 1)
            points_to_subtract = int(points_str)

            if points_to_subtract <= 0:
                print("FEHLER: Punkte muessen positiv sein")
                continue

            # Apply correction
            scores = load_scores_direct()
            current_month = datetime.now(TZ).strftime("%Y-%m")

            if username not in scores:
                print(f"FEHLER: Benutzer '{username}' nicht gefunden in Scores")
                continue

            if current_month not in scores[username]:
                scores[username][current_month] = 0

            old_score = scores[username][current_month]
            scores[username][current_month] = max(0, old_score - points_to_subtract)
            new_score = scores[username][current_month]

            # Save corrected scores
            if save_scores_direct(scores):
                print(f"OK {username}: {old_score} -> {new_score} (-{points_to_subtract} Punkte)")
                corrections_applied = True
            else:
                print(f"FEHLER beim Speichern der Korrektur für {username}")

        except ValueError:
            print("FEHLER: Punkte muessen eine Zahl sein")
        except Exception as e:
            print(f"FEHLER bei der Korrektur: {e}")

    if corrections_applied:
        print("\nKorrekturen erfolgreich angewendet!")
    else:
        print("\nKeine Korrekturen angewendet")

def main():
    """Main function"""
    print("Punkte-Korrektur Hotfix gestartet")
    print("=" * 50)

    if len(sys.argv) > 1 and sys.argv[1] == '--manual':
        manual_correction_mode()
    else:
        apply_corrections()
        print("\nFür manuelle Korrekturen: python hotfix_points_correction.py --manual")

if __name__ == "__main__":
    main()