# -*- coding: utf-8 -*-
"""
Daily Quests & Mini-Games System für Slot Booking Webapp
Täglich wechselnde Herausforderungen und interaktive Spiele
"""

import os
import json
import pytz
import random
import logging
from datetime import datetime, timedelta
from collections import defaultdict

# Logger setup
logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")

# PostgreSQL dual-write support
USE_POSTGRES = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

try:
    from app.models.user import User as UserModel
    from app.models.gamification import DailyQuest as DailyQuestModel, QuestProgress as QuestProgressModel
    from app.models.base import get_db_session
    POSTGRES_AVAILABLE = True
except ImportError:
    logger.warning("PostgreSQL models not available for daily_quests, using JSON-only mode")
    POSTGRES_AVAILABLE = False
    USE_POSTGRES = False

# Daily Quest Definitionen
QUEST_POOL = {
    # Buchungs-Quests
    "speed_booker": {
        "title": "⚡ Blitz-Bucher",
        "description": "Buche 3 Termine in unter 15 Minuten",
        "type": "speed_booking",
        "target": 3,
        "time_limit": 900,  # 15 Minuten in Sekunden
        "rewards": {"xp": 100, "coins": 50, "points": 3},
        "rarity": "common",
        "category": "booking"
    },
    "early_bird": {
        "title": "🌅 Früh-Starter", 
        "description": "Buche vor 10:00 Uhr einen Termin",
        "type": "time_based",
        "target": 1,
        "time_window": "09:00-10:00",
        "rewards": {"xp": 75, "coins": 30, "badge": "early_bird_daily"},
        "rarity": "uncommon",
        "category": "timing"
    },
    "detail_master": {
        "title": "📝 Detail-Meister",
        "description": "Fülle bei 5 Terminen alle Beschreibungsfelder aus",
        "type": "quality_booking", 
        "target": 5,
        "requires_description": True,
        "rewards": {"xp": 80, "coins": 40, "points": 2},
        "rarity": "common",
        "category": "quality"
    },
    "streak_keeper": {
        "title": "🔥 Streak-Bewahrer",
        "description": "Halte deine aktuelle Streak aufrecht",
        "type": "streak_maintenance",
        "target": 1,
        "rewards": {"xp": 60, "coins": 25, "streak_protection": 1},
        "rarity": "rare",
        "category": "consistency"
    },
    "social_climber": {
        "title": "📈 Aufsteiger",
        "description": "Erreiche eine bessere Ranking-Position",
        "type": "rank_improvement",
        "target": 1,
        "rewards": {"xp": 120, "coins": 60, "points": 5},
        "rarity": "epic", 
        "category": "competition"
    },
    
    # Mini-Game Quests
    "slot_spinner": {
        "title": "🎰 Glücks-Spinner",
        "description": "Spiele 3x das Glücksrad nach Buchungen",
        "type": "minigame",
        "target": 3,
        "game": "wheel",
        "rewards": {"coins": 100, "spins": 2},
        "rarity": "common",
        "category": "minigame"
    },
    "lucky_seven": {
        "title": "🍀 Glückliche Sieben",
        "description": "Erziele beim Glücksrad eine 7er Kombination",
        "type": "minigame_achievement", 
        "target": 1,
        "game": "wheel",
        "special_condition": "seven_combo",
        "rewards": {"coins": 500, "xp": 200, "badge": "lucky_seven"},
        "rarity": "legendary",
        "category": "minigame"
    },
    
    # Performance Quests
    "perfectionist": {
        "title": "💎 Perfectionist",
        "description": "Buche 5 Termine ohne Fehler oder Stornierungen",
        "type": "quality_streak",
        "target": 5,
        "rewards": {"xp": 90, "coins": 45, "points": 3},
        "rarity": "uncommon",
        "category": "performance"
    }
}

