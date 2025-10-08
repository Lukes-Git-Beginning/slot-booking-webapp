#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weekly Reset Script for VPS Systemd Timer
Processes weekly points rollover and resets
"""

import sys
import os
from datetime import datetime

# Add project root to Python path (works from /opt/business-hub/scripts/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Change to project root directory for relative imports
os.chdir(project_root)

def main():
    """Process weekly reset for all users"""
    try:
        print(f"[{datetime.now().isoformat()}] Starting weekly reset...")

        # Create Flask app context
        from app import create_app
        app = create_app()

        with app.app_context():
            from app.services.weekly_points import weekly_points
            from app.config.base import Config

            # Get all users
            users = Config.get_all_users()
            print(f"Processing weekly reset for {len(users)} users...")

            if not users:
                print("WARNING: No users found. Check USERLIST environment variable.")
                return 0

            success_count = 0
            error_count = 0

            for user in users:
                try:
                    # Process weekly reset
                    weekly_points.process_weekly_reset(user)
                    success_count += 1
                    print(f"✓ {user}: Weekly reset completed")
                except Exception as e:
                    error_count += 1
                    print(f"✗ {user}: Error - {e}")

            print(f"\n📊 Weekly Reset Summary:")
            print(f"   Success: {success_count}")
            print(f"   Errors: {error_count}")
            print(f"   Total: {len(users)}")
            print(f"[{datetime.now().isoformat()}] Weekly reset completed")

            return 0 if error_count == 0 else 1

    except Exception as e:
        print(f"[{datetime.now().isoformat()}] FATAL ERROR: Weekly reset failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
