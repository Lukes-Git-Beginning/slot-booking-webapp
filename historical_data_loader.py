# -*- coding: utf-8 -*-
"""
Historical Data Loader für Slot Booking Webapp
- Lädt historische Daten aus Excel-Datei
- Konvertiert sie in das bestehende Tracking-Format
- Integriert sie mit dem aktuellen Dashboard
"""

import pandas as pd
import json
import os
import numpy as np
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

TZ = pytz.timezone("Europe/Berlin")

class HistoricalDataLoader:
    def __init__(self):
        self.historical_file = "data/historical/T1-Quoten 11.08.25.xlsx"
        self.output_dir = "data/historical"
        self.tracking_dir = "data/tracking"
        
        # Stelle sicher, dass die Verzeichnisse existieren
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.tracking_dir, exist_ok=True)
    
    def load_historical_data(self):
        """Lädt die historischen Excel-Daten"""
        try:
            print("📊 Lade historische Daten...")
            df = pd.read_excel(self.historical_file)
            
            # Bereinige die Daten
            df = self._clean_data(df)
            
            print(f"✅ {len(df)} historische Datensätze geladen")
            return df
            
        except Exception as e:
            print(f"❌ Fehler beim Laden der historischen Daten: {e}")
            return None
    
    def _clean_data(self, df):
        """Bereinigt die Excel-Daten - nur relevante Spalten und Zeilen"""
        # Entferne Zeilen ohne Datum
        df = df.dropna(subset=['Datum'])
        
        # Konvertiere Datum zu datetime
        df['Datum'] = pd.to_datetime(df['Datum'])
        
        # Fülle NaN-Werte mit 0 für numerische Spalten
        numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
        df[numeric_columns] = df[numeric_columns].fillna(0)
        
        # Fülle NaN-Werte mit leeren Strings für Text-Spalten
        text_columns = df.select_dtypes(include=['object']).columns
        df[text_columns] = df[text_columns].fillna('')
        
        return df
    
    def convert_to_tracking_format(self, df):
        """Konvertiert Excel-Daten in das Tracking-Format - nur relevante Daten"""
        tracking_data = []
        
        for _, row in df.iterrows():
            # Erstelle einen Datensatz für jeden Zeitslot
            date = row['Datum'].strftime('%Y-%m-%d')
            time_slot = f"{int(row['Uhrzeit']):02d}:00"
            
            # Erstelle einen Buchungsdatensatz nur wenn Kunden gelegt wurden
            if row['Gelegt'] > 0:
                booking_record = {
                    "id": f"historical_{date}_{time_slot}",
                    "timestamp": row['Datum'].isoformat(),
                    "customer": f"Historischer_Kunde_{date}_{time_slot}",
                    "date": date,
                    "time": time_slot,
                    "weekday": row['Wochentag'],
                    "week_number": row['Datum'].isocalendar()[1],
                    "user": "historical_data",
                    "potential_type": "historical",
                    "color_id": "2",  # Standard grün
                    "description_length": 0,
                    "has_description": False,
                    "booking_lead_time": 0,
                    "booked_at_hour": row['Datum'].hour,
                    "booked_on_weekday": row['Wochentag'],
                    "source": "historical_excel"
                }
                tracking_data.append(("booking", booking_record))
            
            # Erstelle Outcome-Datensätze basierend auf der neuen Klassifizierung
            outcomes = self._extract_outcomes_new_classification(row)
            for outcome in outcomes:
                tracking_data.append(("outcome", outcome))
        
        return tracking_data
    
    def _extract_outcomes_new_classification(self, row):
        """Extrahiert Outcomes basierend auf der neuen Klassifizierung"""
        outcomes = []
        date = row['Datum'].strftime('%Y-%m-%d')
        time_slot = f"{int(row['Uhrzeit']):02d}:00"
        
        # AUFGETAUCHT: Bestätigt erschienen + Unbestätigt erschienen
        total_appeared = 0
        if row['Bestätigt erschienen'] > 0:
            total_appeared += row['Bestätigt erschienen']
        if row['Unbestätigt erschienen'] > 0:
            total_appeared += row['Unbestätigt erschienen']
        
        if total_appeared > 0:
            outcomes.append({
                "id": f"historical_appeared_{date}_{time_slot}",
                "timestamp": row['Datum'].isoformat(),
                "date": date,
                "time": time_slot,
                "outcome": "appeared",
                "count": int(total_appeared),
                "type": "all",
                "source": "historical_excel"
            })
        
        # NICHT AUFGETAUCHT: Alle anderen Kategorien
        total_not_appeared = 0
        
        # Verschoben (bestätigt + unbestätigt)
        if row['Bestätigt verschoben'] > 0:
            total_not_appeared += row['Bestätigt verschoben']
        if row['Unbestätigt verschoben'] > 0:
            total_not_appeared += row['Unbestätigt verschoben']
        
        # Abgesagt (bestätigt + unbestätigt)
        if row['Bestätigt abgesagt'] > 0:
            total_not_appeared += row['Bestätigt abgesagt']
        if row['Unbestätigt abgesagt'] > 0:
            total_not_appeared += row['Unbestätigt abgesagt']
        
        # Nicht erschienen (bestätigt + unbestätigt)
        if row['Bestätigt nicht erschienen'] > 0:
            total_not_appeared += row['Bestätigt nicht erschienen']
        if row['Unbestätigt nicht erschienen'] > 0:
            total_not_appeared += row['Unbestätigt nicht erschienen']
        
        if total_not_appeared > 0:
            outcomes.append({
                "id": f"historical_not_appeared_{date}_{time_slot}",
                "timestamp": row['Datum'].isoformat(),
                "date": date,
                "time": time_slot,
                "outcome": "not_appeared",
                "count": int(total_not_appeared),
                "type": "all",
                "source": "historical_excel"
            })
        
        return outcomes
    
    def generate_summary_statistics(self, df):
        """Generiert Zusammenfassungsstatistiken mit der neuen Klassifizierung"""
        # Berechne die neuen Metriken
        total_gelegt = df['Gelegt'].sum()
        
        # Aufgetaucht
        total_appeared = df['Bestätigt erschienen'].sum() + df['Unbestätigt erschienen'].sum()
        
        # Nicht aufgetaucht
        total_not_appeared = (
            df['Bestätigt verschoben'].sum() + df['Unbestätigt verschoben'].sum() +
            df['Bestätigt abgesagt'].sum() + df['Unbestätigt abgesagt'].sum() +
            df['Bestätigt nicht erschienen'].sum() + df['Unbestätigt nicht erschienen'].sum()
        )
        
        # Auftauchquote
        appearance_rate = total_appeared / total_gelegt if total_gelegt > 0 else 0
        
        stats = {
            "total_days": len(df['Datum'].dt.date.unique()),
            "date_range": {
                "start": df['Datum'].min().strftime('%Y-%m-%d'),
                "end": df['Datum'].max().strftime('%Y-%m-%d')
            },
            "total_slots": int(total_gelegt),
            "total_appeared": int(total_appeared),
            "total_not_appeared": int(total_not_appeared),
            "appearance_rate": float(appearance_rate),
            "by_weekday": self._get_weekday_stats_new(df),
            "by_time": self._get_time_stats_new(df)
        }
        
        return stats
    
    def _get_weekday_stats_new(self, df):
        """Berechnet Statistiken nach Wochentag mit neuer Klassifizierung"""
        weekday_stats = {}
        for weekday in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            day_data = df[df['Wochentag'] == weekday]
            if len(day_data) > 0:
                total_gelegt = day_data['Gelegt'].sum()
                total_appeared = day_data['Bestätigt erschienen'].sum() + day_data['Unbestätigt erschienen'].sum()
                appearance_rate = total_appeared / total_gelegt if total_gelegt > 0 else 0
                
                weekday_stats[weekday] = {
                    "total_slots": int(total_gelegt),
                    "total_appeared": int(total_appeared),
                    "appearance_rate": float(appearance_rate)
                }
        return weekday_stats
    
    def _get_time_stats_new(self, df):
        """Berechnet Statistiken nach Uhrzeit mit neuer Klassifizierung"""
        time_stats = {}
        for time_slot in sorted(df['Uhrzeit'].unique()):
            time_data = df[df['Uhrzeit'] == time_slot]
            if len(time_data) > 0:
                total_gelegt = time_data['Gelegt'].sum()
                total_appeared = time_data['Bestätigt erschienen'].sum() + time_data['Unbestätigt erschienen'].sum()
                appearance_rate = total_appeared / total_gelegt if total_gelegt > 0 else 0
                
                time_stats[f"{int(time_slot):02d}:00"] = {
                    "total_slots": int(total_gelegt),
                    "total_appeared": int(total_appeared),
                    "appearance_rate": float(appearance_rate)
                }
        return time_stats
    
    def save_historical_data(self, tracking_data, stats):
        """Speichert die konvertierten Daten"""
        try:
            # Speichere Tracking-Daten
            bookings = [record for record_type, record in tracking_data if record_type == "booking"]
            outcomes = [record for record_type, record in tracking_data if record_type == "outcome"]
            
            # Speichere Buchungen
            with open(os.path.join(self.output_dir, "historical_bookings.jsonl"), "w", encoding="utf-8") as f:
                for booking in bookings:
                    f.write(json.dumps(booking, ensure_ascii=False) + "\n")
            
            # Speichere Outcomes
            with open(os.path.join(self.output_dir, "historical_outcomes.jsonl"), "w", encoding="utf-8") as f:
                for outcome in outcomes:
                    f.write(json.dumps(outcome, ensure_ascii=False) + "\n")
            
            # Speichere Statistiken
            with open(os.path.join(self.output_dir, "historical_stats.json"), "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"✅ Historische Daten gespeichert:")
            print(f"   - {len(bookings)} Buchungen")
            print(f"   - {len(outcomes)} Outcomes")
            print(f"   - Statistiken")
            print(f"   - Auftauchquote: {stats['appearance_rate']:.4f} ({stats['appearance_rate']*100:.2f}%)")
            
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Speichern: {e}")
            return False
    
    def process_historical_data(self):
        """Hauptfunktion: Verarbeitet alle historischen Daten"""
        print("🔄 Verarbeite historische Daten...")
        
        # Lade Daten
        df = self.load_historical_data()
        if df is None:
            return False
        
        # Konvertiere zu Tracking-Format
        tracking_data = self.convert_to_tracking_format(df)
        
        # Generiere Statistiken
        stats = self.generate_summary_statistics(df)
        
        # Speichere Daten
        success = self.save_historical_data(tracking_data, stats)
        
        if success:
            print("✅ Historische Daten erfolgreich verarbeitet!")
            return True
        else:
            print("❌ Fehler bei der Verarbeitung")
            return False

if __name__ == "__main__":
    loader = HistoricalDataLoader()
    loader.process_historical_data()
