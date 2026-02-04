# -*- coding: utf-8 -*-
"""
Prestige/Mastery System für Slot Booking Webapp
Erweitert das Level-System um Prestige-Sterne und Mastery-Kategorien
"""

import os
import json
import logging
import pytz
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")

# PostgreSQL dual-write support
USE_POSTGRES = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

try:
    from app.models.weekly import PrestigeData as PrestigeDataModel
    from app.models.gamification import MasteryData as MasteryDataModel
    from app.models.base import get_db_session
    POSTGRES_AVAILABLE = True
except ImportError:
    logger.warning("PostgreSQL models not available for prestige_system, using JSON-only mode")
    POSTGRES_AVAILABLE = False
    USE_POSTGRES = False

# Mastery-Kategorien und ihre Kriterien
MASTERY_CATEGORIES = {
    "booking_master": {
        "name": "🎯 Buchungs-Meister",
        "description": "Meistere die Kunst des perfekten Buchens",
        "levels": {
            1: {"name": "Anfänger", "requirement": 50, "color": "#10b981", "emoji": "📝"},
            2: {"name": "Geübt", "requirement": 150, "color": "#3b82f6", "emoji": "📋"},
            3: {"name": "Experte", "requirement": 300, "color": "#8b5cf6", "emoji": "🎯"},
            4: {"name": "Virtuose", "requirement": 500, "color": "#f59e0b", "emoji": "⭐"},
            5: {"name": "Legendär", "requirement": 750, "color": "#eab308", "emoji": "👑"}
        },
        "metric": "total_bookings"
    },
    "speed_demon": {
        "name": "⚡ Geschwindigkeits-Dämon", 
        "description": "Buche Termine in Rekordgeschwindigkeit",
        "levels": {
            1: {"name": "Flott", "requirement": 10, "color": "#10b981", "emoji": "🏃"},
            2: {"name": "Schnell", "requirement": 25, "color": "#3b82f6", "emoji": "💨"},
            3: {"name": "Blitzschnell", "requirement": 50, "color": "#8b5cf6", "emoji": "⚡"},
            4: {"name": "Lichtgeschwindigkeit", "requirement": 100, "color": "#f59e0b", "emoji": "🚀"},
            5: {"name": "Zeit-Manipulator", "requirement": 150, "color": "#eab308", "emoji": "⏰"}
        },
        "metric": "fast_bookings"  # Buchungen unter 60 Sekunden
    },
    "streak_legend": {
        "name": "🔥 Streak-Legende",
        "description": "Halte unglaubliche Serien am Leben",
        "levels": {
            1: {"name": "Konstant", "requirement": 7, "color": "#10b981", "emoji": "🔥"},
            2: {"name": "Beständig", "requirement": 14, "color": "#3b82f6", "emoji": "💪"},
            3: {"name": "Eisern", "requirement": 30, "color": "#8b5cf6", "emoji": "⚡"},
            4: {"name": "Unaufhaltsam", "requirement": 60, "color": "#f59e0b", "emoji": "🚀"},
            5: {"name": "Ewig", "requirement": 100, "color": "#eab308", "emoji": "♾️"}
        },
        "metric": "best_streak"
    },
    "social_butterfly": {
        "name": "🦋 Sozialer Schmetterling",
        "description": "Sammle Achievements und Badges",
        "levels": {
            1: {"name": "Sammler", "requirement": 5, "color": "#10b981", "emoji": "🎭"},
            2: {"name": "Jäger", "requirement": 15, "color": "#3b82f6", "emoji": "🏹"},
            3: {"name": "Champion", "requirement": 30, "color": "#8b5cf6", "emoji": "🏆"},
            4: {"name": "Legende", "requirement": 50, "color": "#f59e0b", "emoji": "⭐"},
            5: {"name": "Mythisch", "requirement": 75, "color": "#eab308", "emoji": "💫"}
        },
        "metric": "total_badges"
    },
    "perfectionist": {
        "name": "✨ Perfektionist",
        "description": "Erreiche höchste Qualitätsstandards",
        "levels": {
            1: {"name": "Gewissenhaft", "requirement": 20, "color": "#10b981", "emoji": "📝"},
            2: {"name": "Präzise", "requirement": 50, "color": "#3b82f6", "emoji": "🎯"},
            3: {"name": "Makellos", "requirement": 100, "color": "#8b5cf6", "emoji": "✨"},
            4: {"name": "Perfektion", "requirement": 200, "color": "#f59e0b", "emoji": "💎"},
            5: {"name": "Göttlich", "requirement": 300, "color": "#eab308", "emoji": "👑"}
        },
        "metric": "detailed_bookings"  # Buchungen mit Beschreibung
    }
}

