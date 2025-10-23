# -*- coding: utf-8 -*-
"""
Backfill Tracking Data
Erfasst Tracking-Daten rückwirkend für fehlende Tage ab 01.09.2025
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytz

TZ = pytz.timezone("Europe/Berlin")


def backfill_tracking_data(start_date_str="2025-09-01", end_date_str=None, dry_run=False):
    """
    Erfasst Tracking-Daten rückwirkend für alle Tage zwischen start_date und end_date.

    Args:
        start_date_str: Start-Datum im Format YYYY-MM-DD (default: 2025-09-01)
        end_date_str: End-Datum im Format YYYY-MM-DD (default: heute)
        dry_run: Wenn True, werden keine Daten geschrieben (nur Simulation)
    """
    global tracking_system

    # Fix Windows encoding
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 70)
    print("TRACKING DATA BACKFILL")
    print("=" * 70)
    print()

    # Get tracking system from Flask extensions
    from app.core.extensions import tracking_system

    if not tracking_system:
        print("Fehler: Tracking-System nicht verfuegbar!")
        return

    print("Tracking-System erfolgreich initialisiert")
    print()

    # Parse dates
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    else:
        end_date = datetime.now(TZ).date()

    print(f"Start-Datum: {start_date}")
    print(f"End-Datum:   {end_date}")
    print(f"Modus:       {'DRY RUN (keine Aenderungen)' if dry_run else 'LIVE (Daten werden geschrieben)'}")
    print()

    # Berechne Anzahl der Tage
    days_to_process = (end_date - start_date).days + 1
    print(f"Zu verarbeitende Tage: {days_to_process}")
    print()

    if not dry_run:
        confirm = input("Moechtest du fortfahren? (ja/nein): ")
        if confirm.lower() not in ['ja', 'yes', 'y', 'j']:
            print("Abgebrochen")
            return
        print()

    # Tracking-Daten für jeden Tag erfassen
    success_count = 0
    error_count = 0
    skipped_count = 0

    current_date = start_date

    print("Starte Backfill...")
    print("-" * 70)

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        day_name = current_date.strftime("%A")

        try:
            # Check if data already exists
            existing_metrics = tracking_system._load_metrics()

            if date_str in existing_metrics and not dry_run:
                print(f">> {date_str} ({day_name}) - Bereits vorhanden, ueberspringe...")
                skipped_count += 1
            else:
                if dry_run:
                    print(f"[DRY] {date_str} ({day_name}) - Wuerde verarbeitet werden")
                    success_count += 1
                else:
                    # Erfasse Tracking-Daten für diesen Tag
                    print(f"[*] {date_str} ({day_name}) - Verarbeite...", end=" ")

                    result = tracking_system.check_daily_outcomes(check_date=date_str)

                    if result and 'total_slots' in result:
                        slots = result.get('total_slots', 0)
                        completed = result.get('completed', 0)
                        no_shows = result.get('no_shows', 0)
                        print(f"OK ({slots} Slots, {completed} Erschienen, {no_shows} No-Shows)")
                        success_count += 1
                    else:
                        print(f"WARNUNG - Keine Daten gefunden")
                        skipped_count += 1

        except Exception as e:
            print(f"FEHLER {date_str} ({day_name}) - {e}")
            error_count += 1

        # Nächster Tag
        current_date += timedelta(days=1)

    print("-" * 70)
    print()
    print("=" * 70)
    print("BACKFILL ABGESCHLOSSEN")
    print("=" * 70)
    print(f"[OK] Erfolgreich verarbeitet: {success_count}")
    print(f"[>>] Uebersprungen:          {skipped_count}")
    print(f"[!!] Fehler:                 {error_count}")
    print(f"[==] Gesamt:                 {days_to_process}")
    print("=" * 70)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Backfill Tracking Data')
    parser.add_argument('--start', type=str, default='2025-09-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=None,
                       help='End date (YYYY-MM-DD), default: today')
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Dry run mode (no changes)')

    args = parser.parse_args()

    # Initialize Flask app context
    from app import create_app
    from app.config.production import ProductionConfig

    app = create_app(ProductionConfig)

    with app.app_context():
        backfill_tracking_data(
            start_date_str=args.start,
            end_date_str=args.end,
            dry_run=args.dry_run
        )


if __name__ == "__main__":
    main()
