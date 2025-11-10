#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Outcome Check Script for VPS Systemd Timer
Processes daily outcomes, no-shows, and updates user statistics
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add project root to Python path (works from /opt/business-hub/scripts/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Change to project root directory for relative imports
os.chdir(project_root)

def main():
    """Process daily outcomes and statistics"""
    try:
        logger.info("Starting daily outcome check...")

        # Create Flask app context
        from app import create_app
        app = create_app()

        with app.app_context():
            from app.core.google_calendar import GoogleCalendarService
            from app.config.base import ConsultantConfig

            # Initialize services
            try:
                calendar_service = GoogleCalendarService()
                logger.info("✓ Google Calendar service initialized")
            except Exception as e:
                logger.warning(f"Google Calendar not configured: {e}")
                return 0

            # Process yesterday's outcomes
            yesterday = datetime.now() - timedelta(days=1)
            logger.info(f"Processing outcomes for: {yesterday.strftime('%Y-%m-%d')}")

            # Get all consultants
            try:
                consultants = ConsultantConfig.get_consultants()
                logger.info(f"✓ Loaded {len(consultants)} consultants")
            except Exception as e:
                logger.warning(f"Could not load consultants: {e}")
                consultants = {}

            total_no_shows = 0
            total_events = 0

            for consultant_name, calendar_id in consultants.items():
                try:
                    # Get yesterday's events
                    start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)

                    events = calendar_service.get_events(calendar_id, start_time, end_time)
                    consultant_events = len(events)

                    for event in events:
                        total_events += 1

                        # Check for no-show indicators
                        summary = event.get('summary', '').lower()
                        if any(keyword in summary for keyword in ['ghost', 'abgesagt', 'verschoben', 'nicht erschienen']):
                            total_no_shows += 1
                            event_time = event.get('start', {}).get('dateTime', 'Unknown')
                            logger.info(f"  No-Show: {event.get('summary', 'Unknown')} at {event_time}")

                    logger.info(f"  {consultant_name}: {consultant_events} events")

                except Exception as e:
                    logger.error(f"✗ Error processing outcomes for {consultant_name}: {e}")

            # Calculate no-show rate
            if total_events > 0:
                no_show_rate = (total_no_shows / total_events) * 100
                logger.info("=" * 50)
                logger.info("Daily Statistics:")
                logger.info(f"  Total Events: {total_events}")
                logger.info(f"  No-Shows: {total_no_shows}")
                logger.info(f"  No-Show Rate: {no_show_rate:.2f}%")
                logger.info("=" * 50)

                if no_show_rate > 50:
                    logger.warning(f"ALERT: High no-show rate: {no_show_rate:.2f}%")
            else:
                logger.info("No events found for yesterday")

            logger.info("Daily outcome check completed")
            return 0

    except Exception as e:
        logger.critical(f"FATAL ERROR: Daily outcome check failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
