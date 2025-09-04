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
    
    def save_user_badges(self, badges_data):
        """Speichere User Badges mit Backup"""
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
                
            print(f"✅ User Badges gespeichert: {len(badges_data)} Benutzer")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Speichern der User Badges: {e}")
            return False
    
    def load_daily_user_stats(self):
        """Lade Daily User Stats mit Fallback"""
        try:
            # Versuche persistentes Verzeichnis
            stats_file = self.data_dir / "daily_user_stats.json"
            if stats_file.exists():
                with open(stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            # Fallback: static/ Verzeichnis
            static_stats = self.static_dir / "daily_user_stats.json"
            if static_stats.exists():
                with open(static_stats, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Speichere in persistentes Verzeichnis
                    self.save_daily_user_stats(data)
                    return data
            
            # Fallback: Leere Daten
            return {}
        except Exception as e:
            print(f"❌ Fehler beim Laden der Daily User Stats: {e}")
            return {}
    
    def save_daily_user_stats(self, stats_data):
        """Speichere Daily User Stats mit Backup"""
        try:
            # Speichere in persistentem Verzeichnis
            stats_file = self.data_dir / "daily_user_stats.json"
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
            
            # Backup erstellen
            self._create_backup("daily_user_stats.json", stats_data)
            
            # Auch in static/ für Kompatibilität
            static_stats = self.static_dir / "daily_user_stats.json"
            with open(static_stats, "w", encoding="utf-8") as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Daily User Stats gespeichert: {len(stats_data)} Tage")
            return True
        except Exception as e:
            print(f"❌ Fehler beim Speichern der Daily User Stats: {e}")
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
    
    def auto_cleanup_backups(self):
        """Automatische Bereinigung alter Backups"""
        try:
            for filename in ["scores", "champions", "user_badges", "daily_user_stats"]:
                self._cleanup_old_backups(filename)
            print("✅ Backup-Cleanup abgeschlossen")
        except Exception as e:
            print(f"❌ Backup-Cleanup Fehler: {e}")
    
    def _cleanup_old_backups(self, filename):
        """Bereinige alte Backups für eine bestimmte Datei"""
        try:
            backup_files = list(self.backup_dir.glob(f"{filename}_*.backup"))
            
            # Behalte nur die letzten 10 Backups
            if len(backup_files) > 10:
                # Sortiere nach Erstellungsdatum (älteste zuerst)
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                
                # Lösche die ältesten Backups
                files_to_delete = backup_files[:-10]
                for backup_file in files_to_delete:
                    backup_file.unlink()
                    print(f"🗑️ Altes Backup gelöscht: {backup_file.name}")
        except Exception as e:
            print(f"❌ Fehler beim Bereinigen von {filename} Backups: {e}")
    
    def get_backup_statistics(self):
        """Bekomme Backup-Statistiken"""
        try:
            stats = {}
            for filename in ["scores", "champions", "user_badges", "daily_user_stats"]:
                backup_files = list(self.backup_dir.glob(f"{filename}_*.backup"))
                stats[filename] = {
                    "count": len(backup_files),
                    "latest": None,
                    "oldest": None
                }
                
                if backup_files:
                    # Sortiere nach Erstellungsdatum
                    backup_files.sort(key=lambda x: x.stat().st_mtime)
                    stats[filename]["oldest"] = backup_files[0].name
                    stats[filename]["latest"] = backup_files[-1].name
            
            return stats
        except Exception as e:
            print(f"❌ Fehler beim Abrufen der Backup-Statistiken: {e}")
            return {}
    
    def restore_from_latest_backup(self, filename):
        """Stelle aus dem neuesten Backup wieder her"""
        try:
            backup_files = list(self.backup_dir.glob(f"{filename}_*.backup"))
            if not backup_files:
                return False, "Keine Backups verfügbar"
            
            # Neuestes Backup finden
            latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
            
            # Backup laden
            with open(latest_backup, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Daten wiederherstellen
            target_file = self.data_dir / f"{filename}.json"
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ {filename} aus Backup wiederhergestellt: {latest_backup.name}")
            return True, f"Wiederhergestellt aus {latest_backup.name}"
            
        except Exception as e:
            print(f"❌ Fehler beim Wiederherstellen von {filename}: {e}")
            return False, str(e)
    
    def validate_data_integrity(self):
        """Validiere die Integrität aller Daten"""
        try:
            issues = []
            
            # Prüfe alle Daten-Dateien
            for filename in ["scores", "champions", "user_badges", "daily_user_stats"]:
                file_path = self.data_dir / f"{filename}.json"
                
                if not file_path.exists():
                    issues.append(f"Datei fehlt: {filename}.json")
                    continue
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Basis-Validierung
                    if not isinstance(data, dict):
                        issues.append(f"Ungültiges Format: {filename}.json")
                    
                except json.JSONDecodeError:
                    issues.append(f"Ungültiges JSON: {filename}.json")
                except Exception as e:
                    issues.append(f"Fehler beim Lesen von {filename}.json: {e}")
            
            if issues:
                print(f"⚠️ Datenintegritäts-Probleme gefunden: {len(issues)}")
                for issue in issues:
                    print(f"  - {issue}")
                return False, issues
            else:
                print("✅ Alle Daten validiert - keine Probleme gefunden")
                return True, []
                
        except Exception as e:
            print(f"❌ Fehler bei der Datenvalidierung: {e}")
            return False, [str(e)]
    
    def auto_backup_all(self):
        """Automatisches Backup aller Daten"""
        try:
            files_to_backup = ["scores", "champions", "user_badges", "daily_user_stats"]
            backed_up = []
            
            for filename in files_to_backup:
                try:
                    source_file = self.data_dir / f"{filename}.json"
                    if source_file.exists():
                        self._create_backup(filename, None)  # None = lade automatisch
                        backed_up.append(filename)
                except Exception as e:
                    print(f"❌ Backup-Fehler für {filename}: {e}")
            
            if backed_up:
                print(f"✅ Automatisches Backup erstellt für: {', '.join(backed_up)}")
                # Bereinige alte Backups
                self.auto_cleanup_backups()
            
            return backed_up
            
        except Exception as e:
            print(f"❌ Fehler beim automatischen Backup: {e}")
            return []

# Globale Instanz
data_persistence = DataPersistence()
