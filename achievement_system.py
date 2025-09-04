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
    
    # Monatliche Punkte Badges
    "monthly_10": {
        "name": "Monatsanfänger 📅",
        "description": "10 Punkte in einem Monat erreicht",
        "category": "monthly",
        "threshold": 10,
        "emoji": "📅",
        "rarity": "common"
    },
    "monthly_25": {
        "name": "Monatsprofi 📊",
        "description": "25 Punkte in einem Monat erreicht",
        "category": "monthly",
        "threshold": 25,
        "emoji": "📊",
        "rarity": "uncommon"
    },
    "monthly_50": {
        "name": "Monatschampion 🏅",
        "description": "50 Punkte in einem Monat erreicht",
        "category": "monthly",
        "threshold": 50,
        "emoji": "🏅",
        "rarity": "rare"
    },
    "monthly_100": {
        "name": "Monatslegende 🌟",
        "description": "100 Punkte in einem Monat erreicht",
        "category": "monthly",
        "threshold": 100,
        "emoji": "🌟",
        "rarity": "epic"
    },
    
    # Gesamtpunkte Badges
    "total_50": {
        "name": "Erfahrener Spieler 🎮",
        "description": "50 Gesamtpunkte erreicht",
        "category": "total",
        "threshold": 50,
        "emoji": "🎮",
        "rarity": "common"
    },
    "total_100": {
        "name": "Veteran 🛡️",
        "description": "100 Gesamtpunkte erreicht",
        "category": "total",
        "threshold": 100,
        "emoji": "🛡️",
        "rarity": "uncommon"
    },
    "total_250": {
        "name": "Elite-Spieler ⚡",
        "description": "250 Gesamtpunkte erreicht",
        "category": "total",
        "threshold": 250,
        "emoji": "⚡",
        "rarity": "rare"
    },
    "total_500": {
        "name": "Ultimate Champion 🏆",
        "description": "500 Gesamtpunkte erreicht",
        "category": "total",
        "threshold": 500,
        "emoji": "🏆",
        "rarity": "legendary"
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
    "streak_20": {
        "name": "Unaufhaltsam 🚀",
        "description": "20 Arbeitstage in Folge aktiv",
        "category": "streak",
        "threshold": 20,
        "emoji": "🚀",
        "rarity": "epic"
    },
    
    # Spezielle Badges
    "first_booking": {
        "name": "Erste Schritte 👣",
        "description": "Erste Buchung getätigt",
        "category": "special",
        "emoji": "👣",
        "rarity": "common"
    },
    "night_owl": {
        "name": "Nachteule 🌙",
        "description": "10 Abendtermine gebucht (18:00+ Uhr)",
        "category": "special",
        "threshold": 10,
        "emoji": "🌙",
        "rarity": "uncommon"
    },
    "early_bird": {
        "name": "Früher Vogel 🌅",
        "description": "10 Vormittagstermine gebucht (9:00-12:00 Uhr)",
        "category": "special",
        "threshold": 10,
        "emoji": "🌅",
        "rarity": "uncommon"
    },
    "weekend_warrior": {
        "name": "Wochenend-Krieger ⚔️",
        "description": "5 Termine am Freitag gebucht",
        "category": "special",
        "threshold": 5,
        "emoji": "⚔️",
        "rarity": "rare"
    }
}

# Raritäts-Farben für Badges
RARITY_COLORS = {
    "common": "#10b981",
    "uncommon": "#3b82f6", 
    "rare": "#8b5cf6",
    "epic": "#f59e0b",
    "legendary": "#eab308",
    "mythic": "#ec4899"
}

