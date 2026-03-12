# -*- coding: utf-8 -*-
"""
Gameplay Rewards Service - XP-Booster, Streak-Shields, Bonus-Spins, Inventar
"""

import os
import json
import logging
from datetime import datetime, timedelta

import pytz

from app.utils.json_utils import atomic_read_json, atomic_write_json

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")

# PostgreSQL dual-write support
USE_POSTGRES = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

try:
    from app.models.base import get_db_session
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    USE_POSTGRES = False


class GameplayRewards:
    def __init__(self):
        persist_base = os.getenv("PERSIST_BASE", "data")
        self.inventory_file = os.path.join(persist_base, "persistent", "user_inventory.json")

        os.makedirs(os.path.dirname(self.inventory_file), exist_ok=True)
        if not os.path.exists(self.inventory_file):
            with open(self.inventory_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_inventory(self):
        try:
            data = atomic_read_json(self.inventory_file)
            if data is not None:
                return data
        except Exception as e:
            logger.warning(f"Could not load inventory: {e}")
        return {}

    def _save_inventory(self, data):
        try:
            atomic_write_json(self.inventory_file, data)
        except Exception as e:
            logger.error(f"Could not save inventory: {e}")

    def _get_user_inv(self, data, username):
        if username not in data:
            data[username] = {
                "xp_boosters": [],
                "streak_shields": 0,
                "bonus_spins": 0,
                "challenge_coins": 0,
                "history": [],
            }
        return data[username]

    # ------------------------------------------------------------------
    # XP Booster
    # ------------------------------------------------------------------

    def activate_xp_booster(self, username, multiplier=2.0, duration_hours=1):
        """Activate an XP booster for the user."""
        data = self._load_inventory()
        inv = self._get_user_inv(data, username)

        now = datetime.now(TZ)
        expires = now + timedelta(hours=duration_hours)

        booster = {
            "multiplier": multiplier,
            "activated_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }
        inv["xp_boosters"].append(booster)
        inv["history"].append({
            "type": "xp_booster_activated",
            "multiplier": multiplier,
            "duration_hours": duration_hours,
            "timestamp": now.isoformat(),
        })

        self._save_inventory(data)
        logger.info(f"XP booster activated for {username}: {multiplier}x for {duration_hours}h")
        return {"success": True, "booster": booster}

    def get_active_boosters(self, username):
        """Return list of active boosters with remaining time."""
        data = self._load_inventory()
        inv = self._get_user_inv(data, username)

        now = datetime.now(TZ)
        active = []
        for b in inv.get("xp_boosters", []):
            try:
                expires = datetime.fromisoformat(b["expires_at"])
                if expires.tzinfo is None:
                    expires = TZ.localize(expires)
                if expires > now:
                    remaining = (expires - now).total_seconds()
                    active.append({
                        "multiplier": b["multiplier"],
                        "remaining_seconds": int(remaining),
                        "remaining_display": self._format_remaining(remaining),
                        "expires_at": b["expires_at"],
                    })
            except Exception:
                continue
        return active

    def is_xp_boosted(self, username):
        """Check if user has active XP booster. Returns (boosted, multiplier)."""
        boosters = self.get_active_boosters(username)
        if not boosters:
            return False, 1.0
        # Use highest active multiplier
        max_mult = max(b["multiplier"] for b in boosters)
        return True, max_mult

    # ------------------------------------------------------------------
    # Streak Shield
    # ------------------------------------------------------------------

    def activate_streak_shield(self, username):
        """Add a streak shield to the user inventory."""
        data = self._load_inventory()
        inv = self._get_user_inv(data, username)
        inv["streak_shields"] = inv.get("streak_shields", 0) + 1
        inv["history"].append({
            "type": "streak_shield_added",
            "timestamp": datetime.now(TZ).isoformat(),
        })
        self._save_inventory(data)
        logger.info(f"Streak shield added for {username}")
        return {"success": True, "shields": inv["streak_shields"]}

    def use_streak_shield(self, username):
        """Consume one streak shield. Returns True if shield was available."""
        data = self._load_inventory()
        inv = self._get_user_inv(data, username)
        if inv.get("streak_shields", 0) > 0:
            inv["streak_shields"] -= 1
            inv["history"].append({
                "type": "streak_shield_used",
                "timestamp": datetime.now(TZ).isoformat(),
            })
            self._save_inventory(data)
            logger.info(f"Streak shield used by {username}")
            return True
        return False

    def has_streak_shield(self, username):
        data = self._load_inventory()
        inv = self._get_user_inv(data, username)
        return inv.get("streak_shields", 0) > 0

    # ------------------------------------------------------------------
    # Bonus Spins
    # ------------------------------------------------------------------

    def add_bonus_spins(self, username, count):
        data = self._load_inventory()
        inv = self._get_user_inv(data, username)
        inv["bonus_spins"] = inv.get("bonus_spins", 0) + count
        inv["history"].append({
            "type": "bonus_spins_added",
            "count": count,
            "timestamp": datetime.now(TZ).isoformat(),
        })
        self._save_inventory(data)
        logger.info(f"{count} bonus spins added for {username}")
        return {"success": True, "total_spins": inv["bonus_spins"]}

    def use_bonus_spin(self, username):
        data = self._load_inventory()
        inv = self._get_user_inv(data, username)
        if inv.get("bonus_spins", 0) > 0:
            inv["bonus_spins"] -= 1
            inv["history"].append({
                "type": "bonus_spin_used",
                "timestamp": datetime.now(TZ).isoformat(),
            })
            self._save_inventory(data)
            logger.info(f"Bonus spin used by {username}")
            return True
        return False

    def get_bonus_spins(self, username):
        data = self._load_inventory()
        inv = self._get_user_inv(data, username)
        return inv.get("bonus_spins", 0)

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    def get_inventory(self, username):
        """Return full inventory for a user."""
        data = self._load_inventory()
        inv = self._get_user_inv(data, username)

        active_boosters = self.get_active_boosters(username)

        return {
            "xp_boosters": active_boosters,
            "streak_shields": inv.get("streak_shields", 0),
            "bonus_spins": inv.get("bonus_spins", 0),
            "challenge_coins": inv.get("challenge_coins", 0),
        }

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_expired_boosters(self):
        """Remove expired XP boosters from all user inventories."""
        data = self._load_inventory()
        now = datetime.now(TZ)
        cleaned = 0

        for username, inv in data.items():
            original_count = len(inv.get("xp_boosters", []))
            active = []
            for b in inv.get("xp_boosters", []):
                try:
                    expires = datetime.fromisoformat(b["expires_at"])
                    if expires.tzinfo is None:
                        expires = TZ.localize(expires)
                    if expires > now:
                        active.append(b)
                except Exception:
                    continue
            removed = original_count - len(active)
            if removed > 0:
                inv["xp_boosters"] = active
                cleaned += removed

        if cleaned > 0:
            self._save_inventory(data)
            logger.info(f"Cleaned up {cleaned} expired boosters")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_remaining(seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"


gameplay_rewards = GameplayRewards()
