# utils/data_tools/historical_loader.py
"""
Vereinfachter Historical Data Loader ohne pandas
"""

import json
import os
from pathlib import Path
from datetime import datetime

class SimpleHistoricalLoader:
    def __init__(self):
        self.output_dir = Path("data/historical")
        self.tracking_dir = Path("data/tracking")
        
        # Erstelle Verzeichnisse
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
    
    def create_sample_historical_data(self):
        """Erstellt Beispiel-historische Daten für Tests"""
        try:
            print("Creating sample historical data...")
            
            # Beispiel-Statistiken
            sample_stats = {
                "total_days": 30,
                "date_range": {
                    "start": "2025-08-01",
                    "end": "2025-08-31"
                },
                "total_slots": 150,
                "total_appeared": 120,
                "total_not_appeared": 30,
                "appearance_rate": 0.8,
                "by_weekday": {
                    "Monday": {"total_slots": 25, "total_appeared": 20, "appearance_rate": 0.8},
                    "Tuesday": {"total_slots": 25, "total_appeared": 21, "appearance_rate": 0.84},
                    "Wednesday": {"total_slots": 25, "total_appeared": 19, "appearance_rate": 0.76},
                    "Thursday": {"total_slots": 25, "total_appeared": 20, "appearance_rate": 0.8},
                    "Friday": {"total_slots": 25, "total_appeared": 22, "appearance_rate": 0.88}
                },
                "by_time": {
                    "09:00": {"total_slots": 15, "total_appeared": 12, "appearance_rate": 0.8},
                    "11:00": {"total_slots": 30, "total_appeared": 24, "appearance_rate": 0.8},
                    "14:00": {"total_slots": 40, "total_appeared": 32, "appearance_rate": 0.8},
                    "16:00": {"total_slots": 35, "total_appeared": 28, "appearance_rate": 0.8},
                    "18:00": {"total_slots": 20, "total_appeared": 16, "appearance_rate": 0.8},
                    "20:00": {"total_slots": 10, "total_appeared": 8, "appearance_rate": 0.8}
                }
            }
            
            # Speichere Statistiken
            stats_file = self.output_dir / "historical_stats.json"
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(sample_stats, f, ensure_ascii=False, indent=2)
            
            # Beispiel-Buchungen
            sample_bookings = []
            for i in range(10):
                booking = {
                    "id": f"historical_sample_{i}",
                    "timestamp": f"2025-08-{i+1:02d}T14:00:00",
                    "customer": f"Sample_Customer_{i}",
                    "date": f"2025-08-{i+1:02d}",
                    "time": "14:00",
                    "user": "historical_sample",
                    "source": "sample_data"
                }
                sample_bookings.append(booking)
            
            # Speichere Buchungen
            bookings_file = self.output_dir / "historical_bookings.jsonl"
            with open(bookings_file, "w", encoding="utf-8") as f:
                for booking in sample_bookings:
                    f.write(json.dumps(booking, ensure_ascii=False) + "\n")
            
            # Beispiel-Outcomes
            sample_outcomes = []
            for i in range(10):
                # 80% appeared, 20% not appeared
                outcome_type = "appeared" if i < 8 else "not_appeared"
                outcome = {
                    "id": f"historical_outcome_{i}",
                    "timestamp": f"2025-08-{i+1:02d}T14:00:00",
                    "date": f"2025-08-{i+1:02d}",
                    "time": "14:00",
                    "outcome": outcome_type,
                    "source": "sample_data"
                }
                sample_outcomes.append(outcome)
            
            # Speichere Outcomes
            outcomes_file = self.output_dir / "historical_outcomes.jsonl"
            with open(outcomes_file, "w", encoding="utf-8") as f:
                for outcome in sample_outcomes:
                    f.write(json.dumps(outcome, ensure_ascii=False) + "\n")
            
            print(f"Sample historical data created in {self.output_dir}")
            print(f"- {len(sample_bookings)} sample bookings")
            print(f"- {len(sample_outcomes)} sample outcomes")
            print(f"- Statistics with {sample_stats['appearance_rate']*100:.1f}% appearance rate")
            
            return True
            
        except Exception as e:
            print(f"Error creating sample data: {e}")
            return False
    
    def validate_historical_data(self):
        """Validiert vorhandene historische Daten"""
        try:
            print("Validating historical data...")
            
            files = {
                "stats": self.output_dir / "historical_stats.json",
                "bookings": self.output_dir / "historical_bookings.jsonl",
                "outcomes": self.output_dir / "historical_outcomes.jsonl"
            }
            
            results = {}
            
            for name, file_path in files.items():
                if file_path.exists():
                    try:
                        if name == "stats":
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            results[name] = f"Valid JSON with {len(data)} keys"
                        else:
                            with open(file_path, "r", encoding="utf-8") as f:
                                lines = sum(1 for line in f if line.strip())
                            results[name] = f"Valid JSONL with {lines} entries"
                    except Exception as e:
                        results[name] = f"Error: {e}"
                else:
                    results[name] = "File not found"
            
            for name, result in results.items():
                print(f"  {name}: {result}")
            
            return all("Error" not in result for result in results.values())
            
        except Exception as e:
            print(f"Error validating data: {e}")
            return False

if __name__ == "__main__":
    loader = SimpleHistoricalLoader()
    
    # Erstelle Beispieldaten falls keine vorhanden
    if not loader.validate_historical_data():
        print("\nCreating sample data...")
        loader.create_sample_historical_data()
        loader.validate_historical_data()