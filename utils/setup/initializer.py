# utils/setup/initializer.py
"""
Einfache System-Initialisierung
"""

import os
import json
from pathlib import Path

def initialize_system():
    """Initialisiert das System mit den notwendigen Dateien und Verzeichnissen"""
    print("Initializing system...")
    
    # Erstelle Verzeichnisse
    directories = [
        "static",
        "data",
        "data/persistent", 
        "data/backups",
        "data/tracking",
        "data/historical"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"Directory ensured: {dir_path}/")
    
    # Erstelle JSON-Dateien mit Defaults
    json_files = {
        "static/scores.json": {},
        "static/champions.json": {},
        "static/user_badges.json": {},
        "static/daily_user_stats.json": {},
        "static/level_history.json": {},
        "static/mvp_badges.json": {},
        "static/user_levels.json": {},
        "data/tracking/daily_metrics.json": {},
        "data/tracking/customer_profiles.json": {}
    }
    
    for file_path, default_content in json_files.items():
        path = Path(file_path)
        if not path.exists():
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(default_content, f, ensure_ascii=False, indent=2)
                print(f"Created: {file_path}")
            except Exception as e:
                print(f"Could not create {file_path}: {e}")
        else:
            print(f"Exists: {file_path}")
    
    # Erstelle leere JSONL-Dateien
    jsonl_files = [
        "data/tracking/bookings.jsonl",
        "data/tracking/outcomes.jsonl"
    ]
    
    for file_path in jsonl_files:
        path = Path(file_path)
        if not path.exists():
            try:
                path.touch()
                print(f"Created: {file_path}")
            except Exception as e:
                print(f"Could not create {file_path}: {e}")
        else:
            print(f"Exists: {file_path}")
    
    print("System initialization completed!")

if __name__ == "__main__":
    initialize_system()