# Prestige-Titel und Anforderungen
PRESTIGE_LEVELS = {
    1: {"name": "⭐ Prestige I", "color": "#eab308", "requirement": 10},
    2: {"name": "⭐⭐ Prestige II", "color": "#f59e0b", "requirement": 15},
    3: {"name": "⭐⭐⭐ Prestige III", "color": "#ec4899", "requirement": 20},
    4: {"name": "⭐⭐⭐⭐ Prestige IV", "color": "#8b5cf6", "requirement": 25},
    5: {"name": "⭐⭐⭐⭐⭐ Prestige V", "color": "#3b82f6", "requirement": 30},
    6: {"name": "💫 Cosmic Master", "color": "#10b981", "requirement": 50},
}

class PrestigeSystem:
    def __init__(self):
        self.prestige_file = "data/persistent/prestige_data.json"
        self.mastery_file = "data/persistent/mastery_data.json"

        # Ensure directories exist
        os.makedirs("data/persistent", exist_ok=True)

        # Initialize files
        for file_path in [self.prestige_file, self.mastery_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
    
    def load_prestige_data(self):
        """Lade Prestige-Daten aller User (PostgreSQL-first, JSON-fallback)"""
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    rows = session.query(PrestigeDataModel).all()
                    if rows:
                        data = {}
                        for row in rows:
                            data[row.username] = {
                                "prestige_level": row.prestige_level,
                                "prestige_points": row.prestige_points,
                                "total_prestiges": row.prestige_level,
                                "prestige_history": row.prestige_history or [],
                                "xp_offset": row.pre_prestige_points,
                                "last_reset_xp": row.pre_prestige_level,
                                "last_reset_date": row.last_prestige_date.isoformat() if row.last_prestige_date else None
                            }
                        logger.debug(f"Loaded prestige data from PostgreSQL ({len(data)} users)")
                        return data
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"PostgreSQL prestige load failed: {e}, falling back to JSON")
        # JSON Fallback
        try:
            with open(self.prestige_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_prestige_data(self, data):
        """Speichere Prestige-Daten (Dual-Write: PostgreSQL + JSON)"""
        # 1. PostgreSQL write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    for username, user_data in data.items():
                        existing = session.query(PrestigeDataModel).filter_by(username=username).first()
                        if existing:
                            existing.prestige_level = user_data.get("prestige_level", 0)
                            existing.prestige_points = user_data.get("prestige_points", 0)
                            existing.prestige_history = user_data.get("prestige_history", [])
                            existing.pre_prestige_points = user_data.get("xp_offset", 0)
                            existing.pre_prestige_level = user_data.get("last_reset_xp", 0)
                            if user_data.get("last_reset_date"):
                                try:
                                    existing.last_prestige_date = datetime.fromisoformat(user_data["last_reset_date"])
                                except (ValueError, TypeError):
                                    pass
                        else:
                            last_date = None
                            if user_data.get("last_reset_date"):
                                try:
                                    last_date = datetime.fromisoformat(user_data["last_reset_date"])
                                except (ValueError, TypeError):
                                    pass
                            new_row = PrestigeDataModel(
                                username=username,
                                prestige_level=user_data.get("prestige_level", 0),
                                prestige_points=user_data.get("prestige_points", 0),
                                prestige_history=user_data.get("prestige_history", []),
                                pre_prestige_points=user_data.get("xp_offset", 0),
                                pre_prestige_level=user_data.get("last_reset_xp", 0),
                                last_prestige_date=last_date,
                            )
                            session.add(new_row)
                    session.commit()
                    logger.debug("Prestige data saved to PostgreSQL")
                except Exception as e:
                    session.rollback()
                    logger.error(f"PostgreSQL prestige save failed: {e}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"PostgreSQL connection failed for prestige: {e}")
        # 2. JSON write (always, as backup)
        with open(self.prestige_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_mastery_data(self):
        """Lade Mastery-Daten aller User (PostgreSQL-first, JSON-fallback)"""
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    rows = session.query(MasteryDataModel).all()
                    if rows:
                        data = {}
                        for row in rows:
                            if row.username not in data:
                                data[row.username] = {}
                            data[row.username][row.skill_id] = {
                                "level": row.current_level,
                                "upgraded_at": row.unlocked_abilities or []
                            }
                        logger.debug(f"Loaded mastery data from PostgreSQL ({len(data)} users)")
                        return data
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"PostgreSQL mastery load failed: {e}, falling back to JSON")
        # JSON Fallback
        try:
            with open(self.mastery_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_mastery_data(self, data):
        """Speichere Mastery-Daten (Dual-Write: PostgreSQL + JSON)"""
        # 1. PostgreSQL write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    for username, categories in data.items():
                        for category_id, cat_data in categories.items():
                            category_info = MASTERY_CATEGORIES.get(category_id, {})
                            existing = session.query(MasteryDataModel).filter_by(
                                username=username, skill_id=category_id
                            ).first()
                            if existing:
                                existing.current_level = cat_data.get("level", 0)
                                existing.unlocked_abilities = cat_data.get("upgraded_at", [])
                            else:
                                new_row = MasteryDataModel(
                                    username=username,
                                    skill_id=category_id,
                                    skill_name=category_info.get("name", category_id),
                                    skill_category="gamification",
                                    current_level=cat_data.get("level", 0),
                                    current_xp=0,
                                    xp_to_next_level=0,
                                    unlocked_abilities=cat_data.get("upgraded_at", []),
                                )
                                session.add(new_row)
                    session.commit()
                    logger.debug("Mastery data saved to PostgreSQL")
                except Exception as e:
                    session.rollback()
                    logger.error(f"PostgreSQL mastery save failed: {e}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"PostgreSQL connection failed for mastery: {e}")
        # 2. JSON write (always, as backup)
        with open(self.mastery_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def calculate_user_prestige(self, user):
        """Berechne Prestige-Level und verfügbare Upgrades für einen User"""
        try:
            from level_system import LevelSystem
            level_system = LevelSystem()
            user_level_data = level_system.calculate_user_level(user)
            current_level = user_level_data["level"]
        except:
            current_level = 1
        
        prestige_data = self.load_prestige_data()
        user_prestige = prestige_data.get(user, {
            "prestige_level": 0,
            "prestige_points": 0,
            "total_prestiges": 0,
            "prestige_history": []
        })
        
        # Prüfe ob Prestige verfügbar ist (Level 10+)
        can_prestige = current_level >= 10
        next_prestige_level = user_prestige["prestige_level"] + 1
        next_prestige_req = PRESTIGE_LEVELS.get(next_prestige_level, {}).get("requirement", 999)
        
        # Prüfe ob nächstes Prestige erreichbar ist
        can_upgrade = can_prestige and current_level >= next_prestige_req
        
        result = {
            "user": user,
            "current_level": current_level,
            "prestige_level": user_prestige["prestige_level"],
            "prestige_points": user_prestige["prestige_points"],
            "total_prestiges": user_prestige["total_prestiges"],
            "can_prestige": can_prestige,
            "can_upgrade": can_upgrade,
            "next_prestige_requirement": next_prestige_req,
            "prestige_title": self.get_prestige_title(user_prestige["prestige_level"]),
            "prestige_benefits": self.calculate_prestige_benefits(user_prestige["prestige_level"]),
            "mastery_progress": self.calculate_mastery_progress(user)
        }
        
        return result
    
    def perform_prestige(self, user):
        """Führe Prestige-Aufstieg durch (Reset auf Level 1 mit Boni)"""
        try:
            from level_system import LevelSystem
            level_system = LevelSystem()
            user_level_data = level_system.calculate_user_level(user)
            current_level = user_level_data["level"]
        except:
            return {"success": False, "message": "Fehler beim Laden der Level-Daten"}
        
        if current_level < 10:
            return {"success": False, "message": "Mindestens Level 10 für Prestige erforderlich"}
        
        prestige_data = self.load_prestige_data()
        user_prestige = prestige_data.get(user, {
            "prestige_level": 0,
            "prestige_points": 0,
            "total_prestiges": 0,
            "prestige_history": []
        })
        
        next_prestige = user_prestige["prestige_level"] + 1
        if next_prestige not in PRESTIGE_LEVELS:
            return {"success": False, "message": "Maximales Prestige bereits erreicht"}
        
        req_level = PRESTIGE_LEVELS[next_prestige]["requirement"]
        if current_level < req_level:
            return {"success": False, "message": f"Level {req_level} für nächstes Prestige erforderlich"}
        
        # Führe Prestige durch
        prestige_points_gained = current_level  # 1 Punkt pro Level
        user_prestige["prestige_level"] = next_prestige
        user_prestige["prestige_points"] += prestige_points_gained  
        user_prestige["total_prestiges"] += 1
        user_prestige["prestige_history"].append({
            "date": datetime.now(TZ).isoformat(),
            "from_level": current_level,
            "prestige_level": next_prestige,
            "points_gained": prestige_points_gained
        })
        
        prestige_data[user] = user_prestige
        self.save_prestige_data(prestige_data)

        # Reset User Level by storing XP offset
        self._reset_user_level(user)

        return {
            "success": True,
            "message": f"Prestige {next_prestige} erreicht!",
            "prestige_level": next_prestige,
            "points_gained": prestige_points_gained,
            "prestige_title": PRESTIGE_LEVELS[next_prestige]["name"]
        }
    
    def _reset_user_level(self, user):
        """Reset user level by storing current XP as offset (keeps actual data intact)"""
        try:
            from app.services.level_system import LevelSystem
            level_system = LevelSystem()

            # Get current total XP
            user_level_data = level_system.calculate_user_level(user)
            current_xp = user_level_data.get("xp", 0)

            # Store XP offset in prestige data
            prestige_data = self.load_prestige_data()
            if user not in prestige_data:
                prestige_data[user] = {}

            # Add current XP to existing offset (for multiple prestiges)
            existing_offset = prestige_data[user].get("xp_offset", 0)
            prestige_data[user]["xp_offset"] = existing_offset + current_xp
            prestige_data[user]["last_reset_xp"] = current_xp
            prestige_data[user]["last_reset_date"] = datetime.now(TZ).isoformat()

            self.save_prestige_data(prestige_data)

            # Reset level history to start fresh
            try:
                level_history_file = "static/level_history.json"
                with open(level_history_file, "r", encoding="utf-8") as f:
                    level_history = json.load(f)

                if user in level_history:
                    level_history[user]["current_level"] = 1
                    level_history[user]["current_xp"] = 0
                    level_history[user]["prestige_reset"] = datetime.now(TZ).isoformat()

                with open(level_history_file, "w", encoding="utf-8") as f:
                    json.dump(level_history, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error resetting level for {user}: {e}")

    def get_xp_offset(self, user):
        """Get XP offset for user (used by level_system to calculate effective XP)"""
        prestige_data = self.load_prestige_data()
        return prestige_data.get(user, {}).get("xp_offset", 0)

    def calculate_mastery_progress(self, user):
        """Berechne Fortschritt in allen Mastery-Kategorien"""
        # Lade User-Statistiken
        user_stats = self.get_user_metrics(user)
        mastery_data = self.load_mastery_data()
        user_mastery = mastery_data.get(user, {})
        
        progress = {}
        
        for category_id, category in MASTERY_CATEGORIES.items():
            metric_value = user_stats.get(category["metric"], 0)
            current_level = user_mastery.get(category_id, {}).get("level", 0)
            
            # Finde nächstes erreichbares Level
            next_level = current_level + 1
            if next_level in category["levels"]:
                next_requirement = category["levels"][next_level]["requirement"]
                can_upgrade = metric_value >= next_requirement
            else:
                next_level = None
                next_requirement = None
                can_upgrade = False
            
            # Aktueller Level-Info
            current_level_info = None
            if current_level > 0 and current_level in category["levels"]:
                current_level_info = category["levels"][current_level]
            
            progress[category_id] = {
                "category": category,
                "current_level": current_level,
                "current_level_info": current_level_info,
                "metric_value": metric_value,
                "next_level": next_level,
                "next_requirement": next_requirement,
                "can_upgrade": can_upgrade,
                "progress_percent": min(100, (metric_value / next_requirement * 100) if next_requirement else 100)
            }
        
        return progress
    
    def upgrade_mastery(self, user, category_id):
        """Verbessere Mastery-Level in einer Kategorie"""
        if category_id not in MASTERY_CATEGORIES:
            return {"success": False, "message": "Unbekannte Mastery-Kategorie"}
        
        mastery_progress = self.calculate_mastery_progress(user)
        category_progress = mastery_progress.get(category_id, {})
        
        if not category_progress.get("can_upgrade", False):
            return {"success": False, "message": "Upgrade-Anforderungen nicht erfüllt"}
        
        # Führe Upgrade durch
        mastery_data = self.load_mastery_data()
        if user not in mastery_data:
            mastery_data[user] = {}
        if category_id not in mastery_data[user]:
            mastery_data[user][category_id] = {"level": 0, "upgraded_at": []}
        
        new_level = mastery_data[user][category_id]["level"] + 1
        mastery_data[user][category_id]["level"] = new_level
        mastery_data[user][category_id]["upgraded_at"].append(datetime.now(TZ).isoformat())
        
        self.save_mastery_data(mastery_data)
        
        category = MASTERY_CATEGORIES[category_id]
        level_info = category["levels"][new_level]
        
        return {
            "success": True,
            "message": f"Mastery-Level {new_level} in {category['name']} erreicht!",
            "category": category["name"],
            "new_level": new_level,
            "level_name": level_info["name"],
            "emoji": level_info["emoji"]
        }
    
    def get_user_metrics(self, user):
        """Sammle alle relevanten User-Metriken für Mastery-Berechnung"""
        metrics = {
            "total_bookings": 0,
            "fast_bookings": 0,
            "best_streak": 0,
            "total_badges": 0,
            "detailed_bookings": 0
        }
        
        try:
            # Lade Booking-Daten
            from tracking_system import BookingTracker
            tracker = BookingTracker()
            all_bookings = tracker.load_all_bookings()

            user_bookings = [b for b in all_bookings if b.get("user") == user]
            metrics["total_bookings"] = len(user_bookings)

            # Fast bookings: Buchungen mit < 5 Minuten Vorlaufzeit
            fast_bookings = 0
            for b in user_bookings:
                try:
                    # Parse Buchungszeitpunkt
                    booking_timestamp = datetime.fromisoformat(b.get("timestamp", ""))

                    # Parse Terminzeitpunkt (date + time)
                    appointment_date = b.get("date", "")
                    appointment_time = b.get("time", "")
                    appointment_datetime = datetime.strptime(
                        f"{appointment_date} {appointment_time}",
                        "%Y-%m-%d %H:%M"
                    )
                    # Setze Timezone für appointment_datetime
                    appointment_datetime = TZ.localize(appointment_datetime)

                    # Berechne Differenz in Minuten
                    lead_time_minutes = (appointment_datetime - booking_timestamp).total_seconds() / 60

                    # Wenn < 5 Minuten → schnelle Buchung
                    if lead_time_minutes < 5:
                        fast_bookings += 1
                except:
                    pass

            metrics["fast_bookings"] = fast_bookings

            # Detailed bookings
            metrics["detailed_bookings"] = len([b for b in user_bookings if b.get("has_description", False)])

        except:
            pass
        
        try:
            # Lade Streak-Daten
            from achievement_system import achievement_system
            daily_stats = achievement_system.load_daily_stats()
            user_stats = daily_stats.get(user, {})
            streak_info = achievement_system.calculate_advanced_streak(user_stats)
            metrics["best_streak"] = streak_info.get("best_streak", 0)
            
            # Badge count
            user_badges = achievement_system.get_user_badges(user)
            metrics["total_badges"] = user_badges.get("total_badges", 0)
            
        except:
            pass
        
        return metrics
    
    def get_prestige_title(self, prestige_level):
        """Hole Prestige-Titel für gegebenes Level"""
        if prestige_level == 0:
            return {"name": "Bürgerlich", "color": "#9ca3af", "emoji": ""}
        return PRESTIGE_LEVELS.get(prestige_level, {"name": "Unbekannt", "color": "#9ca3af"})
    
    def calculate_prestige_benefits(self, prestige_level):
        """Berechne Boni/Vorteile für Prestige-Level"""
        benefits = []
        
        if prestige_level >= 1:
            benefits.append("🎯 +10% XP Bonus auf alle Aktionen")
        if prestige_level >= 2:  
            benefits.append("⚡ Exklusive Prestige-Badges verfügbar")
        if prestige_level >= 3:
            benefits.append("🎨 Spezielle Avatar-Rahmen freigeschaltet")
        if prestige_level >= 4:
            benefits.append("💫 Cosmic Titel und Effekte")
        if prestige_level >= 5:
            benefits.append("👑 Master-Status und VIP-Funktionen")
        
        return benefits
    
    def get_prestige_leaderboard(self):
        """Erstelle Rangliste nach Prestige-Level"""
        prestige_data = self.load_prestige_data()
        
        leaderboard = []
        for user, data in prestige_data.items():
            leaderboard.append({
                "user": user,
                "prestige_level": data.get("prestige_level", 0),
                "prestige_points": data.get("prestige_points", 0),
                "total_prestiges": data.get("total_prestiges", 0),
                "prestige_title": self.get_prestige_title(data.get("prestige_level", 0))
            })
        
        # Sortiere nach Prestige Level, dann nach Punkten
        leaderboard.sort(key=lambda x: (x["prestige_level"], x["prestige_points"]), reverse=True)
        return leaderboard

# Globale Instanz
prestige_system = PrestigeSystem()