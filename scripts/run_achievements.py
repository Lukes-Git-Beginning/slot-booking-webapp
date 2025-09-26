#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions wrapper for achievement system
Handles imports and path setup for the achievement system
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def run_achievement_check():
    """Run the daily achievement check"""
    try:
        from app.services.achievement_system import achievement_system

        # Run MVP badge check
        print("Checking MVP badges...")
        achievement_system.auto_check_mvp_badges()

        # Process achievements for all users
        print("Processing achievements...")
        from app.config.base import Config
        users = Config.get_all_users()

        for user in users:
            try:
                new_badges = achievement_system.process_user_achievements(user)
                if new_badges:
                    print(f"{user} earned {len(new_badges)} new badges!")
            except Exception as e:
                print(f"Error processing achievements for {user}: {e}")

        print("Achievement check completed successfully")
        return True

    except Exception as e:
        print(f"Achievement check failed: {e}")
        return False

if __name__ == "__main__":
    success = run_achievement_check()
    if not success:
        sys.exit(1)