# utils/maintenance/tasks.py
"""
Vereinfachte tägliche Maintenance-Aufgaben
"""

import os
import json
from datetime import datetime
from pathlib import Path

def run_daily_maintenance():
    """Führt tägliche Wartungsaufgaben aus"""
    print(f"Starting daily maintenance at {datetime.now().isoformat()}")
    
    tasks_completed = []
    
    # Task 1: Cleanup alte Backups
    try:
        cleanup_old_backups()
        tasks_completed.append("backup_cleanup")
    except Exception as e:
        print(f"Backup cleanup failed: {e}")
    
    # Task 2: Validiere kritische Dateien
    try:
        validate_critical_files()
        tasks_completed.append("file_validation")
    except Exception as e:
        print(f"File validation failed: {e}")
    
    # Task 3: Erstelle Status-Report
    try:
        create_status_report(tasks_completed)
        tasks_completed.append("status_report")
    except Exception as e:
        print(f"Status report failed: {e}")
    
    print(f"Daily maintenance completed. Tasks: {', '.join(tasks_completed)}")
    return len(tasks_completed)

def cleanup_old_backups():
    """Bereinigt alte Backup-Dateien"""
    backup_dir = Path("data/backups")
    
    if not backup_dir.exists():
        print("No backup directory found")
        return
    
    # Lösche Backups älter als 7 Tage
    cutoff_time = datetime.now().timestamp() - (7 * 24 * 60 * 60)
    deleted_count = 0
    
    for backup_file in backup_dir.glob("*.json"):
        if backup_file.stat().st_mtime < cutoff_time:
            try:
                backup_file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Could not delete {backup_file}: {e}")
    
    print(f"Cleaned up {deleted_count} old backup files")

def validate_critical_files():
    """Validiert kritische Systemdateien"""
    critical_files = [
        "static/availability.json",
        "static/scores.json", 
        "static/champions.json",
        "static/user_badges.json"
    ]
    
    validation_results = {}
    
    for file_path in critical_files:
        path = Path(file_path)
        
        if not path.exists():
            # Erstelle fehlende Dateien
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, indent=2)
                validation_results[file_path] = "created"
            except Exception as e:
                validation_results[file_path] = f"creation_failed: {e}"
        else:
            # Validiere JSON
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    json.load(f)
                validation_results[file_path] = "valid"
            except json.JSONDecodeError:
                validation_results[file_path] = "invalid_json"
            except Exception as e:
                validation_results[file_path] = f"error: {e}"
    
    print("File validation results:")
    for file_path, result in validation_results.items():
        print(f"  {file_path}: {result}")

def create_status_report(completed_tasks):
    """Erstellt einen einfachen Status-Report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "completed_tasks": completed_tasks,
        "system_status": "operational",
        "task_count": len(completed_tasks)
    }
    
    report_file = Path("data/maintenance_report.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"Status report saved to {report_file}")

if __name__ == "__main__":
    run_daily_maintenance()