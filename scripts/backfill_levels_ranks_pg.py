# -*- coding: utf-8 -*-
"""
Backfill Level-System + Rank-Tracking from JSON into PostgreSQL.

Quellen:
- data/static/user_levels.json       -> UserLevel
- data/static/level_history.json     -> LevelHistory (level_ups pro User)
- data/persistent/rank_history.json  -> RankHistory

Usage:
    python scripts/backfill_levels_ranks_pg.py --dry-run
    python scripts/backfill_levels_ranks_pg.py --execute
"""
import sys
import os
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100


def _load_json(path):
    """Load a JSON file, return empty dict on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load {path}: {e}")
        return {}


def backfill_user_levels(session, persist_base, dry_run):
    """Backfill user_levels from user_levels.json."""
    from app.models.gamification import UserLevel

    levels_file = Path(persist_base) / "static" / "user_levels.json"
    data = _load_json(levels_file)

    if not data:
        logger.info("user_levels.json is empty or missing — skipping UserLevel backfill")
        return 0

    logger.info(f"UserLevel: {len(data)} users found in JSON")

    inserted = 0
    updated = 0
    batch = []

    for username, info in data.items():
        existing = session.query(UserLevel).filter_by(username=username).first()
        updated_at = None
        raw_ts = info.get("updated_at")
        if raw_ts:
            try:
                updated_at = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        if existing:
            if (existing.level != info.get("level", 1)
                    or existing.xp != info.get("xp", 0)):
                if not dry_run:
                    existing.level = info.get("level", 1)
                    existing.xp = info.get("xp", 0)
                    existing.level_title = info.get("level_title")
                    existing.updated_at = updated_at
                updated += 1
        else:
            batch.append(UserLevel(
                username=username,
                level=info.get("level", 1),
                xp=info.get("xp", 0),
                level_title=info.get("level_title"),
                updated_at=updated_at
            ))
            inserted += 1

        if len(batch) >= BATCH_SIZE and not dry_run:
            session.bulk_save_objects(batch)
            session.flush()
            batch = []

    if batch and not dry_run:
        session.bulk_save_objects(batch)
        session.flush()

    logger.info(f"UserLevel: {inserted} to insert, {updated} to update{' (dry-run)' if dry_run else ''}")
    return inserted + updated


def backfill_level_history(session, persist_base, dry_run):
    """Backfill level_history from level_history.json (level_ups arrays)."""
    from app.models.gamification import LevelHistory

    history_file = Path(persist_base) / "static" / "level_history.json"
    data = _load_json(history_file)

    if not data:
        logger.info("level_history.json is empty or missing — skipping LevelHistory backfill")
        return 0

    total_ups = sum(len(v.get("level_ups", [])) for v in data.values() if isinstance(v, dict))
    logger.info(f"LevelHistory: {total_ups} level_up events across {len(data)} users")

    # Build set of existing (username, old_level, new_level, leveled_up_at) for conflict avoidance
    existing_keys = set()
    for row in session.query(
        LevelHistory.username, LevelHistory.old_level, LevelHistory.new_level, LevelHistory.leveled_up_at
    ).all():
        existing_keys.add((row.username, row.old_level, row.new_level,
                           row.leveled_up_at.strftime("%Y-%m-%d %H:%M:%S") if row.leveled_up_at else ""))

    inserted = 0
    skipped = 0
    batch = []

    for username, user_data in data.items():
        if not isinstance(user_data, dict):
            continue
        for up in user_data.get("level_ups", []):
            ts_raw = up.get("timestamp", "")
            try:
                leveled_up_at = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                leveled_up_at = datetime.utcnow()

            key = (username, up.get("old_level", 0), up.get("new_level", 0),
                   leveled_up_at.strftime("%Y-%m-%d %H:%M:%S"))
            if key in existing_keys:
                skipped += 1
                continue

            batch.append(LevelHistory(
                username=username,
                old_level=up.get("old_level", 0),
                new_level=up.get("new_level", 0),
                old_xp=up.get("old_xp", 0),
                new_xp=up.get("new_xp", 0),
                xp_gained=up.get("xp_gained", 0),
                leveled_up_at=leveled_up_at,
                rewards_granted=up.get("rewards_granted")
            ))
            inserted += 1

            if len(batch) >= BATCH_SIZE and not dry_run:
                session.bulk_save_objects(batch)
                session.flush()
                batch = []

    if batch and not dry_run:
        session.bulk_save_objects(batch)
        session.flush()

    logger.info(f"LevelHistory: {inserted} to insert, {skipped} already exist{' (dry-run)' if dry_run else ''}")
    return inserted


def backfill_rank_history(session, persist_base, dry_run):
    """Backfill rank_history from rank_history.json."""
    from app.models.gamification import RankHistory

    history_file = Path(persist_base) / "persistent" / "rank_history.json"
    data = _load_json(history_file)

    if not data:
        logger.info("rank_history.json is empty or missing — skipping RankHistory backfill")
        return 0

    total_entries = sum(len(v) for v in data.values() if isinstance(v, dict))
    logger.info(f"RankHistory: {total_entries} entries across {len(data)} dates")

    inserted = 0
    updated = 0
    batch_insert = []

    for date_str, rank_snapshot in data.items():
        if not isinstance(rank_snapshot, dict):
            continue
        for username, rank_pos in rank_snapshot.items():
            existing = session.query(RankHistory).filter_by(
                date=date_str, username=username
            ).first()

            if existing:
                if existing.rank_position != rank_pos:
                    if not dry_run:
                        existing.rank_position = rank_pos
                    updated += 1
            else:
                batch_insert.append(RankHistory(
                    date=date_str,
                    username=username,
                    rank_position=rank_pos
                ))
                inserted += 1

                if len(batch_insert) >= BATCH_SIZE and not dry_run:
                    session.bulk_save_objects(batch_insert)
                    session.flush()
                    batch_insert = []

    if batch_insert and not dry_run:
        session.bulk_save_objects(batch_insert)
        session.flush()

    logger.info(f"RankHistory: {inserted} to insert, {updated} to update{' (dry-run)' if dry_run else ''}")
    return inserted + updated


def main():
    parser = argparse.ArgumentParser(
        description="Backfill Level-System + Rank-Tracking into PostgreSQL"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true",
                       help="Analyze only, no DB writes")
    group.add_argument("--execute", action="store_true",
                       help="Write data to PostgreSQL")
    args = parser.parse_args()

    dry_run = args.dry_run

    if dry_run:
        logger.info("DRY-RUN mode — no database writes")
    else:
        logger.info("EXECUTE mode — writing to PostgreSQL")

    from app import create_app
    app = create_app()

    persist_base = os.getenv("PERSIST_BASE", "data")

    with app.app_context():
        from app.models.base import get_db_session
        session = get_db_session()

        try:
            total = 0
            total += backfill_user_levels(session, persist_base, dry_run)
            total += backfill_level_history(session, persist_base, dry_run)
            total += backfill_rank_history(session, persist_base, dry_run)

            if not dry_run:
                session.commit()
                logger.info(f"Committed. Total records processed: {total}")
            else:
                session.rollback()
                logger.info(f"Dry-run complete. Total records that would be processed: {total}")

        except Exception as e:
            session.rollback()
            logger.error(f"Backfill failed: {e}", exc_info=True)
            sys.exit(1)
        finally:
            session.close()


if __name__ == "__main__":
    main()
