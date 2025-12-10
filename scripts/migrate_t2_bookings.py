#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T2 Bookings Migration Script: t2_bookings.json → PostgreSQL

Migriert alle T2-Buchungen von JSON zu PostgreSQL (T2Booking Model)
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

from app.models import init_db, get_db_session, T2Booking

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_t2_bookings(dry_run=False):
    """
    Migriert t2_bookings.json → T2Booking Model

    Args:
        dry_run: If True, nur lesen ohne zu schreiben
    """
    logger.info("🚀 Starte T2 Bookings Migration")
    logger.info(f"📍 Mode: {'DRY-RUN' if dry_run else 'LIVE'}")

    # Initialize DB
    try:
        init_db()
        logger.info("✅ PostgreSQL verbunden")
    except Exception as e:
        logger.error(f"❌ PostgreSQL-Fehler: {e}")
        return

    session = get_db_session()

    # JSON-Datei
    t2_bookings_file = project_root / 'data' / 'persistent' / 't2_bookings.json'

    if not t2_bookings_file.exists():
        logger.warning(f"⚠️ Datei nicht gefunden: {t2_bookings_file}")
        logger.info("💡 Das ist OK - keine historischen T2 Bookings vorhanden")
        return

    logger.info(f"📖 Lese: {t2_bookings_file}")

    total = 0
    migrated = 0
    skipped = 0
    errors = 0

    try:
        with open(t2_bookings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle both dict and list formats
        if isinstance(data, dict):
            bookings = data.get('bookings', [])
        else:
            bookings = data  # Legacy list format

        total = len(bookings)
        logger.info(f"📊 Gefunden: {total} T2 Bookings")

        for booking_data in bookings:
            try:
                booking_id = booking_data.get('id')

                if not booking_id:
                    logger.warning(f"  ⚠️ Skip: Booking ohne ID")
                    errors += 1
                    continue

                # Check if already exists
                if not dry_run:
                    existing = session.query(T2Booking).filter_by(booking_id=booking_id).first()
                    if existing:
                        skipped += 1
                        logger.debug(f"  ⏭️ Skip: {booking_id} (exists)")
                        continue

                    # Parse date
                    date_str = booking_data.get('date')
                    if date_str:
                        try:
                            booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                # Try ISO format
                                booking_date = datetime.fromisoformat(date_str).date()
                            except ValueError:
                                logger.error(f"  ❌ Invalid date format for {booking_id}: {date_str}")
                                errors += 1
                                continue
                    else:
                        logger.error(f"  ❌ Missing date for {booking_id}")
                        errors += 1
                        continue

                    # Create T2Booking object
                    # Note: created_at/updated_at are set automatically by Base class
                    booking = T2Booking(
                        booking_id=booking_id,
                        coach=booking_data.get('coach', ''),
                        berater=booking_data.get('berater', ''),
                        customer=booking_data.get('customer', ''),
                        date=booking_date,
                        time=booking_data.get('time', ''),
                        topic=booking_data.get('topic', ''),
                        email=booking_data.get('email', ''),
                        user=booking_data.get('user', ''),
                        event_id=booking_data.get('event_id'),
                        calendar_id=booking_data.get('calendar_id'),
                        status=booking_data.get('status', 'active'),
                        is_rescheduled_from=booking_data.get('is_rescheduled_from')
                    )

                    # Add to session
                    session.add(booking)
                    migrated += 1
                    logger.debug(f"  ✅ Migrate: {booking_id} ({booking_data.get('customer')})")

                else:
                    # Dry-run: Just count
                    migrated += 1
                    logger.debug(f"  [DRY] {booking_id} ({booking_data.get('customer')})")

            except Exception as e:
                errors += 1
                logger.error(f"  ❌ Error migrating {booking_data.get('id', 'unknown')}: {e}")

        # Commit if not dry-run
        if not dry_run and migrated > 0:
            session.commit()
            logger.info("💾 Changes committed")

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse error: {e}")
        return
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return
    finally:
        session.close()

    # Summary
    logger.info("=" * 60)
    logger.info("📊 MIGRATION SUMMARY")
    logger.info(f"Total Bookings: {total}")
    logger.info(f"✅ Migrated: {migrated}")
    logger.info(f"⏭️ Skipped (already exist): {skipped}")
    logger.info(f"❌ Errors: {errors}")
    logger.info("=" * 60)

    if dry_run:
        logger.info("💡 This was a DRY-RUN. No data was written.")
        logger.info("💡 Run without --dry-run to actually migrate.")
    elif migrated > 0:
        logger.info("✅ Migration erfolgreich!")
    else:
        logger.info("⚠️ Keine neuen Daten migriert.")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate T2 Bookings to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Dry-run mode (no writes)')
    parser.add_argument('--execute', action='store_true', help='Execute migration (writes to DB)')

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("⚠️ Please specify --dry-run or --execute")
        parser.print_help()
        sys.exit(1)

    migrate_t2_bookings(dry_run=args.dry_run)
