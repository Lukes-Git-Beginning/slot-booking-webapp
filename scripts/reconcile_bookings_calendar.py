#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Booking vs. Calendar Reconciliation Script

Vergleicht alle Beraterwelt-Buchungen (PostgreSQL + JSONL) mit
Google Calendar Events. Zeigt fehlende Eintraege in beide Richtungen.

Read-only: Aendert keine Daten.
"""

import sys
import re
import json
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Set, Tuple

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


def normalize_name(name: str) -> str:
    """Normalize customer name for comparison."""
    if not name:
        return ""
    # Remove status markers like "( erschienen )", "( Ghost )", etc.
    cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', name)
    # Strip and lowercase
    return cleaned.strip().lower()


def extract_username_from_description(description: str) -> Optional[str]:
    """Extract username from [Booked by: username] tag."""
    if not description:
        return None
    match = re.search(r'\[Booked by:\s*([\w.\-]+)\]', description, re.IGNORECASE)
    return match.group(1) if match else None


def make_match_key(customer: str, booking_date: str, booking_time: str) -> str:
    """Create a normalized match key from customer+date+time."""
    return f"{normalize_name(customer)}|{booking_date}|{booking_time}"


def load_pg_bookings(cutoff_date: date) -> List[Dict]:
    """Load future bookings from PostgreSQL."""
    bookings = []
    try:
        init_db()
        session = get_db_session()
        rows = session.query(Booking).filter(Booking.date >= cutoff_date).all()
        for row in rows:
            bookings.append({
                'customer': row.customer,
                'date': str(row.date),
                'time': row.time,
                'username': row.username,
                'booking_id': row.booking_id,
                'source': 'postgresql',
            })
        session.close()
        logger.info(f"PostgreSQL: {len(bookings)} zukuenftige Buchungen geladen")
    except Exception as e:
        logger.warning(f"PostgreSQL nicht verfuegbar: {e}")
    return bookings


def load_jsonl_bookings(cutoff_date: date) -> List[Dict]:
    """Load future bookings from bookings.jsonl."""
    bookings = []
    jsonl_path = project_root / 'data' / 'tracking' / 'bookings.jsonl'
    if not jsonl_path.exists():
        logger.info(f"JSONL nicht gefunden: {jsonl_path}")
        return bookings

    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    booking_date = record.get('date', '')
                    if booking_date and booking_date >= str(cutoff_date):
                        bookings.append({
                            'customer': record.get('customer', ''),
                            'date': booking_date,
                            'time': record.get('time', ''),
                            'username': record.get('user', record.get('username', '')),
                            'booking_id': record.get('id', ''),
                            'source': 'jsonl',
                        })
                except json.JSONDecodeError:
                    continue
        logger.info(f"JSONL: {len(bookings)} zukuenftige Buchungen geladen")
    except Exception as e:
        logger.warning(f"JSONL Fehler: {e}")
    return bookings


def load_calendar_events(cutoff_date: date) -> List[Dict]:
    """Load future events from Google Calendar."""
    events = []
    try:
        calendar_service = get_google_calendar_service()
        time_min = f"{cutoff_date}T00:00:00+01:00"
        time_max = f"2026-12-31T23:59:59+01:00"

        logger.info(f"Lade Calendar Events von {cutoff_date} bis Ende 2026...")
        result = calendar_service.get_all_events_paginated(
            calendar_id=config.CENTRAL_CALENDAR_ID,
            time_min=time_min,
            time_max=time_max,
            cache_duration=0  # No cache
        )
        raw_events = result.get('items', [])
        logger.info(f"Google Calendar: {len(raw_events)} Events geladen ({result.get('total_pages', 0)} Seiten)")

        for event in raw_events:
            summary = event.get('summary', '')
            # Skip placeholder events (digits only)
            if not summary or summary.isdigit():
                continue
            # Skip cancelled events
            if event.get('status') == 'cancelled':
                continue

            description = event.get('description', '')
            start_dt_str = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', ''))

            try:
                dt = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))
                event_date = str(dt.date())
                event_time = dt.strftime('%H:%M')
            except (ValueError, AttributeError):
                continue

            booked_by = extract_username_from_description(description)
            color_id = event.get('colorId', '9')

            events.append({
                'customer': summary,
                'customer_clean': re.sub(r'\s*\([^)]*\)\s*$', '', summary).strip(),
                'date': event_date,
                'time': event_time,
                'booked_by': booked_by,
                'color_id': color_id,
                'event_id': event.get('id', ''),
                'description': description,
            })
    except Exception as e:
        logger.error(f"Google Calendar Fehler: {e}")
    return events


def reconcile(pg_bookings: List[Dict], jsonl_bookings: List[Dict], cal_events: List[Dict]):
    """Run the reconciliation and print results."""

    # Merge PG + JSONL bookings (PG takes priority)
    all_bookings = {}
    for b in jsonl_bookings:
        key = make_match_key(b['customer'], b['date'], b['time'])
        all_bookings[key] = b
    for b in pg_bookings:
        key = make_match_key(b['customer'], b['date'], b['time'])
        all_bookings[key] = b  # PG overwrites JSONL

    # Build calendar lookup (normalized name + date + time)
    cal_lookup: Dict[str, Dict] = {}
    # Also build a broader lookup (name + date only) for fuzzy time matching
    cal_lookup_date: Dict[str, List[Dict]] = {}
    for ev in cal_events:
        key = make_match_key(ev['customer_clean'], ev['date'], ev['time'])
        cal_lookup[key] = ev
        date_key = f"{normalize_name(ev['customer_clean'])}|{ev['date']}"
        cal_lookup_date.setdefault(date_key, []).append(ev)

    # Build booking lookup for reverse check
    booking_lookup: Set[str] = set()
    booking_lookup_date: Dict[str, List[Dict]] = {}
    for key, b in all_bookings.items():
        booking_lookup.add(key)
        date_key = f"{normalize_name(b['customer'])}|{b['date']}"
        booking_lookup_date.setdefault(date_key, []).append(b)

    # === Direction 1: Bookings missing from Calendar ===
    missing_in_calendar = []
    matched = []
    for key, b in sorted(all_bookings.items(), key=lambda x: (x[1]['date'], x[1]['time'])):
        if key in cal_lookup:
            matched.append(b)
        else:
            # Try fuzzy match (same name + date, different time)
            date_key = f"{normalize_name(b['customer'])}|{b['date']}"
            if date_key in cal_lookup_date:
                # Found by name+date but time differs
                cal_times = [e['time'] for e in cal_lookup_date[date_key]]
                matched.append(b)
                logger.debug(f"  Fuzzy match: {b['customer']} {b['date']} - PG={b['time']}, Cal={cal_times}")
            else:
                missing_in_calendar.append(b)

    # === Direction 2: Calendar events (with Booked-by tag) missing from PG ===
    missing_in_pg = []
    for ev in sorted(cal_events, key=lambda x: (x['date'], x['time'])):
        if not ev['booked_by']:
            continue  # Skip events without booking tag
        key = make_match_key(ev['customer_clean'], ev['date'], ev['time'])
        if key not in booking_lookup:
            # Try fuzzy match
            date_key = f"{normalize_name(ev['customer_clean'])}|{ev['date']}"
            if date_key not in booking_lookup_date:
                missing_in_pg.append(ev)

    # === Output ===
    print("\n" + "=" * 70)
    print("  BOOKING vs. CALENDAR RECONCILIATION")
    print("  Nur zukuenftige Termine (ab heute)")
    print("=" * 70)

    print(f"\n{'=' * 70}")
    print("  BUCHUNGEN OHNE CALENDAR EVENT (in PG/JSONL aber NICHT im Kalender)")
    print(f"{'=' * 70}")
    if missing_in_calendar:
        for i, b in enumerate(missing_in_calendar, 1):
            print(f"  {i:3d}. {b['customer']:<35s} | {b['date']} | {b['time']} | gebucht von: {b['username']}")
    else:
        print("  Keine fehlenden Eintraege - alle Buchungen haben Calendar Events!")

    print(f"\n{'=' * 70}")
    print("  CALENDAR EVENTS OHNE PG BUCHUNG (im Kalender aber NICHT in PG/JSONL)")
    print(f"{'=' * 70}")
    if missing_in_pg:
        for i, ev in enumerate(missing_in_pg, 1):
            print(f"  {i:3d}. {ev['customer_clean']:<35s} | {ev['date']} | {ev['time']} | [Booked by: {ev['booked_by']}]")
    else:
        print("  Keine fehlenden Eintraege - alle Calendar Events sind in PG getrackt!")

    print(f"\n{'=' * 70}")
    print("  ZUSAMMENFASSUNG")
    print(f"{'=' * 70}")
    print(f"  PG/JSONL Buchungen (ab heute):        {len(all_bookings)}")
    print(f"  Calendar Events (ab heute):            {len(cal_events)}")
    print(f"  Calendar Events mit [Booked by:] Tag:  {sum(1 for e in cal_events if e['booked_by'])}")
    print(f"  Matches:                               {len(matched)}")
    print(f"  Nur in PG (FEHLT im Calendar):         {len(missing_in_calendar)}")
    print(f"  Nur im Calendar (FEHLT in PG):         {len(missing_in_pg)}")
    print(f"{'=' * 70}\n")

    return missing_in_calendar, missing_in_pg


if __name__ == '__main__':
    today = date.today()
    logger.info(f"Reconciliation Start - Cutoff: {today}")
    logger.info("=" * 70)

    pg_bookings = load_pg_bookings(today)
    jsonl_bookings = load_jsonl_bookings(today)
    cal_events = load_calendar_events(today)

    if not pg_bookings and not jsonl_bookings:
        logger.warning("KEINE Buchungen in PG oder JSONL gefunden!")
        logger.info("Zeige stattdessen alle zukuenftigen Calendar Events:")
        print(f"\n{'=' * 70}")
        print("  ALLE ZUKUENFTIGEN CALENDAR EVENTS")
        print(f"{'=' * 70}")
        for i, ev in enumerate(sorted(cal_events, key=lambda x: (x['date'], x['time'])), 1):
            booked_by = ev['booked_by'] or 'KEIN TAG'
            print(f"  {i:3d}. {ev['customer_clean']:<35s} | {ev['date']} | {ev['time']} | {booked_by}")
        print(f"\n  Total: {len(cal_events)} Events")
        print(f"  Davon mit [Booked by:] Tag: {sum(1 for e in cal_events if e['booked_by'])}")
        print(f"  Davon OHNE Tag: {sum(1 for e in cal_events if not e['booked_by'])}")
        print(f"{'=' * 70}\n")
    else:
        reconcile(pg_bookings, jsonl_bookings, cal_events)
