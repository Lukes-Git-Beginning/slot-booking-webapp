#!/bin/bash
#
# Daily Tracking: Check outcomes from previous day
# Runs via cron at 21:00 daily
#

cd /opt/business-hub
source venv/bin/activate
set -a; source .env; set +a
python scripts/run_tracking.py >> /var/log/business-hub/tracking.log 2>&1
