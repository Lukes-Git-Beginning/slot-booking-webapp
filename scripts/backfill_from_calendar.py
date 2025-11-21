#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Calendar → PostgreSQL Backfill Script

Extrahiert historische Buchungen aus Google Calendar Events
mit [Booked by: username] Tags und migriert sie nach PostgreSQL.

Überspringt bereits vorhandene Bookings aus Phase 1 (bookings.jsonl).
"""

import sys
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from app.models import init_db, get_db_session, Booking
from app.core.google_calendar import get_google_calendar_service
from app.config.base import config

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Potential Type Mapping (from color_id)
POTENTIAL_TYPES = {
    '1': 'lavender',      # Lavender
    '2': 'top',           # Green (Erschienen)
    '3': 'grape',         # Grape
    '4': 'flamingo',      # Flamingo
    '5': 'sonderkunde',   # Yellow (Sonderkunden)
    '6': 'postponed',     # Orange (Verschoben)
    '7': 'normal',        # Blue (Normal potential)
    '8': 'graphite',      # Graphite
    '9': 'normal',        # Blue (default)
    '10': 'basil',        # Basil
    '11': 'no_show',      # Red (Nicht erschienen, Ghost)
}


def extract_username_from_description(description: str) -> Optional[str]:
    """
    Extrahiert Username aus [Booked by: username] Tag

    Example:
        "Telefonnummer: 0123\n\n[Booked by: christian.mast]" → "christian.mast"
    """
    if not description:
        return None

    match = re.search(r'\[Booked by:\s*([\w.]+)\]', description, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def parse_customer_name(summary: str) -> str:
    """
    Extrahiert Kundenname aus Event-Summary

    Example:
        "Müller, Hans ( erschienen )" → "Müller, Hans"
        "Schmidt, Anna" → "Schmidt, Anna"
    """
    if not summary:
        return "Unknown"

    # Remove status indicators like "( erschienen )", "( nicht erschienen )", etc.
    customer = re.sub(r'\s*\([^)]*\)\s*$', '', summary).strip()
    return customer if customer else "Unknown"


def get_potential_type(color_id: str) -> str:
    """Map Google Calendar color_id to potential_type"""
    return POTENTIAL_TYPES.get(color_id, 'unknown')


def backfill_from_calendar(start_date: str = '2025-09-01', dry_run: bool = False):
    """
    Backfill bookings from Google Calendar to PostgreSQL

    Args:
        start_date: Start date for backfill (ISO format: YYYY-MM-DD)
        dry_run: If True, only show what would be migrated
    """
    logger.info("=" * 70)
    logger.info("🗓️ GOOGLE CALENDAR → POSTGRESQL BACKFILL")
    logger.info("=" * 70)
    logger.info(f"📍 Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    logger.info(f"📅 Start-Datum: {start_date}")

    # Initialize DB
    try:
        init_db()
        logger.info("✅ PostgreSQL verbunden")
    except Exception as e:
        logger.error(f"❌ PostgreSQL-Fehler: {e}")
        return

    session = get_db_session()

    # Initialize Google Calendar
    try:
        calendar_service = get_google_calendar_service()
        logger.info("✅ Google Calendar verbunden")
    except Exception as e:
        logger.error(f"❌ Google Calendar-Fehler: {e}")
        return

    # Fetch ALL events using pagination
    time_min = f"{start_date}T00:00:00+01:00"
    time_max = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+01:00')

    logger.info(f"📡 Lade Events von {start_date} bis heute...")
    logger.info("   (Dies kann 1-2 Minuten dauern bei vielen Events)")

    try:
        events_result = calendar_service.get_all_events_paginated(
            calendar_id=config.CENTRAL_CALENDAR_ID,
            time_min=time_min,
            time_max=time_max,
            cache_duration=0  # No cache for backfill
        )
    except Exception as e:
        logger.error(f"❌ Fehler beim Laden der Events: {e}")
        return

    events = events_result['items']
    total_events = len(events)

    logger.info(f"✅ {total_events} Events geladen ({events_result['total_pages']} Seiten)")
    logger.info("=" * 70)

    # Statistics
    total = 0
    migrated = 0
    skipped_exists = 0
    skipped_no_tag = 0
    skipped_placeholder = 0
    errors = 0

    # Process each event
    for event in events:
        total += 1

        # Skip placeholder events (digits only in summary)
        summary = event.get('summary', '')
        if summary.isdigit():
            skipped_placeholder += 1
            continue

        # Extract username from [Booked by:] tag
        description = event.get('description', '')
        username = extract_username_from_description(description)

        if not username:
            skipped_no_tag += 1
            logger.debug(f"  ⏭️ Skip (no tag): {summary[:30]}")
            continue

        try:
            # Parse event data
            customer = parse_customer_name(summary)

            # Parse datetime
            start_dt_str = event['start'].get('dateTime', event['start'].get('date'))
            dt = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))

            # Generate booking_id (same format as tracking_system.py)
            booking_id = f"{dt.date()}_{dt.strftime('%H:%M')}_{customer}".replace(' ', '_').replace(',', '')

            # Check if already exists in PostgreSQL
            existing = session.query(Booking).filter_by(booking_id=booking_id).first()
            if existing:
                skipped_exists += 1
                logger.debug(f"  ✓ Exists: {customer[:20]} ({dt.date()})")
                continue

            # Create booking with PARTIAL metadata
            if not dry_run:
                color_id = event.get('colorId', '9')
                potential_type = get_potential_type(color_id)

                booking = Booking(
                    booking_id=booking_id,
                    customer=customer,
                    date=dt.date(),
                    time=dt.strftime('%H:%M'),
                    weekday=dt.strftime('%A'),
                    week_number=dt.isocalendar()[1],
                    username=username,
                    potential_type=potential_type,
                    color_id=color_id,
                    description_length=len(description),
                    has_description=bool(description.strip()),
                    # UNKNOWN METADATA (not in Google Calendar):
                    booking_lead_time=0,
                    booked_at_hour=0,
                    booked_on_weekday='Unknown',
                    booking_timestamp=dt  # Use appointment time as approximation
                )
                session.add(booking)
                migrated += 1

                # Commit every 50 bookings
                if migrated % 50 == 0:
                    session.commit()
                    logger.info(f"  ✓ {migrated} neue Bookings migriert...")
            else:
                migrated += 1
                if migrated % 50 == 0:
                    logger.info(f"  ✓ {migrated} neue Bookings gefunden (Dry-Run)...")

        except Exception as e:
            errors += 1
            logger.error(f"  ❌ Fehler bei Event {event.get('id', 'unknown')}: {e}")

    # Final commit
    if not dry_run and migrated > 0:
        session.commit()
        logger.info("✅ Final Commit erfolgreich")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("📊 BACKFILL ERGEBNIS:")
    logger.info("=" * 70)
    logger.info(f"  Total Events geladen:       {total_events}")
    logger.info(f"  Davon verarbeitet:          {total}")
    logger.info(f"  📦 NEU migriert:            {migrated}")
    logger.info(f"  ⏭️  Übersprungen (exists):   {skipped_exists}")
    logger.info(f"  ⏭️  Übersprungen (no tag):   {skipped_no_tag}")
    logger.info(f"  ⏭️  Übersprungen (placeholder): {skipped_placeholder}")
    logger.info(f"  ❌ Fehler:                  {errors}")
    logger.info("=" * 70)

    if not dry_run and migrated > 0:
        # Verify
        total_bookings = session.query(Booking).count()
        logger.info(f"\n✅ PostgreSQL hat jetzt {total_bookings} Bookings insgesamt")
        logger.info(f"   (Vorher: {total_bookings - migrated}, Neu hinzugefügt: {migrated})")

    session.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Backfill bookings from Google Calendar to PostgreSQL'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default='2025-09-01',
        help='Start date for backfill (YYYY-MM-DD), default: 2025-09-01'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test run without database changes'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute actual backfill'
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("❌ Bitte --dry-run oder --execute angeben")
        print("   Beispiel: python backfill_from_calendar.py --dry-run")
        sys.exit(1)

    backfill_from_calendar(
        start_date=args.start_date,
        dry_run=args.dry_run
    )
