# -*- coding: utf-8 -*-
"""
Backfill CustomerProfile from JSON into PostgreSQL.

Quelle: data/tracking/customer_profiles.json (oder Production-Pfad)
Ziel: customer_profiles Tabelle in PostgreSQL
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')


def backfill_customer_profiles(dry_run=False):
    """Migriere customer_profiles.json nach PostgreSQL."""
    from app.models import init_db, get_db_session
    from app.models.tracking import CustomerProfile

    init_db()
    session = get_db_session()

    # Lade JSON-Daten
    json_paths = [
        project_root / 'data' / 'persistent' / 'customer_profiles.json',
        project_root / 'data' / 'tracking' / 'customer_profiles.json',
        project_root / 'data' / 'static' / 'customer_profiles.json',
    ]

    profiles_data = None
    for path in json_paths:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                profiles_data = json.load(f)
            print(f"Geladen: {path} ({len(profiles_data)} Profile)")
            break

    if not profiles_data:
        print("Keine customer_profiles.json gefunden!")
        return

    # Existierende Profile in PG
    existing = {p.customer for p in session.query(CustomerProfile.customer).all()}
    print(f"Bereits in PostgreSQL: {len(existing)} Profile")

    print()
    print("=" * 70)
    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"BACKFILL CustomerProfiles: JSON -> PostgreSQL ({mode})")
    print("=" * 70)

    inserted = 0
    skipped = 0

    for customer_name, data in profiles_data.items():
        if customer_name in existing:
            skipped += 1
            continue

        profile = CustomerProfile(
            customer=customer_name,
            first_seen=data.get('first_seen'),
            last_seen=data.get('last_seen'),
            total_appointments=data.get('total_appointments', 0),
            completed=data.get('completed', 0),
            no_shows=data.get('no_shows', 0),
            cancelled=data.get('cancelled', 0),
            reliability_score=data.get('reliability_score', 100.0),
            risk_level=data.get('risk_level', 'low'),
        )

        if not dry_run:
            session.merge(profile)

        inserted += 1
        if inserted % 100 == 0:
            print(f"  {inserted} Profile verarbeitet...")

    if not dry_run and inserted > 0:
        session.commit()
        print(f"\nCommit erfolgreich")

    session.close()

    print()
    print("=" * 70)
    print(f"ERGEBNIS: {inserted} neue Profile, {skipped} uebersprungen")
    total = session.query if not dry_run else None
    print("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Backfill CustomerProfiles')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run')
    args = parser.parse_args()

    from app import create_app
    from app.config.production import ProductionConfig
    app = create_app(ProductionConfig)

    with app.app_context():
        backfill_customer_profiles(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
