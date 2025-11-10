#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weekly Reset Script for VPS Systemd Timer
Processes weekly points rollover and resets
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
    """Process weekly reset for all users"""
    try:
        logger.info("Starting weekly reset...")

        # Create Flask app context
        from app import create_app
        app = create_app()

        with app.app_context():
            from app.services.weekly_points import weekly_points
            from app.config.base import Config

            # Get all users
            users = Config.get_all_users()
            logger.info(f"Processing weekly reset for {len(users)} users...")

            if not users:
                logger.warning("No users found. Check USERLIST environment variable.")
                return 0

            success_count = 0
            error_count = 0

            for user in users:
                try:
                    # Process weekly reset
                    weekly_points.process_weekly_reset(user)
                    success_count += 1
                    logger.info(f"✓ {user}: Weekly reset completed")
                except Exception as e:
                    error_count += 1
                    logger.error(f"✗ {user}: Error - {e}")

            logger.info("=" * 50)
            logger.info("Weekly Reset Summary:")
            logger.info(f"  Success: {success_count}")
            logger.info(f"  Errors: {error_count}")
            logger.info(f"  Total: {len(users)}")
            logger.info("=" * 50)
            logger.info("Weekly reset completed")

            return 0 if error_count == 0 else 1

    except Exception as e:
        logger.critical(f"FATAL ERROR: Weekly reset failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
