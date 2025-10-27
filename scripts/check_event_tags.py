#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick script to check if events have [Booked by:] tags"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)

from app import create_app
from app.core.google_calendar import get_google_calendar_service
from app.config.base import config
from datetime import datetime, timedelta
import pytz

try:
    app = create_app("app.config.production.ProductionConfig")
except:
    app = create_app()
with app.app_context():
    cal = get_google_calendar_service()
    TZ = pytz.timezone("Europe/Berlin")

    # Get events from last 3 days
    start = (datetime.now(TZ) - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00+01:00")
    end = datetime.now(TZ).strftime("%Y-%m-%dT23:59:59+01:00")

    events = cal.get_events(
        calendar_id=config.CENTRAL_CALENDAR_ID,
        time_min=start,
        time_max=end,
        cache_duration=0
    )

    all_events = events.get("items", [])
    print(f"Total events (last 3 days): {len(all_events)}")
    print()

    # Check first 10 non-placeholder events
    count = 0
    for e in all_events:
        summary = e.get("summary", "")
        if summary.isdigit():
            continue
        count += 1
        desc = e.get("description", "")
        has_tag = "[Booked by:" in desc

        print(f"{count}. {summary[:40]}")
        print(f"   Has description: {len(desc) > 0} chars")
        print(f"   Has [Booked by:] tag: {has_tag}")

        if desc:
            # Show first 100 chars
            print(f"   Description: {desc[:100]}...")

        print()

        if count >= 10:
            break
