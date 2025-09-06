# -*- coding: utf-8 -*-
"""
Level-System für Slot Booking Webapp - Optimiert
"""

import os
import json
import pytz
from datetime import datetime

TZ = pytz.timezone("Europe/Berlin")

class LevelSystem:
    def __init__(self):
        self.data_dir = "data/persistent"
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_json(self, filename, fallback_dir="static"):
        """Generische JSON-Lade-Methode"""
        try:
            primary_path = os.path.join(self.data_dir, filename)
            if os.path.exists(primary_path):
                with open(primary_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            fallback_path = os.path.join(fallback_dir, filename)
            if os.path.exists(fallback_path):
                with open(fallback_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}
    
    def _save_json(self, filename, data, also_static=True):
        """Generische JSON-Speicher-Methode"""
        try:
            primary_path = os.path.join(self.data_dir, filename)
            with open(primary_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            if also_static:
                static_path = os.path.join("static", filename)
                os.makedirs("static", exist_ok=True)
                with open(static_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def calculate_user_level(self, user):
        """Berechne Level, XP und Fortschritt für einen User"""
        # Lade Daten
        scores = self._load_scores()
        user_badges = self._load_user_badges(user)
        
        # Berechne XP
        xp = self._calculate_total_xp(user, scores, user_badges)
        
        # Level aus XP berechnen
        level, level_xp, next_level_xp = self._calculate_level_from_xp(xp)
        
        # Fortschritt berechnen
        progress_to_next = 0
        if next_level_xp > level_xp:
            progress_to_next = ((xp - level_xp) / (next_level_xp - level_xp)) * 100
        
        # Level-Up prüfen
        level_up_info = self._check_level_up(user, level, xp)
        
        # Beste Badge finden
        best_badge = self._get_best_badge(user_badges["badges"])
        
        result = {
            "user": user,
            "level": level,
            "xp": xp,
            "level_xp": level_xp,
            "next_level_xp": next_level_xp,
            "progress_to_next": round(progress_to_next, 1),
            "best_badge": best_badge,
            "level_title": self._get_level_title(level),
            "total_badges": user_badges["total_badges"],
            "progress_color": self._get_progress_color(progress_to_next),
            "best_badge_color": self._get_rarity_color(best_badge["rarity"]) if best_badge else "#10b981",
            "level_up": level_up_info
        }
        
        # Persistiere Level-Stand
        self._save_user_level(user, level, xp)
        
        return result
    
    def _load_scores(self):
        """Lade Scores mit Fallback"""
        try:
            from core.persistence.data_manager import data_persistence
            return data_persistence.load_scores()
        except Exception:
            return self._load_json("scores.json")
    
    def _load_user_badges(self, user):
        """Lade User-Badges mit Fallback"""
        try:
            from features.gamification.achievements import achievement_system
            return achievement_system.get_user_badges(user)
        except Exception:
            badges_data = self._load_json("user_badges.json")
            user_entry = badges_data.get(user, {"badges": []})
            return {
                "badges": user_entry.get("badges", []),
                "total_badges": len(user_entry.get("badges", []))
            }
    
    def _calculate_total_xp(self, user, scores, user_badges):
        """Berechne Gesamt-XP aus Punkten, Badges und Streak"""
        xp = 0
        
        # 1. Punkte-XP (Basis)
        user_scores = scores.get(user, {})
        total_points = sum(user_scores.values())
        xp += total_points * 10
        
        # 2. Badge-XP (Bonus)
        rarity_xp = {
            "common": 50, "uncommon": 100, "rare": 250,
            "epic": 500, "legendary": 1000, "mythic": 2500
        }
        for badge in user_badges["badges"]:
            rarity = badge.get("rarity", "common")
            xp += rarity_xp.get(rarity, 50)
        
        # 3. Streak-XP (Aktivitäts-Bonus)
        try:
            from features.gamification.achievements import achievement_system
            from core.persistence.data_manager import data_persistence
            daily_stats = data_persistence.load_daily_user_stats()
            streak_info = achievement_system.calculate_advanced_streak(daily_stats.get(user, {}))
            xp += streak_info["best_streak"] * 25
        except Exception:
            pass
        
        return int(xp)
    
    def _calculate_level_from_xp(self, xp):
        """Level aus XP berechnen (exponentiell)"""
        if xp < 100:
            return 1, 0, 100
        
        # Level = 1 + sqrt(XP / 100)
        level = int(1 + (xp / 100) ** 0.5)
        level_xp = ((level - 1) ** 2) * 100
        next_level_xp = (level ** 2) * 100
        
        return level, level_xp, next_level_xp
    
    def _check_level_up(self, user, new_level, new_xp):
        """Prüfe Level-Up"""
        level_history = self._load_json("level_history.json")
        
        if user not in level_history:
            level_history[user] = {"current_level": 1, "current_xp": 0, "level_ups": []}
        
        old_level = level_history[user]["current_level"]
        level_up_info = None
        
        if new_level > old_level:
            level_up_info = {
                "old_level": old_level,
                "new_level": new_level,
                "xp_gained": new_xp - level_history[user]["current_xp"],
                "timestamp": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
            }
            level_history[user]["level_ups"].append(level_up_info)
        
        # Update aktueller Stand
        level_history[user].update({
            "current_level": new_level,
            "current_xp": new_xp,
            "last_check": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        })
        
        self._save_json("level_history.json", level_history)
        return level_up_info
    
    def _save_user_level(self, user, level, xp):
        """Speichere aktuellen Level-Stand"""
        levels = self._load_json("user_levels.json")
        levels[user] = {
            "level": level,
            "xp": xp,
            "updated_at": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "level_title": self._get_level_title(level)
        }
        self._save_json("user_levels.json", levels)
    
    def _get_best_badge(self, badges):
        """Finde beste Badge nach Seltenheit"""
        if not badges:
            return None
        
        rarity_order = {"common": 1, "uncommon": 2, "rare": 3, "epic": 4, "legendary": 5, "mythic": 6}
        return max(badges, key=lambda x: (rarity_order.get(x["rarity"], 0), x["earned_date"]))
    
    def _get_level_title(self, level):
        """Level-Titel"""
        titles = {
            1: "Anfänger", 2: "Lernender", 3: "Aktiver", 4: "Erfahrener", 5: "Profi",
            6: "Experte", 7: "Meister", 8: "Champion", 9: "Legende", 10: "Mythos"
        }
        return titles.get(level, f"Level {level} Meister" if level > 10 else f"Level {level}")
    
    def _get_progress_color(self, progress):
        """Progress-Bar Farbe"""
        if progress < 25: return "#ef4444"
        elif progress < 50: return "#f59e0b"
        elif progress < 75: return "#eab308"
        else: return "#10b981"
    
    def _get_rarity_color(self, rarity):
        """Seltenheits-Farbe"""
        colors = {
            "common": "#10b981", "uncommon": "#3b82f6", "rare": "#8b5cf6",
            "epic": "#f59e0b", "legendary": "#eab308", "mythic": "#ec4899"
        }
        return colors.get(rarity, "#10b981")

    def get_level_progress_color(self, progress):
    """Kompatibilitäts-Wrapper für alte Methodenaufrufe"""
    return self._get_progress_color(progress)
    
    def get_level_statistics(self, user):
        """Level-Statistiken für User"""
        level_history = self._load_json("level_history.json")
        user_history = level_history.get(user, {})
        
        level_ups = user_history.get("level_ups", [])
        stats = {
            "current_level": user_history.get("current_level", 1),
            "current_xp": user_history.get("current_xp", 0),
            "total_level_ups": len(level_ups),
            "recent_level_ups": level_ups[-5:],
            "average_xp_per_level": 0
        }
        
        if level_ups:
            total_xp_gained = sum(up.get("xp_gained", 0) for up in level_ups)
            stats["average_xp_per_level"] = total_xp_gained / len(level_ups)
        
        return stats

# Globale Instanz
level_system = LevelSystem()