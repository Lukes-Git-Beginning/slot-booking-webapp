# -*- coding: utf-8 -*-
"""
Fix Usernames in Data Files
Migriert alte/inkonsistente Usernames zu vollständigen Namen in allen Daten-Dateien
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
import sys

# Füge parent directory zum Python path hinzu
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.helpers import normalize_data_usernames, normalize_username


# Dateien die migriert werden sollen
DATA_DIR = Path("data/persistent")
FILES_TO_MIGRATE = [
    "scores.json",
    "user_badges.json",
    "daily_user_stats.json",
]


def create_backup(file_path: Path) -> str:
    """Erstellt Backup der Datei"""
    if not file_path.exists():
        return None

    backup_dir = DATA_DIR / "backups" / "username_fix"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{file_path.stem}_{timestamp}.json"

    shutil.copy2(file_path, backup_path)
    print(f"  ✅ Backup erstellt: {backup_path}")
    return str(backup_path)


def migrate_file(file_path: Path, dry_run: bool = False) -> dict:
    """Migriert eine JSON-Datei"""
    if not file_path.exists():
        return {"status": "skipped", "reason": "Datei nicht gefunden"}

    print(f"\n📄 Migriere: {file_path.name}")

    # Backup erstellen
    if not dry_run:
        backup_path = create_backup(file_path)

    # JSON laden
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {"status": "error", "reason": f"JSON-Fehler: {e}"}

    # Alte Keys ausgeben
    if isinstance(data, dict):
        old_keys = list(data.keys())
        print(f"  🔍 Alte Usernames: {', '.join(old_keys[:10])}")

    # Migrieren
    migrated_data = normalize_data_usernames(data)

    # Neue Keys ausgeben
    if isinstance(migrated_data, dict):
        new_keys = list(migrated_data.keys())
        print(f"  ✨ Neue Usernames: {', '.join(new_keys[:10])}")

    # Speichern
    if not dry_run:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(migrated_data, f, ensure_ascii=False, indent=2)
        print(f"  ✅ Gespeichert")
    else:
        print(f"  🔍 DRY RUN - Keine Änderungen gespeichert")

    return {
        "status": "success",
        "old_count": len(old_keys) if isinstance(data, dict) else 0,
        "new_count": len(new_keys) if isinstance(migrated_data, dict) else 0,
    }


def main(dry_run: bool = False):
    """Hauptfunktion"""
    print("=" * 60)
    print("🔄 USERNAME NORMALISIERUNG IN DATEN-DATEIEN")
    print("=" * 60)
    print(f"Mode: {'DRY RUN (keine Änderungen)' if dry_run else 'LIVE (Dateien werden geändert)'}")
    print()

    results = {}

    for filename in FILES_TO_MIGRATE:
        file_path = DATA_DIR / filename
        result = migrate_file(file_path, dry_run=dry_run)
        results[filename] = result

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 60)

    success_count = sum(1 for r in results.values() if r["status"] == "success")
    skipped_count = sum(1 for r in results.values() if r["status"] == "skipped")
    error_count = sum(1 for r in results.values() if r["status"] == "error")

    print(f"✅ Erfolgreich migriert: {success_count}")
    print(f"⏭️  Übersprungen: {skipped_count}")
    print(f"❌ Fehler: {error_count}")

    if error_count > 0:
        print("\n❌ Dateien mit Fehlern:")
        for filename, result in results.items():
            if result["status"] == "error":
                print(f"  - {filename}: {result['reason']}")

    print("\n" + "=" * 60)
    if not dry_run:
        print("✅ Migration abgeschlossen!")
        print(f"💾 Backups: {DATA_DIR}/backups/username_fix/")
    else:
        print("🔍 DRY RUN abgeschlossen - keine Änderungen vorgenommen")
        print("➡️  Führe erneut ohne --dry-run aus, um Änderungen zu speichern")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    import io

    # Fix Windows encoding BEFORE any output
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if not dry_run:
        print("\n⚠️  WARNUNG: Dies wird Dateien ändern!")
        print("   Backups werden automatisch erstellt.")
        response = input("\n   Fortfahren? (ja/nein): ")
        if response.lower() not in ["ja", "yes", "y", "j"]:
            print("❌ Abgebrochen")
            sys.exit(0)

    main(dry_run=dry_run)
