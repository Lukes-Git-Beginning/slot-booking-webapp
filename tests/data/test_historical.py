import json
import os
from pathlib import Path

def test_historical_data():
    """Test historische Daten ohne pandas dependency"""
    try:
        print("Testing Historical Data...")
        
        # Prüfe ob die Dateien existieren
        historical_dir = Path("data/historical")
        historical_stats_file = historical_dir / "historical_stats.json"
        historical_bookings_file = historical_dir / "historical_bookings.jsonl"
        historical_outcomes_file = historical_dir / "historical_outcomes.jsonl"
        
        files_exist = {
            "stats": historical_stats_file.exists(),
            "bookings": historical_bookings_file.exists(),
            "outcomes": historical_outcomes_file.exists()
        }
        
        print("File Status:")
        for file_type, exists in files_exist.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {file_type}")
        
        # Lade und zeige Statistiken (falls vorhanden)
        if files_exist["stats"]:
            with open(historical_stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
            
            print("\nHistorical Statistics:")
            date_range = stats.get('date_range', {})
            print(f"   - Date Range: {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}")
            print(f"   - Total Days: {stats.get('total_days', 'N/A')}")
            print(f"   - Total Slots: {stats.get('total_slots', 'N/A')}")
            print(f"   - Total Appeared: {stats.get('total_appeared', 'N/A')}")
            
            appearance_rate = stats.get('appearance_rate', 0)
            print(f"   - Appearance Rate: {appearance_rate * 100:.1f}%")
        else:
            print("\nNo historical stats found - this is OK for new installations")
        
        # Zähle Buchungen und Outcomes (falls vorhanden)
        if files_exist["bookings"]:
            try:
                with open(historical_bookings_file, "r", encoding="utf-8") as f:
                    bookings = sum(1 for line in f if line.strip())
                print(f"   - Bookings: {bookings}")
            except Exception as e:
                print(f"   - Bookings: Error reading file ({e})")
        
        if files_exist["outcomes"]:
            try:
                with open(historical_outcomes_file, "r", encoding="utf-8") as f:
                    outcomes = sum(1 for line in f if line.strip())
                print(f"   - Outcomes: {outcomes}")
            except Exception as e:
                print(f"   - Outcomes: Error reading file ({e})")
        
        print("\nHistorical data test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing historical data: {e}")
        return False

if __name__ == "__main__":
    test_historical_data()