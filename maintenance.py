# -*- coding: utf-8 -*-
"""
Tägliche Maintenance-Aufgaben:
- MVP-Badges prüfen/vergaben
- Level-Snapshots für alle bekannten Nutzer aktualisieren

Kann lokal oder via GitHub Actions aufgerufen werden:
python maintenance.py --daily
"""
import os
import json
from datetime import datetime

from achievement_system import achievement_system
from level_system import level_system
from data_persistence import data_persistence

def get_all_users_from_scores():
    scores = data_persistence.load_scores()
    return list(scores.keys())

def run_daily_maintenance():
    # Badges/MVP
    achievement_system.auto_check_mvp_badges()

    # Levels für alle Nutzer neu berechnen/speichern
    users = get_all_users_from_scores()
    for user in users:
        try:
            level_system.calculate_user_level(user)
        except Exception as e:
            print(f"⚠️ Level update failed for {user}: {e}")

    print(f"✅ Daily maintenance completed at {datetime.now().isoformat()}")

if __name__ == "__main__":
    run_daily_maintenance()


