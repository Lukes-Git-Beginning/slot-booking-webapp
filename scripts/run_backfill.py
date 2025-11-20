#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper Script: Runs backfill_bookings_to_postgres in Flask app context
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from app import create_app

# Create Flask app with production config
try:
    app = create_app("app.config.production.ProductionConfig")
except:
    app = create_app()

# Run backfill in app context
with app.app_context():
    from scripts.backfill_bookings_to_postgres import backfill_bookings_to_postgres

    # Parse command line args
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='2025-09-01')
    parser.add_argument('--end', default=None)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--force', '-f', action='store_true')
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("❌ ERROR: Must specify either --dry-run or --execute")
        sys.exit(1)

    # Run backfill
    backfill_bookings_to_postgres(
        start_date_str=args.start,
        end_date_str=args.end,
        dry_run=args.dry_run,
        force=args.force
    )
