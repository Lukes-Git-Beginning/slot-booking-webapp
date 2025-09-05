#!/usr/bin/env python3
"""
Initialisierung des Daten-Persistenz-Systems
Sorgt dafür, dass alle relevanten JSON-Dateien und Verzeichnisse auf dem
persistenten Volume vorhanden sind und bootstrappt fehlende Daten sicher.

Idempotent: Kann bei jedem Start ausgeführt werden.
"""

import os
import json
import shutil
from pathlib import Path
from data_persistence import DataPersistence

def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _ensure_file_json(path: Path, default_obj):
    if not path.exists():
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default_obj, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Konnte Datei nicht erstellen: {path} → {e}")


def initialize_persistence():
    """Initialisiere das Persistenz-System auf dem Volume (idempotent)."""

    print("🔄 Initialisiere Daten-Persistenz-System…")

    # Verzeichnis-Struktur sicherstellen
    static_dir = Path("static")
    data_dir = Path("data")
    persist_dir = data_dir / "persistent"
    backups_dir = data_dir / "backups"
    tracking_dir = data_dir / "tracking"
    _ensure_dir(static_dir)
    _ensure_dir(data_dir)
    _ensure_dir(persist_dir)
    _ensure_dir(backups_dir)
    _ensure_dir(tracking_dir)

    # Dateien, die in static/ leben und von Komponenten direkt genutzt werden
    static_json_files = [
        "scores.json",
        "user_badges.json",
        "champions.json",
        "daily_user_stats.json",
        "level_history.json",
        "mvp_badges.json",
        "user_levels.json",
    ]

    for name in static_json_files:
        _ensure_file_json(static_dir / name, {})

    # Persistenz-Instanz
    persistence = DataPersistence()

    # Bootstrap für persistente Kern-Dateien: Nur anlegen, wenn noch nicht vorhanden
    try:
        scores_persist = persist_dir / "scores.json"
        if not scores_persist.exists():
            # Quelle bevorzugt: static/scores.json → sonst {}
            src = static_dir / "scores.json"
            try:
                with open(src, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
            persistence.save_scores(data)
        print("✅ Scores bereit")
    except Exception as e:
        print(f"❌ Scores Bootstrap Fehler: {e}")

    try:
        champions_persist = persist_dir / "champions.json"
        if not champions_persist.exists():
            src = static_dir / "champions.json"
            try:
                with open(src, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
            persistence.save_champions(data)
        print("✅ Champions bereit")
    except Exception as e:
        print(f"❌ Champions Bootstrap Fehler: {e}")

    try:
        badges_persist = persist_dir / "user_badges.json"
        if not badges_persist.exists():
            src = static_dir / "user_badges.json"
            try:
                with open(src, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
            persistence.save_user_badges(data)
        print("✅ User Badges bereit")
    except Exception as e:
        print(f"❌ User Badges Bootstrap Fehler: {e}")

    try:
        stats_persist = persist_dir / "daily_user_stats.json"
        if not stats_persist.exists():
            src = static_dir / "daily_user_stats.json"
            try:
                with open(src, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
            persistence.save_daily_user_stats(data)
        print("✅ Daily User Stats bereit")
    except Exception as e:
        print(f"❌ Daily User Stats Bootstrap Fehler: {e}")

    # Tracking-Dateien optional initialisieren (falls gewünscht leer anlegen)
    for track_name in ["bookings.jsonl", "outcomes.jsonl", "customer_profiles.json", "daily_metrics.json", "latest_weekly_report.json"]:
        track_path = tracking_dir / track_name
        if not track_path.exists():
            try:
                # jsonl als leere Datei, json als {} bzw. [] sinnvoll
                if track_path.suffix == ".jsonl":
                    track_path.touch()
                else:
                    with open(track_path, "w", encoding="utf-8") as f:
                        json.dump({}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"⚠️ Konnte Tracking-Datei nicht erstellen: {track_path.name} → {e}")

    print("🎉 Persistenz-System initialisiert!")

if __name__ == "__main__":
    initialize_persistence()
