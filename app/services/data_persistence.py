"""
Daten-Persistenz-System für robuste Speicherung von Scores und Badges
"""

import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from app.utils.json_utils import atomic_write_json, atomic_read_json, atomic_update_json

# Logger setup
logger = logging.getLogger(__name__)

class DataPersistence:
    def __init__(self) -> None:
        """
        Primäre Persistenz mit VPS-optimierter Pfad-Logik.

        Pfad-Priorität:
        1. PERSIST_BASE Environment Variable (z.B. /opt/business-hub/data)
        2. VPS Standard: /opt/business-hub/data
        3. Fallback: ./data (lokale Entwicklung)

        Dual-Write: zusätzlich nach static/ für Legacy-Kompatibilität
        """
        persist_base_env = os.getenv("PERSIST_BASE", "")

        # Pfad-Auswahl-Logik
        if persist_base_env:
            # 1. Explizit konfiguriert via Environment Variable
            persist_base = Path(persist_base_env)
        elif Path("/opt/business-hub").exists():
            # 2. VPS Standard-Path
            persist_base = Path("/opt/business-hub/data")
        else:
            # 3. Fallback für lokale Entwicklung
            persist_base = Path("data")

        # Erstelle Verzeichnis falls nicht vorhanden
        if not persist_base.exists():
            persist_base = Path("data")

        self.data_dir: Path = persist_base / "persistent"
        self.backup_dir: Path = persist_base / "backups"
        self.static_dir: Path = Path("static")

        # Erstelle Verzeichnisse
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.static_dir.mkdir(parents=True, exist_ok=True)
    
    def save_scores(self, scores_data: Dict[str, Any]) -> bool:
        """Speichere Scores mit Backup und atomischen Schreibvorgängen"""
        try:
            # Speichere in persistentem Verzeichnis mit atomischen Operationen
            scores_file = str(self.data_dir / "scores.json")
            if not atomic_write_json(scores_file, scores_data):
                return False
            
            # Backup erstellen
            self._create_backup("scores.json", scores_data)
            
            # Auch in static/ für Kompatibilität
            static_scores = str(self.static_dir / "scores.json")
            atomic_write_json(static_scores, scores_data)
                
            logger.info(f"Scores gespeichert: {len(scores_data)} Benutzer")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Scores: {e}")
            return False
    
    def load_scores(self) -> Dict[str, Any]:
        """Lade Scores mit Fallback und atomischen Lesevorgängen"""
        try:
            # Versuche persistentes Verzeichnis
            scores_file = str(self.data_dir / "scores.json")
            data = atomic_read_json(scores_file)
            if data is not None:
                return data
            
            # Fallback: static/ Verzeichnis
            static_scores = str(self.static_dir / "scores.json")
            data = atomic_read_json(static_scores)
            if data is not None:
                # Speichere in persistentes Verzeichnis
                self.save_scores(data)
                return data
            
            # Fallback: Leere Daten
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Laden der Scores: {e}")
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
                
            logger.info(f"Badges gespeichert: {len(badges_data)} Benutzer")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Badges: {e}")
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
            logger.error(f"Fehler beim Laden der Badges: {e}")
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
                
            logger.info(f"Champions gespeichert: {len(champions_data)} Monate")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Champions: {e}")
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
                
            logger.info(f"User Badges gespeichert: {len(badges_data)} Benutzer")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der User Badges: {e}")
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
            logger.error(f"Fehler beim Laden der Daily User Stats: {e}")
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
                
            logger.info(f"Daily User Stats gespeichert: {len(stats_data)} Tage")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Daily User Stats: {e}")
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
            logger.error(f"Fehler beim Laden der Champions: {e}")
            return {}
    
    def _create_backup(self, filename, data):
        """Erstelle Backup mit Timestamp"""
        try:
            # filename inkl. .json erwarten
            if not filename.endswith(".json"):
                filename = f"{filename}.json"

            # Falls keine Daten übergeben wurden, lade aus der aktuellen Datei
            if data is None:
                source_path = self.data_dir / filename
                if source_path.exists():
                    with open(source_path, "r", encoding="utf-8") as sf:
                        data = json.load(sf)
                else:
                    data = {}

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{filename}.{timestamp}.backup"
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Behalte nur die letzten 10 Backups
            self._cleanup_old_backups(filename)
        except Exception as e:
            logger.warning(f"Backup-Fehler für {filename}: {e}")
    
    def auto_cleanup_backups(self):
        """Automatische Bereinigung alter Backups"""
        try:
            for filename in ["scores.json", "champions.json", "user_badges.json", "daily_user_stats.json"]:
                self._cleanup_old_backups(filename)
            logger.info("Backup-Cleanup abgeschlossen")
        except Exception as e:
            logger.error(f"Backup-Cleanup Fehler: {e}")
    
    def _cleanup_old_backups(self, filename):
        """Bereinige alte Backups für eine bestimmte Datei"""
        try:
            # Einheitliches Format: <filename>.json.YYYYmmdd_HHMMSS.backup
            if not filename.endswith(".json"):
                filename = f"{filename}.json"

            backup_files = list(self.backup_dir.glob(f"{filename}.*.backup"))

            # Behalte nur die letzten 10 Backups
            if len(backup_files) > 10:
                # Sortiere nach Erstellungsdatum (älteste zuerst)
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                
                # Lösche die ältesten Backups
                files_to_delete = backup_files[:-10]
                for backup_file in files_to_delete:
                    backup_file.unlink()
                    logger.debug(f"Altes Backup gelöscht: {backup_file.name}")
        except Exception as e:
            logger.error(f"Fehler beim Bereinigen von {filename} Backups: {e}")
    
    def get_backup_statistics(self):
        """Bekomme Backup-Statistiken"""
        try:
            stats = {}
            for filename in ["scores.json", "champions.json", "user_badges.json", "daily_user_stats.json"]:
                backup_files = list(self.backup_dir.glob(f"{filename}.*.backup"))
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
            logger.error(f"Fehler beim Abrufen der Backup-Statistiken: {e}")
            return {}
    
    def restore_from_latest_backup(self, filename):
        """Stelle aus dem neuesten Backup wieder her"""
        try:
            if not filename.endswith(".json"):
                filename = f"{filename}.json"

            backup_files = list(self.backup_dir.glob(f"{filename}.*.backup"))
            if not backup_files:
                return False, "Keine Backups verfügbar"
            
            # Neuestes Backup finden
            latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
            
            # Backup laden
            with open(latest_backup, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Daten wiederherstellen
            target_file = self.data_dir / filename
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{filename} aus Backup wiederhergestellt: {latest_backup.name}")
            return True, f"Wiederhergestellt aus {latest_backup.name}"
            
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen von {filename}: {e}")
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
                logger.warning(f"Datenintegritäts-Probleme gefunden: {len(issues)}")
                for issue in issues:
                    logger.warning(f"  - {issue}")
                return False, issues
            else:
                logger.info("Alle Daten validiert - keine Probleme gefunden")
                return True, []
                
        except Exception as e:
            logger.error(f"Fehler bei der Datenvalidierung: {e}")
            return False, [str(e)]
    
    def auto_backup_all(self):
        """Automatisches Backup aller Daten"""
        try:
            files_to_backup = ["scores.json", "champions.json", "user_badges.json", "daily_user_stats.json"]
            backed_up = []
            
            for filename in files_to_backup:
                try:
                    source_file = self.data_dir / filename
                    if source_file.exists():
                        self._create_backup(filename, None)  # None = lade automatisch
                        backed_up.append(filename)
                except Exception as e:
                    logger.error(f"Backup-Fehler für {filename}: {e}")
            
            if backed_up:
                logger.info(f"Automatisches Backup erstellt für: {', '.join(backed_up)}")
                # Bereinige alte Backups
                self.auto_cleanup_backups()
            
            return backed_up
            
        except Exception as e:
            logger.error(f"Fehler beim automatischen Backup: {e}")
            return []

    def bootstrap_from_static_if_missing(self):
        """Initiale Migration: Falls Dateien im Persist-Verzeichnis fehlen, aus static/ übernehmen."""
        try:
            mapping = {
                "scores.json": (self.save_scores, self.static_dir / "scores.json"),
                "champions.json": (self.save_champions, self.static_dir / "champions.json"),
                "user_badges.json": (self.save_user_badges, self.static_dir / "user_badges.json"),
                "daily_user_stats.json": (self.save_daily_user_stats, self.static_dir / "daily_user_stats.json"),
            }

            migrated_files = []
            for fname, (save_fn, static_path) in mapping.items():
                target_path = self.data_dir / fname
                
                # Migration nur wenn persistent fehlt ODER leer ist, aber static existiert
                should_migrate = False
                if not target_path.exists():
                    should_migrate = True
                    reason = "fehlt"
                elif target_path.stat().st_size == 0 and static_path.exists():
                    should_migrate = True
                    reason = "ist leer"
                elif target_path.exists() and static_path.exists():
                    # Prüfe ob static neuer ist (größere Datei oder neuerer Timestamp)
                    try:
                        static_size = static_path.stat().st_size
                        persist_size = target_path.stat().st_size
                        if static_size > persist_size:
                            should_migrate = True
                            reason = f"static größer ({static_size} vs {persist_size} bytes)"
                    except:
                        pass

                if should_migrate and static_path.exists():
                    try:
                        with open(static_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data:  # Nur migrieren wenn Daten vorhanden
                            save_fn(data)
                            migrated_files.append(f"{fname} ({reason})")
                            logger.info(f"Migriert {fname} aus static/ → persist ({reason})")
                    except Exception as e:
                        logger.warning(f"Konnte {fname} nicht aus static migrieren: {e}")
            
            if migrated_files:
                logger.info(f"Bootstrap-Migration abgeschlossen: {len(migrated_files)} Dateien")
                # Erstelle Backup nach Migration
                self.auto_backup_all()
            else:
                logger.debug("Bootstrap: Keine Migration erforderlich")
                
        except Exception as e:
            logger.error(f"Bootstrap-Fehler: {e}")

    def load_data(self, filename: str, default: Any = None) -> Any:
        """Generische Methode zum Laden von JSON-Daten"""
        try:
            if not filename.endswith('.json'):
                filename += '.json'

            # Versuche persistentes Verzeichnis
            data_file = str(self.data_dir / filename)
            data = atomic_read_json(data_file)
            if data is not None:
                return data

            # Fallback auf static Verzeichnis
            static_file = str(self.static_dir / filename)
            data = atomic_read_json(static_file)
            if data is not None:
                return data

            return default if default is not None else {}

        except Exception as e:
            logger.error(f"Fehler beim Laden von {filename}: {e}")
            return default if default is not None else {}

    def save_data(self, filename: str, data: Any) -> bool:
        """Generische Methode zum Speichern von JSON-Daten"""
        try:
            if not filename.endswith('.json'):
                filename += '.json'

            # Speichere in persistentem Verzeichnis
            data_file = str(self.data_dir / filename)
            if not atomic_write_json(data_file, data):
                return False

            # Backup erstellen
            self._create_backup(filename, data)

            # Auch in static/ für Kompatibilität
            static_file = str(self.static_dir / filename)
            atomic_write_json(static_file, data)

            return True

        except Exception as e:
            logger.error(f"Fehler beim Speichern von {filename}: {e}")
            return False

# Globale Instanz
data_persistence = DataPersistence()
