# -*- coding: utf-8 -*-
"""
Backfill DailyMetrics from BookingOutcome (PG) and JSON into PostgreSQL.

Primaere Quelle: BookingOutcome PG-Tabelle (2783+ Records, 129+ Tage)
Sekundaere Quelle: daily_metrics.json (fuer Tage ohne BookingOutcome)
"""
import sys
import os
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')


def backfill_from_booking_outcomes(session, existing_dates, dry_run=False):
    """Aggregiere BookingOutcome-Records nach Datum und erstelle DailyMetrics."""
    from app.models.booking import BookingOutcome
    from app.models.tracking import DailyMetrics
    from sqlalchemy import func

    print()
    print("=" * 70)
    print("PHASE 1: BookingOutcome -> DailyMetrics")
    print("=" * 70)

    # Alle BookingOutcome-Records laden, gruppiert nach Datum
    rows = session.query(
        BookingOutcome.date,
        BookingOutcome.outcome,
        func.count(BookingOutcome.id)
    ).group_by(
        BookingOutcome.date,
        BookingOutcome.outcome
    ).order_by(BookingOutcome.date).all()

    # Aggregiere nach Datum
    date_outcomes = defaultdict(lambda: {
        "total_slots": 0, "completed": 0, "no_shows": 0,
        "ghosts": 0, "cancelled": 0, "rescheduled": 0, "overhang": 0
    })
    for date_val, outcome, count in rows:
        d = date_outcomes[str(date_val)]
        d["total_slots"] += count
        if outcome == "completed":
            d["completed"] += count
        elif outcome == "no_show":
            d["no_shows"] += count
        elif outcome == "ghost":
            d["ghosts"] += count
        elif outcome == "cancelled":
            d["cancelled"] += count
        elif outcome == "rescheduled":
            d["rescheduled"] += count
        elif outcome == "overhang":
            d["overhang"] += count

    print(f"BookingOutcome: {len(date_outcomes)} Tage mit Daten")

    # by_hour und by_user aus Detail-Records befuellen
    detail_rows = session.query(
        BookingOutcome.date,
        BookingOutcome.time,
        BookingOutcome.outcome,
        BookingOutcome.consultant
    ).order_by(BookingOutcome.date).all()

    date_by_hour = defaultdict(lambda: defaultdict(lambda: {
        "total": 0, "no_shows": 0, "ghosts": 0, "completed": 0,
        "cancelled": 0, "rescheduled": 0, "overhang": 0
    }))
    date_by_user = defaultdict(lambda: defaultdict(lambda: {
        "total": 0, "no_shows": 0, "ghosts": 0, "completed": 0
    }))

    for date_val, time_str, outcome, consultant in detail_rows:
        ds = str(date_val)
        # by_hour
        hour = time_str[:2] + ":00" if time_str else "00:00"
        date_by_hour[ds][hour]["total"] += 1
        if outcome in ("no_show",):
            date_by_hour[ds][hour]["no_shows"] += 1
        elif outcome == "ghost":
            date_by_hour[ds][hour]["ghosts"] += 1
        elif outcome == "completed":
            date_by_hour[ds][hour]["completed"] += 1
        elif outcome == "cancelled":
            date_by_hour[ds][hour]["cancelled"] += 1
        elif outcome == "rescheduled":
            date_by_hour[ds][hour]["rescheduled"] += 1
        elif outcome == "overhang":
            date_by_hour[ds][hour]["overhang"] += 1

        # by_user
        user = consultant or "Unbekannt"
        date_by_user[ds][user]["total"] += 1
        if outcome == "no_show":
            date_by_user[ds][user]["no_shows"] += 1
        elif outcome == "ghost":
            date_by_user[ds][user]["ghosts"] += 1
        elif outcome == "completed":
            date_by_user[ds][user]["completed"] += 1

    inserted = 0
    skipped = 0

    for date_str in sorted(date_outcomes.keys()):
        if date_str in existing_dates:
            skipped += 1
            continue

        m = date_outcomes[date_str]
        total = m["total_slots"]
        if total == 0:
            continue

        no_show_rate = round((m["no_shows"] / total) * 100, 1)
        ghost_rate = round((m["ghosts"] / total) * 100, 1)
        completion_rate = round((m["completed"] / total) * 100, 1)
        cancellation_rate = round((m["cancelled"] / total) * 100, 1)

        by_hour_data = dict(date_by_hour.get(date_str, {}))
        by_user_data = dict(date_by_user.get(date_str, {}))

        if not dry_run:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            dm = DailyMetrics(
                date=date_obj,
                total_slots=total,
                completed=m["completed"],
                no_shows=m["no_shows"],
                ghosts=m["ghosts"],
                cancelled=m["cancelled"],
                rescheduled=m["rescheduled"],
                overhang=m["overhang"],
                no_show_rate=no_show_rate,
                ghost_rate=ghost_rate,
                completion_rate=completion_rate,
                cancellation_rate=cancellation_rate,
                by_hour=json.dumps(by_hour_data) if by_hour_data else None,
                by_user=json.dumps(by_user_data) if by_user_data else None,
                by_potential=None,
                calculated_at=datetime.now()
            )
            session.add(dm)
            existing_dates.add(date_str)

        print(f"[+] {date_str} - {total} Slots, {m['completed']} Completed, {m['no_shows']} No-Shows, {m['ghosts']} Ghosts")
        inserted += 1

    print(f"\nEingefuegt: {inserted}, Uebersprungen: {skipped}")
    return inserted


