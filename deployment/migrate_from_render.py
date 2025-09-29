#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Business Tool Hub - Data Migration Script
Migrate data from Render.com to new home server
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


class DataMigration:
    """
    Data migration handler from Render.com to home server
    """

    # Critical data files that MUST be migrated
    CRITICAL_FILES = [
        'user_stats.json',
        'user_levels.json',
        'user_badges.json',
        'scores.json',
        'champions.json',
        'weekly_points.json'
    ]

    # Optional data files
    OPTIONAL_FILES = [
        'daily_user_stats.json',
        'prestige_data.json',
        'cosmetic_purchases.json',
        'daily_quests.json',
        'behavior_patterns.json',
        'blocked_dates.json',
        'availability.json'
    ]

    def __init__(self, source_dir: str, target_dir: str, dry_run: bool = False):
        """
        Initialize migration

        Args:
            source_dir: Source directory (Render.com data)
            target_dir: Target directory (new server)
            dry_run: If True, only simulate migration
        """
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.dry_run = dry_run
        self.stats = {
            'files_migrated': 0,
            'files_failed': 0,
            'files_skipped': 0,
            'total_size': 0
        }

    def validate_source(self) -> bool:
        """Validate source directory"""
        print_info("Validating source directory...")

        if not self.source_dir.exists():
            print_error(f"Source directory not found: {self.source_dir}")
            return False

        if not self.source_dir.is_dir():
            print_error(f"Source path is not a directory: {self.source_dir}")
            return False

        # Check for critical files
        missing_critical = []
        for filename in self.CRITICAL_FILES:
            file_path = self.source_dir / filename
            if not file_path.exists():
                missing_critical.append(filename)

        if missing_critical:
            print_warning("Missing critical files:")
            for filename in missing_critical:
                print(f"  - {filename}")
            response = input("\nContinue anyway? (yes/no): ")
            if response.lower() != 'yes':
                return False

        print_success("Source directory validated")
        return True

    def validate_target(self) -> bool:
        """Validate target directory"""
        print_info("Validating target directory...")

        # Create target directory if it doesn't exist
        if not self.target_dir.exists():
            if self.dry_run:
                print_info(f"[DRY RUN] Would create: {self.target_dir}")
            else:
                try:
                    self.target_dir.mkdir(parents=True, exist_ok=True)
                    print_success(f"Created target directory: {self.target_dir}")
                except Exception as e:
                    print_error(f"Could not create target directory: {e}")
                    return False

        # Check write permissions
        if not os.access(self.target_dir, os.W_OK):
            print_error(f"No write permission for target directory: {self.target_dir}")
            return False

        print_success("Target directory validated")
        return True

    def backup_existing_data(self) -> Optional[Path]:
        """Create backup of existing data in target directory"""
        print_info("Backing up existing data...")

        # Check if target directory has data
        existing_files = list(self.target_dir.glob('*.json'))
        if not existing_files:
            print_info("No existing data to backup")
            return None

        # Create backup directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = self.target_dir.parent / 'backups' / f'pre_migration_{timestamp}'

        if self.dry_run:
            print_info(f"[DRY RUN] Would backup to: {backup_dir}")
            return backup_dir

        try:
            backup_dir.mkdir(parents=True, exist_ok=True)

            for file in existing_files:
                shutil.copy2(file, backup_dir / file.name)

            print_success(f"Backed up {len(existing_files)} files to: {backup_dir}")
            return backup_dir

        except Exception as e:
            print_error(f"Backup failed: {e}")
            return None

    def validate_json_file(self, file_path: Path) -> bool:
        """Validate JSON file integrity"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except json.JSONDecodeError as e:
            print_warning(f"Invalid JSON in {file_path.name}: {e}")
            return False
        except Exception as e:
            print_warning(f"Could not validate {file_path.name}: {e}")
            return False

    def migrate_file(self, filename: str) -> bool:
        """Migrate a single file"""
        source_file = self.source_dir / filename
        target_file = self.target_dir / filename

        # Check if source exists
        if not source_file.exists():
            self.stats['files_skipped'] += 1
            return False

        # Validate JSON
        if not self.validate_json_file(source_file):
            print_error(f"Skipping invalid file: {filename}")
            self.stats['files_failed'] += 1
            return False

        # Get file size
        file_size = source_file.stat().st_size
        self.stats['total_size'] += file_size

        # Perform migration
        if self.dry_run:
            print_info(f"[DRY RUN] Would migrate: {filename} ({file_size} bytes)")
        else:
            try:
                shutil.copy2(source_file, target_file)
                print_success(f"Migrated: {filename} ({file_size} bytes)")
            except Exception as e:
                print_error(f"Failed to migrate {filename}: {e}")
                self.stats['files_failed'] += 1
                return False

        self.stats['files_migrated'] += 1
        return True

    def migrate_all_files(self):
        """Migrate all data files"""
        print_header("Migrating Data Files")

        all_files = self.CRITICAL_FILES + self.OPTIONAL_FILES

        for filename in all_files:
            self.migrate_file(filename)

        # Also check for any other JSON files in source
        other_json_files = [
            f.name for f in self.source_dir.glob('*.json')
            if f.name not in all_files
        ]

        if other_json_files:
            print_info(f"\nFound {len(other_json_files)} additional JSON files")
            for filename in other_json_files:
                response = input(f"Migrate {filename}? (y/n): ")
                if response.lower() == 'y':
                    self.migrate_file(filename)

    def verify_migration(self) -> bool:
        """Verify migration success"""
        print_header("Verifying Migration")

        if self.dry_run:
            print_info("[DRY RUN] Skipping verification")
            return True

        all_valid = True

        for filename in self.CRITICAL_FILES:
            target_file = self.target_dir / filename
            if not target_file.exists():
                print_error(f"Missing critical file: {filename}")
                all_valid = False
            elif not self.validate_json_file(target_file):
                print_error(f"Invalid JSON in migrated file: {filename}")
                all_valid = False
            else:
                print_success(f"Verified: {filename}")

        return all_valid

    def print_summary(self):
        """Print migration summary"""
        print_header("Migration Summary")

        print(f"Files migrated:  {Colors.GREEN}{self.stats['files_migrated']}{Colors.END}")
        print(f"Files failed:    {Colors.RED}{self.stats['files_failed']}{Colors.END}")
        print(f"Files skipped:   {Colors.YELLOW}{self.stats['files_skipped']}{Colors.END}")
        print(f"Total data size: {Colors.BLUE}{self.stats['total_size'] / 1024:.2f} KB{Colors.END}")

        if self.dry_run:
            print(f"\n{Colors.YELLOW}This was a DRY RUN - no files were actually migrated{Colors.END}")

    def run(self) -> bool:
        """Run full migration process"""
        print_header("Business Tool Hub - Data Migration")

        if self.dry_run:
            print_warning("DRY RUN MODE - No files will be actually migrated")

        # Step 1: Validate
        if not self.validate_source():
            return False

        if not self.validate_target():
            return False

        # Step 2: Backup existing data
        backup_dir = self.backup_existing_data()

        # Step 3: Confirm migration
        if not self.dry_run:
            print(f"\n{Colors.YELLOW}About to migrate data:{Colors.END}")
            print(f"  From: {self.source_dir}")
            print(f"  To:   {self.target_dir}")
            if backup_dir:
                print(f"  Backup: {backup_dir}")

            response = input(f"\n{Colors.BOLD}Proceed with migration? (yes/no): {Colors.END}")
            if response.lower() != 'yes':
                print_info("Migration cancelled")
                return False

        # Step 4: Migrate files
        self.migrate_all_files()

        # Step 5: Verify
        if not self.verify_migration():
            print_error("Migration verification failed!")
            if backup_dir:
                print_info(f"You can restore from backup: {backup_dir}")
            return False

        # Step 6: Summary
        self.print_summary()

        if self.stats['files_failed'] == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Migration completed successfully!{Colors.END}")
            return True
        else:
            print(f"\n{Colors.YELLOW}Migration completed with {self.stats['files_failed']} errors{Colors.END}")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Migrate data from Render.com to home server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (simulate migration)
  python migrate_from_render.py --source /old/data --target /new/data --dry-run

  # Actual migration
  python migrate_from_render.py --source /old/data --target /new/data

  # With custom paths
  python migrate_from_render.py \\
    --source /opt/render/project/src/persist/persistent \\
    --target /opt/business-hub/data/persistent
        """
    )

    parser.add_argument(
        '--source',
        required=True,
        help='Source directory (Render.com data location)'
    )

    parser.add_argument(
        '--target',
        required=True,
        help='Target directory (new server data location)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate migration without actually copying files'
    )

    args = parser.parse_args()

    # Run migration
    migration = DataMigration(args.source, args.target, args.dry_run)
    success = migration.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()