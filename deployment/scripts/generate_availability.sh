#!/bin/bash
# Business Hub - Availability Generation Script
# Generiert verfügbare Zeitslots basierend auf Google Calendar

set -e

APP_DIR="/opt/business-hub"
LOG_FILE="/var/log/business-hub/availability.log"

cd "$APP_DIR"

# Python-Script ausführen
source venv/bin/activate
python scripts/generate_availability.py >> "$LOG_FILE" 2>&1

echo "[$(date)] Availability generation completed" >> "$LOG_FILE"
