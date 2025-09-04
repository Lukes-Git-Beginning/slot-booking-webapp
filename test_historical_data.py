import json
import os

def test_historical_data():
    try:
        print("🔄 Teste historische Daten...")
        
        # Prüfe ob die Dateien existieren
        historical_stats_file = "data/historical/historical_stats.json"
        historical_bookings_file = "data/historical/historical_bookings.jsonl"
        historical_outcomes_file = "data/historical/historical_outcomes.jsonl"
        
        files_exist = {
            "stats": os.path.exists(historical_stats_file),
            "bookings": os.path.exists(historical_bookings_file),
            "outcomes": os.path.exists(historical_outcomes_file)
        }
        
        print("📁 Datei-Status:")
        for file_type, exists in files_exist.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {file_type}")
        
        # Lade und zeige Statistiken
        if files_exist["stats"]:
            with open(historical_stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
            
            print("\n📊 Historische Statistiken:")
            print(f"   - Datumsbereich: {stats.get('date_range', {}).get('start', 'N/A')} bis {stats.get('date_range', {}).get('end', 'N/A')}")
            print(f"   - Tage: {stats.get('total_days', 'N/A')}")
            print(f"   - Termine gelegt: {stats.get('total_slots', 'N/A')}")
            print(f"   - Erschienen: {stats.get('total_appeared', 'N/A')}")
            print(f"   - Erfolgreich: {stats.get('total_success', 'N/A')}")
            print(f"   - Durchschn. Auftauchquote: {stats.get('averages', {}).get('appearance_rate', 0) * 100:.1f}%")
            print(f"   - Durchschn. Erfolgsquote: {stats.get('averages', {}).get('success_rate', 0) * 100:.1f}%")
        
        # Zähle Buchungen und Outcomes
        if files_exist["bookings"]:
            with open(historical_bookings_file, "r", encoding="utf-8") as f:
                bookings = sum(1 for line in f if line.strip())
            print(f"   - Buchungen: {bookings}")
        
        if files_exist["outcomes"]:
            with open(historical_outcomes_file, "r", encoding="utf-8") as f:
                outcomes = sum(1 for line in f if line.strip())
            print(f"   - Outcomes: {outcomes}")
        
        # Zeige beste Zeiten
        if files_exist["stats"] and "by_time" in stats:
            print("\n⏰ Beste Zeiten (Erfolgsquote):")
            time_stats = stats["by_time"]
            sorted_times = sorted(time_stats.items(), 
                                key=lambda x: x[1]["success_rate"], 
                                reverse=True)
            
            for i, (time, data) in enumerate(sorted_times[:3]):
                print(f"   {i+1}. {time}: {data['success_rate'] * 100:.1f}%")
        
        # Zeige Wochentag-Analyse
        if files_exist["stats"] and "by_weekday" in stats:
            print("\n📅 Wochentag-Analyse (Erfolgsquote):")
            weekday_stats = stats["by_weekday"]
            sorted_weekdays = sorted(weekday_stats.items(), 
                                   key=lambda x: x[1]["success_rate"], 
                                   reverse=True)
            
            for weekday, data in sorted_weekdays:
                print(f"   - {weekday}: {data['success_rate'] * 100:.1f}%")
        
        print("\n✅ Historische Daten erfolgreich getestet!")
        return True
        
    except Exception as e:
        print(f"❌ Fehler beim Testen: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_historical_data()
