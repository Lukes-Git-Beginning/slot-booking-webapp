# -*- coding: utf-8 -*-
"""
Backfill Security Data (AccountLockout + AuditLog) from JSON into PostgreSQL.

Quellen:
  - data/persistent/account_lockouts.json
  - data/persistent/audit_log.json

Usage:
  python scripts/backfill_security_pg.py --dry-run
  python scripts/backfill_security_pg.py --execute
"""
import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')


def backfill_account_lockouts(session, dry_run=False):
    """Backfill AccountLockout-Records aus JSON nach PostgreSQL."""
    from app.models.security import AccountLockout as AccountLockoutModel

    print()
    print("=" * 70)
    print("PHASE 1: account_lockouts.json -> PostgreSQL")
    print("=" * 70)

    json_path = project_root / 'data' / 'persistent' / 'account_lockouts.json'
    if not json_path.exists():
        print(f"Datei nicht gefunden: {json_path}")
        return 0

    with open(json_path, 'r', encoding='utf-8') as f:
        lockout_data = json.load(f)

    if not isinstance(lockout_data, dict):
        print(f"Unerwartetes Format in {json_path}: erwartet dict")
        return 0

    print(f"JSON-Eintraege: {len(lockout_data)}")

    # Bestehende Usernames in PG ermitteln
    existing_usernames = {
        row.username for row in session.query(AccountLockoutModel.username).all()
    }
    print(f"Bereits in PG: {len(existing_usernames)}")

    inserted = 0
    skipped = 0

    for username, user_data in lockout_data.items():
        if username in existing_usernames:
            skipped += 1
            continue

        if not isinstance(user_data, dict):
            print(f"[!] Ueberspringe {username}: ungueltiges Format")
            skipped += 1
            continue

        first_attempt = None
        last_attempt = None
        locked_until = None

        try:
            if user_data.get('first_attempt'):
                first_attempt = datetime.fromisoformat(user_data['first_attempt'])
            if user_data.get('last_attempt'):
                last_attempt = datetime.fromisoformat(user_data['last_attempt'])
            if user_data.get('locked_until'):
                locked_until = datetime.fromisoformat(user_data['locked_until'])
        except ValueError as e:
            print(f"[!] Datums-Parse-Fehler fuer {username}: {e}")

        failed_attempts = user_data.get('failed_attempts', 0)

        print(f"[+] {username} — {failed_attempts} Fehlversuche, locked_until={user_data.get('locked_until', 'None')}")

        if not dry_run:
            row = AccountLockoutModel(
                username=username,
                failed_attempts=failed_attempts,
                first_attempt=first_attempt,
                last_attempt=last_attempt,
                locked_until=locked_until,
                lockout_tier=0
            )
            session.add(row)

        inserted += 1

    print(f"\nEingefuegt: {inserted}, Uebersprungen: {skipped}")
    return inserted


def backfill_audit_logs(session, dry_run=False):
    """Backfill AuditLog-Records aus JSON nach PostgreSQL."""
    from app.models.security import AuditLog as AuditLogModel

    print()
    print("=" * 70)
    print("PHASE 2: audit_log.json -> PostgreSQL")
    print("=" * 70)

    json_path = project_root / 'data' / 'persistent' / 'audit_log.json'
    if not json_path.exists():
        print(f"Datei nicht gefunden: {json_path}")
        return 0

    with open(json_path, 'r', encoding='utf-8') as f:
        audit_data = json.load(f)

    if not isinstance(audit_data, list):
        print(f"Unerwartetes Format in {json_path}: erwartet list")
        return 0

    print(f"JSON-Eintraege: {len(audit_data)}")

    # Bestehende Timestamps+User-Kombinationen fuer ON CONFLICT-Handling
    existing_count = session.query(AuditLogModel).count()
    print(f"Bereits in PG: {existing_count} Eintraege")

    # Einfachster Ansatz: nur einlesen wenn PG leer
    if existing_count > 0:
        print("PG hat bereits Eintraege — ueberspringe Backfill (ON CONFLICT: keine unique constraints auf audit_logs)")
        print("Tipp: Fuer Re-Backfill erst TRUNCATE TABLE audit_logs ausfuehren")
        return 0

    inserted = 0
    errors = 0

    for i, entry in enumerate(audit_data):
        if not isinstance(entry, dict):
            errors += 1
            continue

        timestamp_str = entry.get('timestamp', '')
        if not timestamp_str:
            errors += 1
            continue

        try:
            # Strip trailing Z (may duplicate offset if +00:00Z)
            clean_ts = timestamp_str.rstrip('Z')
            if not clean_ts[-6:].startswith(('+', '-')):
                clean_ts += '+00:00'
            ts = datetime.fromisoformat(clean_ts)
            # Offset-aware -> offset-naive fuer PG (ohne Timezone)
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
        except ValueError as e:
            print(f"[!] Eintrag {i}: Datums-Parse-Fehler '{timestamp_str}': {e}")
            errors += 1
            continue

        if not dry_run:
            row = AuditLogModel(
                timestamp=ts,
                event_type=entry.get('event_type', 'unknown'),
                action=entry.get('action', ''),
                user=entry.get('user', 'unknown'),
                ip_address=entry.get('ip_address'),
                user_agent=entry.get('user_agent'),
                severity=entry.get('severity', 'info'),
                details=entry.get('details') or {}
            )
            session.add(row)

        inserted += 1

    # Batch-Commit alle 500 Records
    if not dry_run and inserted > 0:
        session.flush()

    print(f"\nEingefuegt: {inserted}, Fehler: {errors}")
    return inserted


def backfill_security(dry_run=False):
    """Backfill Security-Daten aus JSON nach PostgreSQL."""
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    from app.utils.db_utils import db_session_scope

    print("=" * 70)
    print("BACKFILL Security: JSON -> PostgreSQL")
    print(f"Modus: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 70)

    with db_session_scope() as session:
        lockout_count = backfill_account_lockouts(session, dry_run)
        audit_count = backfill_audit_logs(session, dry_run)

        if not dry_run:
            session.commit()

    print()
    print("=" * 70)
    print(f"GESAMT:")
    print(f"  AccountLockouts eingefuegt: {lockout_count}")
    print(f"  AuditLog-Eintraege eingefuegt: {audit_count}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Backfill Security-Daten (AccountLockout + AuditLog) in PostgreSQL'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', '-n', action='store_true', help='Nur anzeigen, nichts schreiben')
    group.add_argument('--execute', action='store_true', help='Tatsaechlich in PG schreiben')
    args = parser.parse_args()

    dry_run = args.dry_run

    from app import create_app
    from app.config.production import ProductionConfig
    app = create_app(ProductionConfig)

    with app.app_context():
        backfill_security(dry_run=dry_run)


if __name__ == '__main__':
    main()
