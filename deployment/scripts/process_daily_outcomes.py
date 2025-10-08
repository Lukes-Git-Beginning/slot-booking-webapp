#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Outcome Check Script for VPS Systemd Timer
Processes daily outcomes, no-shows, and updates user statistics
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to Python path (works from /opt/business-hub/scripts/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Change to project root directory for relative imports
os.chdir(project_root)

def main():
    """Process daily outcomes and statistics"""
    try:
        print(f"[{datetime.now().isoformat()}] Starting daily outcome check...")

        from app.core.google_calendar import GoogleCalendarService
        from app.config.base import Config

        # Initialize services
        calendar_service = GoogleCalendarService()

        if not calendar_service.is_configured():
            print("WARNING: Google Calendar not configured, skipping outcome check")
            return 0

        # Process yesterday's outcomes
        yesterday = datetime.now() - timedelta(days=1)
        print(f"Processing outcomes for: {yesterday.strftime('%Y-%m-%d')}")

        # Get all consultants
        try:
            consultants = Config.get_consultants()
            print(f"Checking outcomes for {len(consultants)} consultants...")
        except Exception as e:
            print(f"WARNING: Could not load consultants: {e}")
            consultants = {}

        total_no_shows = 0
        total_events = 0

        for consultant_name, calendar_id in consultants.items():
            try:
                # Get yesterday's events
                start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)

                events = calendar_service.get_events(calendar_id, start_time, end_time)

                for event in events:
                    total_events += 1

                    # Check for no-show indicators
                    summary = event.get('summary', '').lower()
                    if any(keyword in summary for keyword in ['ghost', 'abgesagt', 'verschoben', 'nicht erschienen']):
                        total_no_shows += 1
                        event_time = event.get('start', {}).get('dateTime', 'Unknown')
                        print(f"No-Show detected: {event.get('summary', 'Unknown')} at {event_time}")

            except Exception as e:
                print(f"✗ Error processing outcomes for {consultant_name}: {e}")

        # Calculate no-show rate
        if total_events > 0:
            no_show_rate = (total_no_shows / total_events) * 100
            print(f"\n📊 Daily Statistics:")
            print(f"   Total Events: {total_events}")
            print(f"   No-Shows: {total_no_shows}")
            print(f"   No-Show Rate: {no_show_rate:.2f}%")

            if no_show_rate > 50:
                print(f"⚠️  ALERT: High no-show rate: {no_show_rate:.2f}%")
        else:
            print("No events found for yesterday")

        print(f"[{datetime.now().isoformat()}] Daily outcome check completed")
        return 0

    except Exception as e:
        print(f"[{datetime.now().isoformat()}] FATAL ERROR: Daily outcome check failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
