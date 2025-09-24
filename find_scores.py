#!/usr/bin/env python3
import os
import json

def find_scores_file():
    """Find the scores file on the server"""
    print("Suche nach allen JSON-Dateien mit 'scores'...")

    # Search in common directories
    search_dirs = [
        ".",
        "data",
        "static",
        "src",
        "app",
        "../",
        "/opt/render/project/src",
        "/opt/render/project/src/data",
        "/opt/render/project/src/static"
    ]

    found_files = []

    for base_dir in search_dirs:
        if os.path.exists(base_dir):
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                if 'scores' in data or 'Ladislav' in str(data):
                                    found_files.append(file_path)
                                    print(f"GEFUNDEN: {file_path}")
                                    if 'scores' in data:
                                        print(f"  Benutzer: {list(data.get('scores', {}).keys())}")
                        except:
                            pass

    if not found_files:
        print("Keine Scores-Datei gefunden!")
        print("Alle JSON-Dateien:")
        for base_dir in search_dirs:
            if os.path.exists(base_dir):
                for root, dirs, files in os.walk(base_dir):
                    for file in files:
                        if file.endswith('.json'):
                            print(f"  {os.path.join(root, file)}")

    return found_files

if __name__ == "__main__":
    find_scores_file()