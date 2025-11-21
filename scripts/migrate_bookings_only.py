#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Einfaches Script: Migriert NUR bookings.jsonl → PostgreSQL
Überspringt existierende Daten mit session.merge()
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.models import init_db, get_db_session, Booking

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_bookings_only(dry_run=False):
    """
    Migriert bookings.jsonl → Booking Model
    """
    logger.info("🚀 Starte Booking-Migration")
    logger.info(f"📍 Mode: {'DRY-RUN' if dry_run else 'LIVE'}")

    # Initialize DB
    try:
        init_db()
        logger.info("✅ PostgreSQL verbunden")
    except Exception as e:
        logger.error(f"❌ PostgreSQL-Fehler: {e}")
        return

    session = get_db_session()

    # JSONL-Datei
    bookings_file = project_root / 'data' / 'tracking' / 'bookings.jsonl'

    if not bookings_file.exists():
        logger.error(f"❌ Datei nicht gefunden: {bookings_file}")
        return

    logger.info(f"📖 Lese: {bookings_file}")

    total = 0
    migrated = 0
    skipped = 0
    errors = 0

    try:
        with open(bookings_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                if not line.strip():
                    continue

                total += 1

                try:
                    booking_data = json.loads(line)

                    # Check if already exists
                    booking_id = booking_data.get('id', f"unknown_{line_num}")

                    if not dry_run:
                        # Check existence
                        existing = session.query(Booking).filter_by(booking_id=booking_id).first()
                        if existing:
                            skipped += 1
                            logger.debug(f"  ⏭️ Skip: {booking_id} (exists)")
                            continue

                        # Parse date
                        date_obj = datetime.strptime(booking_data['date'], '%Y-%m-%d').date()

                        # Create booking
                        booking = Booking(
                            booking_id=booking_id,
                            customer=booking_data.get('customer', 'Unknown'),
                            date=date_obj,
                            time=booking_data.get('time', '00:00'),
                            weekday=booking_data.get('weekday', 'Monday'),
                            week_number=booking_data.get('week_number', 1),
                            username=booking_data.get('user', 'unknown'),
                            potential_type=booking_data.get('potential_type', 'unknown'),
                            color_id=booking_data.get('color_id', '9'),
                            description_length=booking_data.get('description_length', 0),
                            has_description=booking_data.get('has_description', False),
                            booking_lead_time=booking_data.get('booking_lead_time', 0),
                            booked_at_hour=booking_data.get('booked_at_hour', 0),
                            booked_on_weekday=booking_data.get('booked_on_weekday', 'Monday'),
                            booking_timestamp=datetime.fromisoformat(
                                booking_data.get('timestamp', datetime.utcnow().isoformat()).replace('Z', '+00:00')
                            )
                        )
                        session.add(booking)
                        migrated += 1

                        if migrated % 10 == 0:
                            session.commit()
                            logger.info(f"  ✓ {migrated} Bookings migriert...")
                    else:
                        migrated += 1

                except Exception as e:
                    errors += 1
                    logger.error(f"  ❌ Line {line_num}: {e}")

        if not dry_run:
            session.commit()
            logger.info("✅ Commit erfolgreich")

        logger.info("\n" + "="*60)
        logger.info("📊 ERGEBNIS:")
        logger.info(f"  Total gelesen:      {total}")
        logger.info(f"  Neu migriert:       {migrated}")
        logger.info(f"  Übersprungen:       {skipped}")
        logger.info(f"  Fehler:             {errors}")
        logger.info("="*60)

        if not dry_run:
            # Verify
            count = session.query(Booking).count()
            logger.info(f"\n✅ PostgreSQL hat jetzt {count} Bookings")

    except Exception as e:
        logger.error(f"❌ Fehler: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate bookings.jsonl to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Test run without changes')
    parser.add_argument('--execute', action='store_true', help='Execute migration')

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("❌ Bitte --dry-run oder --execute angeben")
        sys.exit(1)

    migrate_bookings_only(dry_run=args.dry_run)