# Wheel/Slot Machine Konfiguration
WHEEL_PRIZES = {
    # Blank/Dud outcomes (50% total)
    "niete_1": {"name": "💸 Niete!", "value": 0, "weight": 25, "color": "#6b7280"},
    "niete_2": {"name": "😭 Pech gehabt!", "value": 0, "weight": 15, "color": "#6b7280"},
    "niete_3": {"name": "🤷 Beim nächsten Mal!", "value": 0, "weight": 10, "color": "#6b7280"},

    # Winning outcomes (50% total)
    "coins_small": {"name": "💰 Coins", "value": 25, "weight": 15, "color": "#fbbf24"},
    "coins_medium": {"name": "💰💰 Coins", "value": 50, "weight": 10, "color": "#f59e0b"},
    "coins_large": {"name": "💰💰💰 Coins", "value": 100, "weight": 5, "color": "#d97706"},
    "xp_boost": {"name": "⚡ XP Boost", "value": 50, "weight": 8, "color": "#3b82f6"},
    "mystery_box": {"name": "📦 Mystery Box", "value": 1, "weight": 6, "color": "#6b7280"},
    "streak_shield": {"name": "🛡️ Streak Schutz", "value": 1, "weight": 4, "color": "#10b981"},
    "badge_token": {"name": "🎖️ Badge Token", "value": 1, "weight": 2, "color": "#8b5cf6"},
    "jackpot": {"name": "🎰 JACKPOT!", "value": 1000, "weight": 1, "color": "#ec4899"}
}

