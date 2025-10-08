#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Achievement Processing Script for VPS Systemd Timer
Processes daily achievements and badges for all users
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
    """Process achievements for all users"""
    try:
        print(f"[{datetime.now().isoformat()}] Starting achievement processing...")

        # Create Flask app context
        from app import create_app
        app = create_app()

        with app.app_context():
            from app.services.achievement_system import achievement_system
            from app.config.base import Config

            # Auto-check MVP badges
            print("Checking MVP badges...")
            try:
                achievement_system.auto_check_mvp_badges()
            except Exception as e:
                print(f"MVP badge check warning: {e}")

            # Get all users
            users = Config.get_all_users()
            print(f"Processing achievements for {len(users)} users...")

            if not users:
                print("WARNING: No users found. Check USERLIST environment variable.")
                return 0

            total_new_badges = 0
            for user in users:
                try:
                    new_badges = achievement_system.process_user_achievements(user)
                    if new_badges:
                        badge_names = ', '.join([b.get('name', 'Unknown') for b in new_badges])
                        print(f"✓ {user} earned {len(new_badges)} new badges: {badge_names}")
                        total_new_badges += len(new_badges)
                    else:
                        print(f"  {user}: No new badges")
                except Exception as e:
                    print(f"✗ Error processing achievements for {user}: {e}")

            print(f"[{datetime.now().isoformat()}] Achievement processing completed: {total_new_badges} badges awarded")
            return 0

    except Exception as e:
        print(f"[{datetime.now().isoformat()}] FATAL ERROR: Achievement processing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
