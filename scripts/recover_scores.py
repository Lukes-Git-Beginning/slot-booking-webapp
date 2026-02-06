#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Score Recovery Script
Rekonstruiert fehlende Dez 2025, Jan 2026 und Feb 2-5 Scores
aus Level-History, Coin-Logs und PostgreSQL Bookings.

Usage:
    python3 scripts/recover_scores.py              # DRY-RUN (nur anzeigen)
    python3 scripts/recover_scores.py --apply       # Scores wirklich schreiben
"""

import os
import sys
import json
import re
import gzip
import subprocess
from collections import defaultdict
from datetime import datetime

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)

DRY_RUN = "--apply" not in sys.argv

# XP per badge rarity (same as level_system.py)
RARITY_XP = {
    "common": 50, "uncommon": 100, "rare": 250,
    "epic": 500, "legendary": 1000, "mythic": 2500
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_coin_logs():
    """Extract 'Added X coins to user Y (total: Z)' from rotated logs."""
    entries = []  # [(timestamp, user, points, total_coins)]
    pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - booking_system - INFO - "
        r"Added (\d+) coins to user (\S+) \(total: (\d+)\)"
    )

    log_dir = "/var/log/business-hub"
    if not os.path.exists(log_dir):
        log_dir = "logs"

    # Read compressed logs (oldest first)
    for i in range(14, 1, -1):
        gz_path = os.path.join(log_dir, f"error.log.{i}.gz")
        if os.path.exists(gz_path):
            with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = pattern.search(line)
                    if m:
                        entries.append((m.group(1), m.group(3), int(m.group(2)), int(m.group(4))))

    # Read error.log.1 (uncompressed)
    log1 = os.path.join(log_dir, "error.log.1")
    if os.path.exists(log1):
        with open(log1, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    entries.append((m.group(1), m.group(3), int(m.group(2)), int(m.group(4))))

    # Read current error.log
    log0 = os.path.join(log_dir, "error.log")
    if os.path.exists(log0):
        with open(log0, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    entries.append((m.group(1), m.group(3), int(m.group(2)), int(m.group(4))))

    entries.sort(key=lambda x: x[0])
    return entries


def get_pg_booking_counts():
    """Get booking counts per user per month from PostgreSQL."""
    counts = defaultdict(lambda: defaultdict(int))
    try:
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("""
            SELECT username,
                   to_char(date, 'YYYY-MM') as month,
                   count(*)
            FROM bookings
            WHERE date >= '2025-12-01' AND date < '2026-02-06'
            GROUP BY username, to_char(date, 'YYYY-MM')
            ORDER BY username, month
        """)
        for row in cur.fetchall():
            counts[row[0]][row[1]] = row[2]
        conn.close()
    except Exception as e:
        print(f"  WARNING: PostgreSQL not available: {e}")
    return counts


def main():
    print("=" * 70)
    print("SCORE RECOVERY SCRIPT")
    print("=" * 70)
    if DRY_RUN:
        print("MODE: DRY-RUN (keine Aenderungen, nur Anzeige)")
        print("      Nutze --apply um Scores zu schreiben")
    else:
        print("MODE: LIVE - Scores werden geschrieben!")
    print()

    # 1. Load current data
    scores = load_json("data/persistent/scores.json")
    level_history = load_json("static/level_history.json")
    badges = load_json("data/persistent/user_badges.json")

    # 2. Extract coin logs
    print("Extrahiere Coin-Logs...")
    coin_entries = extract_coin_logs()
    print(f"  {len(coin_entries)} Eintraege gefunden")

    # Group coin entries by user and month
    coin_by_user_month = defaultdict(lambda: defaultdict(int))
    for ts, user, points, total in coin_entries:
        month = ts[:7]  # "YYYY-MM"
        coin_by_user_month[user][month] += points

    # 3. Get booking counts from PostgreSQL
    print("Lade Buchungen aus PostgreSQL...")
    pg_booking_counts = get_pg_booking_counts()

    # 4. Calculate missing scores for each user
    print()
    print("=" * 70)
    print("ANALYSE PRO USER")
    print("=" * 70)

    recovery_data = {}  # {user: {month: points}}

    for user in sorted(set(list(level_history.keys()) + list(scores.keys()))):
        user_lh = level_history.get(user, {})
        user_scores = scores.get(user, {})
        user_badges = badges.get(user, {})
        current_total = sum(user_scores.values())

        # Calculate badge XP
        badge_xp = sum(
            RARITY_XP.get(b.get("rarity", "common"), 50)
            for b in user_badges.get("badges", [])
        )

        # Find peak XP from level history
        level_ups = user_lh.get("level_ups", [])
        peak_xp = max(
            [lu.get("new_xp", 0) for lu in level_ups] + [user_lh.get("current_xp", 0)]
        )

        if peak_xp <= 0:
            continue

        # Back-calculate minimum total points
        min_total = (peak_xp - badge_xp) / 10.0

        # Check which months are missing
        missing_months = []
        for m in ["2025-12", "2026-01"]:
            if m not in user_scores:
                missing_months.append(m)

        # Check Feb 2-5 shortfall
        feb_from_logs = coin_by_user_month.get(user, {}).get("2026-02", 0)
        feb_in_scores = user_scores.get("2026-02", 0)
        feb_shortfall = max(0, feb_from_logs - feb_in_scores)

        total_missing = min_total - current_total + feb_shortfall
        if total_missing <= 2 and not missing_months:
            continue

        print(f"\n--- {user} ---")
        print(f"  Aktuell: {user_scores}")
        print(f"  Aktuell Total: {current_total}")
        print(f"  Peak XP: {peak_xp}, Badge XP: {badge_xp}")
        print(f"  Min Total (Level-History): {min_total:.0f}")
        print(f"  Fehlende Monate: {missing_months or 'keine'}")

        # Get coin data for this user from logs
        user_coin_months = coin_by_user_month.get(user, {})
        print(f"  Coin-Log Daten: {dict(user_coin_months)}")

        # Get booking counts
        user_bookings = pg_booking_counts.get(user, {})
        print(f"  PG Buchungen: {dict(user_bookings)}")

        # Reconstruct missing months
        user_recovery = {}

        # Step A: Use coin logs for months where we have data
        for month in ["2025-12", "2026-01"]:
            if month in user_coin_months and month not in user_scores:
                user_recovery[month] = user_coin_months[month]
                print(f"  -> {month}: {user_coin_months[month]} pts (aus Coin-Logs)")

        # Step B: For months without coin logs, distribute remaining missing points
        known_from_logs = sum(user_recovery.values())
        remaining_missing = max(0, min_total - current_total - known_from_logs)

        months_needing_estimate = [
            m for m in missing_months if m not in user_recovery
        ]

        if months_needing_estimate and remaining_missing > 0:
            # Distribute by booking count ratio
            total_bookings = sum(user_bookings.get(m, 1) for m in months_needing_estimate)
            for month in months_needing_estimate:
                bookings = user_bookings.get(month, 1)
                estimated = int(remaining_missing * bookings / max(total_bookings, 1))
                user_recovery[month] = estimated
                print(f"  -> {month}: {estimated} pts (geschaetzt, {bookings} Buchungen)")

        # Step C: Fix Feb shortfall
        if feb_shortfall > 0 and "2026-02" not in user_recovery:
            # Add the shortfall to existing Feb score
            user_recovery["2026-02"] = feb_in_scores + feb_shortfall
            print(f"  -> 2026-02: {feb_in_scores} + {feb_shortfall} = {feb_in_scores + feb_shortfall} pts (Feb-Korrektur)")

        # Step D: Check if we still need more points after estimates
        # (for points earned after last level-up but before data loss)
        estimated_total = current_total + sum(
            v - user_scores.get(k, 0) for k, v in user_recovery.items()
        )
        if estimated_total < min_total:
            # Add extra points to the latest missing month proportionally
            shortfall = int(min_total - estimated_total)
            if "2026-01" in user_recovery:
                user_recovery["2026-01"] += shortfall
                print(f"  -> 2026-01: +{shortfall} pts (Level-History Korrektur)")
            elif missing_months:
                last_m = missing_months[-1]
                user_recovery[last_m] = user_recovery.get(last_m, 0) + shortfall
                print(f"  -> {last_m}: +{shortfall} pts (Level-History Korrektur)")

        if user_recovery:
            recovery_data[user] = user_recovery
            new_total = current_total + sum(
                v - user_scores.get(k, 0) for k, v in user_recovery.items()
            )
            print(f"  ERGEBNIS: Total {current_total} -> {new_total}")

    # 5. Summary
    print()
    print("=" * 70)
    print("ZUSAMMENFASSUNG")
    print("=" * 70)

    if not recovery_data:
        print("Keine Recovery noetig!")
        return

    for user, months in sorted(recovery_data.items()):
        old_total = sum(scores.get(user, {}).values())
        delta = sum(v - scores.get(user, {}).get(k, 0) for k, v in months.items())
        print(f"  {user}: +{delta} pts ({months})")

    # 6. Apply if not dry-run
    if DRY_RUN:
        print()
        print("DRY-RUN: Keine Aenderungen vorgenommen.")
        print("Nutze --apply um die Scores zu schreiben.")
        return

    print()
    print("SCHREIBE SCORES...")

    # Merge recovery into current scores
    for user, months in recovery_data.items():
        if user not in scores:
            scores[user] = {}
        for month, points in months.items():
            scores[user][month] = points

    # Write to JSON files
    scores_file = "data/persistent/scores.json"
    static_file = "static/scores.json"

    for path in [scores_file, static_file]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
        print(f"  Geschrieben: {path}")

    # Write to PostgreSQL
    try:
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()

        for user, months in recovery_data.items():
            for month, points in months.items():
                cur.execute(
                    "SELECT id FROM scores WHERE username = %s AND month = %s",
                    (user, month)
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        "UPDATE scores SET points = %s, updated_at = NOW() WHERE username = %s AND month = %s",
                        (points, user, month)
                    )
                else:
                    cur.execute(
                        "INSERT INTO scores (username, month, points, bookings_count, created_at, updated_at) "
                        "VALUES (%s, %s, %s, 0, NOW(), NOW())",
                        (user, month, points)
                    )

        conn.commit()
        conn.close()
        print("  PostgreSQL aktualisiert")
    except Exception as e:
        print(f"  WARNING: PostgreSQL write failed: {e}")

    print()
    print("RECOVERY ABGESCHLOSSEN!")
    print("Bitte Service neustarten: systemctl restart business-hub")


if __name__ == "__main__":
    main()
