# -*- coding: utf-8 -*-
"""
Personalization & Customization System für Slot Booking Webapp
Custom Avatars, persönliche Ziele, Themes und individuelle Einstellungen
"""

import os
import json
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

TZ = pytz.timezone("Europe/Berlin")

# Avatar-Komponenten
AVATAR_COMPONENTS = {
    "backgrounds": {
        "gradient_blue": {"name": "Blau Verlauf", "color": "linear-gradient(135deg, #3b82f6, #1d4ed8)", "unlock": "free"},
        "gradient_green": {"name": "Grün Verlauf", "color": "linear-gradient(135deg, #10b981, #059669)", "unlock": "level_5"},
        "gradient_purple": {"name": "Lila Verlauf", "color": "linear-gradient(135deg, #8b5cf6, #7c3aed)", "unlock": "badge_rare"},
        "gradient_gold": {"name": "Gold Verlauf", "color": "linear-gradient(135deg, #f59e0b, #d97706)", "unlock": "badge_epic"},
        "gradient_rainbow": {"name": "Regenbogen", "color": "linear-gradient(135deg, #f59e0b, #ec4899, #8b5cf6, #3b82f6, #10b981)", "unlock": "prestige_1"},
        "starfield": {"name": "Sternenhimmel", "color": "radial-gradient(circle, #1e293b 0%, #0f172a 100%)", "unlock": "mastery_max"},
        "cosmic": {"name": "Kosmisch", "color": "linear-gradient(135deg, #0c0a09, #1c1917, #ec4899)", "unlock": "prestige_3"}
    },
    "borders": {
        "simple": {"name": "Einfach", "style": "2px solid #e5e7eb", "unlock": "free"},
        "glow": {"name": "Leuchtend", "style": "3px solid #3b82f6", "glow": "0 0 10px rgba(59,130,246,0.5)", "unlock": "level_10"},
        "rainbow": {"name": "Regenbogen", "style": "3px solid transparent", "background": "linear-gradient(45deg, #f59e0b, #ec4899, #8b5cf6, #3b82f6, #10b981)", "unlock": "badge_legendary"},
        "fire": {"name": "Feuer", "style": "3px solid #ef4444", "glow": "0 0 15px rgba(239,68,68,0.8)", "unlock": "streak_30"},
        "diamond": {"name": "Diamant", "style": "4px solid #e5e7eb", "glow": "0 0 20px rgba(255,255,255,0.8)", "unlock": "prestige_2"},
        "mythic": {"name": "Mythisch", "style": "4px solid #ec4899", "glow": "0 0 25px rgba(236,72,153,1)", "unlock": "badge_mythic"}
    },
    "effects": {
        "none": {"name": "Keine", "effect": "", "unlock": "free"},
        "sparkle": {"name": "Funkelnd", "effect": "sparkle", "unlock": "level_15"},
        "floating": {"name": "Schwebend", "effect": "float", "unlock": "badge_rare"},
        "pulse": {"name": "Pulsierend", "effect": "pulse", "unlock": "streak_14"},
        "rotate": {"name": "Rotierend", "effect": "rotate", "unlock": "daily_quest_master"},
        "bounce": {"name": "Hüpfend", "effect": "bounce", "unlock": "social_butterfly"}
    },
    "titles": {
        "none": {"name": "", "text": "", "unlock": "free"},
        "rookie": {"name": "Rookie", "text": "🌱 Neuling", "color": "#10b981", "unlock": "level_3"},
        "expert": {"name": "Expert", "text": "⚡ Experte", "color": "#3b82f6", "unlock": "level_10"},
        "master": {"name": "Master", "text": "👑 Meister", "color": "#f59e0b", "unlock": "level_20"},
        "legend": {"name": "Legend", "text": "🏆 Legende", "color": "#ec4899", "unlock": "prestige_1"},
        "cosmic": {"name": "Cosmic", "text": "💫 Kosmisch", "color": "#8b5cf6", "unlock": "prestige_3"}
    }
}

