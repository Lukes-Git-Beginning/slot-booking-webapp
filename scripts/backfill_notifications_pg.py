# -*- coding: utf-8 -*-
"""
Backfill Notifications from JSON into PostgreSQL.

Quelle: data/persistent/user_notifications.json
Ziel: notifications Tabelle in PostgreSQL

Jeder User bekommt seine eigene Notification-Row.
notification_id-Format: "{original_id}-{username}" (eindeutig pro User)

Verwendung:
    python scripts/backfill_notifications_pg.py --dry-run   # Vorschau
    python scripts/backfill_notifications_pg.py --execute   # Ausfuehren
"""
import argparse
import json
import logging
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100


def load_notifications_json() -> dict:
    """Laedt user_notifications.json aus bekannten Pfaden."""
    json_paths = [
        project_root / 'data' / 'persistent' / 'user_notifications.json',
        project_root / 'data' / 'user_notifications.json',
        project_root / 'data' / 'static' / 'user_notifications.json',
    ]

    for path in json_paths:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Geladen: {path}")
            return data

    logger.error("Keine user_notifications.json gefunden!")
    return {}


def backfill_notifications(dry_run: bool = True) -> dict:
    """
    Migriert user_notifications.json nach PostgreSQL.

    Args:
        dry_run: Bei True werden keine Aenderungen gespeichert.

    Returns:
        Dict mit Statistiken: inserted, skipped, errors
    """
    from app.models import init_db, get_db_session
    from app.models.notification import Notification

    init_db()
    session = get_db_session()

    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info("=" * 70)
    logger.info(f"BACKFILL Notifications: JSON -> PostgreSQL ({mode})")
    logger.info("=" * 70)

    # JSON-Daten laden
    all_notifications = load_notifications_json()
    if not all_notifications:
        logger.warning("Keine Notifications zum Migrieren gefunden.")
        session.close()
        return {'inserted': 0, 'skipped': 0, 'errors': 0}

    total_notifs = sum(len(notifs) for notifs in all_notifications.values())
    logger.info(f"Gefunden: {len(all_notifications)} User, {total_notifs} Notifications gesamt")

    # Bereits vorhandene notification_ids aus PG laden
    existing_ids = {
        row.notification_id
        for row in session.query(Notification.notification_id).all()
    }
    logger.info(f"Bereits in PostgreSQL: {len(existing_ids)} Notification-Rows")

    inserted = 0
    skipped = 0
    errors = 0
    batch: list = []

    for username, notifications in all_notifications.items():
        for notif in notifications:
            original_id = notif.get('id', '')
            if not original_id:
                logger.warning(f"Notification ohne ID fuer User {username} uebersprungen")
                errors += 1
                continue

            # Eindeutige PG-ID pro User
            pg_notification_id = f"{original_id}-{username}"

            if pg_notification_id in existing_ids:
                skipped += 1
                continue

            # Timestamp parsen
            created_at = None
            ts = notif.get('timestamp', '')
            if ts:
                try:
                    created_at = _parse_timestamp(ts)
                except Exception:
                    logger.debug(f"Timestamp '{ts}' konnte nicht geparst werden, verwende None")

            notif_row = Notification(
                notification_id=pg_notification_id,
                username=username,
                title=notif.get('title', ''),
                message=notif.get('message', ''),
                notification_type=notif.get('type', 'info'),
                is_read=notif.get('read', False),
                is_dismissed=notif.get('dismissed', False),
                show_popup=notif.get('show_popup', False),
                roles=notif.get('roles', []),
                actions=notif.get('actions', []),
            )

            # created_at manuell setzen wenn vorhanden
            if created_at:
                notif_row.created_at = created_at
                notif_row.updated_at = created_at

            batch.append(notif_row)
            inserted += 1

            # Batch-Insert alle BATCH_SIZE Eintraege
            if len(batch) >= BATCH_SIZE:
                if not dry_run:
                    try:
                        session.bulk_save_objects(batch)
                        session.commit()
                        logger.info(f"  Batch committed: {inserted} Notifications bisher")
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Batch-Insert fehlgeschlagen: {e}")
                        errors += len(batch)
                        inserted -= len(batch)
                else:
                    logger.info(f"  [DRY RUN] Wuerde {len(batch)} Notifications einfuegen (bisher: {inserted})")
                batch = []

    # Letzten Batch committen
    if batch:
        if not dry_run:
            try:
                session.bulk_save_objects(batch)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Letzter Batch-Insert fehlgeschlagen: {e}")
                errors += len(batch)
                inserted -= len(batch)
        else:
            logger.info(f"  [DRY RUN] Wuerde letzten Batch mit {len(batch)} Notifications einfuegen")

    session.close()

    logger.info("=" * 70)
    logger.info(f"ERGEBNIS ({mode}):")
    logger.info(f"  Eingefuegt:    {inserted}")
    logger.info(f"  Uebersprungen: {skipped}")
    logger.info(f"  Fehler:        {errors}")
    logger.info("=" * 70)

    return {'inserted': inserted, 'skipped': skipped, 'errors': errors}


def _parse_timestamp(ts: str):
    """Parst einen ISO-Timestamp-String zu einem datetime-Objekt."""
    from datetime import datetime
    # Versuche verschiedene Formate
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unbekanntes Timestamp-Format: {ts}")


def main():
    parser = argparse.ArgumentParser(
        description='Backfill user_notifications.json nach PostgreSQL'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Vorschau: Zeigt was migriert wuerde, ohne Aenderungen zu speichern'
    )
    group.add_argument(
        '--execute',
        action='store_true',
        help='Fuehrt die Migration durch und schreibt in PostgreSQL'
    )
    args = parser.parse_args()

    from app import create_app
    from app.config.production import ProductionConfig
    app = create_app(ProductionConfig)

    with app.app_context():
        dry_run = not args.execute
        result = backfill_notifications(dry_run=dry_run)

        if result['errors'] > 0:
            sys.exit(1)


if __name__ == '__main__':
    main()
