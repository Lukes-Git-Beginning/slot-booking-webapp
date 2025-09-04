# -*- coding: utf-8 -*-
"""
Achievement/Badge System für Slot Booking Webapp
Gamification mit Badges, Achievements und MVP-System
"""

import os
import json
import pytz
from datetime import datetime, timedelta
from collections import defaultdict

TZ = pytz.timezone("Europe/Berlin")

# Definiere alle verfügbaren Badges
ACHIEVEMENT_DEFINITIONS = {
    # Tägliche Punkte Badges
    "daily_10": {
        "name": "Anfänger 🌱",
        "description": "10 Punkte an einem Tag erreicht",
        "category": "daily",
        "threshold": 10,
        "emoji": "🌱",
        "rarity": "common"
    },
    "daily_20": {
        "name": "Aufsteiger ⭐",
        "description": "20 Punkte an einem Tag erreicht",
        "category": "daily", 
        "threshold": 20,
        "emoji": "⭐",
        "rarity": "uncommon"
    },
    "daily_40": {
        "name": "Champion 🏆",
        "description": "40 Punkte an einem Tag erreicht",
        "category": "daily",
        "threshold": 40,
        "emoji": "🏆",
        "rarity": "rare"
    },
    "daily_60": {
        "name": "Legende 👑",
        "description": "60 Punkte an einem Tag erreicht",
        "category": "daily",
        "threshold": 60,
        "emoji": "👑",
        "rarity": "legendary"
    },
    
    # Wöchentliche Punkte Badges
    "weekly_50": {
        "name": "Wochenkrieger ⚔️",
        "description": "100 Punkte in einer Woche erreicht",
        "category": "weekly",
        "threshold": 100,
        "emoji": "⚔️",
        "rarity": "uncommon"
    },
    "weekly_100": {
        "name": "Wochenmeister 🎯",
        "description": "200 Punkte in einer Woche erreicht",
        "category": "weekly",
        "threshold": 200,
        "emoji": "🎯",
        "rarity": "rare"
    },
    
    # MVP Badges
    "mvp_week": {
        "name": "Wochenmvp 🥇",
        "description": "Beste Woche - Wochenkönig",
        "category": "mvp",
        "emoji": "🥇",
        "rarity": "epic"
    },
    "mvp_month": {
        "name": "Monatsmvp 👑",
        "description": "Bester Monat - Monatskönig",
        "category": "mvp", 
        "emoji": "👑",
        "rarity": "legendary"
    },
    "mvp_year": {
        "name": "Jahresmvp 💎",
        "description": "Bestes Jahr - Absolute Legende",
        "category": "mvp",
        "emoji": "💎",
        "rarity": "mythic"
    },
    
    # Streak Badges
    "streak_2": {
        "name": "Konstant 🔥",
        "description": "2 Arbeitstage in Folge aktiv",
        "category": "streak",
        "threshold": 2,
        "emoji": "🔥",
        "rarity": "common"
    },
    "streak_5": {
        "name": "Durchhalter 💪",
        "description": "5 Arbeitstage in Folge aktiv",
        "category": "streak",
        "threshold": 5,
        "emoji": "💪",
        "rarity": "uncommon"
    },
    "streak_10": {
        "name": "Eiserner Wille ⚡",
        "description": "10 Arbeitstage in Folge aktiv",
        "category": "streak",
        "threshold": 10,
        "emoji": "⚡",
        "rarity": "rare"
    },
    
    # All-Time Total Badges
    "total_50": {
        "name": "Anfänger 📈",
        "description": "Insgesamt 50 Kunden gelegt",
        "category": "total",
        "threshold": 50,
        "emoji": "📈",
        "rarity": "common"
    },
    "total_100": {
        "name": "Erfahren 🎯",
        "description": "Insgesamt 100 Kunden gelegt",
        "category": "total",
        "threshold": 100,
        "emoji": "🎯",
        "rarity": "uncommon"
    },
    "total_150": {
        "name": "Profi 🏆",
        "description": "Insgesamt 150 Kunden gelegt",
        "category": "total",
        "threshold": 150,
        "emoji": "🏆",
        "rarity": "rare"
    },
    "total_250": {
        "name": "Erfahrener ⚔️",
        "description": "Insgesamt 250 Kunden gelegt",
        "category": "total",
        "threshold": 250,
        "emoji": "⚔️",
        "rarity": "epic"
    },
    "total_500": {
        "name": "Meister 👑",
        "description": "Insgesamt 500 Kunden gelegt",
        "category": "total",
        "threshold": 500,
        "emoji": "👑",
        "rarity": "legendary"
    },
    "total_1000": {
        "name": "Legende 💎",
        "description": "Insgesamt 1000 Kunden gelegt",
        "category": "total",
        "threshold": 1000,
        "emoji": "💎",
        "rarity": "mythic"
    },
    "streak_7": {
        "name": "Unaufhaltbar 🚀",
        "description": "7 Arbeitstage in Folge aktiv", 
        "category": "streak",
        "threshold": 7,
        "emoji": "🚀",
        "rarity": "rare"
    },
    
    # Spezial Badges
    "first_booking": {
        "name": "Neuling 🎯",
        "description": "Erste Buchung gemacht",
        "category": "special",
        "emoji": "🎯",
        "rarity": "common"
    },
    "night_owl": {
        "name": "Nachteule 🦉",
        "description": "10 Abendtermine (20:00) gebucht",
        "category": "special", 
        "threshold": 10,
        "emoji": "🦉",
        "rarity": "uncommon"
    }
}

