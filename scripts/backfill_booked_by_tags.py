#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill Script: Add [Booked by: username] tags to existing Google Calendar events

This script reads booking data from bookings.jsonl and updates Google Calendar
events that are missing the [Booked by:] tag in their description.

Usage:
    python scripts/backfill_booked_by_tags.py --dry-run   # Show what would be changed
    python scripts/backfill_booked_by_tags.py --execute   # Actually update events
    python scripts/backfill_booked_by_tags.py --verify    # Verify tags are present
"""

import sys
import os
import json
import argparse
import pytz
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)

# Load .env file for environment variables (Google credentials, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, '.env'))
    print(f"✓ Loaded environment variables from {project_root}/.env")
except ImportError:
    print("Warning: python-dotenv not installed, relying on system environment variables")
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def main():
    parser = argparse.ArgumentParser(description='Backfill [Booked by:] tags in Google Calendar events')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--execute', action='store_true', help='Actually update the events')
    parser.add_argument('--verify', action='store_true', help='Verify tags are present')
    parser.add_argument('--days-back', type=int, default=60, help='How many days back to check (default: 60)')

    args = parser.parse_args()

    if not (args.dry_run or args.execute or args.verify):
        print("ERROR: Must specify one of --dry-run, --execute, or --verify")
        parser.print_help()
        sys.exit(1)

    from app import create_app

    # Use production config if available (for server runs)
    try:
        app = create_app("app.config.production.ProductionConfig")
    except:
        app = create_app()

    with app.app_context():
        from app.core.google_calendar import get_google_calendar_service
        from app.config.base import config

        TZ = pytz.timezone('Europe/Berlin')

        print("=" * 80)
        print("BACKFILL: Add [Booked by:] tags to Google Calendar events")
        print("=" * 80)
        print()

        # Step 1: Load bookings.jsonl data
        print("[1/5] Loading bookings data...")
        bookings_file = "data/tracking/bookings.jsonl"

        if not os.path.exists(bookings_file):
            print(f"ERROR: {bookings_file} not found!")
            sys.exit(1)

        booking_map = {}  # key: "customer_date_time" → username

        with open(bookings_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    booking = json.loads(line.strip())
                    customer = booking['customer']
                    date = booking['date']
                    time = booking['time']
                    user = booking['user']

                    # Create MULTIPLE keys per booking for different name formats
                    # This handles: "Nachname, Vorname" → "Nachname Vorname" (Calendar format change)

                    # Key 1: Original format (e.g., "Sungur, Maria")
                    key1 = f"{customer}_{date}_{time}".lower().replace(' ', '_')
                    booking_map[key1] = user

                    # Key 2: Without comma (e.g., "Sungur Maria")
                    customer_no_comma = customer.replace(',', '')  # "Sungur, Maria" → "Sungur Maria"
                    key2 = f"{customer_no_comma}_{date}_{time}".lower().replace(' ', '_')
                    booking_map[key2] = user

                    # Key 3: Swap first/last name (e.g., "Maria Sungur")
                    if ',' in customer:
                        parts = [p.strip() for p in customer.split(',', 1)]
                        if len(parts) == 2:
                            customer_swapped = f"{parts[1]} {parts[0]}"  # "Maria Sungur"
                            key3 = f"{customer_swapped}_{date}_{time}".lower().replace(' ', '_')
                            booking_map[key3] = user

                except Exception as e:
                    print(f"WARNING: Error parsing booking line: {e}")
                    continue

        print(f"✓ Loaded {len(booking_map)} bookings from {bookings_file}")
        print()

        # Step 2: Get Google Calendar events
        print("[2/5] Fetching Google Calendar events...")
        calendar_service = get_google_calendar_service()

        if not calendar_service:
            print("ERROR: Could not initialize Google Calendar service!")
            sys.exit(1)

        # Get events from last N days
        end_date = datetime.now(TZ)
        start_date = end_date - timedelta(days=args.days_back)

        print(f"Date range: {start_date.date()} to {end_date.date()}")

        events_result = calendar_service.get_events(
            calendar_id=config.CENTRAL_CALENDAR_ID,
            time_min=start_date.isoformat(),
            time_max=end_date.isoformat(),
            cache_duration=0  # No cache
        )

        all_events = events_result.get('items', []) if events_result else []
        print(f"✓ Fetched {len(all_events)} events from Google Calendar")
        print()

        # Step 3: Analyze events
        print("[3/5] Analyzing events...")

        stats = {
            'total': len(all_events),
            'already_tagged': 0,
            'placeholder': 0,
            'matched': 0,
            'no_match': 0,
            'to_update': []
        }

        for event in all_events:
            event_id = event.get('id')
            summary = event.get('summary', '').strip()
            description = event.get('description', '')

            # Skip placeholder events (only digits)
            if summary.isdigit():
                stats['placeholder'] += 1
                continue

            # Check if already has tag
            if '[Booked by:' in description:
                stats['already_tagged'] += 1
                continue

            # Extract date and time
            start_dt = event.get('start', {}).get('dateTime', '')
            if not start_dt:
                continue

            try:
                dt = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                event_date = dt.strftime('%Y-%m-%d')
                event_time = dt.strftime('%H:%M')
            except:
                continue

            # Try to match with bookings.jsonl
            # Normalize summary: remove status markers like " ( erschienen )", " ( Verschoben )", etc.
            import re
            summary_normalized = re.sub(r'\s*\([^)]*\)\s*$', '', summary).strip()

            # Try to match (we have multiple keys per booking, so just normalize the summary and try)
            key = f"{summary_normalized}_{event_date}_{event_time}".lower().replace(' ', '_')
            matched_username = booking_map.get(key)

            # 🔍 DEBUG: Show first 5 non-matches
            if not matched_username and stats['no_match'] < 5:
                print(f"  DEBUG: No match for '{summary[:40]}...' on {event_date} {event_time}")
                print(f"         Normalized: '{summary_normalized}'")
                print(f"         Key: '{key}'")
                print(f"         Sample booking keys: {list(booking_map.keys())[:3]}")
                print()

            if matched_username:
                stats['matched'] += 1
                stats['to_update'].append({
                    'event_id': event_id,
                    'summary': summary,
                    'date': event_date,
                    'time': event_time,
                    'username': matched_username,
                    'current_description': description
                })
            else:
                stats['no_match'] += 1

        # Print statistics
        print(f"Total events:        {stats['total']}")
        print(f"Placeholder events:  {stats['placeholder']}")
        print(f"Already tagged:      {stats['already_tagged']}")
        print(f"Matched in data:     {stats['matched']}")
        print(f"No match found:      {stats['no_match']}")
        print()

        if stats['matched'] == 0:
            print("No events to update. Exiting.")
            return 0

        # Step 4: Update or show what would be updated
        if args.dry_run:
            print("[4/5] DRY RUN - Would update these events:")
            print("-" * 80)
            for i, update in enumerate(stats['to_update'], 1):
                print(f"{i}. {update['summary']}")
                print(f"   Date: {update['date']} {update['time']}")
                print(f"   Would add: [Booked by: {update['username']}]")
                print()

            print(f"DRY RUN: Would update {len(stats['to_update'])} events")
            print("Run with --execute to actually update these events")

        elif args.execute:
            print("[4/5] EXECUTING - Updating events...")

            # Create backup first
            backup_file = f"data/tracking/backfill_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(stats['to_update'], f, ensure_ascii=False, indent=2)
            print(f"✓ Backup created: {backup_file}")

            updated_count = 0
            failed_count = 0

            for i, update in enumerate(stats['to_update'], 1):
                try:
                    event_id = update['event_id']
                    username = update['username']
                    current_desc = update['current_description']

                    # Create new description with tag
                    tag = f"[Booked by: {username}]"
                    if current_desc:
                        new_description = f"{current_desc}\n\n{tag}"
                    else:
                        new_description = tag

                    # Update event
                    calendar_service.service.events().patch(
                        calendarId=config.CENTRAL_CALENDAR_ID,
                        eventId=event_id,
                        body={'description': new_description}
                    ).execute()

                    updated_count += 1
                    print(f"✓ [{i}/{len(stats['to_update'])}] Updated: {update['summary']} ({update['date']} {update['time']})")

                    # Rate limiting
                    import time
                    time.sleep(0.2)  # Max 5 updates/second

                except Exception as e:
                    failed_count += 1
                    print(f"✗ [{i}/{len(stats['to_update'])}] FAILED: {update['summary']} - {e}")

            print()
            print(f"EXECUTE: Updated {updated_count} events, {failed_count} failed")

        elif args.verify:
            print("[4/5] VERIFYING - Checking if tags are present...")

            verified_count = 0
            missing_count = 0

            for update in stats['to_update']:
                event_id = update['event_id']

                try:
                    # Fetch fresh event
                    event = calendar_service.service.events().get(
                        calendarId=config.CENTRAL_CALENDAR_ID,
                        eventId=event_id
                    ).execute()

                    description = event.get('description', '')

                    if '[Booked by:' in description:
                        verified_count += 1
                        print(f"✓ {update['summary']} has tag")
                    else:
                        missing_count += 1
                        print(f"✗ {update['summary']} MISSING tag")

                except Exception as e:
                    print(f"ERROR: Could not verify {update['summary']}: {e}")

            print()
            print(f"VERIFY: {verified_count} have tags, {missing_count} missing")

        # Step 5: Done
        print()
        print("[5/5] Done!")
        print("=" * 80)

        return 0

if __name__ == "__main__":
    sys.exit(main())
