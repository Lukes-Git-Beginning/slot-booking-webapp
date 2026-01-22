# -*- coding: utf-8 -*-
"""
Level-System für Slot Booking Webapp
Integriert Punkte und Badges in ein ausgewogenes Level-System
"""

import os
import json
import pytz
import logging
from datetime import datetime, timedelta
from collections import defaultdict

# Logger setup
logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")

class LevelSystem:
    def __init__(self):
        self.levels_file = "static/user_levels.json"
        self.level_history_file = "static/level_history.json"
        os.makedirs("static", exist_ok=True)
        
        # Initialisiere Files wenn nicht vorhanden
        if not os.path.exists(self.levels_file):
            with open(self.levels_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
        
        if not os.path.exists(self.level_history_file):
            with open(self.level_history_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
    
    def calculate_user_level(self, user):
        """Berechne Level, XP und Fortschritt für einen User"""
        try:
            from app.core.extensions import data_persistence
            scores = data_persistence.load_scores()
        except:
            try:
                with open("static/scores.json", "r", encoding="utf-8") as f:
                    scores = json.load(f)
            except:
                scores = {}

        # Lade Badge-System
        try:
            from achievement_system import achievement_system
            user_badges = achievement_system.get_user_badges(user)
        except:
            user_badges = {"badges": [], "total_badges": 0}

        user_scores = scores.get(user, {})

        # Berechne XP basierend auf verschiedenen Faktoren
        raw_xp = self.calculate_total_xp(user_scores, user_badges)

        # Apply prestige XP offset (level resets on prestige but data stays)
        xp_offset = self._get_prestige_xp_offset(user)
        xp = max(0, raw_xp - xp_offset)
        
        # Level-Berechnung (exponentiell steigend)
        level, level_xp, next_level_xp = self.calculate_level_from_xp(xp)
        
        # Prüfe auf Level-Up
        level_up_info = self.check_level_up(user, level, xp)
        
        # Beste Badge finden
        best_badge = self.get_best_badge(user_badges["badges"])
        
        # Level-Titel basierend auf Level
        level_title = self.get_level_title(level)
        
        # Fortschritt zum nächsten Level
        progress_to_next = 0
        if next_level_xp > level_xp:
            progress_to_next = ((xp - level_xp) / (next_level_xp - level_xp)) * 100
        
        # Progress-Farbe basierend auf Fortschritt
        progress_color = self.get_level_progress_color(progress_to_next)
        
        # Beste Badge-Farbe
        best_badge_color = "#10b981"  # Default grün
        if best_badge:
            best_badge_color = self.get_rarity_color(best_badge["rarity"])
        
        result = {
            "user": user,
            "level": level,
            "xp": xp,
            "level_xp": level_xp,
            "next_level_xp": next_level_xp,
            "progress_to_next": round(progress_to_next, 1),
            "best_badge": best_badge,
            "level_title": level_title,
            "total_badges": user_badges["total_badges"],
            "progress_color": progress_color,
            "best_badge_color": best_badge_color,
            "level_up": level_up_info
        }

        # Persistiere aktuellen Level-Stand in user_levels.json
        try:
            with open(self.levels_file, "r", encoding="utf-8") as f:
                levels = json.load(f)
        except Exception:
            levels = {}
        levels[user] = {
            "level": level,
            "xp": xp,
            "updated_at": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "level_title": level_title
        }
        try:
            with open(self.levels_file, "w", encoding="utf-8") as f:
                json.dump(levels, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return result
    
    def check_level_up(self, user, new_level, new_xp):
        """Prüfe ob User ein Level aufgestiegen ist"""
        try:
            # Lade Level-Historie
            with open(self.level_history_file, "r", encoding="utf-8") as f:
                level_history = json.load(f)
        except:
            level_history = {}
        
        if user not in level_history:
            level_history[user] = {
                "current_level": 1,
                "current_xp": 0,
                "level_ups": [],
                "last_check": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
            }
        
        old_level = level_history[user]["current_level"]
        old_xp = level_history[user]["current_xp"]
        
        level_up_info = None
        now_ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        
        # Prüfe auf Level-Up
        if new_level > old_level:
            level_up_info = {
                "old_level": old_level,
                "new_level": new_level,
                "old_xp": old_xp,
                "new_xp": new_xp,
                "xp_gained": new_xp - old_xp,
                "timestamp": now_ts
            }
            level_history[user]["level_ups"].append(level_up_info)
            logger.info(f"LEVEL UP! {user} ist von Level {old_level} auf Level {new_level} aufgestiegen!")

        # Aktualisiere Snapshot immer
        level_history[user]["current_level"] = new_level
        level_history[user]["current_xp"] = new_xp
        level_history[user]["last_check"] = now_ts

        # Speicher immer Historie (auch ohne Level-Up), damit Datei nicht leer bleibt
        try:
            with open(self.level_history_file, "w", encoding="utf-8") as f:
                json.dump(level_history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        
        return level_up_info
    
    def calculate_total_xp(self, user_scores, user_badges):
        """Berechne Gesamt-XP aus Punkten und Badges"""
        xp = 0
        
        # 1. Punkte-XP (50% der Gesamt-XP)
        total_points = sum(user_scores.values())
        xp += total_points * 10  # 10 XP pro Punkt
        
        # 2. Badge-XP (30% der Gesamt-XP)
        badge_xp = 0
        for badge in user_badges["badges"]:
            rarity = badge["rarity"]
            # XP basierend auf Seltenheit
            rarity_xp = {
                "common": 50,
                "uncommon": 100,
                "rare": 250,
                "epic": 500,
                "legendary": 1000,
                "mythic": 2500
            }
            badge_xp += rarity_xp.get(rarity, 50)
        
        xp += badge_xp
        
        # 3. Streak-XP (20% der Gesamt-XP)
        try:
            from achievement_system import achievement_system
            from app.core.extensions import data_persistence
            daily_stats = data_persistence.load_daily_user_stats()
            streak_info = achievement_system.calculate_advanced_streak(daily_stats.get(user, {}))
            streak_xp = streak_info["best_streak"] * 25  # 25 XP pro Streak-Tag
            xp += streak_xp
        except:
            pass
        
        return int(xp)
    
    def calculate_level_from_xp(self, xp):
        """Berechne Level basierend auf XP (exponentiell steigend)"""
        if xp < 100:
            level = 1
            level_xp = 0
            next_level_xp = 100
        else:
            # Exponentielle Formel: Level = 1 + sqrt(XP / 100)
            level = int(1 + (xp / 100) ** 0.5)
            
            # XP für aktuelles Level
            level_xp = ((level - 1) ** 2) * 100
            
            # XP für nächstes Level
            next_level_xp = (level ** 2) * 100
        
        return level, level_xp, next_level_xp
    
    def get_best_badge(self, badges):
        """Finde die beste Badge basierend auf Seltenheit"""
        if not badges:
            return None
        
        # Raritäts-Reihenfolge (höher = besser)
        rarity_order = {
            "common": 1,
            "uncommon": 2,
            "rare": 3,
            "epic": 4,
            "legendary": 5,
            "mythic": 6
        }
        
        # Sortiere nach Seltenheit und dann nach Datum
        sorted_badges = sorted(badges, 
                             key=lambda x: (rarity_order.get(x["rarity"], 0), x["earned_date"]), 
                             reverse=True)
        
        return sorted_badges[0]
    
    def get_level_title(self, level):
        """Bekomme Level-Titel basierend auf Level"""
        titles = {
            1: "Anfänger",
            2: "Lernender",
            3: "Aktiver",
            4: "Erfahrener",
            5: "Profi",
            6: "Experte",
            7: "Meister",
            8: "Champion",
            9: "Legende",
            10: "Mythos"
        }
        
        if level <= 10:
            return titles.get(level, f"Level {level}")
        else:
            return f"Level {level} Meister"
    
    def get_level_progress_color(self, progress):
        """Bekomme Farbe für Progress-Bar basierend auf Fortschritt"""
        if progress < 25:
            return "#ef4444"  # Rot
        elif progress < 50:
            return "#f59e0b"  # Orange
        elif progress < 75:
            return "#eab308"  # Gelb
        else:
            return "#10b981"  # Grün
    
    def get_rarity_color(self, rarity):
        """Bekomme Farbe für Rarität"""
        colors = {
            "common": "#10b981",
            "uncommon": "#3b82f6",
            "rare": "#8b5cf6",
            "epic": "#f59e0b",
            "legendary": "#eab308",
            "mythic": "#ec4899"
        }
        return colors.get(rarity, "#10b981")
    
    def _get_prestige_xp_offset(self, user):
        """Get XP offset from prestige system (level resets on prestige)"""
        try:
            from app.services.prestige_system import prestige_system
            return prestige_system.get_xp_offset(user)
        except Exception:
            return 0

    def get_level_statistics(self, user):
        """Bekomme Level-Statistiken für User"""
        try:
            with open(self.level_history_file, "r", encoding="utf-8") as f:
                level_history = json.load(f)
        except:
            return {}
        
        user_history = level_history.get(user, {})
        
        stats = {
            "current_level": user_history.get("current_level", 1),
            "current_xp": user_history.get("current_xp", 0),
            "total_level_ups": len(user_history.get("level_ups", [])),
            "recent_level_ups": user_history.get("level_ups", [])[-5:],  # Letzte 5 Level-Ups
            "fastest_level_up": None,
            "average_xp_per_level": 0
        }
        
        level_ups = user_history.get("level_ups", [])
        if level_ups:
            # Schnellster Level-Up
            fastest = min(level_ups, key=lambda x: x.get("xp_gained", 0))
            stats["fastest_level_up"] = fastest
            
            # Durchschnittliche XP pro Level
            total_xp_gained = sum(up.get("xp_gained", 0) for up in level_ups)
            stats["average_xp_per_level"] = total_xp_gained / len(level_ups)
        
        return stats

# Globale Instanz
level_system = LevelSystem()
