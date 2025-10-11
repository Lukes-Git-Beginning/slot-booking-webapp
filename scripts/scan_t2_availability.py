#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
T2 Availability Scanner CLI Script
Runs within Flask app context to access Google Calendar credentials
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run T2 availability scan within Flask app context"""
    logger.info("=== T2 Availability Scan Started ===")

    # Create Flask app with production config
    app = create_app('app.config.production.ProductionConfig')

    # Run within app context
    with app.app_context():
        try:
            # Import inside app context
            from app.services.t2_availability_service import get_availability_service

            availability_service = get_availability_service()
            result = availability_service.scan_all_closers_availability(days=42)
            logger.info(f"=== Scan Complete: {len(result)} closers processed ===")

            # Print summary
            for closer, availability in result.items():
                days_with_slots = sum(1 for slots in availability.values() if len(slots) > 0)
                total_slots = sum(len(slots) for slots in availability.values())
                logger.info(f"  {closer}: {days_with_slots} days with {total_slots} total slots")

            return 0
        except Exception as e:
            logger.error(f"=== Scan Failed: {e} ===", exc_info=True)
            return 1

if __name__ == '__main__':
    sys.exit(main())