# Theme-Konfigurationen
THEMES = {
    "default": {
        "name": "Standard",
        "primary": "#5a9fff",
        "accent": "#3b82f6", 
        "background": "#0f172a",
        "surface": "#1e293b",
        "text": "#f8fafc",
        "unlock": "free"
    },
    "emerald": {
        "name": "Smaragd",
        "primary": "#10b981",
        "accent": "#059669",
        "background": "#064e3b",
        "surface": "#065f46", 
        "text": "#ecfdf5",
        "unlock": "level_8"
    },
    "sunset": {
        "name": "Sonnenuntergang",
        "primary": "#f59e0b",
        "accent": "#d97706",
        "background": "#451a03",
        "surface": "#78350f",
        "text": "#fef3c7",
        "unlock": "badge_epic"
    },
    "midnight": {
        "name": "Mitternacht",
        "primary": "#8b5cf6",
        "accent": "#7c3aed",
        "background": "#1e1b4b",
        "surface": "#312e81",
        "text": "#ede9fe",
        "unlock": "streak_21"
    },
    "cherry": {
        "name": "Kirsche",
        "primary": "#ec4899",
        "accent": "#db2777",
        "background": "#4a044e",
        "surface": "#701a75",
        "text": "#fdf2f8",
        "unlock": "prestige_1"
    },
    "cosmic": {
        "name": "Kosmisch",
        "primary": "#06b6d4",
        "accent": "#0891b2",
        "background": "linear-gradient(135deg, #0c0a09, #1c1917, #ec4899)",
        "surface": "rgba(30, 41, 59, 0.8)",
        "text": "#f0f9ff",
        "unlock": "prestige_2"
    }
}

# Goal Templates
GOAL_TEMPLATES = {
    "daily_points": {
        "name": "Tägliche Punkte",
        "description": "Erreiche X Punkte pro Tag",
        "type": "daily",
        "default_target": 10,
        "min_target": 1,
        "max_target": 50,
        "reward_multiplier": 1.2
    },
    "weekly_bookings": {
        "name": "Wöchentliche Buchungen",
        "description": "Mache X Buchungen pro Woche", 
        "type": "weekly",
        "default_target": 15,
        "min_target": 5,
        "max_target": 100,
        "reward_multiplier": 1.1
    },
    "streak_maintenance": {
        "name": "Streak halten",
        "description": "Halte eine Streak von X Tagen",
        "type": "streak",
        "default_target": 7,
        "min_target": 3,
        "max_target": 365,
        "reward_multiplier": 1.5
    },
    "badge_collection": {
        "name": "Badge Sammlung",
        "description": "Sammle X neue Badges",
        "type": "collection",
        "default_target": 3,
        "min_target": 1,
        "max_target": 20,
        "reward_multiplier": 1.3
    },
    "rank_improvement": {
        "name": "Ranking verbessern",
        "description": "Erreiche Rang X oder besser",
        "type": "ranking",
        "default_target": 5,
        "min_target": 1,
        "max_target": 20,
        "reward_multiplier": 1.4
    }
}

