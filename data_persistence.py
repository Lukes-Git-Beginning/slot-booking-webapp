"""
Daten-Persistenz-System für robuste Speicherung von Scores und Badges
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
    
    def save_scores(self, scores_data):
        """Speichere Scores mit Backup"""
        try:
            # Speichere in persistentem Verzeichnis
            scores_file = self.data_dir / "scores.json"
            with open(scores_file, "w", encoding="utf-8") as f:
                json.dump(scores_data, f, indent=2, ensure_ascii=False)
            
            # Backup erstellen
            self._create_backup("scores.json", scores_data)
            
            # Auch in static/ für Kompatibilität
            static_scores = self.static_dir / "scores.json"
            with open(static_scores, "w", encoding="utf-8") as f:
                json.dump(scores_data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Scores gespeichert: {len(scores_data)} Benutzer")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Speichern der Scores: {e}")
            return False
    
    def load_scores(self):
        """Lade Scores mit Fallback"""
        try:
            # Versuche persistentes Verzeichnis
            scores_file = self.data_dir / "scores.json"
            if scores_file.exists():
                with open(scores_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            # Fallback: static/ Verzeichnis
            static_scores = self.static_dir / "scores.json"
            if static_scores.exists():
                with open(static_scores, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Speichere in persistentes Verzeichnis
                    self.save_scores(data)
                    return data
            
            # Fallback: Leere Daten
            return {}
        except Exception as e:
            print(f"❌ Fehler beim Laden der Scores: {e}")
            return {}
    
    def save_badges(self, badges_data):
        """Speichere Badges mit Backup"""
        try:
            # Speichere in persistentem Verzeichnis
            badges_file = self.data_dir / "user_badges.json"
            with open(badges_file, "w", encoding="utf-8") as f:
                json.dump(badges_data, f, indent=2, ensure_ascii=False)
            
            # Backup erstellen
            self._create_backup("user_badges.json", badges_data)
            
            # Auch in static/ für Kompatibilität
            static_badges = self.static_dir / "user_badges.json"
            with open(static_badges, "w", encoding="utf-8") as f:
                json.dump(badges_data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Badges gespeichert: {len(badges_data)} Benutzer")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Speichern der Badges: {e}")
            return False
    
    def load_badges(self):
        """Lade Badges mit Fallback"""
        try:
            # Versuche persistentes Verzeichnis
            badges_file = self.data_dir / "user_badges.json"
            if badges_file.exists():
                with open(badges_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            # Fallback: static/ Verzeichnis
            static_badges = self.static_dir / "user_badges.json"
            if static_badges.exists():
                with open(static_badges, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Speichere in persistentes Verzeichnis
                    self.save_badges(data)
                    return data
            
            # Fallback: Leere Daten
            return {}
        except Exception as e:
            print(f"❌ Fehler beim Laden der Badges: {e}")
            return {}
    
    def save_champions(self, champions_data):
        """Speichere Champions mit Backup"""
        try:
            # Speichere in persistentem Verzeichnis
            champions_file = self.data_dir / "champions.json"
            with open(champions_file, "w", encoding="utf-8") as f:
                json.dump(champions_data, f, indent=2, ensure_ascii=False)
            
            # Backup erstellen
            self._create_backup("champions.json", champions_data)
            
            # Auch in static/ für Kompatibilität
            static_champions = self.static_dir / "champions.json"
            with open(static_champions, "w", encoding="utf-8") as f:
                json.dump(champions_data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Champions gespeichert: {len(champions_data)} Monate")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Speichern der Champions: {e}")
            return False
    
    def load_champions(self):
        """Lade Champions mit Fallback"""
        try:
            # Versuche persistentes Verzeichnis
            champions_file = self.data_dir / "champions.json"
            if champions_file.exists():
                with open(champions_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            # Fallback: static/ Verzeichnis
            static_champions = self.static_dir / "champions.json"
            if static_champions.exists():
                with open(static_champions, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Speichere in persistentes Verzeichnis
                    self.save_champions(data)
                    return data
            
            # Fallback: Leere Daten
            return {}
        except Exception as e:
            print(f"❌ Fehler beim Laden der Champions: {e}")
            return {}
    
    def _create_backup(self, filename, data):
        """Erstelle Backup mit Timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{filename}.{timestamp}.backup"
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Behalte nur die letzten 5 Backups
            self._cleanup_old_backups(filename)
        except Exception as e:
            print(f"⚠️ Backup-Fehler für {filename}: {e}")
    
    def _cleanup_old_backups(self, filename):
        """Lösche alte Backups (behalte nur die letzten 5)"""
        try:
            pattern = f"{filename}.*.backup"
            backups = list(self.backup_dir.glob(pattern))
            backups.sort(reverse=True)
            
            # Lösche alte Backups (behalte nur die letzten 5)
            for backup in backups[5:]:
                backup.unlink()
        except Exception as e:
            print(f"⚠️ Backup-Cleanup-Fehler: {e}")
    
    def restore_from_backup(self, filename):
        """Stelle Daten aus dem neuesten Backup wieder her"""
        try:
            pattern = f"{filename}.*.backup"
            backups = list(self.backup_dir.glob(pattern))
            if not backups:
                print(f"❌ Keine Backups für {filename} gefunden")
                return False
            
            # Nehme das neueste Backup
            latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
            
            with open(latest_backup, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Stelle wieder her
            if filename == "scores.json":
                self.save_scores(data)
            elif filename == "user_badges.json":
                self.save_badges(data)
            elif filename == "champions.json":
                self.save_champions(data)
            
            print(f"✅ {filename} aus Backup wiederhergestellt: {latest_backup.name}")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Wiederherstellen von {filename}: {e}")
            return False

# Globale Instanz
data_persistence = DataPersistence()
