# -*- coding: utf-8 -*-
"""
Backfill Lootbox data from JSON file into PostgreSQL (lootbox_data table).

Source:
  - data/persistent/lootboxes.json -> LootboxData (upsert per username)
"""
import sys
import os
import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')


def backfill_lootbox(session, dry_run=False):
    from app.models.gamification import LootboxData

    persist_base = os.getenv("PERSIST_BASE", "data")
    lootbox_file = Path(persist_base) / "persistent" / "lootboxes.json"

    if not lootbox_file.exists():
        print(f"WARNING: {lootbox_file} not found, nothing to backfill")
        return 0, 0

    with open(lootbox_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded lootbox data for {len(data)} users from {lootbox_file}")

    inserted = 0
    updated = 0

    for username, user_data in data.items():
        existing = session.query(LootboxData).filter_by(username=username).first()
        crates = user_data.get("crates", [])
        history = user_data.get("history", [])
        pity = user_data.get("pity_counter", 0)

        if existing:
            existing.crates = crates
            existing.history = history
            existing.pity_counter = pity
            updated += 1
        else:
            row = LootboxData(
                username=username,
                crates=crates,
                history=history,
                pity_counter=pity,
            )
            session.add(row)
            inserted += 1

    if not dry_run:
        session.commit()
        print(f"Committed: {inserted} inserted, {updated} updated LootboxData rows")
    else:
        session.rollback()
        print(f"DRY RUN: would insert {inserted}, update {updated} LootboxData rows")

    return inserted, updated


def main():
    dry_run = "--dry-run" in sys.argv

    from app import create_app
    app = create_app()

    with app.app_context():
        from app.utils.db_utils import db_session_scope
        with db_session_scope() as session:
            backfill_lootbox(session, dry_run=dry_run)


if __name__ == "__main__":
    main()
