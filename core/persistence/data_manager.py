"""
Daten-Persistenz-System für robuste Speicherung von Scores und Badges
Optimiert und ohne Code-Duplikation
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

class DataPersistence:
    def __init__(self):
        self.data_dir = Path("data/persistent")
        self.backup_dir = Path("data/backups")
        self.static_dir = Path("static")
        
        # Erstelle Verzeichnisse
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Unterstützte Datentypen
        self.data_types = ["scores", "user_badges", "champions", "daily_user_stats"]
    
    def _save_data(self, data_type: str, data: dict) -> bool:
        """Generische Speicher-Methode mit Backup"""
        try:
            filename = f"{data_type}.json"
            
            # Speichere in persistentem Verzeichnis
            primary_file = self.data_dir / filename
            with open(primary_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Backup erstellen
            self._create_backup(data_type, data)
            
            # Fallback in static/ für Kompatibilität
            static_file = self.static_dir / filename
            with open(static_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            print(f"❌ Fehler beim Speichern von {data_type}: {e}")
            return False
    
    def _load_data(self, data_type: str) -> dict:
        """Generische Lade-Methode mit Fallback"""
        try:
            filename = f"{data_type}.json"
            
            # Versuche persistentes Verzeichnis
            primary_file = self.data_dir / filename
            if primary_file.exists():
                with open(primary_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            # Fallback: static/ Verzeichnis
            static_file = self.static_dir / filename
            if static_file.exists():
                with open(static_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Migriere zu persistentem Verzeichnis
                    self._save_data(data_type, data)
                    return data
            
            return {}
        except Exception as e:
            print(f"❌ Fehler beim Laden von {data_type}: {e}")
            return {}
    
    # Public API - Clean Interface
    def save_scores(self, data): return self._save_data("scores", data)
    def save_badges(self, data): return self._save_data("user_badges", data)
    def save_champions(self, data): return self._save_data("champions", data)
    def save_daily_user_stats(self, data): return self._save_data("daily_user_stats", data)
    def save_user_badges(self, data): return self._save_data("user_badges", data)  # Alias
    
    def load_scores(self): return self._load_data("scores")
    def load_badges(self): return self._load_data("user_badges")
    def load_champions(self): return self._load_data("champions")
    def load_daily_user_stats(self): return self._load_data("daily_user_stats")
    
    def _create_backup(self, data_type: str, data: dict):
        """Erstelle Backup mit Timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{data_type}_{timestamp}.backup"
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Behalte nur die letzten 10 Backups
            self._cleanup_old_backups(data_type)
        except Exception as e:
            print(f"⚠️ Backup-Fehler für {data_type}: {e}")
    
    def _cleanup_old_backups(self, data_type: str):
        """Bereinige alte Backups für einen Datentyp"""
        try:
            backup_files = list(self.backup_dir.glob(f"{data_type}_*.backup"))
            
            if len(backup_files) > 10:
                # Sortiere nach Erstellungsdatum (älteste zuerst)
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                
                # Lösche die ältesten Backups
                for backup_file in backup_files[:-10]:
                    backup_file.unlink()
        except Exception as e:
            print(f"❌ Backup-Cleanup Fehler für {data_type}: {e}")
    
    def auto_cleanup_backups(self):
        """Automatische Bereinigung aller Backups"""
        try:
            for data_type in self.data_types:
                self._cleanup_old_backups(data_type)
            print("✅ Backup-Cleanup abgeschlossen")
        except Exception as e:
            print(f"❌ Backup-Cleanup Fehler: {e}")
    
    def restore_from_latest_backup(self, data_type: str):
        """Stelle aus dem neuesten Backup wieder her"""
        try:
            backup_files = list(self.backup_dir.glob(f"{data_type}_*.backup"))
            if not backup_files:
                return False, "Keine Backups verfügbar"
            
            # Neuestes Backup finden
            latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
            
            # Backup laden und wiederherstellen
            with open(latest_backup, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Daten wiederherstellen
            if self._save_data(data_type, data):
                return True, f"Wiederhergestellt aus {latest_backup.name}"
            else:
                return False, "Wiederherstellung fehlgeschlagen"
                
        except Exception as e:
            return False, str(e)
    
    def validate_data_integrity(self):
        """Validiere die Integrität aller Daten"""
        issues = []
        
        for data_type in self.data_types:
            file_path = self.data_dir / f"{data_type}.json"
            
            if not file_path.exists():
                issues.append(f"Datei fehlt: {data_type}.json")
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if not isinstance(data, dict):
                    issues.append(f"Ungültiges Format: {data_type}.json")
                    
            except json.JSONDecodeError:
                issues.append(f"Ungültiges JSON: {data_type}.json")
            except Exception as e:
                issues.append(f"Fehler bei {data_type}.json: {e}")
        
        if issues:
            print(f"⚠️ Datenintegritäts-Probleme: {len(issues)}")
            return False, issues
        else:
            print("✅ Alle Daten validiert")
            return True, []
    
    def get_backup_statistics(self):
        """Backup-Statistiken"""
        stats = {}
        for data_type in self.data_types:
            backup_files = list(self.backup_dir.glob(f"{data_type}_*.backup"))
            stats[data_type] = {
                "count": len(backup_files),
                "latest": backup_files[-1].name if backup_files else None
            }
        return stats
    
    def auto_backup_all(self):
        """Automatisches Backup aller Daten"""
        backed_up = []
        for data_type in self.data_types:
            source_file = self.data_dir / f"{data_type}.json"
            if source_file.exists():
                try:
                    data = self._load_data(data_type)
                    self._create_backup(data_type, data)
                    backed_up.append(data_type)
                except Exception as e:
                    print(f"❌ Backup-Fehler für {data_type}: {e}")
        
        if backed_up:
            print(f"✅ Backup erstellt für: {', '.join(backed_up)}")
            self.auto_cleanup_backups()
        
        return backed_up

# Globale Instanz
data_persistence = DataPersistence()