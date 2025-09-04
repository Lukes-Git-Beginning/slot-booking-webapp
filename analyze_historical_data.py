import pandas as pd
import json

def analyze_historical_data():
    try:
        # Lade die Excel-Datei
        df = pd.read_excel('data/historical/T1-Quoten 11.08.25.xlsx')
        
        print("=== HISTORISCHE DATEN ANALYSE ===")
        print(f"Datei: T1-Quoten 11.08.25.xlsx")
        print(f"Zeilen: {len(df)}")
        print(f"Spalten: {len(df.columns)}")
        print()
        
        print("=== SPALTEN ===")
        for i, col in enumerate(df.columns):
            print(f"{i+1}. {col}")
        print()
        
        print("=== ERSTE 5 ZEILEN ===")
        print(df.head().to_string())
        print()
        
        print("=== DATENTYPEN ===")
        print(df.dtypes)
        print()
        
        print("=== BEISPIELDATEN ===")
        # Zeige ein paar Beispieldaten
        for i in range(min(3, len(df))):
            print(f"Zeile {i+1}:")
            for col in df.columns:
                print(f"  {col}: {df.iloc[i][col]}")
            print()
        
        # Speichere die Analyse als JSON
        analysis = {
            "file_info": {
                "filename": "T1-Quoten 11.08.25.xlsx",
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": df.dtypes.to_dict()
            },
            "sample_data": df.head().to_dict('records')
        }
        
        with open('data/historical/analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
        
        print("✅ Analyse gespeichert in data/historical/analysis.json")
        
    except Exception as e:
        print(f"❌ Fehler beim Analysieren: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_historical_data()
