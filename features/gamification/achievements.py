# -*- coding: utf-8 -*-
"""
Achievement/Badge System für Slot Booking Webapp - Optimiert
"""

import os
import json
import pytz
from datetime import datetime, timedelta
from collections import defaultdict

TZ = pytz.timezone("Europe/Berlin")

# Kompakte Badge-Definitionen
ACHIEVEMENT_DEFINITIONS = {
    # Daily Badges
    "daily_10": {"name": "Anfänger 🌱", "threshold": 10, "category": "daily", "rarity": "common"},
    "daily_20": {"name": "Aufsteiger ⭐", "threshold": 20, "category": "daily", "rarity": "uncommon"},
    "daily_40": {"name": "Champion 🏆", "threshold": 40, "category": "daily", "rarity": "rare"},
    "daily_60": {"name": "Legende 👑", "threshold": 60, "category": "daily", "rarity": "legendary"},
    
    # Weekly Badges
    "weekly_50": {"name": "Wochenkrieger ⚔️", "threshold": 100, "category": "weekly", "rarity": "uncommon"},
    "weekly_100": {"name": "Wochenmeister 🎯", "threshold": 200, "category": "weekly", "rarity": "rare"},
    
    # Monthly Badges
    "monthly_10": {"name": "Monatsanfänger 📅", "threshold": 10, "category": "monthly", "rarity": "common"},
    "monthly_25": {"name": "Monatsprofi 📊", "threshold": 25, "category": "monthly", "rarity": "uncommon"},
    "monthly_50": {"name": "Monatschampion 🥉", "threshold": 50, "category": "monthly", "rarity": "rare"},
    "monthly_100": {"name": "Monatslegende 🌟", "threshold": 100, "category": "monthly", "rarity": "epic"},
    
    # Total Badges
    "total_50": {"name": "Erfahrener Spieler 🎮", "threshold": 50, "category": "total", "rarity": "common"},
    "total_100": {"name": "Veteran 🛡️", "threshold": 100, "category": "total", "rarity": "uncommon"},
    "total_250": {"name": "Elite-Spieler ⚡", "threshold": 250, "category": "total", "rarity": "rare"},
    "total_500": {"name": "Ultimate Champion 🏆", "threshold": 500, "category": "total", "rarity": "legendary"},
    
    # Streak Badges
    "streak_2": {"name": "Konstant 🔥", "threshold": 2, "category": "streak", "rarity": "common"},
    "streak_5": {"name": "Durchhalter 💪", "threshold": 5, "category": "streak", "rarity": "uncommon"},
    "streak_10": {"name": "Eiserner Wille ⚡", "threshold": 10, "category": "streak", "rarity": "rare"},
    "streak_20": {"name": "Unaufhaltsam 🚀", "threshold": 20, "category": "streak", "rarity": "epic"},
    
    # Special Badges
    "first_booking": {"name": "Erste Schritte 👣", "category": "special", "rarity": "common"},
    "night_owl": {"name": "Nachteule 🌙", "threshold": 10, "category": "special", "rarity": "uncommon"},
    "early_bird": {"name": "Früher Vogel 🌅", "threshold": 10, "category": "special", "rarity": "uncommon"},
    
    # MVP Badges  
    "mvp_week": {"name": "Wochenmvp 🥇", "category": "mvp", "rarity": "epic"},
    "mvp_month": {"name": "Monatsmvp 👑", "category": "mvp", "rarity": "legendary"},
    "mvp_year": {"name": "Jahresmvp 💎", "category": "mvp", "rarity": "mythic"}
}

RARITY_COLORS = {
    "common": "#10b981", "uncommon": "#3b82f6", "rare": "#8b5cf6",
    "epic": "#f59e0b", "legendary": "#eab308", "mythic": "#ec4899"
}

