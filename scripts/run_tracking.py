#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions wrapper for tracking_system.py
Handles imports and path setup for the tracking system
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# Import and run the tracking system
if __name__ == "__main__":
    from app.services.tracking_system import run_daily_outcome_check, recalculate_all_outcomes

    if len(sys.argv) > 1 and sys.argv[1] == "--recalculate":
        recalculate_all_outcomes()
    else:
        run_daily_outcome_check()