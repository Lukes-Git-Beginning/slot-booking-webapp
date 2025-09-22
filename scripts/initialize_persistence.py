#!/usr/bin/env python3
"""
Initialisierung des Daten-Persistenz-Systems
Kopiert bestehende Daten in die neuen persistenten Verzeichnisse
"""

import os
import json
import shutil
from pathlib import Path
from data_persistence import DataPersistence

def initialize_persistence():
    """Initialisiere das Persistenz-System mit bestehenden Daten"""
    
    print("🔄 Initialisiere Daten-Persistenz-System...")
    
    # Erstelle Persistenz-Instanz
    persistence = DataPersistence()
    
    # Kopiere Scores
    try:
        with open("static/scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
        persistence.save_scores(scores)
        print("✅ Scores kopiert")
    except Exception as e:
        print(f"❌ Fehler beim Kopieren der Scores: {e}")
    
    # Kopiere Champions
    try:
        with open("static/champions.json", "r", encoding="utf-8") as f:
            champions = json.load(f)
        persistence.save_champions(champions)
        print("✅ Champions kopiert")
    except Exception as e:
        print(f"❌ Fehler beim Kopieren der Champions: {e}")
    
    # Kopiere User Badges
    try:
        with open("static/user_badges.json", "r", encoding="utf-8") as f:
            badges = json.load(f)
        persistence.save_user_badges(badges)
        print("✅ User Badges kopiert")
    except Exception as e:
        print(f"❌ Fehler beim Kopieren der User Badges: {e}")
    
    # Kopiere Daily User Stats
    try:
        with open("static/daily_user_stats.json", "r", encoding="utf-8") as f:
            stats = json.load(f)
        persistence.save_daily_user_stats(stats)
        print("✅ Daily User Stats kopiert")
    except Exception as e:
        print(f"❌ Fehler beim Kopieren der Daily User Stats: {e}")
    
    print("🎉 Persistenz-System initialisiert!")

if __name__ == "__main__":
    initialize_persistence()
