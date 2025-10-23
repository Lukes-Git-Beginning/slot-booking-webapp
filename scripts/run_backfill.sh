#!/bin/bash
# Wrapper script to run backfill with environment variables loaded

# Change to app directory
cd /opt/business-hub

# Load environment variables
set -a
source /opt/business-hub/.env
set +a

# Run backfill script
/opt/business-hub/venv/bin/python3 /opt/business-hub/scripts/backfill_tracking.py "$@"