class PersonalizationSystem:
    def __init__(self):
        self.profiles_file = "data/persistent/user_profiles.json"
        self.customization_file = "data/persistent/user_customizations.json"
        self.goals_file = "data/persistent/personal_goals.json"
        self.achievements_file = "data/persistent/customization_achievements.json"
        
        # Ensure directories exist
        os.makedirs("data/persistent", exist_ok=True)
        
        # Initialize files
        for file_path in [self.profiles_file, self.customization_file, self.goals_file, self.achievements_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
    
    def load_user_profile(self, user):
        """Lade vollständiges User-Profil mit Customizations"""
        try:
            with open(self.profiles_file, "r", encoding="utf-8") as f:
                profiles = json.load(f)
        except:
            profiles = {}
        
        # Default Profile
        default_profile = {
            "user": user,
            "created_at": datetime.now(TZ).isoformat(),
            "display_name": user,
            "bio": "",
            "favorite_quote": "",
            "privacy_settings": {
                "show_in_leaderboard": True,
                "show_statistics": True,
                "allow_friend_requests": True
            },
            "notification_preferences": {
                "achievement_notifications": True,
                "daily_quest_reminders": True,
                "streak_warnings": True,
                "level_up_celebrations": True
            },
            "customization": self.get_user_customization(user),
            "theme": "default",
            "last_active": datetime.now(TZ).isoformat()
        }
        
        user_profile = profiles.get(user, default_profile)
        # Update last active
        user_profile["last_active"] = datetime.now(TZ).isoformat()
        
        profiles[user] = user_profile
        with open(self.profiles_file, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        
        return user_profile
    
    def update_user_profile(self, user, updates):
        """Update User-Profil mit neuen Daten"""
        profile = self.load_user_profile(user)
        
        # Update erlaubte Felder
        allowed_fields = ["display_name", "bio", "favorite_quote", "privacy_settings", 
                         "notification_preferences", "theme"]
        
        for field, value in updates.items():
            if field in allowed_fields:
                profile[field] = value
        
        profile["last_updated"] = datetime.now(TZ).isoformat()
        
        # Speichere Updates
        with open(self.profiles_file, "r", encoding="utf-8") as f:
            profiles = json.load(f)
        
        profiles[user] = profile
        
        with open(self.profiles_file, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        
        return profile
    
    def get_user_customization(self, user):
        """Lade User Avatar-Customization"""
        try:
            with open(self.customization_file, "r", encoding="utf-8") as f:
                customizations = json.load(f)
        except:
            customizations = {}
        
        default_customization = {
            "avatar": {
                "background": "gradient_blue",
                "border": "simple", 
                "effect": "none",
                "title": "none"
            },
            "unlocked_items": ["gradient_blue", "simple", "none"]
        }
        
        return customizations.get(user, default_customization)
    
    def update_user_customization(self, user, customization_data):
        """Update User Avatar-Customization"""
        try:
            with open(self.customization_file, "r", encoding="utf-8") as f:
                customizations = json.load(f)
        except:
            customizations = {}
        
        current = self.get_user_customization(user)
        
        # Prüfe ob Items freigeschaltet sind
        for component, item in customization_data.get("avatar", {}).items():
            if item not in current.get("unlocked_items", []):
                return {"success": False, "message": f"{item} ist noch nicht freigeschaltet"}
        
        # Update Customization
        current["avatar"].update(customization_data.get("avatar", {}))
        customizations[user] = current
        
        with open(self.customization_file, "w", encoding="utf-8") as f:
            json.dump(customizations, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": "Avatar erfolgreich aktualisiert"}
    
    def check_unlock_progress(self, user):
        """Prüfe und schalte neue Customization-Items frei"""
        unlocked_items = []

        # Admin-Users bekommen automatisch alles freigeschaltet
        admin_users = ["Luke", "admin", "Jose", "Simon", "Alex", "David"]
        if user in admin_users:
            # Sammle alle Item-IDs
            all_items = []
            for category, items in AVATAR_COMPONENTS.items():
                all_items.extend(items.keys())
            for theme_id in THEMES.keys():
                all_items.append(theme_id)

            return {
                "total_unlocked": all_items,
                "newly_unlocked": [],
                "unlock_count": len(all_items)
            }

        try:
            # Lade User-Daten für Unlock-Prüfung
            from level_system import LevelSystem
            from achievement_system import achievement_system
            from prestige_system import prestige_system

            level_system = LevelSystem()
            user_level = level_system.calculate_user_level(user)
            user_badges = achievement_system.get_user_badges(user)
            user_prestige = prestige_system.calculate_user_prestige(user)

            current_level = user_level["level"]
            badge_rarities = [b.get("rarity", "common") for b in user_badges.get("badges", [])]
            prestige_level = user_prestige["prestige_level"]

            # Daily stats für Streak-Check
            daily_stats = achievement_system.load_daily_stats()
            user_stats = daily_stats.get(user, {})
            streak_info = achievement_system.calculate_advanced_streak(user_stats)
            current_streak = streak_info.get("work_streak", 0)
            
            # Prüfe alle Avatar-Komponenten
            for category, items in AVATAR_COMPONENTS.items():
                for item_id, item_data in items.items():
                    unlock_condition = item_data["unlock"]
                    should_unlock = False
                    
                    if unlock_condition == "free":
                        should_unlock = True
                    elif unlock_condition.startswith("level_"):
                        required_level = int(unlock_condition.split("_")[1])
                        should_unlock = current_level >= required_level
                    elif unlock_condition.startswith("badge_"):
                        required_rarity = unlock_condition.split("_")[1]
                        should_unlock = required_rarity in badge_rarities
                    elif unlock_condition.startswith("prestige_"):
                        required_prestige = int(unlock_condition.split("_")[1])
                        should_unlock = prestige_level >= required_prestige
                    elif unlock_condition.startswith("streak_"):
                        required_streak = int(unlock_condition.split("_")[1])
                        should_unlock = current_streak >= required_streak
                    
                    if should_unlock:
                        unlocked_items.append(item_id)
            
            # Prüfe Themes
            for theme_id, theme_data in THEMES.items():
                unlock_condition = theme_data["unlock"]
                should_unlock = False
                
                if unlock_condition == "free":
                    should_unlock = True
                elif unlock_condition.startswith("level_"):
                    required_level = int(unlock_condition.split("_")[1])
                    should_unlock = current_level >= required_level
                elif unlock_condition.startswith("badge_"):
                    required_rarity = unlock_condition.split("_")[1]
                    should_unlock = required_rarity in badge_rarities
                elif unlock_condition.startswith("prestige_"):
                    required_prestige = int(unlock_condition.split("_")[1])
                    should_unlock = prestige_level >= required_prestige
                elif unlock_condition.startswith("streak_"):
                    required_streak = int(unlock_condition.split("_")[1])
                    should_unlock = current_streak >= required_streak
                
                if should_unlock:
                    unlocked_items.append(theme_id)
            
            # Update unlocked items
            customization = self.get_user_customization(user)
            existing_unlocked = set(customization.get("unlocked_items", []))
            new_unlocked = set(unlocked_items)
            
            newly_unlocked = list(new_unlocked - existing_unlocked)
            
            if newly_unlocked:
                customization["unlocked_items"] = list(new_unlocked)
                
                try:
                    with open(self.customization_file, "r", encoding="utf-8") as f:
                        customizations = json.load(f)
                except:
                    customizations = {}
                
                customizations[user] = customization
                
                with open(self.customization_file, "w", encoding="utf-8") as f:
                    json.dump(customizations, f, ensure_ascii=False, indent=2)
            
            return {
                "newly_unlocked": newly_unlocked,
                "total_unlocked": list(new_unlocked)
            }
        
        except Exception as e:
            print(f"Fehler beim Unlock-Check für {user}: {e}")
            return {"newly_unlocked": [], "total_unlocked": []}
    
    def get_personal_goals(self, user):
        """Lade persönliche Ziele eines Users"""
        try:
            with open(self.goals_file, "r", encoding="utf-8") as f:
                goals = json.load(f)
        except:
            goals = {}
        
        user_goals = goals.get(user, [])
        
        # Update progress for existing goals
        updated_goals = []
        for goal in user_goals:
            updated_goal = self._update_goal_progress(user, goal)
            updated_goals.append(updated_goal)
        
        return updated_goals
    
    def create_personal_goal(self, user, goal_template, custom_target=None):
        """Erstelle neues persönliches Ziel"""
        if goal_template not in GOAL_TEMPLATES:
            return {"success": False, "message": "Unbekannte Ziel-Vorlage"}
        
        template = GOAL_TEMPLATES[goal_template]
        target = custom_target if custom_target else template["default_target"]
        
        # Validiere Target
        if target < template["min_target"] or target > template["max_target"]:
            return {"success": False, 
                   "message": f"Ziel muss zwischen {template['min_target']} und {template['max_target']} liegen"}
        
        new_goal = {
            "id": f"{goal_template}_{datetime.now(TZ).timestamp()}",
            "template": goal_template,
            "name": template["name"],
            "description": template["description"].replace("X", str(target)),
            "type": template["type"],
            "target": target,
            "current_progress": 0,
            "created_at": datetime.now(TZ).isoformat(),
            "deadline": self._calculate_deadline(template["type"]),
            "reward_multiplier": template["reward_multiplier"],
            "completed": False,
            "claimed": False
        }
        
        # Speichere Ziel
        try:
            with open(self.goals_file, "r", encoding="utf-8") as f:
                goals = json.load(f)
        except:
            goals = {}
        
        if user not in goals:
            goals[user] = []
        
        goals[user].append(new_goal)
        
        with open(self.goals_file, "w", encoding="utf-8") as f:
            json.dump(goals, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": "Persönliches Ziel erstellt!", "goal": new_goal}
    
    def _calculate_deadline(self, goal_type):
        """Berechne Deadline basierend auf Ziel-Typ"""
        now = datetime.now(TZ)
        
        if goal_type == "daily":
            return (now + timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()
        elif goal_type == "weekly":
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            return (now + timedelta(days=days_until_sunday)).replace(hour=23, minute=59, second=59).isoformat()
        else:
            return (now + timedelta(days=30)).replace(hour=23, minute=59, second=59).isoformat()
    
    def _update_goal_progress(self, user, goal):
        """Update Fortschritt eines persönlichen Ziels"""
        try:
            goal_type = goal["type"]
            template = goal["template"]
            target = goal["target"]
            
            current_progress = 0
            
            if goal_type == "daily":
                # Heutige Punkte
                from achievement_system import achievement_system
                daily_stats = achievement_system.load_daily_stats()
                today = datetime.now(TZ).strftime("%Y-%m-%d")
                user_stats = daily_stats.get(user, {})
                current_progress = user_stats.get(today, {}).get("points", 0)
            
            elif goal_type == "weekly":
                # Wöchentliche Buchungen
                if template == "weekly_bookings":
                    from tracking_system import BookingTracker
                    tracker = BookingTracker()
                    all_bookings = tracker.load_all_bookings()
                    
                    # Aktuelle Woche
                    now = datetime.now(TZ)
                    week_start = now - timedelta(days=now.weekday())
                    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    week_bookings = [b for b in all_bookings 
                                   if b.get("user") == user and 
                                   datetime.fromisoformat(b.get("timestamp", "2000-01-01")) >= week_start]
                    current_progress = len(week_bookings)
            
            elif goal_type == "streak":
                # Streak-Ziele
                from achievement_system import achievement_system
                daily_stats = achievement_system.load_daily_stats()
                user_stats = daily_stats.get(user, {})
                streak_info = achievement_system.calculate_advanced_streak(user_stats)
                current_progress = streak_info.get("work_streak", 0)
            
            elif goal_type == "collection":
                # Badge-Sammlung
                if template == "badge_collection":
                    from achievement_system import achievement_system
                    user_badges = achievement_system.get_user_badges(user)
                    
                    # Zähle Badges seit Ziel-Erstellung
                    created_at = datetime.fromisoformat(goal["created_at"])
                    recent_badges = [b for b in user_badges.get("badges", [])
                                   if datetime.fromisoformat(b.get("earned_date", "2000-01-01")) >= created_at]
                    current_progress = len(recent_badges)
            
            elif goal_type == "ranking":
                # Ranking-Ziele
                from data_persistence import data_persistence
                scores = data_persistence.load_scores()
                current_month = datetime.now(TZ).strftime("%Y-%m")
                
                user_score = scores.get(user, {}).get(current_month, 0)
                all_scores = [(u, s.get(current_month, 0)) for u, s in scores.items()]
                all_scores.sort(key=lambda x: x[1], reverse=True)
                
                current_rank = next((i + 1 for i, (u, s) in enumerate(all_scores) if u == user), 999)
                current_progress = target - current_rank + 1 if current_rank <= target else 0
            
            # Update goal
            goal["current_progress"] = current_progress
            goal["completed"] = current_progress >= target
            goal["progress_percent"] = min(100, (current_progress / target) * 100) if target > 0 else 0
            
            # Prüfe Deadline
            try:
                deadline = datetime.fromisoformat(goal["deadline"])
                goal["expired"] = datetime.now(TZ) > deadline
            except:
                goal["expired"] = False
        
        except Exception as e:
            print(f"Fehler beim Goal-Update für {user}: {e}")
        
        return goal
    
    def claim_goal_reward(self, user, goal_id):
        """Hole Belohnung für abgeschlossenes persönliches Ziel ab"""
        user_goals = self.get_personal_goals(user)
        goal = next((g for g in user_goals if g["id"] == goal_id), None)
        
        if not goal:
            return {"success": False, "message": "Ziel nicht gefunden"}
        
        if not goal["completed"]:
            return {"success": False, "message": "Ziel noch nicht abgeschlossen"}
        
        if goal.get("claimed", False):
            return {"success": False, "message": "Belohnung bereits abgeholt"}
        
        # Berechne Belohnung
        base_reward = 50  # Base XP
        multiplied_reward = int(base_reward * goal["reward_multiplier"])
        
        # Markiere als abgeholt
        goal["claimed"] = True
        goal["claimed_at"] = datetime.now(TZ).isoformat()
        
        # Speichere Update
        try:
            with open(self.goals_file, "r", encoding="utf-8") as f:
                goals = json.load(f)
        except:
            goals = {}
        
        goals[user] = user_goals
        
        with open(self.goals_file, "w", encoding="utf-8") as f:
            json.dump(goals, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": f"Belohnung für '{goal['name']}' erhalten!",
            "reward": {
                "xp": multiplied_reward,
                "goal_title": goal["name"]
            }
        }
    
    def get_customization_shop(self, user):
        """Hole verfügbare Customization-Items mit Unlock-Status"""
        unlocked = self.check_unlock_progress(user)
        unlocked_items = set(unlocked["total_unlocked"])
        
        shop = {
            "avatar_components": {},
            "themes": {},
            "locked_count": 0,
            "unlocked_count": len(unlocked_items)
        }
        
        # Avatar Components
        for category, items in AVATAR_COMPONENTS.items():
            shop["avatar_components"][category] = []
            for item_id, item_data in items.items():
                shop["avatar_components"][category].append({
                    "id": item_id,
                    "name": item_data["name"],
                    "unlocked": item_id in unlocked_items,
                    "unlock_condition": item_data["unlock"],
                    "preview": item_data
                })
        
        # Themes
        for theme_id, theme_data in THEMES.items():
            shop["themes"][theme_id] = {
                "id": theme_id,
                "name": theme_data["name"],
                "unlocked": theme_id in unlocked_items,
                "unlock_condition": theme_data["unlock"],
                "preview": theme_data
            }
        
        # Zähle locked items
        all_items = sum(len(items) for items in AVATAR_COMPONENTS.values()) + len(THEMES)
        shop["locked_count"] = all_items - len(unlocked_items)
        
        return shop

# Globale Instanz
personalization_system = PersonalizationSystem()