# utils/data_tools/analyzer.py
"""
Einfacher Data Analyzer ohne externe Dependencies
"""

import json
import os
from pathlib import Path
from datetime import datetime

def analyze_availability_data():
    """Analysiert die availability.json ohne pandas"""
    try:
        availability_file = Path("static/availability.json")
        
        if not availability_file.exists():
            print("Keine availability.json gefunden")
            return False
        
        with open(availability_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print("=== AVAILABILITY DATA ANALYSIS ===")
        print(f"Total slots: {len(data)}")
        print(f"File size: {availability_file.stat().st_size} bytes")
        
        # Analysiere Berater
        all_advisors = set()
        slots_by_time = {}
        slots_by_date = {}
        
        for slot_time, advisors in data.items():
            if isinstance(advisors, list):
                all_advisors.update(advisors)
                
                # Extrahiere Zeit und Datum
                try:
                    date_part, time_part = slot_time.split(" ")
                    slots_by_time[time_part] = slots_by_time.get(time_part, 0) + 1
                    slots_by_date[date_part] = slots_by_date.get(date_part, 0) + 1
                except ValueError:
                    continue
        
        print(f"\nUnique advisors: {len(all_advisors)}")
        print("Advisors:", ", ".join(sorted(all_advisors)))
        
        print(f"\nSlots by time:")
        for time, count in sorted(slots_by_time.items()):
            print(f"  {time}: {count} slots")
        
        print(f"\nDate range:")
        dates = sorted(slots_by_date.keys())
        if dates:
            print(f"  From: {dates[0]}")
            print(f"  To: {dates[-1]}")
            print(f"  Total days: {len(dates)}")
        
        # Speichere Analyse
        analysis = {
            "analyzed_at": datetime.now().isoformat(),
            "total_slots": len(data),
            "unique_advisors": len(all_advisors),
            "advisors": list(sorted(all_advisors)),
            "slots_by_time": slots_by_time,
            "date_range": {
                "start": dates[0] if dates else None,
                "end": dates[-1] if dates else None,
                "total_days": len(dates)
            }
        }
        
        analysis_file = Path("data/analysis_simple.json")
        analysis_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        print(f"\nAnalysis saved to: {analysis_file}")
        return True
        
    except Exception as e:
        print(f"Error analyzing data: {e}")
        return False

def analyze_tracking_data():
    """Analysiert Tracking-Daten"""
    try:
        tracking_dir = Path("data/tracking")
        
        if not tracking_dir.exists():
            print("Kein tracking Verzeichnis gefunden")
            return False
        
        print("=== TRACKING DATA ANALYSIS ===")
        
        # Zähle Dateien und Zeilen
        for file_name in ["bookings.jsonl", "outcomes.jsonl"]:
            file_path = tracking_dir / file_name
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = sum(1 for line in f if line.strip())
                size = file_path.stat().st_size
                print(f"{file_name}: {lines} entries ({size} bytes)")
            else:
                print(f"{file_name}: Not found")
        
        # JSON Dateien
        for file_name in ["daily_metrics.json", "customer_profiles.json"]:
            file_path = tracking_dir / file_name
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    size = file_path.stat().st_size
                    if isinstance(data, dict):
                        print(f"{file_name}: {len(data)} entries ({size} bytes)")
                    else:
                        print(f"{file_name}: {size} bytes")
                except json.JSONDecodeError:
                    print(f"{file_name}: Invalid JSON")
            else:
                print(f"{file_name}: Not found")
        
        return True
        
    except Exception as e:
        print(f"Error analyzing tracking data: {e}")
        return False

if __name__ == "__main__":
    print("Running simple data analysis...")
    analyze_availability_data()
    print()
    analyze_tracking_data()