RARITY_COLORS = {
    "common": "#10b981",      # Grün
    "uncommon": "#3b82f6",    # Blau  
    "rare": "#8b5cf6",        # Lila
    "epic": "#f59e0b",        # Orange
    "legendary": "#eab308",   # Gold
    "mythic": "#ec4899"       # Pink
}

class AchievementSystem:
    def __init__(self):
        self.badges_file = "static/user_badges.json"
        self.daily_stats_file = "static/daily_user_stats.json"
        os.makedirs("static", exist_ok=True)
        
        # Initialisiere Files wenn nicht vorhanden
        for file_path in [self.badges_file, self.daily_stats_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
    
    def load_badges(self):
        """Lade alle User-Badges"""
        try:
            with open(self.badges_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_badges(self, badges_data):
        """Speichere User-Badges"""
        try:
            with open(self.badges_file, "w", encoding="utf-8") as f:
                json.dump(badges_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der Badges: {e}")
    
    def load_daily_stats(self):
        """Lade tägliche User-Statistiken"""
        try:
            with open(self.daily_stats_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_daily_stats(self, stats_data):
        """Speichere tägliche User-Statistiken"""
        try:
            with open(self.daily_stats_file, "w", encoding="utf-8") as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der Stats: {e}")
    
    def add_points_and_check_achievements(self, user, points, slot_time="", context=""):
        """
        Füge Punkte hinzu und prüfe auf neue Achievements
        Erweitert die bestehende add_points_to_user Funktion
        """
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        month = datetime.now(TZ).strftime("%Y-%m")
        
        # Aktualisiere tägliche Stats
        daily_stats = self.load_daily_stats()
        if user not in daily_stats:
            daily_stats[user] = {}
        if today not in daily_stats[user]:
            daily_stats[user][today] = {
                "points": 0,
                "bookings": 0,
                "evening_bookings": 0,
                "first_booking": False
            }
        
        # Update Stats
        daily_stats[user][today]["points"] += points
        daily_stats[user][today]["bookings"] += 1
        
        # Spezielle Tracking
        if slot_time.startswith("20:"):
            daily_stats[user][today]["evening_bookings"] += 1
        
        if daily_stats[user][today]["bookings"] == 1 and len(daily_stats[user]) == 1:
            daily_stats[user][today]["first_booking"] = True
        
        self.save_daily_stats(daily_stats)
        
        # Prüfe Achievements
        new_badges = self.check_achievements(user, daily_stats[user])
        
        return new_badges
    
    def check_achievements(self, user, user_stats):
        """Prüfe alle möglichen Achievements für einen User"""
        badges_data = self.load_badges()
        if user not in badges_data:
            badges_data[user] = {
                "badges": [],
                "earned_dates": {},
                "total_badges": 0
            }
        
        new_badges = []
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        user_badges = [badge["id"] for badge in badges_data[user]["badges"]]
        
        # 1. Tägliche Punkte Badges prüfen
        today_points = user_stats.get(today, {}).get("points", 0)
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if definition["category"] == "daily" and badge_id not in user_badges:
                if today_points >= definition["threshold"]:
                    new_badge = self.award_badge(user, badge_id, definition, badges_data)
                    if new_badge:
                        new_badges.append(new_badge)
        
        # 2. Wöchentliche Punkte prüfen
        week_points = self.calculate_week_points(user_stats)
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if definition["category"] == "weekly" and badge_id not in user_badges:
                if week_points >= definition["threshold"]:
                    new_badge = self.award_badge(user, badge_id, definition, badges_data)
                    if new_badge:
                        new_badges.append(new_badge)
        
        # 3. Streak Badges prüfen
        current_streak = self.calculate_streak(user_stats)
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if definition["category"] == "streak" and badge_id not in user_badges:
                if current_streak >= definition["threshold"]:
                    new_badge = self.award_badge(user, badge_id, definition, badges_data)
                    if new_badge:
                        new_badges.append(new_badge)
        
        # 4. All-Time Total Badges prüfen
        total_bookings = sum(stats.get("bookings", 0) for stats in user_stats.values())
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if definition["category"] == "total" and badge_id not in user_badges:
                if total_bookings >= definition["threshold"]:
                    new_badge = self.award_badge(user, badge_id, definition, badges_data)
                    if new_badge:
                        new_badges.append(new_badge)
        
        # 5. Spezielle Badges prüfen
        self.check_special_badges(user, user_stats, badges_data, new_badges)
        
        # 5. MVP Badges werden separat vergeben (siehe check_and_award_mvp_badges)
        
        self.save_badges(badges_data)
        return new_badges
    
    def check_special_badges(self, user, user_stats, badges_data, new_badges):
        """Prüfe spezielle Achievement-Bedingungen"""
        user_badges = [badge["id"] for badge in badges_data[user]["badges"]]
        
        # First Booking Badge
        if "first_booking" not in user_badges:
            for date, stats in user_stats.items():
                if stats.get("first_booking", False):
                    definition = ACHIEVEMENT_DEFINITIONS["first_booking"]
                    new_badge = self.award_badge(user, "first_booking", definition, badges_data)
                    if new_badge:
                        new_badges.append(new_badge)
                    break
        
        # Night Owl Badge
        if "night_owl" not in user_badges:
            total_evening = sum(stats.get("evening_bookings", 0) for stats in user_stats.values())
            if total_evening >= 10:
                definition = ACHIEVEMENT_DEFINITIONS["night_owl"]
                new_badge = self.award_badge(user, "night_owl", definition, badges_data)
                if new_badge:
                    new_badges.append(new_badge)
    
    def award_badge(self, user, badge_id, definition, badges_data):
        """Vergebe ein Badge an einen User"""
        if user not in badges_data:
            badges_data[user] = {"badges": [], "earned_dates": {}, "total_badges": 0}
        
        # Prüfe ob Badge bereits vorhanden
        existing_badges = [badge["id"] for badge in badges_data[user]["badges"]]
        if badge_id in existing_badges:
            return None
        
        # Erstelle Badge-Objekt
        badge = {
            "id": badge_id,
            "name": definition["name"],
            "description": definition["description"],
            "emoji": definition["emoji"],
            "rarity": definition["rarity"],
            "category": definition["category"],
            "earned_date": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "color": RARITY_COLORS[definition["rarity"]]
        }
        
        # Füge Badge hinzu
        badges_data[user]["badges"].append(badge)
        badges_data[user]["earned_dates"][badge_id] = badge["earned_date"]
        badges_data[user]["total_badges"] += 1
        
        print(f"🎖️ Badge verliehen: {user} erhält '{definition['name']}' ({definition['emoji']})")
        
        return badge
    
    def calculate_week_points(self, user_stats):
        """Berechne Punkte der aktuellen Woche"""
        today = datetime.now(TZ).date()
        week_start = today - timedelta(days=today.weekday())
        
        week_points = 0
        for i in range(7):
            check_date = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
            week_points += user_stats.get(check_date, {}).get("points", 0)
        
        return week_points
    
    def calculate_streak(self, user_stats):
        """Berechne aktuelle Streak (aufeinanderfolgende Arbeitstage mit Aktivität)"""
        today = datetime.now(TZ).date()
        streak = 0
        
        # Gehe rückwärts durch die Tage
        for i in range(60):  # Max 60 Tage zurück prüfen (für längere Streaks)
            check_date = (today - timedelta(days=i))
            
            # Nur Arbeitstage berücksichtigen (Montag-Freitag)
            if check_date.weekday() < 5:  # 0=Montag, 4=Freitag
                check_date_str = check_date.strftime("%Y-%m-%d")
                if check_date_str in user_stats and user_stats[check_date_str].get("points", 0) > 0:
                    streak += 1
                else:
                    break  # Streak unterbrochen
            # Wochenenden überspringen - Streak bleibt bestehen
        
        return streak
    
    def check_and_award_mvp_badges(self):
        """
        Prüfe und vergebe MVP Badges
        Sollte wöchentlich/monatlich als Cron Job laufen
        """
        badges_data = self.load_badges()
        
        # Lade Scores für MVP-Bestimmung
        try:
            from data_persistence import data_persistence
            scores = data_persistence.load_scores()
        except:
            return
        
        current_date = datetime.now(TZ)
        
        # 1. Wochen-MVP (jeden Montag prüfen)
        if current_date.weekday() == 0:  # Montag
            self.award_weekly_mvp(scores, badges_data, current_date)
        
        # 2. Monats-MVP (jeden 1. des Monats prüfen)
        if current_date.day == 1:
            self.award_monthly_mvp(scores, badges_data, current_date)
        
        # 3. Jahres-MVP (jeden 1. Januar prüfen)
        if current_date.month == 1 and current_date.day == 1:
            self.award_yearly_mvp(scores, badges_data, current_date)
        
        self.save_badges(badges_data)
    
    def award_weekly_mvp(self, scores, badges_data, current_date):
        """Vergebe Wochen-MVP Badge"""
        # Berechne Punkte der letzten Woche
        last_week = current_date - timedelta(weeks=1)
        week_scores = defaultdict(int)
        
        daily_stats = self.load_daily_stats()
        
        for user, user_daily_stats in daily_stats.items():
            for date_str, stats in user_daily_stats.items():
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                week_start = last_week.date() - timedelta(days=last_week.weekday())
                week_end = week_start + timedelta(days=6)
                
                if week_start <= date_obj <= week_end:
                    week_scores[user] += stats.get("points", 0)
        
        if week_scores:
            mvp_user = max(week_scores.keys(), key=lambda x: week_scores[x])
            if week_scores[mvp_user] > 0:
                definition = ACHIEVEMENT_DEFINITIONS["mvp_week"]
                self.award_badge(mvp_user, f"mvp_week_{last_week.strftime('%Y_W%V')}", definition, badges_data)
    
    def award_monthly_mvp(self, scores, badges_data, current_date):
        """Vergebe Monats-MVP Badge"""
        last_month = (current_date.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        
        # Finde User mit höchsten Punkten im letzten Monat
        month_scores = {}
        for user, user_scores in scores.items():
            month_scores[user] = user_scores.get(last_month, 0)
        
        if month_scores:
            mvp_user = max(month_scores.keys(), key=lambda x: month_scores[x])
            if month_scores[mvp_user] > 0:
                definition = ACHIEVEMENT_DEFINITIONS["mvp_month"]
                self.award_badge(mvp_user, f"mvp_month_{last_month}", definition, badges_data)
    
    def award_yearly_mvp(self, scores, badges_data, current_date):
        """Vergebe Jahres-MVP Badge"""
        last_year = current_date.year - 1
        
        # Berechne Jahres-Punkte
        year_scores = defaultdict(int)
        for user, user_scores in scores.items():
            for month, points in user_scores.items():
                if month.startswith(str(last_year)):
                    year_scores[user] += points
        
        if year_scores:
            mvp_user = max(year_scores.keys(), key=lambda x: year_scores[x])
            if year_scores[mvp_user] > 0:
                definition = ACHIEVEMENT_DEFINITIONS["mvp_year"]
                self.award_badge(mvp_user, f"mvp_year_{last_year}", definition, badges_data)
    
    def get_user_badges(self, user):
        """Hole alle Badges eines Users"""
        badges_data = self.load_badges()
        return badges_data.get(user, {"badges": [], "total_badges": 0})
    
    def get_badge_leaderboard(self):
        """Erstelle Rangliste nach Badge-Anzahl"""
        badges_data = self.load_badges()
        leaderboard = []
        
        for user, data in badges_data.items():
            # Zähle Badges nach Seltenheit für Gewichtung
            rarity_points = 0
            rarity_counts = defaultdict(int)
            
            for badge in data["badges"]:
                rarity = badge["rarity"]
                rarity_counts[rarity] += 1
                
                # Gewichtung nach Seltenheit
                weights = {
                    "common": 1,
                    "uncommon": 2,
                    "rare": 4,
                    "epic": 6,
                    "legendary": 10,
                    "mythic": 20
                }
                rarity_points += weights.get(rarity, 1)
            
            leaderboard.append({
                "user": user,
                "total_badges": data["total_badges"],
                "rarity_points": rarity_points,
                "rarity_breakdown": dict(rarity_counts),
                "badges": data["badges"]
            })
        
        # Sortiere nach Rarity Points, dann nach Total Badges
        leaderboard.sort(key=lambda x: (x["rarity_points"], x["total_badges"]), reverse=True)
        
        return leaderboard
    
    def get_all_badge_definitions(self):
        """Gebe alle Badge-Definitionen zurück"""
        return ACHIEVEMENT_DEFINITIONS
    
    def get_user_badge_progress(self, user):
        """Berechne den Fortschritt eines Users für alle Badges"""
        progress = {}
        daily_stats = self.load_daily_stats()
        user_stats = daily_stats.get(user, {})
        
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        today_points = user_stats.get(today, {}).get("points", 0)
        
        # Berechne Wochenpunkte
        week_start = datetime.now(TZ) - timedelta(days=datetime.now(TZ).weekday())
        week_points = 0
        for date_str, stats in user_stats.items():
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_obj >= week_start.date():
                    week_points += stats.get("points", 0)
            except:
                continue
        
        # Berechne Streak
        current_streak = self.calculate_streak(user_stats)
        
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            earned = False
            current = 0
            target = definition.get("threshold", 0)
            
            if definition["category"] == "daily":
                current = today_points
                earned = current >= target
            elif definition["category"] == "weekly":
                current = week_points
                earned = current >= target
            elif definition["category"] == "streak":
                current = current_streak
                earned = current >= target
            elif definition["category"] == "mvp":
                # MVP Badges werden separat vergeben
                earned = False
                current = 0
                target = 1
            elif definition["category"] == "special":
                # Spezielle Badges haben eigene Logik
                if badge_id == "first_booking":
                    earned = any(stats.get("first_booking", False) for stats in user_stats.values())
                elif badge_id == "night_owl":
                    total_evening = sum(stats.get("evening_bookings", 0) for stats in user_stats.values())
                    current = total_evening
                    target = 10
                    earned = current >= target
            
            progress[badge_id] = {
                "earned": earned,
                "current": current,
                "target": target,
                "progress_percent": min(100, (current / target * 100) if target > 0 else 0)
            }
        
        return progress

# Globale Instanz für Import in anderen Modulen
achievement_system = AchievementSystem()