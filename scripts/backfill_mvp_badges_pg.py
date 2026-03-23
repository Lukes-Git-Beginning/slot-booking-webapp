# -*- coding: utf-8 -*-
"""
Backfill MVP-Badges aus mvp_badges.json nach PostgreSQL.

Quelle: data/persistent/mvp_badges.json
Ziel: user_badges Tabelle (category='mvp')

Verwendung:
    python scripts/backfill_mvp_badges_pg.py
    python scripts/backfill_mvp_badges_pg.py --dry-run
"""
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

RARITY_COLORS = {
    "common": "#10b981",
    "uncommon": "#3b82f6",
    "rare": "#8b5cf6",
    "epic": "#f59e0b",
    "legendary": "#eab308",
    "mythic": "#ec4899"
}


def backfill_mvp_badges(dry_run: bool = False) -> dict:
    """Migriere mvp_badges.json nach PostgreSQL (user_badges, category='mvp')."""
    from app.models import init_db, get_db_session
    from app.models.gamification import UserBadge

    init_db()
    session = get_db_session()

    # JSON-Quelldatei suchen
    json_paths = [
        project_root / 'data' / 'persistent' / 'mvp_badges.json',
        project_root / 'data' / 'static' / 'mvp_badges.json',
        project_root / 'static' / 'mvp_badges.json',
    ]

    mvp_data = None
    source_path = None
    for path in json_paths:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                mvp_data = json.load(f)
            source_path = path
            logger.info(f"Quelle: {path} ({len(mvp_data)} User-Eintraege)")
            break

    if not mvp_data:
        logger.error("Keine mvp_badges.json gefunden!")
        return {"inserted": 0, "skipped": 0, "errors": 0}

    # Bestehende MVP-Eintraege in PG laden
    existing_pairs = set()
    for row in session.query(UserBadge.username, UserBadge.badge_id).filter(
        UserBadge.category == 'mvp'
    ).all():
        existing_pairs.add((row.username, row.badge_id))
    logger.info(f"Bereits in PostgreSQL (MVP): {len(existing_pairs)} Eintraege")

    inserted = 0
    skipped = 0
    errors = 0

    for username, user_data in mvp_data.items():
        badges = user_data.get("badges", [])
        if not badges:
            continue

        for badge in badges:
            badge_id = badge.get("id", "")
            if not badge_id:
                logger.warning(f"Badge ohne ID fuer {username}, uebersprungen")
                continue

            if (username, badge_id) in existing_pairs:
                skipped += 1
                continue

            earned_str = badge.get("earned_date", "")
            try:
                earned_date = datetime.strptime(earned_str, "%Y-%m-%d %H:%M:%S") if earned_str else datetime.utcnow()
            except (ValueError, TypeError):
                earned_date = datetime.utcnow()

            color = badge.get("color", RARITY_COLORS.get(badge.get("rarity", "epic"), "#f59e0b"))

            try:
                if not dry_run:
                    session.add(UserBadge(
                        username=username,
                        badge_id=badge_id,
                        name=badge.get("name", badge_id),
                        description=badge.get("description", ""),
                        emoji=badge.get("emoji", "🏅"),
                        rarity=badge.get("rarity", "epic"),
                        category="mvp",
                        color=color,
                        earned_date=earned_date,
                        badge_metadata={"period": badge.get("period", "")}
                    ))
                logger.info(f"{'[DRY-RUN] ' if dry_run else ''}INSERT: {username} / {badge_id} (period={badge.get('period', '')})")
                inserted += 1
            except Exception as e:
                logger.error(f"Fehler bei {username}/{badge_id}: {e}")
                errors += 1
                session.rollback()
                continue

    if not dry_run and inserted > 0:
        try:
            session.commit()
            logger.info(f"Commit: {inserted} neue MVP-Badges geschrieben")
        except Exception as e:
            logger.error(f"Commit fehlgeschlagen: {e}")
            session.rollback()
            return {"inserted": 0, "skipped": skipped, "errors": errors + inserted}
    else:
        session.rollback()

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description="Backfill MVP-Badges nach PostgreSQL")
    parser.add_argument('--dry-run', action='store_true', help='Nur anzeigen, nichts schreiben')
    args = parser.parse_args()

    logger.info(f"Starte MVP-Badges Backfill {'(DRY-RUN)' if args.dry_run else ''}")
    result = backfill_mvp_badges(dry_run=args.dry_run)
    logger.info(
        f"Fertig: {result['inserted']} inserted, "
        f"{result['skipped']} skipped, "
        f"{result['errors']} errors"
    )


if __name__ == '__main__':
    main()