def backfill_from_json(session, existing_dates, dry_run=False):
    """Backfill fehlende Tage aus JSON (sekundaere Quelle)."""
    from app.core.extensions import tracking_system
    from app.models.tracking import DailyMetrics

    json_path = getattr(tracking_system, 'metrics_file', None)
    if not json_path or not os.path.exists(json_path):
        print(f"JSON nicht gefunden: {json_path}")
        return 0

    print()
    print("=" * 70)
    print("PHASE 2: JSON -> DailyMetrics (fehlende Tage)")
    print("=" * 70)

    with open(json_path, "r", encoding="utf-8") as f:
        all_metrics = json.load(f)

    # Pre-backfill mergen
    pre_path = json_path + ".pre-backfill"
    if os.path.exists(pre_path):
        with open(pre_path, "r", encoding="utf-8") as f:
            pre = json.load(f)
        for k, v in pre.items():
            if k not in all_metrics and isinstance(v, dict):
                all_metrics[k] = v

    inserted = 0
    for date_str, metrics in sorted(all_metrics.items()):
        if not isinstance(metrics, dict):
            continue
        total = metrics.get("total_slots", 0)
        if total == 0 or date_str in existing_dates:
            continue

        if not dry_run:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            dm = DailyMetrics(
                date=date_obj,
                total_slots=total,
                completed=metrics.get("completed", 0),
                no_shows=metrics.get("no_shows", 0),
                ghosts=metrics.get("ghosts", 0),
                cancelled=metrics.get("cancelled", 0),
                rescheduled=metrics.get("rescheduled", 0),
                overhang=metrics.get("overhang", 0),
                no_show_rate=round((metrics.get("no_shows", 0) / total) * 100, 1),
                ghost_rate=round((metrics.get("ghosts", 0) / total) * 100, 1),
                completion_rate=round((metrics.get("completed", 0) / total) * 100, 1),
                cancellation_rate=round((metrics.get("cancelled", 0) / total) * 100, 1),
                by_hour=json.dumps(metrics.get("by_hour", {})) if metrics.get("by_hour") else None,
                by_user=json.dumps(metrics.get("by_user", {})) if metrics.get("by_user") else None,
                by_potential=json.dumps(metrics.get("by_potential", {})) if metrics.get("by_potential") else None,
                calculated_at=datetime.now()
            )
            session.add(dm)
            existing_dates.add(date_str)

        print(f"[+] {date_str} - {total} Slots (from JSON)")
        inserted += 1

    print(f"\nEingefuegt: {inserted}")
    return inserted


def backfill_daily_metrics(dry_run=False):
    """Backfill DailyMetrics from BookingOutcome + JSON."""
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    from app.models.tracking import DailyMetrics
    from app.utils.db_utils import db_session_scope

    print("=" * 70)
    print("BACKFILL DailyMetrics: BookingOutcome + JSON -> PostgreSQL")
    print(f"Modus: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 70)

    with db_session_scope() as session:
        existing_dates = set()
        for row in session.query(DailyMetrics.date).all():
            existing_dates.add(str(row.date))
        print(f"\nPG DailyMetrics hat bereits {len(existing_dates)} Tage")

        # Phase 1: BookingOutcome (primaere Quelle)
        bo_count = backfill_from_booking_outcomes(session, existing_dates, dry_run)

        # Phase 2: JSON (sekundaere Quelle fuer fehlende Tage)
        json_count = backfill_from_json(session, existing_dates, dry_run)

        if not dry_run:
            session.commit()

    print()
    print("=" * 70)
    print(f"GESAMT: {bo_count + json_count} neue DailyMetrics eingefuegt")
    print(f"  BookingOutcome: {bo_count}")
    print(f"  JSON:           {json_count}")
    print(f"  Bereits in PG:  {len(existing_dates) - bo_count - json_count}")
    print("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Backfill DailyMetrics')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run')
    args = parser.parse_args()

    from app import create_app
    from app.config.production import ProductionConfig
    app = create_app(ProductionConfig)

    with app.app_context():
        backfill_daily_metrics(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
