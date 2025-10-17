#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backup Cleanup - Keep only last 30 days of backups"""

import os
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BACKUP_DIR = Path("/opt/business-hub/data/persistent/backups")
MAX_AGE_DAYS = 30

def cleanup_old_backups():
    """Remove backups older than MAX_AGE_DAYS"""
    cutoff = time.time() - (MAX_AGE_DAYS * 86400)
    removed = 0

    for backup_file in BACKUP_DIR.glob("*.json"):
        if backup_file.stat().st_mtime < cutoff:
            backup_file.unlink()
            removed += 1
            logger.info(f"Deleted: {backup_file.name}")

    logger.info(f"Cleanup complete: {removed} backups removed")
    return removed

if __name__ == "__main__":
    cleanup_old_backups()
