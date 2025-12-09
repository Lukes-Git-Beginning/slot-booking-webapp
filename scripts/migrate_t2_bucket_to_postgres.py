#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T2 Bucket System: JSON → PostgreSQL Migration

Migrates:
1. closers dict → T2CloserConfig (3 rows)
2. bucket state → T2BucketState (singleton)
3. draw_history → T2DrawHistory
4. user_last_draw → T2UserLastDraw

Usage:
    python scripts/migrate_t2_bucket_to_postgres.py --dry-run   # Test without changes
    python scripts/migrate_t2_bucket_to_postgres.py --execute   # Execute migration
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import pytz

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from app.models import (
    init_db,
    get_db_session,
    T2CloserConfig,
    T2BucketState,
    T2DrawHistory,
    T2UserLastDraw
)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")


def migrate_t2_bucket(dry_run=False):
    """Migrate T2 bucket system from JSON to PostgreSQL"""

    logger.info("=" * 60)
    logger.info("🚀 T2 Bucket System Migration: JSON → PostgreSQL")
    logger.info("=" * 60)
    logger.info(f"📍 Mode: {'DRY-RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
    logger.info("")

    # Initialize DB
    try:
        init_db()
        logger.info("✅ PostgreSQL connected")
    except Exception as e:
        logger.error(f"❌ PostgreSQL error: {e}")
        return

    session = get_db_session()

    # JSON file
    bucket_file = project_root / 'data' / 'persistent' / 't2_bucket_system.json'

    if not bucket_file.exists():
        logger.error(f"❌ File not found: {bucket_file}")
        logger.info("ℹ️  This might be normal if the system hasn't been used yet")
        return

    logger.info(f"📖 Reading: {bucket_file}")

    # Load JSON
    try:
        with open(bucket_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"❌ Error reading JSON: {e}")
        return

    logger.info(f"✅ JSON loaded successfully")
    logger.info("")

    stats = {
        'closers': 0,
        'bucket_state': 0,
        'draw_history': 0,
        'user_last_draw': 0,
        'errors': 0
    }

    try:
        # ===== 1. MIGRATE CLOSERS =====
        closers_data = data.get('closers', {})
        logger.info(f"📊 Migrating {len(closers_data)} closers...")

        for name, config in closers_data.items():
            try:
                if dry_run:
                    logger.info(f"  [DRY-RUN] Would insert: {name} ({config['full_name']})")
                    stats['closers'] += 1
                else:
                    # Check if exists
                    existing = session.query(T2CloserConfig).filter_by(name=name).first()
                    if existing:
                        logger.debug(f"  ⏭️  Skip: {name} (already exists)")
                        continue

                    closer = T2CloserConfig(
                        name=name,
                        full_name=config['full_name'],
                        color=config['color'],
                        default_probability=config['default_probability'],
                        is_active=True
                    )
                    session.add(closer)
                    session.flush()  # Get ID
                    stats['closers'] += 1
                    logger.info(f"  ✅ {name} ({config['full_name']}) - prob: {config['default_probability']}")

            except Exception as e:
                logger.error(f"  ❌ Error migrating closer {name}: {e}")
                stats['errors'] += 1

        if not dry_run:
            session.commit()
            logger.info(f"✅ Closers committed: {stats['closers']}")
        logger.info("")

        # ===== 2. MIGRATE BUCKET STATE (SINGLETON) =====
        logger.info("📊 Migrating bucket state (singleton)...")

        try:
            if dry_run:
                logger.info(f"  [DRY-RUN] Would insert bucket state:")
                logger.info(f"    - Probabilities: {data.get('probabilities', {})}")
                logger.info(f"    - Bucket size: {len(data.get('bucket', []))}")
                logger.info(f"    - Total draws: {data.get('total_draws', 0)}")
                logger.info(f"    - Max draws: {data.get('bucket_size_config', 20)}")
                stats['bucket_state'] = 1
            else:
                # Check if singleton exists
                existing = session.query(T2BucketState).filter_by(singleton_id=1).first()
                if existing:
                    logger.info("  ⏭️  Bucket state already exists, skipping")
                else:
                    last_reset_str = data.get('last_reset')
                    if last_reset_str:
                        last_reset = datetime.fromisoformat(last_reset_str)
                    else:
                        last_reset = datetime.now(TZ)

                    bucket_state = T2BucketState(
                        singleton_id=1,
                        probabilities=data.get('probabilities', {}),
                        bucket=data.get('bucket', []),
                        total_draws=data.get('total_draws', 0),
                        stats=data.get('stats', {}),
                        max_draws_before_reset=data.get('bucket_size_config', 20),
                        last_reset=last_reset
                    )
                    session.add(bucket_state)
                    session.commit()
                    stats['bucket_state'] = 1
                    logger.info(f"  ✅ Bucket state created (total draws: {data.get('total_draws', 0)})")

        except Exception as e:
            logger.error(f"  ❌ Error migrating bucket state: {e}")
            stats['errors'] += 1

        logger.info("")

        # ===== 3. MIGRATE DRAW HISTORY =====
        draw_history = data.get('draw_history', [])
        logger.info(f"📊 Migrating {len(draw_history)} draw records...")

        batch_size = 50
        for i, draw in enumerate(draw_history):
            try:
                if dry_run:
                    if i < 3:  # Show first 3
                        logger.info(f"  [DRY-RUN] Would insert: {draw.get('user')} drew {draw.get('closer')} at {draw.get('timestamp')}")
                    elif i == 3:
                        logger.info(f"  [DRY-RUN] ... and {len(draw_history) - 3} more")
                    stats['draw_history'] += 1
                else:
                    # Parse timestamp
                    drawn_at = datetime.fromisoformat(draw['timestamp'])

                    draw_record = T2DrawHistory(
                        username=draw['user'],
                        closer_drawn=draw['closer'],
                        draw_type=draw.get('draw_type', 'T2'),
                        customer_name=draw.get('customer_name'),
                        bucket_size_after=draw.get('bucket_size_after', 0),
                        probability_after=draw.get('probability_after', 0.0),
                        drawn_at=drawn_at
                    )
                    session.add(draw_record)
                    stats['draw_history'] += 1

                    # Commit in batches
                    if stats['draw_history'] % batch_size == 0:
                        session.commit()
                        logger.info(f"  ✓ {stats['draw_history']} draws migrated...")

            except Exception as e:
                logger.error(f"  ❌ Error migrating draw {i}: {e}")
                stats['errors'] += 1

        if not dry_run:
            session.commit()
            logger.info(f"✅ Draw history committed: {stats['draw_history']}")
        logger.info("")

        # ===== 4. MIGRATE USER LAST DRAW =====
        user_last_draw = data.get('user_last_draw', {})
        logger.info(f"📊 Migrating {len(user_last_draw)} user timeout records...")

        for username, last_draw in user_last_draw.items():
            try:
                if dry_run:
                    logger.info(f"  [DRY-RUN] Would insert: {username} last drew {last_draw.get('closer')} at {last_draw.get('timestamp')}")
                    stats['user_last_draw'] += 1
                else:
                    # Check if exists
                    existing = session.query(T2UserLastDraw).filter_by(username=username).first()
                    if existing:
                        logger.debug(f"  ⏭️  Skip: {username} (already exists)")
                        continue

                    # Parse timestamp
                    last_draw_at = datetime.fromisoformat(last_draw['timestamp'])

                    user_draw = T2UserLastDraw(
                        username=username,
                        last_draw_at=last_draw_at,
                        last_closer_drawn=last_draw['closer'],
                        last_draw_type=last_draw.get('draw_type', 'T2'),
                        last_customer_name=last_draw.get('customer_name')
                    )
                    session.add(user_draw)
                    stats['user_last_draw'] += 1
                    logger.info(f"  ✅ {username}: last draw at {last_draw_at.strftime('%Y-%m-%d %H:%M')}")

            except Exception as e:
                logger.error(f"  ❌ Error migrating user {username}: {e}")
                stats['errors'] += 1

        if not dry_run:
            session.commit()
            logger.info(f"✅ User timeouts committed: {stats['user_last_draw']}")
        logger.info("")

        # ===== SUMMARY =====
        logger.info("=" * 60)
        logger.info("📊 MIGRATION RESULT:")
        logger.info(f"  Closers:        {stats['closers']:>4}")
        logger.info(f"  Bucket State:   {stats['bucket_state']:>4}")
        logger.info(f"  Draw History:   {stats['draw_history']:>4}")
        logger.info(f"  User Timeouts:  {stats['user_last_draw']:>4}")
        logger.info(f"  Errors:         {stats['errors']:>4}")
        logger.info("=" * 60)

        if not dry_run:
            # Verify
            logger.info("")
            logger.info("🔍 Verification:")
            closer_count = session.query(T2CloserConfig).count()
            bucket_count = session.query(T2BucketState).count()
            draw_count = session.query(T2DrawHistory).count()
            user_count = session.query(T2UserLastDraw).count()

            logger.info(f"  T2CloserConfig:   {closer_count} rows")
            logger.info(f"  T2BucketState:    {bucket_count} rows (should be 1)")
            logger.info(f"  T2DrawHistory:    {draw_count} rows")
            logger.info(f"  T2UserLastDraw:   {user_count} rows")

            if bucket_count != 1:
                logger.warning(f"⚠️  Expected 1 bucket state, found {bucket_count}")

            logger.info("")
            logger.info("✅ Migration complete!")

    except Exception as e:
        logger.error(f"❌ Migration error: {e}")
        if not dry_run:
            session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate T2 Bucket to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Test without changes')
    parser.add_argument('--execute', action='store_true', help='Execute migration')

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("❌ Please specify --dry-run or --execute")
        print("")
        print("Examples:")
        print("  python scripts/migrate_t2_bucket_to_postgres.py --dry-run")
        print("  python scripts/migrate_t2_bucket_to_postgres.py --execute")
        sys.exit(1)

    migrate_t2_bucket(dry_run=args.dry_run)
