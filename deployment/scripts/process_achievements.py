#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Achievement Processing Script for VPS Systemd Timer
Processes daily achievements and badges for all users
"""

import sys
import os
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add project root to Python path (works from /opt/business-hub/scripts/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Change to project root directory for relative imports
os.chdir(project_root)

def main():
    """Process achievements for all users"""
    try:
        logger.info("Starting achievement processing...")

        # Create Flask app context
        from app import create_app
        app = create_app()

        with app.app_context():
            from app.services.achievement_system import achievement_system
            from app.config.base import Config

            # Auto-check MVP badges
            logger.info("Checking MVP badges...")
            try:
                achievement_system.auto_check_mvp_badges()
            except Exception as e:
                logger.warning(f"MVP badge check warning: {e}")

            # Get all users
            users = Config.get_all_users()
            logger.info(f"Processing achievements for {len(users)} users...")

            if not users:
                logger.warning("No users found. Check USERLIST environment variable.")
                return 0

            total_new_badges = 0
            for user in users:
                try:
                    new_badges = achievement_system.process_user_achievements(user)
                    if new_badges:
                        badge_names = ', '.join([b.get('name', 'Unknown') for b in new_badges])
                        logger.info(f"✓ {user} earned {len(new_badges)} new badges: {badge_names}")
                        total_new_badges += len(new_badges)
                    else:
                        logger.debug(f"{user}: No new badges")
                except Exception as e:
                    logger.error(f"✗ Error processing achievements for {user}: {e}")

            logger.info("=" * 50)
            logger.info(f"Achievement processing completed: {total_new_badges} badges awarded")
            logger.info("=" * 50)
            return 0

    except Exception as e:
        logger.critical(f"FATAL ERROR: Achievement processing failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
