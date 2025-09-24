#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Points Correction - Automatische Analyse und Korrektur
Analysiert automatisch alle Buchungen der letzten 3 Tage und berechnet korrekte Punkte-Differenzen
"""

import json
import os
import pytz
from datetime import datetime, timedelta
from collections import defaultdict

# Import app modules
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.google_calendar import get_google_calendar_service
from app.config.base import config, slot_config

TZ = pytz.timezone(slot_config.TIMEZONE)

def calculate_correct_points(hour, slot_date, estimated_utilization=0.5):
    """Calculate correct points based on new system"""
    # Base points based on estimated utilization
    if estimated_utilization <= 0.33:
        points = 5
    elif estimated_utilization <= 0.66:
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

def load_tracking_data():
    """Load tracking data to identify who booked what"""
    tracking_files = [
        "data/tracking/daily_metrics.json",
        "data/tracking/customer_profiles.json"
    ]

    tracking_data = {}
    print("Suche nach Tracking-Dateien:")

    for file_path in tracking_files:
        print(f"  Prüfe: {file_path} - {'EXISTS' if os.path.exists(file_path) else 'NOT FOUND'}")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    tracking_data[os.path.basename(file_path)] = data
                    print(f"  ✓ Geladen: {file_path} ({len(data)} Einträge)")
            except Exception as e:
                print(f"  ✗ FEHLER beim Laden {file_path}: {e}")
        else:
            # Try alternative paths
            alt_paths = [
                file_path.replace("data/", ""),
                file_path.replace("data/", "static/"),
                f"src/{file_path}",
                f"/opt/render/project/src/{file_path}"
            ]
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    print(f"  ✓ Gefunden unter: {alt_path}")
                    try:
                        with open(alt_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            tracking_data[os.path.basename(file_path)] = data
                            print(f"    Geladen: ({len(data)} Einträge)")
                    except Exception as e:
                        print(f"    FEHLER: {e}")
                    break

    print(f"Geladene Tracking-Dateien: {list(tracking_data.keys())}")
    return tracking_data

def analyze_recent_bookings_smart():
    """Smart analysis of recent bookings with automatic user mapping"""
    print("Intelligente Analyse der letzten 3 Tage...")

    # Calculate date range
    today = datetime.now(TZ).date()
    start_date = today - timedelta(days=3)
    end_date = today

    print(f"Zeitraum: {start_date} bis {end_date}")

    # Load tracking data first
    tracking_data = load_tracking_data()
    daily_metrics = tracking_data.get('daily_metrics.json', {})

    # Analyze from daily metrics (this should have user->booking mapping)
    user_corrections = defaultdict(int)
    detailed_analysis = []

    for days_back in range(4):  # Last 3-4 days
        check_date = today - timedelta(days=days_back)
        date_str = check_date.strftime("%Y-%m-%d")

        if date_str in daily_metrics:
            day_data = daily_metrics[date_str]
            print(f"\nAnalysiere {date_str}:")

            # Check by_hour data for bookings
            if 'by_hour' in day_data:
                for hour, hour_data in day_data['by_hour'].items():
                    total_bookings = hour_data.get('total', 0)
                    if total_bookings > 0:
                        print(f"  {hour}: {total_bookings} Buchungen")

                        # Calculate what points should have been vs old system
                        old_points_per_booking = 10  # Old system
                        correct_points_per_booking = calculate_correct_points(hour, check_date, 0.5)

                        points_diff_per_booking = old_points_per_booking - correct_points_per_booking
                        total_excess_points = points_diff_per_booking * total_bookings

                        detailed_analysis.append({
                            'date': date_str,
                            'hour': hour,
                            'bookings': total_bookings,
                            'old_points_per': old_points_per_booking,
                            'correct_points_per': correct_points_per_booking,
                            'excess_per_booking': points_diff_per_booking,
                            'total_excess': total_excess_points
                        })

                        print(f"    Alte Punkte: {old_points_per_booking} -> Korrekt: {correct_points_per_booking}")
                        print(f"    Überschuss pro Buchung: {points_diff_per_booking}")
                        print(f"    Gesamt-Überschuss: {total_excess_points}")

            # Try to map to users if by_user data available
            if 'by_user' in day_data:
                print(f"  Benutzer-Daten gefunden für {date_str}")
                for user, user_data in day_data['by_user'].items():
                    user_bookings = user_data.get('bookings', 0)
                    if user_bookings > 0:
                        # Estimate points excess for this user
                        # We don't know exact times, so use average
                        avg_excess_per_booking = 5  # Conservative estimate (10 old - ~5 new average)
                        estimated_excess = user_bookings * avg_excess_per_booking
                        user_corrections[user] += estimated_excess

                        print(f"    {user}: {user_bookings} Buchungen -> geschätzt {estimated_excess} Punkte-Überschuss")

    return user_corrections, detailed_analysis

def get_current_scores():
    """Load current user scores"""
    possible_paths = [
        "data/persistent/persistent_data.json",
        "src/data/persistent/persistent_data.json",
        "/opt/render/project/src/data/persistent/persistent_data.json",
        "static/persistent_data.json",
        "persistent_data.json"
    ]

    print("Suche nach Scores-Datei:")
    for scores_file in possible_paths:
        print(f"  Prüfe: {scores_file} - {'EXISTS' if os.path.exists(scores_file) else 'NOT FOUND'}")
        if os.path.exists(scores_file):
            try:
                with open(scores_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    scores = data.get('scores', {})
                    print(f"  ✓ Scores geladen: {list(scores.keys())}")
                    return scores
            except Exception as e:
                print(f"  ✗ FEHLER beim Laden {scores_file}: {e}")

    print("  Keine Scores-Datei gefunden!")
    return {}

def save_corrected_scores(scores):
    """Save corrected scores back to file"""
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
        print(f"FEHLER beim Speichern: {e}")
        return False

def apply_smart_corrections():
    """Apply smart corrections automatically"""
    print("=" * 60)
    print("SMART POINTS CORRECTION - Automatische Analyse")
    print("=" * 60)

    # Get current scores
    current_scores = get_current_scores()
    print(f"Aktuelle Benutzer: {list(current_scores.keys())}")

    # Analyze recent bookings
    user_corrections, detailed_analysis = analyze_recent_bookings_smart()

    if not user_corrections and detailed_analysis:
        # Fallback: Equal distribution based on total excess points
        print(f"\nKeine Benutzer-spezifischen Daten gefunden.")
        print("FALLBACK: Gleichmäßige Verteilung basierend auf aktuellen Scores...")

        total_excess = sum(analysis['total_excess'] for analysis in detailed_analysis)
        print(f"Gesamt-Überschuss aus Buchungen: {total_excess} Punkte")

        if current_scores:
            current_month = datetime.now(TZ).strftime("%Y-%m")
            active_users = []

            for user, user_scores in current_scores.items():
                if current_month in user_scores and user_scores[current_month] > 0:
                    active_users.append(user)

            print(f"Aktive Benutzer mit Punkten: {active_users}")

            if active_users:
                # Distribute excess based on current score proportion
                total_current_points = sum(current_scores[user].get(current_month, 0) for user in active_users)

                for user in active_users:
                    user_current = current_scores[user].get(current_month, 0)
                    if total_current_points > 0:
                        proportion = user_current / total_current_points
                        estimated_excess = int(total_excess * proportion)
                        if estimated_excess > 0:
                            user_corrections[user] = estimated_excess
                            print(f"  {user}: {user_current} Punkte -> geschätzt {estimated_excess} Punkte-Überschuss")

    if not user_corrections:
        print("\nKeine automatischen Korrekturen identifiziert.")
        print("Möglicherweise sind bereits korrekte Punkte vergeben oder keine Tracking-Daten verfügbar.")
        return {}, current_scores

    print("\n" + "=" * 50)
    print("IDENTIFIZIERTE KORREKTUREN:")
    print("=" * 50)

    current_month = datetime.now(TZ).strftime("%Y-%m")
    total_corrections = 0

    for user, excess_points in user_corrections.items():
        if user in current_scores and excess_points > 0:
            current_user_score = current_scores[user].get(current_month, 0)
            corrected_score = max(0, current_user_score - excess_points)

            print(f"{user}:")
            print(f"  Aktuell: {current_user_score} Punkte")
            print(f"  Abzuziehen: {excess_points} Punkte")
            print(f"  Nach Korrektur: {corrected_score} Punkte")
            print()

            total_corrections += excess_points

    print(f"GESAMT zu korrigierende Punkte: {total_corrections}")

    # Confirmation
    if total_corrections > 0:
        print("\nDETAILLIERTE ANALYSE:")
        print("-" * 40)
        for analysis in detailed_analysis:
            if analysis['total_excess'] > 0:
                print(f"{analysis['date']} {analysis['hour']}: {analysis['bookings']} Buchungen")
                print(f"  {analysis['old_points_per']} -> {analysis['correct_points_per']} Punkte/Buchung")
                print(f"  Überschuss: {analysis['total_excess']} Punkte")

        print(f"\nMöchtest du diese Korrekturen anwenden? (ja/nein)")
        print("HINWEIS: Dies wird die Punktestände permanent ändern!")

        # For automated execution, we'll create a preview mode
        return user_corrections, current_scores

    return {}, current_scores

def create_correction_preview():
    """Create a preview of what would be corrected"""
    corrections, current_scores = apply_smart_corrections()

    if corrections:
        print("\n" + "=" * 50)
        print("PREVIEW-MODUS: Korrekturen NICHT angewendet")
        print("=" * 50)
        print("Um die Korrekturen tatsächlich anzuwenden:")
        print("python smart_points_correction.py --apply")

    return corrections, current_scores

def apply_corrections_confirmed(corrections, current_scores):
    """Actually apply the corrections"""
    current_month = datetime.now(TZ).strftime("%Y-%m")

    # Apply corrections
    for user, excess_points in corrections.items():
        if user in current_scores:
            old_score = current_scores[user].get(current_month, 0)
            current_scores[user][current_month] = max(0, old_score - excess_points)
            print(f"✓ {user}: {old_score} -> {current_scores[user][current_month]} (-{excess_points})")

    # Save corrected scores
    if save_corrected_scores(current_scores):
        print("\n✅ Korrekturen erfolgreich angewendet!")
        return True
    else:
        print("\n❌ FEHLER beim Speichern der Korrekturen!")
        return False

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--apply':
        # Apply mode
        corrections, current_scores = apply_smart_corrections()
        if corrections:
            print("\nWENDE KORREKTUREN AN...")
            apply_corrections_confirmed(corrections, current_scores)
    else:
        # Preview mode
        create_correction_preview()

if __name__ == "__main__":
    main()