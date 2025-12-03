# -*- coding: utf-8 -*-
"""
Daily Reward System
Daily login rewards with streak bonuses
"""

import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Tuple
from app.core.extensions import data_persistence

logger = logging.getLogger(__name__)
TZ = pytz.timezone('Europe/Berlin')


class DailyRewardSystem:
    """Service für Daily Login Rewards"""

    def __init__(self):
        self.rewards_file = 'daily_rewards'

        # Reward-Konfiguration
        self.BASE_REWARD = 10  # Coins für Login
        self.STREAK_BONUS = 5   # +5 Coins pro Streak-Tag (max +40)
        self.MAX_STREAK_BONUS = 40  # Max Streak-Bonus bei 8+ Tagen

        # Meilenstein-Belohnungen
        self.MILESTONE_REWARDS = {
            7: 100,   # 1 Woche = 100 Coins Bonus
            30: 500,  # 1 Monat = 500 Coins Bonus
            100: 2000 # 100 Tage = 2000 Coins Bonus
        }

    def _load_rewards_data(self) -> Dict[str, dict]:
        """Lade Daily Reward Daten"""
        return data_persistence.load_data(self.rewards_file, {})

    def _save_rewards_data(self, data: Dict[str, dict]):
        """Speichere Daily Reward Daten"""
        data_persistence.save_data(self.rewards_file, data)

    def check_daily_reward(self, username: str) -> Dict:
        """
        Prüfe ob User Daily Reward claimen kann
        Returns: {
            'available': bool,
            'streak': int,
            'reward_amount': int,
            'milestone_bonus': int,
            'last_login': str,
            'next_reward_in': str
        }
        """
        rewards_data = self._load_rewards_data()
        today = datetime.now(TZ).date()
        today_str = today.strftime('%Y-%m-%d')

        if username not in rewards_data:
            # Neuer User - erster Login
            return {
                'available': True,
                'streak': 1,
                'reward_amount': self.BASE_REWARD,
                'milestone_bonus': 0,
                'last_login': None,
                'next_reward_in': '0h',
                'is_first_time': True
            }

        user_data = rewards_data[username]
        last_reward_date_str = user_data.get('last_reward_date')

        if not last_reward_date_str:
            # User existiert, aber noch nie Reward geclaimt
            return {
                'available': True,
                'streak': 1,
                'reward_amount': self.BASE_REWARD,
                'milestone_bonus': 0,
                'last_login': user_data.get('last_login'),
                'next_reward_in': '0h',
                'is_first_time': True
            }

        last_reward_date = datetime.strptime(last_reward_date_str, '%Y-%m-%d').date()

        # Check ob bereits heute geclaimt
        if last_reward_date >= today:
            # Bereits heute geclaimt
            next_midnight = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            hours_until = int((next_midnight - datetime.now(TZ)).total_seconds() / 3600)

            return {
                'available': False,
                'streak': user_data.get('streak', 1),
                'reward_amount': 0,
                'milestone_bonus': 0,
                'last_login': user_data.get('last_login'),
                'next_reward_in': f'{hours_until}h',
                'already_claimed_today': True
            }

        # Check Streak
        yesterday = today - timedelta(days=1)
        if last_reward_date == yesterday:
            # Streak continues
            streak = user_data.get('streak', 0) + 1
        elif last_reward_date < yesterday:
            # Streak broken, restart
            streak = 1
        else:
            streak = 1

        # Calculate Reward
        streak_bonus = min(streak * self.STREAK_BONUS, self.MAX_STREAK_BONUS)
        base_reward = self.BASE_REWARD + streak_bonus

        # Check Milestone
        milestone_bonus = self.MILESTONE_REWARDS.get(streak, 0)

        return {
            'available': True,
            'streak': streak,
            'reward_amount': base_reward,
            'milestone_bonus': milestone_bonus,
            'last_login': user_data.get('last_login'),
            'next_reward_in': '0h',
            'streak_continued': last_reward_date == yesterday
        }

    def claim_daily_reward(self, username: str) -> Tuple[bool, str, Dict]:
        """
        Claime Daily Reward
        Returns: (success, message, reward_info)
        """
        reward_check = self.check_daily_reward(username)

        if not reward_check['available']:
            return False, "Daily Reward bereits heute geclaimt!", reward_check

        # Update Reward Data
        rewards_data = self._load_rewards_data()
        today = datetime.now(TZ).date().strftime('%Y-%m-%d')

        if username not in rewards_data:
            rewards_data[username] = {}

        rewards_data[username].update({
            'last_login': today,
            'last_reward_date': today,
            'streak': reward_check['streak'],
            'total_rewards_claimed': rewards_data.get(username, {}).get('total_rewards_claimed', 0) + reward_check['reward_amount'] + reward_check['milestone_bonus']
        })

        self._save_rewards_data(rewards_data)

        # Add Coins
        try:
            from app.services.daily_quests import daily_quest_system
            coins_data = daily_quest_system.load_user_coins()
            current_coins = coins_data.get(username, 0)
            total_reward = reward_check['reward_amount'] + reward_check['milestone_bonus']
            coins_data[username] = current_coins + total_reward
            daily_quest_system.save_user_coins(coins_data)

            logger.info(f"Daily reward claimed: {username} received {total_reward} coins (streak: {reward_check['streak']})")

            # Success Message
            if reward_check['milestone_bonus'] > 0:
                message = f"🎉 {reward_check['streak']}-Tage Meilenstein! +{total_reward} Coins ({reward_check['reward_amount']} + {reward_check['milestone_bonus']} Bonus)"
            else:
                message = f"✅ Daily Reward: +{reward_check['reward_amount']} Coins (Streak: {reward_check['streak']} Tage)"

            return True, message, reward_check

        except Exception as e:
            logger.error(f"Error adding daily reward coins: {e}")
            return False, "Fehler beim Hinzufügen der Coins", reward_check

    def update_last_login(self, username: str):
        """
        Update last login (wird bei jedem Login aufgerufen)
        OHNE Reward zu claimen
        """
        rewards_data = self._load_rewards_data()
        today = datetime.now(TZ).date().strftime('%Y-%m-%d')

        if username not in rewards_data:
            rewards_data[username] = {}

        rewards_data[username]['last_login'] = today
        self._save_rewards_data(rewards_data)


# Global instance
daily_reward_system = DailyRewardSystem()
