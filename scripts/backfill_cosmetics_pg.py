# -*- coding: utf-8 -*-
"""
Backfill Cosmetics data from JSON files into PostgreSQL (UserCosmetic table).

Sources:
  - data/persistent/cosmetic_purchases.json  -> UserCosmetic (is_owned=True)
  - data/persistent/active_cosmetics.json    -> UserCosmetic (is_active=True)

Handles ON CONFLICT via upsert logic (check-then-insert/update).
"""
import sys
import os
import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')


def backfill_cosmetics(session, dry_run=False):
    from app.models.cosmetics import UserCosmetic

    persist_base = os.getenv("PERSIST_BASE", "data")
    purchases_file = Path(persist_base) / "persistent" / "cosmetic_purchases.json"
    active_file = Path(persist_base) / "persistent" / "active_cosmetics.json"

    # Load source data
    purchases = {}
    active = {}

    if purchases_file.exists():
        with open(purchases_file, "r", encoding="utf-8") as f:
            purchases = json.load(f)
        print(f"Loaded purchases for {len(purchases)} users from {purchases_file}")
    else:
        print(f"WARNING: {purchases_file} not found, skipping purchases backfill")

    if active_file.exists():
        with open(active_file, "r", encoding="utf-8") as f:
            active = json.load(f)
        print(f"Loaded active cosmetics for {len(active)} users from {active_file}")
    else:
        print(f"WARNING: {active_file} not found, skipping active backfill")

    inserted = 0
    updated = 0

    # Map list_key -> item_type
    def list_key_to_type(list_key):
        if list_key == "effects":
            return "effect"
        return list_key.rstrip("s")

    # Build active lookup: {username: {item_id: True}}
    active_lookup = {}
    for username, user_active in active.items():
        active_lookup[username] = set()
        if user_active.get("title"):
            active_lookup[username].add(user_active["title"])
        if user_active.get("theme") and user_active["theme"] != "default":
            active_lookup[username].add(user_active["theme"])
        if user_active.get("avatar") and user_active["avatar"] not in ("🧑‍💼", None):
            active_lookup[username].add(user_active["avatar"])
        if user_active.get("frame"):
            active_lookup[username].add(user_active["frame"])
        for eff in user_active.get("effects", []):
            active_lookup[username].add(eff)

    # Process purchases -> UserCosmetic rows
    for username, user_data in purchases.items():
        user_actives = active_lookup.get(username, set())
        for list_key in ["titles", "themes", "avatars", "effects", "frames"]:
            item_type = list_key_to_type(list_key)
            for item_id in user_data.get(list_key, []):
                is_active_flag = item_id in user_actives
                existing = session.query(UserCosmetic).filter_by(
                    username=username, item_id=item_id
                ).first()
                if existing:
                    existing.is_owned = True
                    existing.is_active = is_active_flag
                    updated += 1
                else:
                    row = UserCosmetic(
                        username=username,
                        item_id=item_id,
                        item_type=item_type,
                        item_category="visual" if item_type != "effect" else "animation",
                        name=item_id,
                        rarity="common",
                        is_owned=True,
                        is_active=is_active_flag,
                        purchase_price=0,
                    )
                    session.add(row)
                    inserted += 1

    if not dry_run:
        session.commit()
        print(f"Committed: {inserted} inserted, {updated} updated UserCosmetic rows")
    else:
        session.rollback()
        print(f"DRY RUN: would insert {inserted}, update {updated} UserCosmetic rows")

    return inserted, updated


def main():
    dry_run = "--dry-run" in sys.argv

    from app import create_app
    app = create_app()

    with app.app_context():
        from app.utils.db_utils import db_session_scope
        with db_session_scope() as session:
            backfill_cosmetics(session, dry_run=dry_run)


if __name__ == "__main__":
    main()