class AchievementSystem:
    def __init__(self):
        self.badges_file = "static/user_badges.json"
        self.mvp_file = "static/mvp_badges.json"
        os.makedirs("static", exist_ok=True)
        
        # Initialisiere Files wenn nicht vorhanden
        if not os.path.exists(self.badges_file):
            with open(self.badges_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
        
        if not os.path.exists(self.mvp_file):
            with open(self.mvp_file, "w", encoding="utf-8") as f:
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
    
    def load_mvp_badges(self):
        """Lade MVP-Badges"""
        try:
            with open(self.mvp_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_mvp_badges(self, mvp_data):
        """Speichere MVP-Badges"""
        try:
            with open(self.mvp_file, "w", encoding="utf-8") as f:
                json.dump(mvp_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der MVP-Badges: {e}")
    
    def load_daily_stats(self):
        """Lade tägliche User-Statistiken"""
        try:
            with open("static/daily_user_stats.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_daily_stats(self, stats_data):
        """Speichere tägliche User-Statistiken"""
        try:
            with open("static/daily_user_stats.json", "w", encoding="utf-8") as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der Stats: {e}")
    
    def add_points_and_check_achievements(self, user, points):
        """
        Erweitert die bestehende add_points_to_user Funktion
        Prüft automatisch auf neue Achievements
        """
        try:
            from data_persistence import data_persistence
            
            # Lade aktuelle Daten
            scores = data_persistence.load_scores()
            daily_stats = data_persistence.load_daily_user_stats()
            badges_data = self.load_badges()
            
            # Update Scores
            month = datetime.now(TZ).strftime("%Y-%m")
            today = datetime.now(TZ).strftime("%Y-%m-%d")
            
            if user not in scores:
                scores[user] = {}
            if month not in scores[user]:
                scores[user][month] = 0
            scores[user][month] += points
            
            # Update Daily Stats
            if user not in daily_stats:
                daily_stats[user] = {}
            if today not in daily_stats[user]:
                daily_stats[user][today] = {"points": 0, "bookings": 0, "first_booking": False}
            
            daily_stats[user][today]["points"] += points
            daily_stats[user][today]["bookings"] += 1
            
            # Markiere erste Buchung
            if not daily_stats[user][today].get("first_booking", False):
                daily_stats[user][today]["first_booking"] = True
            
            # Speichere Updates
            data_persistence.save_scores(scores)
            data_persistence.save_daily_user_stats(daily_stats)
            
            # Prüfe auf neue Badges
            new_badges = self.check_achievements(user, scores, daily_stats, badges_data)
            
            # Automatische MVP-Prüfung
            self.auto_check_mvp_badges()
            
            return new_badges
            
        except Exception as e:
            print(f"❌ Achievement System Fehler: {e}")
            return []
    
    def check_achievements(self, user, scores, daily_stats, badges_data):
        """Prüfe alle Achievement-Bedingungen für einen User"""
        new_badges = []
        
        # 1. Tägliche Punkte Badges
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        if today in daily_stats.get(user, {}):
            daily_points = daily_stats[user][today]["points"]
            for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
                if definition["category"] == "daily" and "threshold" in definition:
                    if daily_points >= definition["threshold"]:
                        new_badge = self.award_badge(user, badge_id, definition, badges_data)
                        if new_badge:
                            new_badges.append(new_badge)
        
        # 2. Wöchentliche Punkte Badges
        week_points = self.calculate_week_points(daily_stats.get(user, {}))
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if definition["category"] == "weekly" and "threshold" in definition:
                if week_points >= definition["threshold"]:
                    new_badge = self.award_badge(user, badge_id, definition, badges_data)
                    if new_badge:
                        new_badges.append(new_badge)
        
        # 3. Monatliche Punkte Badges
        user_scores = scores.get(user, {})
        month_points = sum(user_scores.values())
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if definition["category"] == "monthly" and "threshold" in definition:
                if month_points >= definition["threshold"]:
                    new_badge = self.award_badge(user, badge_id, definition, badges_data)
                    if new_badge:
                        new_badges.append(new_badge)
        
        # 4. Gesamtpunkte Badges
        total_points = sum(sum(month_scores.values()) for month_scores in scores.values())
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if definition["category"] == "total" and "threshold" in definition:
                if total_points >= definition["threshold"]:
                    new_badge = self.award_badge(user, badge_id, definition, badges_data)
                    if new_badge:
                        new_badges.append(new_badge)
        
        # 5. Streak Badges
        streak_info = self.calculate_advanced_streak(daily_stats.get(user, {}))
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if definition["category"] == "streak" and "threshold" in definition:
                if streak_info["best_streak"] >= definition["threshold"]:
                    new_badge = self.award_badge(user, badge_id, definition, badges_data)
                    if new_badge:
                        new_badges.append(new_badge)
        
        # 6. Spezielle Badges
        self.check_special_badges(user, daily_stats.get(user, {}), badges_data, new_badges)
        
        self.save_badges(badges_data)
        return new_badges
    
    def check_special_badges(self, user, user_stats, badges_data, new_badges):
        """Prüfe spezielle Achievement-Bedingungen"""
        user_badges = [badge["id"] for badge in badges_data.get(user, {}).get("badges", [])]
        
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
            check_date = week_start + timedelta(days=i)
            check_date_str = check_date.strftime("%Y-%m-%d")
            if check_date_str in user_stats:
                week_points += user_stats[check_date_str].get("points", 0)
        
        return week_points
    
    def calculate_advanced_streak(self, user_stats):
        """Erweiterte Streak-Berechnung mit verschiedenen Kategorien"""
        today = datetime.now(TZ).date()
        
        # Arbeits-Streak (nur Arbeitstage)
        work_streak = self.calculate_work_streak(user_stats)
        
        # Buchungs-Streak (jeder Tag mit Buchung)
        booking_streak = self.calculate_booking_streak(user_stats)
        
        # Punkte-Streak (jeder Tag mit Punkten)
        points_streak = self.calculate_points_streak(user_stats)
        
        return {
            "work_streak": work_streak,
            "booking_streak": booking_streak, 
            "points_streak": points_streak,
            "best_streak": max(work_streak, booking_streak, points_streak)
        }
    
    def calculate_work_streak(self, user_stats):
        """Berechne Arbeits-Streak (nur Montag-Freitag)"""
        today = datetime.now(TZ).date()
        streak = 0
        
        for i in range(60):
            check_date = today - timedelta(days=i)
            if check_date.weekday() < 5:  # Nur Arbeitstage
                check_date_str = check_date.strftime("%Y-%m-%d")
                if check_date_str in user_stats and user_stats[check_date_str].get("points", 0) > 0:
                    streak += 1
                else:
                    break
        
        return streak
    
    def calculate_booking_streak(self, user_stats):
        """Berechne Buchungs-Streak (jeder Tag mit Buchung)"""
        today = datetime.now(TZ).date()
        streak = 0
        
        for i in range(60):
            check_date = today - timedelta(days=i)
            check_date_str = check_date.strftime("%Y-%m-%d")
            if check_date_str in user_stats and user_stats[check_date_str].get("bookings", 0) > 0:
                streak += 1
            else:
                break
        
        return streak
    
    def calculate_points_streak(self, user_stats):
        """Berechne Punkte-Streak (jeder Tag mit Punkten)"""
        today = datetime.now(TZ).date()
        streak = 0
        
        for i in range(60):
            check_date = today - timedelta(days=i)
            check_date_str = check_date.strftime("%Y-%m-%d")
            if check_date_str in user_stats and user_stats[check_date_str].get("points", 0) > 0:
                streak += 1
            else:
                break
        
        return streak
    
    def auto_check_mvp_badges(self):
        """Automatische MVP-Badge-Vergabe - sollte täglich laufen"""
        try:
            from data_persistence import data_persistence
            scores = data_persistence.load_scores()
            mvp_data = self.load_mvp_badges()
            
            # Monats-MVP
            current_month = datetime.now(TZ).strftime("%Y-%m")
            month_scores = [(u, v.get(current_month, 0)) for u, v in scores.items()]
            if month_scores:
                best_user = max(month_scores, key=lambda x: x[1])[0]
                if best_user and month_scores[0][1] > 0:  # Nur wenn Punkte vorhanden
                    self.award_mvp_badge(best_user, "mvp_month", current_month, mvp_data)
            
            # Jahres-MVP (alle Monate des Jahres)
            current_year = datetime.now(TZ).year
            year_scores = defaultdict(int)
            for user, user_scores in scores.items():
                for month, points in user_scores.items():
                    if month.startswith(str(current_year)):
                        year_scores[user] += points
            
            if year_scores:
                best_user = max(year_scores.items(), key=lambda x: x[1])[0]
                if best_user and year_scores[best_user] > 0:  # Nur wenn Punkte vorhanden
                    self.award_mvp_badge(best_user, "mvp_year", str(current_year), mvp_data)
            
            self.save_mvp_badges(mvp_data)
            
        except Exception as e:
            print(f"❌ MVP-Badge Fehler: {e}")
    
    def award_mvp_badge(self, user, badge_type, period, mvp_data):
        """Vergebe MVP-Badge an User"""
        if user not in mvp_data:
            mvp_data[user] = {"badges": [], "periods": {}}
        
        # Prüfe ob Badge bereits für diese Periode vergeben
        if period in mvp_data[user]["periods"]:
            return None
        
        definition = ACHIEVEMENT_DEFINITIONS[badge_type]
        
        badge = {
            "id": badge_type,
            "name": definition["name"],
            "description": f"{definition['description']} ({period})",
            "emoji": definition["emoji"],
            "rarity": definition["rarity"],
            "category": definition["category"],
            "earned_date": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "period": period,
            "color": RARITY_COLORS[definition["rarity"]]
        }
        
        mvp_data[user]["badges"].append(badge)
        mvp_data[user]["periods"][period] = badge["earned_date"]
        
        print(f"🏆 MVP-Badge verliehen: {user} erhält '{definition['name']}' für {period}")
        
        return badge
    
    def get_user_badges(self, user):
        """Hole alle Badges eines Users - berechnet automatisch basierend auf aktuellen Punkten"""
        # Lade aktuelle Scores
        try:
            from data_persistence import data_persistence
            scores = data_persistence.load_scores()
        except:
            try:
                with open("static/scores.json", "r", encoding="utf-8") as f:
                    scores = json.load(f)
            except:
                scores = {}
        
        # Berechne Badges basierend auf aktuellen Punkten
        user_badges = self.calculate_badges_from_points(user, scores)
        
        return {
            "badges": user_badges,
            "total_badges": len(user_badges)
        }
    
    def calculate_badges_from_points(self, user, scores):
        """Berechne Badges automatisch basierend auf aktuellen Punktzahlen"""
        badges = []
        user_scores = scores.get(user, {})
        
        # Aktueller Monat
        current_month = datetime.now(TZ).strftime("%Y-%m")
        current_month_points = user_scores.get(current_month, 0)
        
        # Gesamtpunkte (alle Monate)
        total_points = sum(user_scores.values())
        
        # Tägliche Punkte (heute)
        daily_stats = self.load_daily_stats()
        user_stats = daily_stats.get(user, {})
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        today_points = user_stats.get(today, {}).get("points", 0)
        
        # Wöchentliche Punkte
        week_start = datetime.now(TZ) - timedelta(days=datetime.now(TZ).weekday())
        week_points = 0
        for date_str, stats in user_stats.items():
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_obj >= week_start.date():
                    week_points += stats.get("points", 0)
            except:
                continue
        
        # Streak berechnen
        current_streak = self.calculate_streak(user_stats)
        
        # Badges basierend auf Punkten vergeben
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            earned = False
            earned_date = None
            
            if definition["category"] == "daily":
                if today_points >= definition.get("threshold", 0):
                    earned = True
                    earned_date = today
            elif definition["category"] == "weekly":
                if week_points >= definition.get("threshold", 0):
                    earned = True
                    earned_date = today
            elif definition["category"] == "streak":
                if current_streak >= definition.get("threshold", 0):
                    earned = True
                    earned_date = today
            elif definition["category"] == "monthly":
                if current_month_points >= definition.get("threshold", 0):
                    earned = True
                    earned_date = current_month
            elif definition["category"] == "total":
                if total_points >= definition.get("threshold", 0):
                    earned = True
                    earned_date = current_month
            elif definition["category"] == "mvp":
                # MVP Badges werden separat vergeben
                earned = False
                current = 0
                target = 1
                if badge_id == "mvp_month":
                    # Prüfe ob User Champion des aktuellen Monats ist
                    try:
                        champions = data_persistence.load_champions()
                        month_champion = champions.get(current_month, {}).get("user")
                        if month_champion == user:
                            earned = True
                            earned_date = current_month
                    except:
                        pass
                elif badge_id == "mvp_year":
                    # Prüfe ob User Champion des aktuellen Jahres ist
                    try:
                        champions = data_persistence.load_champions()
                        year_champion = champions.get(str(current_year), {}).get("user")
                        if year_champion == user:
                            earned = True
                            earned_date = str(current_year)
                    except:
                        pass
            
            if earned:
                badges.append({
                    "id": badge_id,
                    "name": definition["name"],
                    "description": definition["description"],
                    "category": definition["category"],
                    "emoji": definition["emoji"],
                    "rarity": definition["rarity"],
                    "earned_date": earned_date,
                    "threshold": definition.get("threshold", 0)
                })
        
        return badges
    
    def get_badge_leaderboard(self):
        """Erstelle Rangliste nach Badge-Anzahl - berechnet automatisch basierend auf aktuellen Punkten"""
        # Lade aktuelle Scores
        try:
            from data_persistence import data_persistence
            scores = data_persistence.load_scores()
        except:
            try:
                with open("static/scores.json", "r", encoding="utf-8") as f:
                    scores = json.load(f)
            except:
                scores = {}
        
        leaderboard = []
        
        for user in scores.keys():
            # Berechne Badges für jeden User
            user_badges = self.calculate_badges_from_points(user, scores)
            
            # Zähle Badges nach Seltenheit für Gewichtung
            rarity_points = 0
            rarity_counts = defaultdict(int)
            
            for badge in user_badges:
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
                "total_badges": len(user_badges),
                "rarity_points": rarity_points,
                "rarity_breakdown": dict(rarity_counts),
                "badges": user_badges
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
    
    def get_badge_progress(self, user):
        """Bekomme Fortschritt für alle verfügbaren Badges"""
        try:
            from data_persistence import data_persistence
            scores = data_persistence.load_scores()
            daily_stats = data_persistence.load_daily_user_stats()
        except:
            try:
                with open("static/scores.json", "r", encoding="utf-8") as f:
                    scores = json.load(f)
                with open("static/daily_user_stats.json", "r", encoding="utf-8") as f:
                    daily_stats = json.load(f)
            except:
                scores = {}
                daily_stats = {}
        
        user_scores = scores.get(user, {})
        user_daily_stats = daily_stats.get(user, {})
        
        progress = {}
        
        for badge_id, definition in ACHIEVEMENT_DEFINITIONS.items():
            if "threshold" not in definition:
                continue
                
            current = 0
            target = definition["threshold"]
            
            if definition["category"] == "daily":
                today = datetime.now(TZ).strftime("%Y-%m-%d")
                current = user_daily_stats.get(today, {}).get("points", 0)
            elif definition["category"] == "weekly":
                current = self.calculate_week_points(user_daily_stats)
            elif definition["category"] == "monthly":
                current = sum(user_scores.values())
            elif definition["category"] == "total":
                current = sum(sum(month_scores.values()) for month_scores in scores.values())
            elif definition["category"] == "streak":
                current = self.calculate_streak(user_daily_stats)
            
            progress[badge_id] = {
                "current": current,
                "target": target,
                "percentage": min((current / target) * 100, 100) if target > 0 else 0
            }
        
        return progress

# Globale Instanz für Import in anderen Modulen
achievement_system = AchievementSystem()