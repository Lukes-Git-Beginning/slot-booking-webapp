# -*- coding: utf-8 -*-
"""
Backfill User-Management data from JSON files into PostgreSQL (User table).

Sources:
  - data/persistent/user_registry.json  -> User (roles, admin_overrides, deleted_users)
  - data/persistent/user_passwords.json -> User.password_hash
  - data/persistent/login_history.json  -> User.last_login (neuester erfolgreicher Login)

Usage:
  python scripts/backfill_users_pg.py --dry-run
  python scripts/backfill_users_pg.py --execute
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')


def backfill_users(session, dry_run=False):
    from app.models.user import User as UserModel

    persist_base = os.getenv("PERSIST_BASE", "data")
    registry_file = Path(persist_base) / "persistent" / "user_registry.json"
    passwords_file = Path(persist_base) / "persistent" / "user_passwords.json"
    login_history_file = Path(persist_base) / "persistent" / "login_history.json"

    # --- Load source data ---
    registry = {}
    passwords = {}
    login_history = {}

    if registry_file.exists():
        with open(registry_file, "r", encoding="utf-8") as f:
            registry = json.load(f)
        print(f"Loaded user_registry.json")
    else:
        print(f"WARNING: {registry_file} not found")

    if passwords_file.exists():
        with open(passwords_file, "r", encoding="utf-8") as f:
            passwords = json.load(f)
        print(f"Loaded user_passwords.json ({len(passwords)} users)")
    else:
        print(f"WARNING: {passwords_file} not found")

    if login_history_file.exists():
        with open(login_history_file, "r", encoding="utf-8") as f:
            login_history = json.load(f)
        print(f"Loaded login_history.json ({len(login_history)} users)")
    else:
        print(f"WARNING: {login_history_file} not found, last_login will not be set")

    # --- Build combined user set ---
    added_users = registry.get('added_users', {})
    deleted_users = set(registry.get('deleted_users', []))
    admin_overrides = registry.get('admin_overrides', {})
    roles = registry.get('roles', {})

    all_usernames = set(passwords.keys()) | set(added_users.keys())

    print(f"\nTotal users to process: {len(all_usernames)}")
    print(f"Deleted (will be is_active=False): {len(deleted_users)}")

    inserted = 0
    updated = 0

    for username in sorted(all_usernames):
        is_active = username not in deleted_users
        is_admin = bool(admin_overrides.get(username, False))
        role = roles.get(username, 'user')
        password_hash = passwords.get(username)

        # Determine last_login from login_history
        last_login = None
        user_logins = login_history.get(username, [])
        for entry in user_logins:
            if entry.get('success', True):
                ts = entry.get('timestamp')
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts)
                        # Store as naive datetime (no tzinfo) to match PG column
                        last_login = dt.replace(tzinfo=None)
                    except Exception:
                        pass
                break  # Neuester erfolgreicher Login (Liste ist neueste zuerst)

        existing = session.query(UserModel).filter_by(username=username).first()

        if existing:
            existing.is_active = is_active
            existing.is_admin = is_admin
            existing.role = role
            if password_hash:
                existing.password_hash = password_hash
            if last_login and existing.last_login is None:
                existing.last_login = last_login
            updated += 1
            print(f"  UPDATE {username}: active={is_active}, admin={is_admin}, role={role}")
        else:
            row = UserModel(
                username=username,
                password_hash=password_hash,
                is_admin=is_admin,
                is_active=is_active,
                role=role,
                last_login=last_login,
            )
            session.add(row)
            inserted += 1
            print(f"  INSERT {username}: active={is_active}, admin={is_admin}, role={role}")

    print(f"\nSummary: {inserted} to insert, {updated} to update")

    if not dry_run:
        session.commit()
        print(f"Committed: {inserted} inserted, {updated} updated User rows")
    else:
        session.rollback()
        print(f"DRY RUN: no changes written to database")

    return inserted, updated


def main():
    if '--execute' not in sys.argv and '--dry-run' not in sys.argv:
        print("Usage: python scripts/backfill_users_pg.py [--dry-run | --execute]")
        print("  --dry-run   Show what would be done, no DB writes")
        print("  --execute   Actually write to PostgreSQL")
        sys.exit(1)

    dry_run = '--execute' not in sys.argv

    if dry_run:
        print("=== DRY RUN mode — no changes will be written ===\n")
    else:
        print("=== EXECUTE mode — writing to PostgreSQL ===\n")

    from app import create_app
    app = create_app()

    with app.app_context():
        from app.utils.db_utils import db_session_scope
        with db_session_scope() as session:
            backfill_users(session, dry_run=dry_run)


if __name__ == "__main__":
    main()
