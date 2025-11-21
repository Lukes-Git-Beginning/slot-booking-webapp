#!/bin/bash
#
# Calendar-Sync Wrapper Script
# Runs daily to sync manual Google Calendar bookings to PostgreSQL
#

# Calculate start date (7 days ago)
START_DATE=$(date -d "7 days ago" +%Y-%m-%d)

# Change to project directory
cd /opt/business-hub

# Activate virtual environment
source venv/bin/activate

# Run backfill script
python scripts/backfill_from_calendar.py --start-date "$START_DATE" --execute

# Exit with script's exit code
exit $?