class DailyQuestSystem:
    def __init__(self):
        self.quests_file = "data/persistent/daily_quests.json"
        self.user_progress_file = "data/persistent/quest_progress.json"
        self.minigame_file = "data/persistent/minigame_data.json"
        self.coins_file = "data/persistent/user_coins.json"
        
        # Ensure directories exist
        os.makedirs("data/persistent", exist_ok=True)
        
        # Initialize files
        for file_path in [self.quests_file, self.user_progress_file, self.minigame_file, self.coins_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
    
    def load_daily_quests(self):
        """Lade tägliche Quest-Konfiguration (PostgreSQL-first, JSON-Fallback)"""
        # 1. PostgreSQL-first
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    rows = session.query(DailyQuestModel).all()
                    if rows:
                        data = {}
                        for row in rows:
                            date_str = row.quest_date.strftime("%Y-%m-%d") if hasattr(row.quest_date, 'strftime') else str(row.quest_date)
                            if date_str not in data:
                                data[date_str] = {
                                    "date": date_str,
                                    "generated_at": row.created_at.isoformat() if row.created_at else None,
                                    "quests": [],
                                    "bonus_multiplier": (row.reward_items or {}).get("bonus_multiplier", 1.0)
                                }
                            quest_pool_entry = QUEST_POOL.get(row.quest_id, {})
                            data[date_str]["quests"].append({
                                "id": row.quest_id,
                                "title": row.title,
                                "description": row.description,
                                "type": row.target_type,
                                "target": row.target_value,
                                "rewards": {
                                    "xp": quest_pool_entry.get("rewards", {}).get("xp", 0),
                                    "coins": row.reward_coins,
                                    "points": row.reward_points
                                },
                                "rarity": row.difficulty,
                                "category": row.category
                            })
                        logger.debug(f"Loaded daily quests from PostgreSQL ({len(data)} dates)")
                        return data
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"PostgreSQL daily quests load failed: {e}, falling back to JSON")

        # 2. JSON-Fallback
        try:
            with open(self.quests_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_daily_quests(self, data):
        """Speichere tägliche Quest-Konfiguration (Dual-Write: PostgreSQL + JSON)"""
        # 1. PostgreSQL write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    for date_str, day_data in data.items():
                        if not isinstance(day_data, dict):
                            continue
                        bonus_multiplier = day_data.get("bonus_multiplier", 1.0)
                        for quest in day_data.get("quests", []):
                            quest_id = quest.get("id", "")
                            if not quest_id:
                                continue
                            try:
                                quest_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            except (ValueError, TypeError):
                                continue

                            existing = session.query(DailyQuestModel).filter_by(
                                quest_id=quest_id
                            ).first()
                            rewards = quest.get("rewards", {})
                            if existing:
                                existing.quest_date = quest_date
                                existing.title = quest.get("title", "")
                                existing.description = quest.get("description", "")
                                existing.category = quest.get("category", "booking")
                                existing.difficulty = quest.get("rarity", "common")
                                existing.target_value = quest.get("target", 1)
                                existing.target_type = quest.get("type", "booking")
                                existing.reward_points = rewards.get("points", 0)
                                existing.reward_coins = rewards.get("coins", 0)
                                existing.reward_items = {"bonus_multiplier": bonus_multiplier}
                            else:
                                new_row = DailyQuestModel(
                                    quest_id=quest_id,
                                    quest_date=quest_date,
                                    title=quest.get("title", ""),
                                    description=quest.get("description", ""),
                                    category=quest.get("category", "booking"),
                                    difficulty=quest.get("rarity", "common"),
                                    target_value=quest.get("target", 1),
                                    target_type=quest.get("type", "booking"),
                                    reward_points=rewards.get("points", 0),
                                    reward_coins=rewards.get("coins", 0),
                                    reward_items={"bonus_multiplier": bonus_multiplier},
                                    is_active=True
                                )
                                session.add(new_row)
                    session.commit()
                    logger.debug("Daily quests saved to PostgreSQL")
                except Exception as e:
                    session.rollback()
                    logger.error(f"PostgreSQL daily quests save failed: {e}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"PostgreSQL connection failed for daily quests: {e}")

        # 2. JSON write (always, as backup)
        with open(self.quests_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_user_progress(self):
        """Lade User Quest-Fortschritt (PostgreSQL-first, JSON-Fallback)"""
        # 1. PostgreSQL-first
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    rows = session.query(QuestProgressModel).all()
                    if rows:
                        data = {}
                        for row in rows:
                            if row.username not in data:
                                data[row.username] = {}
                            # Ermittle date_str aus quest_id oder started_at
                            date_str = row.started_at.strftime("%Y-%m-%d") if row.started_at else "unknown"
                            if date_str not in data[row.username]:
                                data[row.username][date_str] = {}
                            data[row.username][date_str][row.quest_id] = {
                                "progress": row.current_value,
                                "completed": row.is_completed,
                                "claimed": row.is_claimed
                            }
                        logger.debug(f"Loaded quest progress from PostgreSQL ({len(data)} users)")
                        return data
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"PostgreSQL quest progress load failed: {e}, falling back to JSON")

        # 2. JSON-Fallback
        try:
            with open(self.user_progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_user_progress(self, data):
        """Speichere User Quest-Fortschritt (Dual-Write: PostgreSQL + JSON)"""
        # 1. PostgreSQL write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    for username, dates in data.items():
                        if not isinstance(dates, dict):
                            continue
                        for date_str, quests in dates.items():
                            if not isinstance(quests, dict):
                                continue
                            try:
                                quest_date = datetime.strptime(date_str, "%Y-%m-%d")
                            except (ValueError, TypeError):
                                continue
                            for quest_id, progress in quests.items():
                                if not isinstance(progress, dict):
                                    continue
                                current_value = progress.get("progress", 0)
                                is_completed = progress.get("completed", False)
                                is_claimed = progress.get("claimed", False)
                                # Ermittle target_value aus QUEST_POOL
                                target_value = QUEST_POOL.get(quest_id, {}).get("target", 1)

                                existing = session.query(QuestProgressModel).filter_by(
                                    username=username, quest_id=quest_id
                                ).first()
                                if existing:
                                    existing.current_value = current_value
                                    existing.is_completed = is_completed
                                    existing.is_claimed = is_claimed
                                    existing.progress_percent = min(100.0, (current_value / target_value * 100)) if target_value > 0 else 0.0
                                    existing.last_progress_at = datetime.utcnow()
                                    if is_completed and not existing.completed_at:
                                        existing.completed_at = datetime.utcnow()
                                else:
                                    new_row = QuestProgressModel(
                                        username=username,
                                        quest_id=quest_id,
                                        current_value=current_value,
                                        target_value=target_value,
                                        progress_percent=min(100.0, (current_value / target_value * 100)) if target_value > 0 else 0.0,
                                        is_completed=is_completed,
                                        is_claimed=is_claimed,
                                        started_at=quest_date,
                                        completed_at=datetime.utcnow() if is_completed else None,
                                        last_progress_at=datetime.utcnow()
                                    )
                                    session.add(new_row)
                    session.commit()
                    logger.debug("Quest progress saved to PostgreSQL")
                except Exception as e:
                    session.rollback()
                    logger.error(f"PostgreSQL quest progress save failed: {e}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"PostgreSQL connection failed for quest progress: {e}")

        # 2. JSON write (always, as backup)
        with open(self.user_progress_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_user_coins(self):
        """Lade User Coin-Guthaben (PostgreSQL-first, JSON-Fallback)"""
        # 1. PostgreSQL-first
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    rows = session.query(UserModel.username, UserModel.total_coins).all()
                    if rows:
                        data = {row.username: row.total_coins for row in rows}
                        logger.debug(f"Loaded user coins from PostgreSQL ({len(data)} users)")
                        return data
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"PostgreSQL coins load failed: {e}, falling back to JSON")

        # 2. JSON-Fallback
        try:
            with open(self.coins_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_user_coins(self, data):
        """Speichere User Coin-Guthaben (Dual-Write: PostgreSQL + JSON)"""
        # 1. PostgreSQL write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                session = get_db_session()
                try:
                    for username, coins in data.items():
                        existing = session.query(UserModel).filter_by(username=username).first()
                        if existing:
                            existing.total_coins = int(coins)
                        else:
                            logger.debug(f"User {username} not found in PostgreSQL, skipping coins update")
                    session.commit()
                    logger.debug("User coins saved to PostgreSQL")
                except Exception as e:
                    session.rollback()
                    logger.error(f"PostgreSQL coins save failed: {e}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"PostgreSQL connection failed for coins: {e}")

        # 2. JSON write (always, as backup)
        with open(self.coins_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def generate_daily_quests(self, date_str=None):
        """Generiere tägliche Quests für einen bestimmten Tag"""
        if date_str is None:
            date_str = datetime.now(TZ).strftime("%Y-%m-%d")
        
        # Seed für konsistente tägliche Quests
        random.seed(date_str)
        
        # Wähle 3-5 Quests aus verschiedenen Kategorien
        categories = list(set(q["category"] for q in QUEST_POOL.values()))
        selected_quests = []
        
        # Mindestens eine Quest pro Kategorie (bis zu 5)
        for category in categories[:5]:
            category_quests = [qid for qid, quest in QUEST_POOL.items() if quest["category"] == category]
            if category_quests:
                quest_id = random.choice(category_quests)
                quest = QUEST_POOL[quest_id].copy()
                quest["id"] = quest_id
                selected_quests.append(quest)
        
        # Shuffle für zufällige Reihenfolge
        random.shuffle(selected_quests)
        
        daily_quests = {
            "date": date_str,
            "generated_at": datetime.now(TZ).isoformat(),
            "quests": selected_quests[:4],  # Maximal 4 Quests pro Tag
            "bonus_multiplier": random.choice([1.0, 1.2, 1.5])  # Zufälliger Tagesbonus
        }
        
        # Speichere generierte Quests
        all_quests = self.load_daily_quests()
        all_quests[date_str] = daily_quests
        self.save_daily_quests(all_quests)
        
        # Reset random seed
        random.seed()
        
        return daily_quests
    
    def get_user_daily_quests(self, user, date_str=None):
        """Hole tägliche Quests für einen User mit aktuellem Fortschritt"""
        if date_str is None:
            date_str = datetime.now(TZ).strftime("%Y-%m-%d")
        
        # Lade oder generiere tägliche Quests
        all_quests = self.load_daily_quests()
        if date_str not in all_quests:
            daily_quests = self.generate_daily_quests(date_str)
        else:
            daily_quests = all_quests[date_str]
        
        # Lade User-Fortschritt
        user_progress = self.load_user_progress()
        user_day_progress = user_progress.get(user, {}).get(date_str, {})
        
        # Kombiniere Quests mit Fortschritt
        quests_with_progress = []
        for quest in daily_quests["quests"]:
            quest_id = quest["id"]
            progress = user_day_progress.get(quest_id, {"progress": 0, "completed": False, "claimed": False})
            
            quest_data = {
                "id": quest_id,
                "title": quest["title"],
                "description": quest["description"],
                "type": quest["type"],
                "target": quest["target"],
                "progress": progress["progress"],
                "completed": progress["completed"],
                "claimed": progress["claimed"],
                "rewards": quest["rewards"],
                "rarity": quest["rarity"],
                "category": quest["category"],
                "progress_percent": min(100, (progress["progress"] / quest["target"]) * 100)
            }
            
            quests_with_progress.append(quest_data)
        
        return {
            "date": date_str,
            "quests": quests_with_progress,
            "bonus_multiplier": daily_quests.get("bonus_multiplier", 1.0),
            "total_completed": sum(1 for q in quests_with_progress if q["completed"]),
            "total_claimed": sum(1 for q in quests_with_progress if q["claimed"])
        }
    
    def update_quest_progress(self, user, quest_type, data=None):
        """Update Quest-Fortschritt basierend auf User-Aktionen"""
        date_str = datetime.now(TZ).strftime("%Y-%m-%d")
        user_quests = self.get_user_daily_quests(user, date_str)
        
        user_progress = self.load_user_progress()
        if user not in user_progress:
            user_progress[user] = {}
        if date_str not in user_progress[user]:
            user_progress[user][date_str] = {}
        
        updated_quests = []
        
        for quest in user_quests["quests"]:
            if quest["completed"] or quest["claimed"]:
                continue
                
            quest_id = quest["id"]
            current_progress = quest["progress"]
            
            # Prüfe ob Quest-Typ zu dieser Aktion passt
            should_update = False
            progress_increment = 0
            
            if quest_type == "booking" and quest["type"] in ["speed_booking", "quality_booking"]:
                if quest["type"] == "speed_booking":
                    # Prüfe Geschwindigkeit (simuliert)
                    booking_time = data.get("booking_duration", 120)
                    if booking_time < 100:  # Unter 100 Sekunden = schnell
                        progress_increment = 1
                        should_update = True
                elif quest["type"] == "quality_booking":
                    # Prüfe Beschreibung
                    has_description = data.get("has_description", False)
                    if has_description:
                        progress_increment = 1
                        should_update = True
            
            elif quest_type == "time_based" and quest["type"] == "time_based":
                current_hour = datetime.now(TZ).hour
                if quest.get("time_window") == "09:00-10:00" and current_hour == 9:
                    progress_increment = 1
                    should_update = True
            
            elif quest_type == "minigame" and quest["type"] == "minigame":
                game_type = data.get("game", "")
                if quest.get("game") == game_type:
                    progress_increment = 1
                    should_update = True
            
            elif quest_type == "streak" and quest["type"] == "streak_maintenance":
                # Automatisch erfüllt wenn User heute aktiv war
                progress_increment = 1
                should_update = True
            
            if should_update:
                new_progress = current_progress + progress_increment
                new_progress = min(new_progress, quest["target"])
                
                user_progress[user][date_str][quest_id] = {
                    "progress": new_progress,
                    "completed": new_progress >= quest["target"],
                    "claimed": False,
                    "last_updated": datetime.now(TZ).isoformat()
                }
                
                if new_progress >= quest["target"]:
                    updated_quests.append({
                        "quest_id": quest_id,
                        "quest_title": quest["title"],
                        "completed": True,
                        "rewards": quest["rewards"]
                    })
        
        self.save_user_progress(user_progress)
        return updated_quests
    
    def claim_quest_reward(self, user, quest_id, date_str=None):
        """Hole Quest-Belohnung ab"""
        if date_str is None:
            date_str = datetime.now(TZ).strftime("%Y-%m-%d")
        
        user_progress = self.load_user_progress()
        quest_progress = user_progress.get(user, {}).get(date_str, {}).get(quest_id, {})
        
        if not quest_progress.get("completed", False):
            return {"success": False, "message": "Quest nicht abgeschlossen"}
        
        if quest_progress.get("claimed", False):
            return {"success": False, "message": "Belohnung bereits abgeholt"}
        
        # Finde Quest-Definition
        daily_quests = self.load_daily_quests().get(date_str, {})
        quest_def = None
        for quest in daily_quests.get("quests", []):
            if quest["id"] == quest_id:
                quest_def = quest
                break
        
        if not quest_def:
            return {"success": False, "message": "Quest nicht gefunden"}
        
        # Vergebe Belohnungen
        rewards_given = self.give_rewards(user, quest_def["rewards"], daily_quests.get("bonus_multiplier", 1.0))
        
        # Markiere als abgeholt
        user_progress[user][date_str][quest_id]["claimed"] = True
        user_progress[user][date_str][quest_id]["claimed_at"] = datetime.now(TZ).isoformat()
        self.save_user_progress(user_progress)
        
        return {
            "success": True,
            "message": f"Belohnung für '{quest_def['title']}' erhalten!",
            "rewards": rewards_given,
            "quest_title": quest_def["title"]
        }
    
    def give_rewards(self, user, rewards, multiplier=1.0):
        """Vergebe Belohnungen an User"""
        given_rewards = {}
        
        # Coins
        if "coins" in rewards:
            coins_data = self.load_user_coins()
            current_coins = coins_data.get(user, 0)
            coin_reward = int(rewards["coins"] * multiplier)
            coins_data[user] = current_coins + coin_reward
            self.save_user_coins(coins_data)
            given_rewards["coins"] = coin_reward
        
        # XP (delegieren an Level-System)
        if "xp" in rewards:
            xp_reward = int(rewards["xp"] * multiplier)
            given_rewards["xp"] = xp_reward
            # XP wird über Punkte-System gehandhabt - Level-System berechnet XP automatisch aus Gesamtpunkten
            try:
                from achievement_system import achievement_system
                achievement_system.add_points_and_check_achievements(user, xp_reward)
            except Exception as e:
                logger.warning(f"Could not add XP rewards via achievement system", extra={'error': str(e)})
        
        # Punkte (delegieren an Scoring-System)
        if "points" in rewards:
            points_reward = int(rewards["points"] * multiplier)
            given_rewards["points"] = points_reward
            # Integration mit data_persistence.py über achievement_system
            try:
                from achievement_system import achievement_system
                achievement_system.add_points_and_check_achievements(user, points_reward)
            except Exception as e:
                logger.warning(f"Could not add points rewards via achievement system", extra={'error': str(e)})
        
        # Spezielle Rewards
        for reward_type in ["badge", "streak_protection", "spins"]:
            if reward_type in rewards:
                given_rewards[reward_type] = rewards[reward_type]
        
        return given_rewards
    
    def spin_wheel(self, user):
        """Führe Glücksrad-Spin durch"""
        # Prüfe ob User genug Coins hat (kostet 10 Coins)
        coins_data = self.load_user_coins()
        user_coins = coins_data.get(user, 0)
        
        if user_coins < 10:
            return {"success": False, "message": "Nicht genug Coins (10 Coins benötigt)"}
        
        # Deduct coins
        coins_data[user] = user_coins - 10
        self.save_user_coins(coins_data)
        
        # Gewichtete Zufallsauswahl
        prizes = []
        weights = []
        for prize_id, prize_data in WHEEL_PRIZES.items():
            prizes.append(prize_id)
            weights.append(prize_data["weight"])
        
        selected_prize = random.choices(prizes, weights=weights, k=1)[0]
        prize_data = WHEEL_PRIZES[selected_prize]
        
        # Vergebe Preis
        reward = {}
        if selected_prize.startswith("niete"):
            # Blank/Dud outcome - no reward given
            reward = {"type": "niete", "value": 0}
        elif selected_prize.startswith("coins"):
            coins_data[user] = coins_data.get(user, 0) + prize_data["value"]
            self.save_user_coins(coins_data)
            reward = {"type": "coins", "value": prize_data["value"]}
        elif selected_prize == "xp_boost":
            reward = {"type": "xp", "value": prize_data["value"]}
        elif selected_prize == "jackpot":
            coins_data[user] = coins_data.get(user, 0) + prize_data["value"]
            self.save_user_coins(coins_data)
            reward = {"type": "jackpot", "value": prize_data["value"]}
        else:
            reward = {"type": selected_prize, "value": prize_data["value"]}
        
        # Update Quest-Fortschritt
        self.update_quest_progress(user, "minigame", {"game": "wheel"})
        
        # Speichere Spin-Historie
        minigame_data = self.load_minigame_data()
        if user not in minigame_data:
            minigame_data[user] = {"spins": [], "total_spins": 0, "total_winnings": 0}
        
        minigame_data[user]["spins"].append({
            "date": datetime.now(TZ).isoformat(),
            "prize": selected_prize,
            "value": prize_data["value"],
            "cost": 10
        })
        minigame_data[user]["total_spins"] += 1
        if selected_prize.startswith("coins") or selected_prize == "jackpot":
            minigame_data[user]["total_winnings"] += prize_data["value"]
        
        # Behalte nur letzte 100 Spins
        if len(minigame_data[user]["spins"]) > 100:
            minigame_data[user]["spins"] = minigame_data[user]["spins"][-100:]
        
        self.save_minigame_data(minigame_data)
        
        return {
            "success": True,
            "prize": {
                "id": selected_prize,
                "name": prize_data["name"],
                "value": prize_data["value"],
                "color": prize_data["color"]
            },
            "reward": reward,
            "remaining_coins": coins_data.get(user, 0)
        }
    
    def load_minigame_data(self):
        """Lade Mini-Game Daten"""
        try:
            with open(self.minigame_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    
    def save_minigame_data(self, data):
        """Speichere Mini-Game Daten"""
        with open(self.minigame_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_user_coins(self, user):
        """Hole User Coin-Guthaben"""
        coins_data = self.load_user_coins()
        return coins_data.get(user, 0)
    
    def get_quest_leaderboard(self):
        """Erstelle Rangliste nach Quest-Abschlüssen"""
        user_progress = self.load_user_progress()
        
        leaderboard = defaultdict(lambda: {"completed_quests": 0, "claimed_rewards": 0})
        
        for user, user_data in user_progress.items():
            for date, date_data in user_data.items():
                for quest_id, quest_progress in date_data.items():
                    if quest_progress.get("completed", False):
                        leaderboard[user]["completed_quests"] += 1
                    if quest_progress.get("claimed", False):
                        leaderboard[user]["claimed_rewards"] += 1
        
        # Sortiere nach abgeschlossenen Quests
        sorted_leaderboard = sorted(
            leaderboard.items(), 
            key=lambda x: (x[1]["completed_quests"], x[1]["claimed_rewards"]), 
            reverse=True
        )
        
        return [{"user": user, **stats} for user, stats in sorted_leaderboard]

# Globale Instanz
daily_quest_system = DailyQuestSystem()