# -*- coding: utf-8 -*-
"""
Level-System für Slot Booking Webapp
Integriert Punkte und Badges in ein ausgewogenes Level-System
"""

import os
import json
import pytz
from datetime import datetime, timedelta
from collections import defaultdict

TZ = pytz.timezone("Europe/Berlin")

class LevelSystem:
    def __init__(self):
        self.levels_file = "static/user_levels.json"
        os.makedirs("static", exist_ok=True)
        
        # Initialisiere File wenn nicht vorhanden
        if not os.path.exists(self.levels_file):
            with open(self.levels_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
    
    def calculate_user_level(self, user):
        """Berechne Level, XP und Fortschritt für einen User"""
        try:
            from data_persistence import data_persistence
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
        xp = self.calculate_total_xp(user_scores, user_badges)
        
        # Level-Berechnung (exponentiell steigend)
        level, level_xp, next_level_xp = self.calculate_level_from_xp(xp)
        
        # Beste Badge finden
        best_badge = self.get_best_badge(user_badges["badges"])
        
        # Level-Titel basierend auf Level
        level_title = self.get_level_title(level)
        
        # Fortschritt zum nächsten Level
        progress_to_next = 0
        if next_level_xp > level_xp:
            progress_to_next = ((xp - level_xp) / (next_level_xp - level_xp)) * 100
        
        return {
            "user": user,
            "level": level,
            "xp": xp,
            "level_xp": level_xp,
            "next_level_xp": next_level_xp,
            "progress_to_next": round(progress_to_next, 1),
            "best_badge": best_badge,
            "level_title": level_title,
            "total_badges": user_badges["total_badges"]
        }
    
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
            daily_stats = achievement_system.load_daily_stats()
            user_stats = daily_stats.get(user, {})
            current_streak = achievement_system.calculate_streak(user_stats)
            xp += current_streak * 25  # 25 XP pro Streak-Tag
        except:
            pass
        
        return int(xp)
    
    def calculate_level_from_xp(self, xp):
        """Berechne Level aus XP (exponentiell steigend)"""
        if xp < 100:
            return 1, 0, 100
        
        # Level-Formel: Level = 1 + sqrt(XP / 100)
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
        
        # Sortiere nach Seltenheit
        rarity_order = ["mythic", "legendary", "epic", "rare", "uncommon", "common"]
        
        best_badge = None
        best_rarity_index = len(rarity_order)
        
        for badge in badges:
            rarity_index = rarity_order.index(badge["rarity"])
            if rarity_index < best_rarity_index:
                best_rarity_index = rarity_index
                best_badge = badge
        
        return best_badge
    
    def get_level_title(self, level):
        """Gebe Level-Titel basierend auf Level zurück"""
        titles = {
            1: "Neuling",
            2: "Anfänger",
            3: "Auszubildender",
            4: "Praktikant",
            5: "Junior",
            6: "Mitarbeiter",
            7: "Erfahrener",
            8: "Senior",
            9: "Experte",
            10: "Profi",
            11: "Spezialist",
            12: "Veteran",
            13: "Meister",
            14: "Champion",
            15: "Legende",
            16: "Mythos",
            17: "Gott",
            18: "Unsterblicher",
            19: "Ewiger",
            20: "Ultimate"
        }
        
        if level <= 20:
            return titles.get(level, f"Level {level}")
        else:
            return f"Ultimate +{level - 20}"
    
    def get_level_progress_color(self, progress):
        """Gebe Farbe für Level-Fortschritt zurück"""
        if progress < 25:
            return "#ef4444"  # Rot
        elif progress < 50:
            return "#f97316"  # Orange
        elif progress < 75:
            return "#eab308"  # Gelb
        else:
            return "#10b981"  # Grün
    
    def get_rarity_color(self, rarity):
        """Gebe Farbe für Badge-Seltenheit zurück"""
        colors = {
            "common": "#10b981",      # Grün
            "uncommon": "#3b82f6",    # Blau
            "rare": "#8b5cf6",        # Lila
            "epic": "#f59e0b",        # Orange
            "legendary": "#eab308",   # Gold
            "mythic": "#ec4899"       # Pink
        }
        return colors.get(rarity, "#6b7280")

# Globale Instanz
level_system = LevelSystem()
