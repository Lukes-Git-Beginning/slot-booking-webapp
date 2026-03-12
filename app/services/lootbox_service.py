# -*- coding: utf-8 -*-
"""
Lootbox / Crate System - Purchase, open and collect rewards from crates
"""

import os
import json
import random
import logging
import uuid
from datetime import datetime

import pytz

from app.utils.json_utils import atomic_read_json, atomic_write_json

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")

CRATE_TYPES = {
    "common": {"name": "Bronze-Kiste", "price": 100, "color": "#CD7F32", "icon": "box"},
    "rare": {"name": "Silber-Kiste", "price": 300, "color": "#C0C0C0", "icon": "gift"},
    "epic": {"name": "Gold-Kiste", "price": 750, "color": "#FFD700", "icon": "sparkles"},
    "legendary": {"name": "Diamant-Kiste", "price": 1500, "color": "#00BFFF", "icon": "gem"},
}

# Loot tables: list of (weight, reward_type, reward_config) per crate type
# reward_type: coins, xp, cosmetic, booster, streak_shield, bonus_spins
LOOT_TABLES = {
    "common": [
        (50, "coins", {"min": 10, "max": 50}),
        (30, "xp", {"min": 20, "max": 60}),
        (15, "cosmetic", {"rarity": "common"}),
        (5, "cosmetic", {"rarity": "rare"}),
    ],
    "rare": [
        (35, "coins", {"min": 30, "max": 100}),
        (25, "xp", {"min": 50, "max": 120}),
        (25, "cosmetic", {"rarity": "rare"}),
        (10, "booster", {"multiplier": 1.5, "hours": 1}),
        (5, "cosmetic", {"rarity": "epic"}),
    ],
    "epic": [
        (20, "coins", {"min": 50, "max": 200}),
        (20, "xp", {"min": 100, "max": 250}),
        (25, "cosmetic", {"rarity": "epic"}),
        (15, "booster", {"multiplier": 2.0, "hours": 1}),
        (10, "streak_shield", {}),
        (10, "cosmetic", {"rarity": "legendary"}),
    ],
    "legendary": [
        (15, "coins", {"min": 100, "max": 500}),
        (15, "xp", {"min": 200, "max": 500}),
        (20, "cosmetic", {"rarity": "legendary"}),
        (20, "cosmetic", {"rarity": "epic"}),
        (15, "booster", {"multiplier": 2.0, "hours": 2}),
        (15, "bonus_spins", {"count": 3}),
    ],
}

# Pool of cosmetics that can drop from crates, organised by rarity
COSMETIC_DROPS = {
    "common": [
        {"id": "frame_starter", "type": "frame", "name": "Basis-Rahmen"},
        {"id": "booking_rookie", "type": "title", "name": "Buchungs-Neuling"},
        {"id": "coffee_addict", "type": "title", "name": "Koffein-Junkie"},
        {"id": "early_bird", "type": "title", "name": "Frueher Vogel"},
    ],
    "rare": [
        {"id": "frame_gold", "type": "frame", "name": "Goldrahmen"},
        {"id": "frame_neon", "type": "frame", "name": "Neon"},
        {"id": "frame_frost", "type": "frame", "name": "Frost"},
        {"id": "frame_cherry", "type": "frame", "name": "Kirschbluete"},
        {"id": "booking_overlord", "type": "title", "name": "Buchungs-Overlord"},
    ],
    "epic": [
        {"id": "frame_diamond", "type": "frame", "name": "Diamant"},
        {"id": "frame_fire", "type": "frame", "name": "Feuer"},
        {"id": "frame_shadow", "type": "frame", "name": "Schatten"},
        {"id": "confetti_explosion", "type": "effect", "name": "Konfetti-Explosion"},
        {"id": "rainbow_glow", "type": "effect", "name": "Regenbogen-Leuchten"},
    ],
    "legendary": [
        {"id": "frame_rainbow", "type": "frame", "name": "Regenbogen"},
        {"id": "particle_trail", "type": "effect", "name": "Partikel-Spur"},
        {"id": "temporal_lord", "type": "title", "name": "Zeit-Lord"},
        {"id": "booking_deity", "type": "title", "name": "Buchungs-Gottheit"},
    ],
}

PITY_THRESHOLD = 10  # Guaranteed rare+ after this many opens without one


