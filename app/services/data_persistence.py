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

# PostgreSQL dual-write support
USE_POSTGRES = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

try:
    from app.models.gamification import Score as ScoreModel, UserBadge as UserBadgeModel, Champion as ChampionModel
    from app.models.user import UserStats as UserStatsModel
    from app.models.base import get_db_session
    POSTGRES_AVAILABLE = True
except ImportError:
    logger.warning("PostgreSQL models not available for data_persistence, using JSON-only mode")
    POSTGRES_AVAILABLE = False
    USE_POSTGRES = False

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
        """Speichere Scores (Dual-Write: PostgreSQL + JSON)"""
        # 1. PostgreSQL write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    for username, months in scores_data.items():
                        if not isinstance(months, dict):
                            continue
                        for month, points in months.items():
                            points_int = int(points) if isinstance(points, (int, float, str)) else 0
                            existing = session.query(ScoreModel).filter_by(
                                username=username, month=month
                            ).first()
                            if existing:
                                existing.points = points_int
                            else:
                                new_row = ScoreModel(
                                    username=username,
                                    month=month,
                                    points=points_int,
                                    bookings_count=0
                                )
                                session.add(new_row)
                    session.commit()
                    logger.debug("Scores saved to PostgreSQL")
                except Exception as e:
                    session.rollback()
                    logger.error(f"PostgreSQL scores save failed: {e}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"PostgreSQL connection failed for scores: {e}")

        # 2. JSON write (always, as backup)
        try:
            scores_file = str(self.data_dir / "scores.json")
            if not atomic_write_json(scores_file, scores_data):
                return False

            self._create_backup("scores.json", scores_data)

            static_scores = str(self.static_dir / "scores.json")
            atomic_write_json(static_scores, scores_data)

            logger.info(f"Scores gespeichert: {len(scores_data)} Benutzer")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Scores: {e}")
            return False
    
    def load_scores(self) -> Dict[str, Any]:
        """Lade Scores (PostgreSQL-first, JSON-Fallback)"""
        # 1. PostgreSQL-first
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    rows = session.query(ScoreModel).all()
                    if rows:
                        data = {}
                        for row in rows:
                            if row.username not in data:
                                data[row.username] = {}
                            data[row.username][row.month] = row.points
                        logger.debug(f"Loaded scores from PostgreSQL ({len(data)} users)")
                        return self._normalize_usernames_in_data(data)
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"PostgreSQL scores load failed: {e}, falling back to JSON")

        # 2. JSON-Fallback
        try:
            scores_file = str(self.data_dir / "scores.json")
            data = atomic_read_json(scores_file)
            if data is not None:
                data = self._normalize_usernames_in_data(data)
                return data

            static_scores = str(self.static_dir / "scores.json")
            data = atomic_read_json(static_scores)
            if data is not None:
                data = self._normalize_usernames_in_data(data)
                self.save_scores(data)
                return data

            return {}
        except Exception as e:
            logger.error(f"Fehler beim Laden der Scores: {e}")
            return {}
    
    def save_badges(self, badges_data):
        """Speichere Badges (Dual-Write: PostgreSQL + JSON)"""
        # 1. PostgreSQL write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    for username, user_data in badges_data.items():
                        badges_list = user_data.get("badges", []) if isinstance(user_data, dict) else []
                        for badge in badges_list:
                            badge_id = badge.get("id", "")
                            if not badge_id:
                                continue
                            # Parse earned_date
                            earned_date = None
                            earned_date_str = badge.get("earned_date")
                            if earned_date_str:
                                try:
                                    earned_date = datetime.fromisoformat(earned_date_str)
                                except (ValueError, TypeError):
                                    try:
                                        earned_date = datetime.strptime(earned_date_str, "%Y-%m-%d %H:%M:%S")
                                    except (ValueError, TypeError):
                                        earned_date = datetime.utcnow()
                            else:
                                earned_date = datetime.utcnow()

                            existing = session.query(UserBadgeModel).filter_by(
                                username=username, badge_id=badge_id
                            ).first()
                            if existing:
                                existing.name = badge.get("name", "")
                                existing.description = badge.get("description", "")
                                existing.emoji = badge.get("emoji", "")
                                existing.rarity = badge.get("rarity", "common")
                                existing.category = badge.get("category", "special")
                                existing.color = badge.get("color", "#3b82f6")
                                existing.earned_date = earned_date
                            else:
                                new_row = UserBadgeModel(
                                    username=username,
                                    badge_id=badge_id,
                                    name=badge.get("name", ""),
                                    description=badge.get("description", ""),
                                    emoji=badge.get("emoji", ""),
                                    rarity=badge.get("rarity", "common"),
                                    category=badge.get("category", "special"),
                                    color=badge.get("color", "#3b82f6"),
                                    earned_date=earned_date
                                )
                                session.add(new_row)
                    session.commit()
                    logger.debug("Badges saved to PostgreSQL")
                except Exception as e:
                    session.rollback()
                    logger.error(f"PostgreSQL badges save failed: {e}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"PostgreSQL connection failed for badges: {e}")

        # 2. JSON write (always, as backup)
        try:
            badges_file = self.data_dir / "user_badges.json"
            with open(badges_file, "w", encoding="utf-8") as f:
                json.dump(badges_data, f, indent=2, ensure_ascii=False)

            self._create_backup("user_badges.json", badges_data)

            static_badges = self.static_dir / "user_badges.json"
            with open(static_badges, "w", encoding="utf-8") as f:
                json.dump(badges_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Badges gespeichert: {len(badges_data)} Benutzer")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Badges: {e}")
            return False
    
    def load_badges(self):
        """Lade Badges (PostgreSQL-first, JSON-Fallback)"""
        # 1. PostgreSQL-first
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    rows = session.query(UserBadgeModel).all()
                    if rows:
                        data = {}
                        for row in rows:
                            if row.username not in data:
                                data[row.username] = {
                                    "badges": [],
                                    "earned_dates": {},
                                    "total_badges": 0
                                }
                            earned_str = row.earned_date.strftime("%Y-%m-%d %H:%M:%S") if row.earned_date else None
                            data[row.username]["badges"].append({
                                "id": row.badge_id,
                                "name": row.name,
                                "description": row.description,
                                "emoji": row.emoji or "",
                                "rarity": row.rarity or "common",
                                "category": row.category or "special",
                                "earned_date": earned_str,
                                "color": row.color or "#3b82f6"
                            })
                            data[row.username]["earned_dates"][row.badge_id] = earned_str
                        for username in data:
                            data[username]["total_badges"] = len(data[username]["badges"])
                        logger.debug(f"Loaded badges from PostgreSQL ({len(data)} users)")
                        return self._normalize_usernames_in_data(data)
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"PostgreSQL badges load failed: {e}, falling back to JSON")

        # 2. JSON-Fallback
        try:
            badges_file = self.data_dir / "user_badges.json"
            if badges_file.exists():
                with open(badges_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return self._normalize_usernames_in_data(data)

            static_badges = self.static_dir / "user_badges.json"
            if static_badges.exists():
                with open(static_badges, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data = self._normalize_usernames_in_data(data)
                    self.save_badges(data)
                    return data

            return {}
        except Exception as e:
            logger.error(f"Fehler beim Laden der Badges: {e}")
            return {}
    
    def save_champions(self, champions_data):
        """Speichere Champions (Dual-Write: PostgreSQL + JSON)"""
        # 1. PostgreSQL write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    for period, champ_data in champions_data.items():
                        if not isinstance(champ_data, dict):
                            continue
                        username = champ_data.get("user", "")
                        if not username:
                            continue
                        # Bestimme period_type aus Format
                        period_type = "weekly" if "-W" in period or (len(period.split("-")) == 2 and len(period.split("-")[1]) <= 2 and int(period.split("-")[1]) > 12) else "monthly"

                        existing = session.query(ChampionModel).filter_by(
                            period=period, rank=1
                        ).first()
                        if existing:
                            existing.username = username
                            existing.total_points = champ_data.get("score", 0)
                            existing.stats_data = {k: v for k, v in champ_data.items() if k not in ("user", "score")}
                        else:
                            new_row = ChampionModel(
                                period=period,
                                period_type=period_type,
                                username=username,
                                rank=1,
                                total_points=champ_data.get("score", 0),
                                total_bookings=0,
                                show_rate=0.0,
                                reward_coins=0,
                                stats_data={k: v for k, v in champ_data.items() if k not in ("user", "score")}
                            )
                            session.add(new_row)
                    session.commit()
                    logger.debug("Champions saved to PostgreSQL")
                except Exception as e:
                    session.rollback()
                    logger.error(f"PostgreSQL champions save failed: {e}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"PostgreSQL connection failed for champions: {e}")

        # 2. JSON write (always, as backup)
        try:
            champions_file = self.data_dir / "champions.json"
            with open(champions_file, "w", encoding="utf-8") as f:
                json.dump(champions_data, f, indent=2, ensure_ascii=False)

            self._create_backup("champions.json", champions_data)

            static_champions = self.static_dir / "champions.json"
            with open(static_champions, "w", encoding="utf-8") as f:
                json.dump(champions_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Champions gespeichert: {len(champions_data)} Monate")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Champions: {e}")
            return False
    
    def save_user_badges(self, badges_data):
        """Speichere User Badges (delegiert an save_badges für Dual-Write)"""
        return self.save_badges(badges_data)
    
    def load_daily_user_stats(self):
        """Lade Daily User Stats (PostgreSQL-first, JSON-Fallback)"""
        # 1. PostgreSQL-first
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    rows = session.query(UserStatsModel).filter_by(stat_type='daily').all()
                    if rows:
                        data = {}
                        for row in rows:
                            date_str = row.stat_date.strftime("%Y-%m-%d") if hasattr(row.stat_date, 'strftime') else str(row.stat_date)
                            if date_str not in data:
                                data[date_str] = {}
                            data[date_str][row.username] = {
                                "bookings": row.bookings_count,
                                "points": row.points_earned,
                                "badges_earned": row.achievements_unlocked
                            }
                            # Merge additional metrics from JSON field
                            if row.metrics_data and isinstance(row.metrics_data, dict):
                                data[date_str][row.username].update(row.metrics_data)
                        logger.debug(f"Loaded daily user stats from PostgreSQL ({len(data)} dates)")
                        return data
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"PostgreSQL daily stats load failed: {e}, falling back to JSON")

        # 2. JSON-Fallback
        try:
            stats_file = self.data_dir / "daily_user_stats.json"
            if stats_file.exists():
                with open(stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)

            static_stats = self.static_dir / "daily_user_stats.json"
            if static_stats.exists():
                with open(static_stats, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.save_daily_user_stats(data)
                    return data

            return {}
        except Exception as e:
            logger.error(f"Fehler beim Laden der Daily User Stats: {e}")
            return {}
    
    def save_daily_user_stats(self, stats_data):
        """Speichere Daily User Stats (Dual-Write: PostgreSQL + JSON)"""
        # 1. PostgreSQL write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    for date_str, users in stats_data.items():
                        if not isinstance(users, dict):
                            continue
                        try:
                            stat_date = datetime.strptime(date_str, "%Y-%m-%d")
                        except (ValueError, TypeError):
                            continue
                        for username, user_stats in users.items():
                            if not isinstance(user_stats, dict):
                                continue
                            bookings = user_stats.get("bookings", 0)
                            points = user_stats.get("points", 0)
                            badges = user_stats.get("badges_earned", 0)
                            # Extra fields go into metrics_data
                            extra = {k: v for k, v in user_stats.items() if k not in ("bookings", "points", "badges_earned")}

                            existing = session.query(UserStatsModel).filter(
                                UserStatsModel.username == username,
                                UserStatsModel.stat_date == stat_date,
                                UserStatsModel.stat_type == 'daily'
                            ).first()
                            if existing:
                                existing.bookings_count = bookings
                                existing.points_earned = points
                                existing.achievements_unlocked = badges
                                if extra:
                                    existing.metrics_data = extra
                            else:
                                new_row = UserStatsModel(
                                    username=username,
                                    stat_date=stat_date,
                                    stat_type='daily',
                                    bookings_count=bookings,
                                    points_earned=points,
                                    achievements_unlocked=badges,
                                    metrics_data=extra if extra else None
                                )
                                session.add(new_row)
                    session.commit()
                    logger.debug("Daily user stats saved to PostgreSQL")
                except Exception as e:
                    session.rollback()
                    logger.error(f"PostgreSQL daily stats save failed: {e}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"PostgreSQL connection failed for daily stats: {e}")

        # 2. JSON write (always, as backup)
        try:
            stats_file = self.data_dir / "daily_user_stats.json"
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)

            self._create_backup("daily_user_stats.json", stats_data)

            static_stats = self.static_dir / "daily_user_stats.json"
            with open(static_stats, "w", encoding="utf-8") as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Daily User Stats gespeichert: {len(stats_data)} Tage")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Daily User Stats: {e}")
            return False
    
    def load_champions(self):
        """Lade Champions (PostgreSQL-first, JSON-Fallback)"""
        # 1. PostgreSQL-first
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    rows = session.query(ChampionModel).filter_by(rank=1).all()
                    if rows:
                        data = {}
                        for row in rows:
                            entry = {
                                "user": row.username,
                                "score": row.total_points
                            }
                            # Merge stats_data zurueck
                            if row.stats_data and isinstance(row.stats_data, dict):
                                entry.update(row.stats_data)
                            data[row.period] = entry
                        logger.debug(f"Loaded champions from PostgreSQL ({len(data)} periods)")
                        return data
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"PostgreSQL champions load failed: {e}, falling back to JSON")

        # 2. JSON-Fallback
        try:
            champions_file = self.data_dir / "champions.json"
            if champions_file.exists():
                with open(champions_file, "r", encoding="utf-8") as f:
                    return json.load(f)

            static_champions = self.static_dir / "champions.json"
            if static_champions.exists():
                with open(static_champions, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.save_champions(data)
                    return data

            return {}
        except Exception as e:
            logger.error(f"Fehler beim Laden der Champions: {e}")
            return {}
    
    def _normalize_usernames_in_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalisiert Usernames in geladenen Daten.
        Wird beim Laden von scores, badges, etc. aufgerufen.
        """
        try:
            from app.utils.helpers import normalize_data_usernames
            return normalize_data_usernames(data)
        except ImportError:
            # Fallback: keine Normalisierung
            logger.warning("Could not import normalize_data_usernames, skipping normalization")
            return data
        except Exception as e:
            logger.error(f"Error normalizing usernames: {e}")
            return data

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
            
            # Prüfe Schreibbarkeit des Backup-Verzeichnisses
            try:
                test_file = self.backup_dir / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                issues.append(f"Backup-Verzeichnis nicht beschreibbar: {self.backup_dir} ({e})")

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

    def validate_scores_integrity(self):
        """Startup-Check: Scores gegen Level-History cross-validieren.

        Erkennt fehlende Score-Monate indem min. erwartete Punkte
        (aus Level-History XP) mit tatsächlichen Scores verglichen werden.
        """
        try:
            scores = self.load_scores()
            if not scores:
                return

            lh_path = self.static_dir / "level_history.json"
            if not lh_path.exists():
                return
            with open(lh_path, "r", encoding="utf-8") as f:
                level_history = json.load(f)
            if not level_history:
                return

            # Badge-XP einmal laden
            RARITY_XP = {
                "common": 50, "uncommon": 100, "rare": 250,
                "epic": 500, "legendary": 1000, "mythic": 2500
            }
            all_badges = {}
            try:
                badges_path = self.data_dir / "user_badges.json"
                if badges_path.exists():
                    with open(badges_path, "r", encoding="utf-8") as f:
                        all_badges = json.load(f)
            except Exception:
                pass

            warnings = []
            for user, lh_data in level_history.items():
                level_ups = lh_data.get("level_ups", [])
                peak_xp = max(
                    [lu.get("new_xp", 0) for lu in level_ups] + [lh_data.get("current_xp", 0)]
                )
                if peak_xp <= 0:
                    continue

                user_badges = all_badges.get(user, {})
                badge_xp = sum(
                    RARITY_XP.get(b.get("rarity", "common"), 50)
                    for b in user_badges.get("badges", [])
                )

                min_total_points = (peak_xp - badge_xp) / 10.0
                actual_total = sum(scores.get(user, {}).values())

                if actual_total < min_total_points * 0.9:
                    warnings.append(
                        f"{user}: Score {actual_total} < Min {min_total_points:.0f} "
                        f"(peak_xp={peak_xp}, badge_xp={badge_xp})"
                    )

            if warnings:
                logger.warning(f"SCORE INTEGRITY: {len(warnings)} User unter Level-History-Minimum!")
                for w in warnings:
                    logger.warning(f"  SCORE INTEGRITY: {w}")

        except Exception as e:
            logger.error(f"Score-Integrity-Check fehlgeschlagen: {e}")

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
            # Path Traversal Protection: Remove any path components
            import os.path
            filename = os.path.basename(filename)  # Strips '../' attacks

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
            # Path Traversal Protection: Remove any path components
            import os.path
            filename = os.path.basename(filename)  # Strips '../' attacks

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