class AchievementSystem:
    def __init__(self):
        self.data_dir = "data/persistent"
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_json(self, filename, fallback_dir="static"):
        """Generische JSON-Lade-Methode mit Fallback"""
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
    
    def add_points_and_check_achievements(self, user, points):
        """Hauptfunktion: Punkte hinzufügen und Achievements prüfen"""
        try:
            from core.persistence.data_manager import data_persistence
            
            # Lade Daten
            scores = data_persistence.load_scores()
            daily_stats = data_persistence.load_daily_user_stats()
            badges_data = self._load_json("user_badges.json")
            
            # Update Scores & Stats
            month = datetime.now(TZ).strftime("%Y-%m")
            today = datetime.now(TZ).strftime("%Y-%m-%d")
            
            if user not in scores:
                scores[user] = {}
            scores[user][month] = scores[user].get(month, 0) + points
            
            if user not in daily_stats:
                daily_stats[user] = {}
            if today not in daily_stats[user]:
                daily_stats[user][today] = {"points": 0, "bookings": 0}
            
            daily_stats[user][today]["points"] += points
            daily_stats[user][today]["bookings"] += 1
            
            # Speichere Updates
            data_persistence.save_scores(scores)
            data_persistence.save_daily_user_stats(daily_stats)
            
            # Prüfe Achievements
            new_badges = self._check_all_achievements(user, scores, daily_stats, badges_data)
            
            return new_badges
            
        except Exception as e:
            print(f"Achievement System Fehler: {e}")
            return []
    
    def _check_all_achievements(self, user, scores, daily_stats, badges_data):
        """Konsolidierte Achievement-Prüfung"""
        new_badges = []
        
        # Berechne alle Werte einmal
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        user_scores = scores.get(user, {})
        user_daily_stats = daily_stats.get(user, {})
        
        daily_points = user_daily_stats.get(today, {}).get("points", 0)
        week_points = self._calculate_week_points(user_daily_stats)
        month_points = sum(user_scores.values())
        total_points = sum(sum(month_scores.values()) for month_scores in scores.values())
        streak = self._calculate_streak(user_daily_stats)
        
        # Prüfe alle Badge-Kategorien
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if self._has_badge(user, badge_id, badges_data):
                continue
                
            earned = False
            category = definition["category"]
            threshold = definition.get("threshold", 0)
            
            if category == "daily" and daily_points >= threshold:
                earned = True
            elif category == "weekly" and week_points >= threshold:
                earned = True
            elif category == "monthly" and month_points >= threshold:
                earned = True
            elif category == "total" and total_points >= threshold:
                earned = True
            elif category == "streak" and streak >= threshold:
                earned = True
            elif category == "special":
                earned = self._check_special_badge(badge_id, user_daily_stats)
            
            if earned:
                badge = self._award_badge(user, badge_id, definition, badges_data)
                if badge:
                    new_badges.append(badge)
        
        self._save_json("user_badges.json", badges_data)
        return new_badges
    
    def _check_special_badge(self, badge_id, user_stats):
        """Prüfe spezielle Badge-Bedingungen"""
        if badge_id == "first_booking":
            return any(stats.get("bookings", 0) > 0 for stats in user_stats.values())
        elif badge_id == "night_owl":
            return sum(stats.get("evening_bookings", 0) for stats in user_stats.values()) >= 10
        elif badge_id == "early_bird":
            return sum(stats.get("morning_bookings", 0) for stats in user_stats.values()) >= 10
        return False
    
    def _has_badge(self, user, badge_id, badges_data):
        """Prüfe ob User bereits ein Badge hat"""
        user_badges = badges_data.get(user, {}).get("badges", [])
        return any(badge["id"] == badge_id for badge in user_badges)
    
    def _award_badge(self, user, badge_id, definition, badges_data):
        """Vergebe Badge an User"""
        if user not in badges_data:
            badges_data[user] = {"badges": [], "total_badges": 0}
        
        # Füge Emoji zum Namen hinzu
        name = definition["name"]
        if "emoji" not in definition and "🌱⭐🏆👑⚔️🎯📅📊🥉🌟🎮🛡️⚡🔥💪🚀👣🌙🌅🥇💎" in name:
            emoji = name[-2:]  # Letzten 2 Zeichen = Emoji
            name_without_emoji = name[:-3]  # Name ohne Emoji und Leerzeichen
        else:
            emoji = definition.get("emoji", "🏅")
            name_without_emoji = name
        
        badge = {
            "id": badge_id,
            "name": name,
            "emoji": emoji,
            "rarity": definition["rarity"],
            "category": definition["category"],
            "earned_date": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "color": RARITY_COLORS[definition["rarity"]]
        }
        
        badges_data[user]["badges"].append(badge)
        badges_data[user]["total_badges"] = len(badges_data[user]["badges"])
        
        return badge
    
    def _calculate_week_points(self, user_stats):
        """Berechne Punkte der aktuellen Woche"""
        today = datetime.now(TZ).date()
        week_start = today - timedelta(days=today.weekday())
        
        week_points = 0
        for i in range(7):
            check_date = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
            week_points += user_stats.get(check_date, {}).get("points", 0)
        
        return week_points
    
    def _calculate_streak(self, user_stats):
        """Berechne aktuelle Arbeits-Streak"""
        today = datetime.now(TZ).date()
        streak = 0
        
        for i in range(60):
            check_date = today - timedelta(days=i)
            if check_date.weekday() < 5:  # Nur Arbeitstage
                check_date_str = check_date.strftime("%Y-%m-%d")
                if user_stats.get(check_date_str, {}).get("points", 0) > 0:
                    streak += 1
                else:
                    break
        
        return streak
    
    def get_user_badges(self, user):
        """Hole User-Badges"""
        badges_data = self._load_json("user_badges.json")
        user_entry = badges_data.get(user, {"badges": []})
        return {
            "badges": user_entry.get("badges", []),
            "total_badges": len(user_entry.get("badges", []))
        }
    
    def get_badge_leaderboard(self):
        """Badge-Rangliste mit Rarität-Punkten"""
        badges_data = self._load_json("user_badges.json")
        leaderboard = []
        
        rarity_weights = {"common": 1, "uncommon": 2, "rare": 4, "epic": 6, "legendary": 10, "mythic": 20}
        
        for user, entry in badges_data.items():
            user_badges = entry.get("badges", [])
            rarity_points = sum(rarity_weights.get(badge.get("rarity", "common"), 1) for badge in user_badges)
            
            leaderboard.append({
                "user": user,
                "total_badges": len(user_badges),
                "rarity_points": rarity_points,
                "badges": user_badges
            })
        
        leaderboard.sort(key=lambda x: (x["rarity_points"], x["total_badges"]), reverse=True)
        return leaderboard
    
    def get_next_achievements(self, user, limit=5):
        """Nächste erreichbare Badges"""
        try:
            from core.persistence.data_manager import data_persistence
            scores = data_persistence.load_scores()
            daily_stats = data_persistence.load_daily_user_stats()
        except Exception:
            return []
        
        badges_data = self._load_json("user_badges.json")
        user_badges = {badge["id"] for badge in badges_data.get(user, {}).get("badges", [])}
        
        # Berechne aktuelle Werte
        user_scores = scores.get(user, {})
        user_daily_stats = daily_stats.get(user, {})
        
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        daily_points = user_daily_stats.get(today, {}).get("points", 0)
        week_points = self._calculate_week_points(user_daily_stats)
        month_points = sum(user_scores.values())
        total_points = sum(sum(month_scores.values()) for month_scores in scores.values())
        streak = self._calculate_streak(user_daily_stats)
        
        next_badges = []
        
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if badge_id in user_badges or "threshold" not in definition:
                continue
            
            category = definition["category"]
            target = definition["threshold"]
            current = 0
            
            if category == "daily":
                current = daily_points
            elif category == "weekly":
                current = week_points
            elif category == "monthly":
                current = month_points
            elif category == "total":
                current = total_points
            elif category == "streak":
                current = streak
            
            if current < target:
                remaining = target - current
                next_badges.append({
                    "id": badge_id,
                    "name": definition["name"],
                    "rarity": definition["rarity"],
                    "category": category,
                    "current": current,
                    "target": target,
                    "remaining": remaining,
                    "progress_percent": round((current / target) * 100, 1)
                })
        
        # Sortiere nach geringstem Restbedarf
        next_badges.sort(key=lambda x: x["remaining"])
        return next_badges[:limit]
    
    def backfill_persistent_badges(self):
        """Reparatur: Vergebe Badges rückwirkend"""
        try:
            from core.persistence.data_manager import data_persistence
            scores = data_persistence.load_scores()
            daily_stats = data_persistence.load_daily_user_stats()
            badges_data = self._load_json("user_badges.json")
            
            total_awarded = 0
            users = set(scores.keys()) | set(daily_stats.keys())
            
            for user in users:
                new_badges = self._check_all_achievements(user, scores, daily_stats, badges_data)
                total_awarded += len(new_badges)
            
            self._save_json("user_badges.json", badges_data)
            return {"users_processed": len(users), "badges_awarded": total_awarded}
            
        except Exception as e:
            return {"error": str(e)}

# Globale Instanz
achievement_system = AchievementSystem()