#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migrate T2 Bookings Format: List -> Dict
Converts legacy list format to {'bookings': [...]} dict format

Usage:
    python scripts/migrate_t2_bookings_format.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Data paths
PERSIST_BASE = os.getenv("PERSIST_BASE", str(project_root / "data"))
if not os.path.exists(PERSIST_BASE):
    PERSIST_BASE = str(project_root / "data")

DATA_DIR = Path(PERSIST_BASE) / "persistent"
T2_FILE = DATA_DIR / "t2_bookings.json"


def migrate():
    """Migrate T2 bookings from list to dict format"""

    print("=" * 60)
    print("T2 Bookings Format Migration: List -> Dict")
    print("=" * 60)

    # Check if file exists
    if not T2_FILE.exists():
        print(f"❌ File not found: {T2_FILE}")
        print("✅ No migration needed (file doesn't exist yet)")
        return

    print(f"📖 Reading: {T2_FILE}")

    # Load current data
    try:
        with open(T2_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    # Check format
    if isinstance(data, list):
        print(f"📊 Current format: LIST with {len(data)} bookings")
        print("🔄 Converting to dict format...")

        # Create backup
        backup_file = T2_FILE.with_suffix(f'.json.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        print(f"💾 Creating backup: {backup_file}")

        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Backup created: {backup_file}")
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            print("⚠️  Aborting migration for safety")
            return

        # Convert to dict format
        new_data = {'bookings': data}

        # Save new format
        try:
            with open(T2_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Migration complete: {len(data)} bookings converted")
            print(f"📁 New format: {{'bookings': [{len(data)} items]}}")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            print(f"⚠️  Restoring from backup: {backup_file}")
            # Restore backup
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            with open(T2_FILE, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            print("✅ Backup restored")
            return

    elif isinstance(data, dict) and 'bookings' in data:
        bookings_count = len(data.get('bookings', []))
        print(f"✅ Already in dict format with {bookings_count} bookings")
        print("ℹ️  No migration needed")

    else:
        print(f"⚠️  WARNING: Unexpected format: {type(data)}")
        if isinstance(data, dict):
            print(f"   Keys found: {list(data.keys())}")
        print("❌ Migration aborted (unknown format)")
        return

    print("=" * 60)
    print("✅ Migration check complete")
    print("=" * 60)


if __name__ == '__main__':
    migrate()