class LootboxService:
    def __init__(self):
        persist_base = os.getenv("PERSIST_BASE", "data")
        self.lootbox_file = os.path.join(persist_base, "persistent", "lootboxes.json")
        os.makedirs(os.path.dirname(self.lootbox_file), exist_ok=True)
        if not os.path.exists(self.lootbox_file):
            with open(self.lootbox_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_data(self):
        try:
            data = atomic_read_json(self.lootbox_file)
            if data is not None:
                return data
        except Exception as e:
            logger.warning(f"Could not load lootbox data: {e}")
        return {}

    def _save_data(self, data):
        try:
            atomic_write_json(self.lootbox_file, data)
        except Exception as e:
            logger.error(f"Could not save lootbox data: {e}")

    def _get_user_data(self, data, username):
        if username not in data:
            data[username] = {
                "crates": [],
                "history": [],
                "pity_counter": 0,
            }
        return data[username]

    # ------------------------------------------------------------------
    # Purchase
    # ------------------------------------------------------------------

    def purchase_crate(self, username, crate_type):
        """Purchase a crate. Caller must handle coin deduction."""
        if crate_type not in CRATE_TYPES:
            return {"success": False, "message": "Unbekannter Kisten-Typ"}

        crate_info = CRATE_TYPES[crate_type]
        crate_id = str(uuid.uuid4())[:8]

        data = self._load_data()
        user_data = self._get_user_data(data, username)

        crate = {
            "id": crate_id,
            "type": crate_type,
            "purchased_at": datetime.now(TZ).isoformat(),
            "opened": False,
        }
        user_data["crates"].append(crate)
        self._save_data(data)

        logger.info(f"{username} purchased {crate_type} crate ({crate_id})")
        return {
            "success": True,
            "crate_id": crate_id,
            "crate_type": crate_type,
            "crate_name": crate_info["name"],
            "price": crate_info["price"],
        }

    # ------------------------------------------------------------------
    # Open
    # ------------------------------------------------------------------

    def open_crate(self, username, crate_id):
        """Open a purchased crate and roll loot."""
        data = self._load_data()
        user_data = self._get_user_data(data, username)

        # Find crate
        crate = None
        for c in user_data["crates"]:
            if c["id"] == crate_id and not c.get("opened"):
                crate = c
                break

        if not crate:
            return {"success": False, "message": "Kiste nicht gefunden oder bereits geoeffnet"}

        crate_type = crate["type"]
        loot_table = LOOT_TABLES.get(crate_type, LOOT_TABLES["common"])

        # Pity system
        pity = user_data.get("pity_counter", 0)
        reward = self._roll_loot(loot_table, pity)

        # Update pity counter
        is_good_drop = reward["type"] == "cosmetic" and reward.get("rarity") in ("epic", "legendary")
        if is_good_drop:
            user_data["pity_counter"] = 0
        else:
            user_data["pity_counter"] = pity + 1

        # Mark crate opened
        crate["opened"] = True
        crate["opened_at"] = datetime.now(TZ).isoformat()
        crate["reward"] = reward

        # Record history
        user_data["history"].append({
            "crate_id": crate_id,
            "crate_type": crate_type,
            "reward": reward,
            "opened_at": crate["opened_at"],
        })

        # Keep only last 50 history entries
        if len(user_data["history"]) > 50:
            user_data["history"] = user_data["history"][-50:]

        self._save_data(data)

        # Apply reward
        applied = self._apply_reward(username, reward)

        logger.info(f"{username} opened {crate_type} crate ({crate_id}): {reward['type']} - {reward.get('display', '')}")

        try:
            from app.services.audit_service import audit_service
            audit_service.log('lootbox_opened', username, {
                'crate_type': crate_type,
                'reward_type': reward['type'],
                'reward_display': reward.get('display', ''),
            })
        except Exception as e:
            logger.debug(f"Audit log for lootbox skipped: {e}")

        return {
            "success": True,
            "reward": reward,
            "applied": applied,
            "crate_type": crate_type,
        }

    def _roll_loot(self, loot_table, pity_counter):
        """Weighted random roll from a loot table with pity system."""
        # Pity system: after PITY_THRESHOLD opens without epic+, guarantee rare+
        if pity_counter >= PITY_THRESHOLD:
            # Filter to only rare+ cosmetics or boosters/shields
            good_entries = [
                entry for entry in loot_table
                if (entry[1] == "cosmetic" and entry[2].get("rarity") in ("rare", "epic", "legendary"))
                or entry[1] in ("booster", "streak_shield", "bonus_spins")
            ]
            if good_entries:
                loot_table = good_entries

        weights = [entry[0] for entry in loot_table]
        chosen = random.choices(loot_table, weights=weights, k=1)[0]
        _, reward_type, config = chosen

        return self._build_reward(reward_type, config)

    def _build_reward(self, reward_type, config):
        """Build a concrete reward dict from type and config."""
        if reward_type == "coins":
            amount = random.randint(config["min"], config["max"])
            return {"type": "coins", "amount": amount, "display": f"{amount} Coins"}

        if reward_type == "xp":
            amount = random.randint(config["min"], config["max"])
            return {"type": "xp", "amount": amount, "display": f"{amount} XP"}

        if reward_type == "cosmetic":
            rarity = config["rarity"]
            pool = COSMETIC_DROPS.get(rarity, COSMETIC_DROPS["common"])
            item = random.choice(pool)
            return {
                "type": "cosmetic",
                "rarity": rarity,
                "item_id": item["id"],
                "item_type": item["type"],
                "item_name": item["name"],
                "display": f"{item['name']} ({rarity})",
            }

        if reward_type == "booster":
            return {
                "type": "booster",
                "multiplier": config.get("multiplier", 1.5),
                "hours": config.get("hours", 1),
                "display": f"{config.get('multiplier', 1.5)}x XP-Booster ({config.get('hours', 1)}h)",
            }

        if reward_type == "streak_shield":
            return {"type": "streak_shield", "display": "Streak-Shield"}

        if reward_type == "bonus_spins":
            count = config.get("count", 1)
            return {"type": "bonus_spins", "count": count, "display": f"{count}x Bonus-Spin"}

        return {"type": "coins", "amount": 10, "display": "10 Coins"}

    def _apply_reward(self, username, reward):
        """Actually grant the reward to the user. Returns dict with what was applied."""
        reward_type = reward["type"]
        applied = {"type": reward_type}

        try:
            if reward_type == "coins":
                from app.services.daily_quests import daily_quest_system
                coins_data = daily_quest_system.load_user_coins()
                coins_data[username] = coins_data.get(username, 0) + reward["amount"]
                daily_quest_system.save_user_coins(coins_data)
                applied["amount"] = reward["amount"]

            elif reward_type == "xp":
                # XP is added via scores (10 points = XP in level system)
                from app.services.data_persistence import data_persistence
                scores = data_persistence.load_scores()
                import pytz
                month = datetime.now(TZ).strftime("%Y-%m")
                if username not in scores:
                    scores[username] = {}
                scores[username][month] = scores[username].get(month, 0) + (reward["amount"] // 10)
                data_persistence.save_scores(scores)
                applied["xp"] = reward["amount"]

            elif reward_type == "cosmetic":
                from app.services.cosmetics_shop import cosmetics_shop
                # Grant cosmetic to user without coin cost
                purchases = cosmetics_shop.load_purchases()
                if username not in purchases:
                    purchases[username] = {"titles": [], "themes": [], "avatars": [], "effects": [], "frames": [], "purchase_history": []}

                item_type = reward["item_type"]
                list_key = item_type + "s" if item_type != "effect" else "effects"
                if list_key not in purchases[username]:
                    purchases[username][list_key] = []
                if reward["item_id"] not in purchases[username].get(list_key, []):
                    purchases[username][list_key].append(reward["item_id"])
                    purchases[username]["purchase_history"].append({
                        "item_type": item_type,
                        "item_id": reward["item_id"],
                        "item_name": reward["item_name"],
                        "price": 0,
                        "source": "lootbox",
                        "purchased_at": datetime.now(TZ).isoformat(),
                    })
                    cosmetics_shop.save_purchases(purchases)
                applied["item_id"] = reward["item_id"]

            elif reward_type == "booster":
                from app.services.gameplay_rewards import gameplay_rewards
                gameplay_rewards.activate_xp_booster(
                    username,
                    multiplier=reward.get("multiplier", 1.5),
                    duration_hours=reward.get("hours", 1),
                )
                applied["booster"] = True

            elif reward_type == "streak_shield":
                from app.services.gameplay_rewards import gameplay_rewards
                gameplay_rewards.activate_streak_shield(username)
                applied["shield"] = True

            elif reward_type == "bonus_spins":
                from app.services.gameplay_rewards import gameplay_rewards
                gameplay_rewards.add_bonus_spins(username, reward.get("count", 1))
                applied["spins"] = reward.get("count", 1)

        except Exception as e:
            logger.error(f"Failed to apply lootbox reward for {username}: {e}")
            applied["error"] = str(e)

        return applied

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_unopened_crates(self, username):
        data = self._load_data()
        user_data = self._get_user_data(data, username)
        return [c for c in user_data["crates"] if not c.get("opened")]

    def get_loot_history(self, username, limit=20):
        data = self._load_data()
        user_data = self._get_user_data(data, username)
        history = user_data.get("history", [])
        return list(reversed(history[-limit:]))


lootbox_service = LootboxService()
