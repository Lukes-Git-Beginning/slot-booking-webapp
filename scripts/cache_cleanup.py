#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cache Cleanup Script
Automatic cleanup of old cache files to prevent disk space issues
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/business-hub/cache-cleanup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class CacheCleanup:
    def __init__(self, cache_dir: str = "/opt/business-hub/cache"):
        self.cache_dir = cache_dir

        # Cleanup configuration
        self.max_age_days = 7  # Delete files older than 7 days
        self.max_size_mb = 50  # Trigger cleanup if cache exceeds 50MB
        self.target_size_mb = 30  # Clean down to 30MB if size exceeded

    def get_cache_stats(self):
        """Get current cache statistics"""
        try:
            cache_files = list(Path(self.cache_dir).glob("*.cache"))
            total_size = sum(f.stat().st_size for f in cache_files)

            stats = {
                'total_files': len(cache_files),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_size_bytes': total_size,
                'cache_dir': self.cache_dir
            }

            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return None

    def clean_old_files(self, dry_run=False):
        """Remove cache files older than max_age_days"""
        try:
            cutoff_time = time.time() - (self.max_age_days * 24 * 3600)
            removed_files = 0
            freed_bytes = 0

            for cache_file in Path(self.cache_dir).glob("*.cache"):
                if cache_file.stat().st_mtime < cutoff_time:
                    file_size = cache_file.stat().st_size

                    if dry_run:
                        logger.info(f"[DRY RUN] Would delete: {cache_file.name} ({file_size} bytes)")
                    else:
                        cache_file.unlink()
                        logger.info(f"Deleted old cache file: {cache_file.name}")

                    removed_files += 1
                    freed_bytes += file_size

            freed_mb = round(freed_bytes / (1024 * 1024), 2)

            if removed_files > 0:
                action = "Would delete" if dry_run else "Deleted"
                logger.info(f"{action} {removed_files} old cache files, freed {freed_mb} MB")
            else:
                logger.info("No old cache files found to delete")

            return removed_files, freed_mb

        except Exception as e:
            logger.error(f"Error cleaning old files: {e}")
            return 0, 0

    def clean_by_size(self, dry_run=False):
        """Remove oldest files if cache exceeds max size"""
        try:
            stats = self.get_cache_stats()
            if not stats:
                return 0, 0

            if stats['total_size_mb'] <= self.max_size_mb:
                logger.info(f"Cache size OK: {stats['total_size_mb']} MB (limit: {self.max_size_mb} MB)")
                return 0, 0

            logger.warning(f"Cache size exceeded: {stats['total_size_mb']} MB > {self.max_size_mb} MB")

            # Get all cache files sorted by modification time (oldest first)
            cache_files = sorted(
                Path(self.cache_dir).glob("*.cache"),
                key=lambda f: f.stat().st_mtime
            )

            target_bytes = self.target_size_mb * 1024 * 1024
            current_bytes = stats['total_size_bytes']
            removed_files = 0
            freed_bytes = 0

            for cache_file in cache_files:
                if current_bytes <= target_bytes:
                    break

                file_size = cache_file.stat().st_size

                if dry_run:
                    logger.info(f"[DRY RUN] Would delete: {cache_file.name} ({file_size} bytes)")
                else:
                    cache_file.unlink()
                    logger.info(f"Deleted cache file to reduce size: {cache_file.name}")

                removed_files += 1
                freed_bytes += file_size
                current_bytes -= file_size

            freed_mb = round(freed_bytes / (1024 * 1024), 2)
            final_mb = round(current_bytes / (1024 * 1024), 2)

            action = "Would delete" if dry_run else "Deleted"
            logger.info(f"{action} {removed_files} files to reduce cache size from {stats['total_size_mb']} MB to {final_mb} MB")

            return removed_files, freed_mb

        except Exception as e:
            logger.error(f"Error cleaning by size: {e}")
            return 0, 0

    def run_cleanup(self, dry_run=False):
        """Run complete cleanup process"""
        logger.info("=" * 60)
        logger.info("Starting cache cleanup...")
        logger.info(f"Dry run: {dry_run}")

        # Get initial stats
        initial_stats = self.get_cache_stats()
        if initial_stats:
            logger.info(f"Initial cache: {initial_stats['total_files']} files, {initial_stats['total_size_mb']} MB")

        # Clean old files
        old_files, old_size = self.clean_old_files(dry_run)

        # Clean by size if needed
        size_files, size_freed = self.clean_by_size(dry_run)

        # Get final stats
        final_stats = self.get_cache_stats()
        if final_stats:
            logger.info(f"Final cache: {final_stats['total_files']} files, {final_stats['total_size_mb']} MB")

        total_removed = old_files + size_files
        total_freed = old_size + size_freed

        logger.info(f"Cleanup complete: Removed {total_removed} files, freed {total_freed} MB")
        logger.info("=" * 60)

        return {
            'removed_files': total_removed,
            'freed_mb': total_freed,
            'initial_stats': initial_stats,
            'final_stats': final_stats
        }

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Clean up old cache files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--cache-dir', default='/opt/business-hub/cache', help='Cache directory path')
    parser.add_argument('--max-age', type=int, default=7, help='Delete files older than this many days')
    parser.add_argument('--max-size', type=int, default=50, help='Maximum cache size in MB')

    args = parser.parse_args()

    cleanup = CacheCleanup(cache_dir=args.cache_dir)
    cleanup.max_age_days = args.max_age
    cleanup.max_size_mb = args.max_size

    try:
        result = cleanup.run_cleanup(dry_run=args.dry_run)

        if result['removed_files'] > 0:
            sys.exit(0)  # Success
        else:
            sys.exit(0)  # Also success, just nothing to clean

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
