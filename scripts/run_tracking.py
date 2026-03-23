#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Tracking Cron Job
Handles imports, path setup, and Flask app context for the tracking system.
Requires app context for PostgreSQL Dual-Write (db_session_scope).
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# Load .env for standalone execution (cron jobs)
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

if __name__ == "__main__":
    from app import create_app
    from app.config.production import ProductionConfig
    app = create_app(ProductionConfig)

    with app.app_context():
        from app.services.tracking_system import run_daily_outcome_check, recalculate_all_outcomes

        if len(sys.argv) > 1 and sys.argv[1] == "--recalculate":
            recalculate_all_outcomes()
        else:
            run_daily_outcome_check()
