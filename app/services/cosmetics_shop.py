# -*- coding: utf-8 -*-
"""
Cosmetics Shop System für Slot Booking Webapp
Lustige Titel, Themes und Personalisierungsoptionen mit Coins kaufen
"""

import os
import json
import pytz
import logging
from datetime import datetime, timedelta

# Logger setup
logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")

# Lustige Titel Shop
TITLE_SHOP = {
    # Günstige Titel (50-100 Coins)
    "booking_rookie": {
        "name": "🌱 Buchungs-Neuling",
        "price": 50,
        "description": "Für alle, die gerade erst anfangen",
        "rarity": "common",
        "category": "beginner"
    },
    "coffee_addict": {
        "name": "☕ Koffein-Junkie", 
        "price": 75,
        "description": "Bucht nur nach dem dritten Espresso",
        "rarity": "common",
        "category": "lifestyle"
    },
    "early_bird": {
        "name": "🐦 Früher Vogel",
        "price": 80,
        "description": "Immer der Erste im Büro",
        "rarity": "common", 
        "category": "timing"
    },
    "night_owl": {
        "name": "🦉 Nachtaktiv",
        "price": 80,
        "description": "Bucht am liebsten Abendtermine",
        "rarity": "common",
        "category": "timing"
    },
    
    # Mittlere Titel (150-250 Coins)
    "speed_demon": {
        "name": "💨 Geschwindigkeitsdämon",
        "price": 150,
        "description": "Bucht schneller als der eigene Schatten",
        "rarity": "uncommon",
        "category": "performance"
    },
    "detail_detective": {
        "name": "🔍 Detail-Detektiv",
        "price": 180,
        "description": "Füllt jedes Feld perfekt aus",
        "rarity": "uncommon",
        "category": "quality"
    },
    "calendar_wizard": {
        "name": "🧙‍♂️ Kalender-Zauberer",
        "price": 200,
        "description": "Beherrscht jeden Terminkalender",
        "rarity": "uncommon",
        "category": "skill"
    },
    "streak_master": {
        "name": "🔥 Streak-Meister",
        "price": 220,
        "description": "Verliert nie seine Serie",
        "rarity": "uncommon",
        "category": "consistency"
    },
    "weekend_warrior": {
        "name": "⚔️ Wochenend-Krieger",
        "price": 180,
        "description": "Plant schon Freitag die nächste Woche",
        "rarity": "uncommon",
        "category": "planning"
    },
    
    # Teure Titel (300-500 Coins)
    "booking_overlord": {
        "name": "👑 Buchungs-Overlord",
        "price": 350,
        "description": "Herrscht über alle Terminkalender",
        "rarity": "rare",
        "category": "dominance"
    },
    "time_bender": {
        "name": "⏰ Zeit-Verbieger",
        "price": 400,
        "description": "Macht aus 24 Stunden irgendwie 30",
        "rarity": "rare",
        "category": "mystical"
    },
    "slot_whisperer": {
        "name": "💫 Slot-Flüsterer",
        "price": 450,
        "description": "Spricht mit freien Terminen",
        "rarity": "rare",
        "category": "mystical"
    },
    "efficiency_god": {
        "name": "⚡ Effizienz-Gott",
        "price": 380,
        "description": "Optimiert alles bis zur Perfektion",
        "rarity": "rare",
        "category": "performance"
    },
    
    # Legendäre Titel (600-1000 Coins)
    "chronos_disciple": {
        "name": "🕰️ Chronos' Jünger",
        "price": 750,
        "description": "Zeit ist nur ein Konstrukt",
        "rarity": "epic",
        "category": "legendary"
    },
    "appointment_architect": {
        "name": "🏗️ Termin-Architekt",
        "price": 800,
        "description": "Erbaut Terminkathedralen",
        "rarity": "epic",
        "category": "legendary"
    },
    "slot_emperor": {
        "name": "🏆 Slot-Kaiser",
        "price": 900,
        "description": "Regiert das Slot-Imperium",
        "rarity": "epic",
        "category": "legendary"
    },
    
    # Mythische Titel (1000+ Coins)
    "temporal_lord": {
        "name": "🌌 Zeit-Lord",
        "price": 1500,
        "description": "Meister von Raum und Zeit",
        "rarity": "legendary",
        "category": "mythical"
    },
    "booking_deity": {
        "name": "✨ Buchungs-Gottheit", 
        "price": 2000,
        "description": "Transzendiert die Grenzen normaler Termine",
        "rarity": "legendary",
        "category": "mythical"
    }
}

# Farb-Themes Shop
COLOR_THEMES = {
    "sunset_vibes": {
        "name": "🌅 Sonnenuntergang-Vibes",
        "price": 200,
        "description": "Warme Orange- und Rosatöne",
        "colors": {"primary": "#ff6b35", "secondary": "#f7931e", "accent": "#ff9f43"},
        "rarity": "common"
    },
    "ocean_breeze": {
        "name": "🌊 Ozean-Brise",
        "price": 200, 
        "description": "Beruhigende Blau- und Türkistöne",
        "colors": {"primary": "#0066cc", "secondary": "#00aaff", "accent": "#33ccff"},
        "rarity": "common"
    },
    "forest_zen": {
        "name": "🌲 Wald-Zen",
        "price": 250,
        "description": "Entspannende Grün- und Brauntöne",
        "colors": {"primary": "#2d5a27", "secondary": "#4a7c59", "accent": "#7fb069"},
        "rarity": "uncommon"
    },
    "neon_cyber": {
        "name": "💾 Neon-Cyber",
        "price": 400,
        "description": "Futuristisches Neon-Design",
        "colors": {"primary": "#ff00ff", "secondary": "#00ffff", "accent": "#ffff00"},
        "rarity": "rare"
    },
    "royal_purple": {
        "name": "👑 Königliches Lila",
        "price": 600,
        "description": "Luxuriöse Lila- und Goldtöne",
        "colors": {"primary": "#663399", "secondary": "#9966cc", "accent": "#ffd700"},
        "rarity": "epic"
    },
    "rainbow_explosion": {
        "name": "🌈 Regenbogen-Explosion",
        "price": 1000,
        "description": "Alle Farben des Spektrums",
        "colors": {"primary": "rainbow", "secondary": "rainbow", "accent": "rainbow"},
        "rarity": "legendary",
        "special_effect": "rainbow_animation"
    }
}

# Avatar Shop - Male & Female Variants (PNG Images)
AVATAR_SHOP = {
    # Basic Professional Avatars (50-100 Coins)
    "business_male": {
        "emoji": "🧑‍💼",
        "name": "Business",
        "price": 50,
        "category": "professional",
        "gender": "male",
        "image": "/static/avatars/business_male.png",
        "description": "Professioneller Business-Look"
    },
    "business_female": {
        "emoji": "👩‍💼",
        "name": "Business",
        "price": 50,
        "category": "professional",
        "gender": "female",
        "image": "/static/avatars/business_female.png",
        "description": "Professioneller Business-Look"
    },
    "developer_male": {
        "emoji": "👨‍💻",
        "name": "Developer",
        "price": 75,
        "category": "tech",
        "gender": "male",
        "image": "/static/avatars/developer_male.png",
        "description": "Code-Ninja im Flow"
    },
    "developer_female": {
        "emoji": "👩‍💻",
        "name": "Developer",
        "price": 75,
        "category": "tech",
        "gender": "female",
        "image": "/static/avatars/developer_female.png",
        "description": "Code-Ninja im Flow"
    },
    "manager_male": {
        "emoji": "👨‍💼",
        "name": "Manager",
        "price": 80,
        "category": "professional",
        "gender": "male",
        "image": "/static/avatars/manager_male.png",
        "description": "Führungskraft mit Weitblick"
    },
    "manager_female": {
        "emoji": "👩‍💼",
        "name": "Manager",
        "price": 80,
        "category": "professional",
        "gender": "female",
        "image": "/static/avatars/manager_female.png",
        "description": "Führungskraft mit Weitblick"
    },
    "student_male": {
        "emoji": "👨‍🎓",
        "name": "Student",
        "price": 60,
        "category": "academic",
        "gender": "male",
        "image": "/static/avatars/student_male.png",
        "description": "Wissbegieriger Lernender"
    },
    "student_female": {
        "emoji": "👩‍🎓",
        "name": "Studentin",
        "price": 60,
        "category": "academic",
        "gender": "female",
        "image": "/static/avatars/student_female.png",
        "description": "Wissbegierige Lernende"
    },

    # Fun Avatars (150-200 Coins)
    "ninja_male": {
        "emoji": "🥷",
        "name": "Ninja",
        "price": 150,
        "category": "fun",
        "gender": "male",
        "image": "/static/avatars/ninja_male.png",
        "description": "Meister der Schatten"
    },
    "ninja_female": {
        "emoji": "🥷",
        "name": "Ninja",
        "price": 150,
        "category": "fun",
        "gender": "female",
        "image": "/static/avatars/ninja_female.png",
        "description": "Meisterin der Schatten"
    },
    "superhero_male": {
        "emoji": "🦸‍♂️",
        "name": "Superheld",
        "price": 200,
        "category": "heroic",
        "gender": "male",
        "image": "/static/avatars/superhero_male.png",
        "description": "Retter in der Not"
    },
    "superhero_female": {
        "emoji": "🦸‍♀️",
        "name": "Superheldin",
        "price": 200,
        "category": "heroic",
        "gender": "female",
        "image": "/static/avatars/superhero_female.png",
        "description": "Retterin in der Not"
    },
    "wizard_male": {
        "emoji": "🧙‍♂️",
        "name": "Zauberer",
        "price": 180,
        "category": "mystical",
        "gender": "male",
        "image": "/static/avatars/wizard_male.png",
        "description": "Meister der Magie"
    },
    "wizard_female": {
        "emoji": "🧙‍♀️",
        "name": "Zauberin",
        "price": 180,
        "category": "mystical",
        "gender": "female",
        "image": "/static/avatars/wizard_female.png",
        "description": "Meisterin der Magie"
    },
    "pirate_male": {
        "emoji": "🏴‍☠️",
        "name": "Pirat",
        "price": 160,
        "category": "adventure",
        "gender": "male",
        "image": "/static/avatars/pirate_male.png",
        "description": "Abenteurer der Meere"
    },
    "pirate_female": {
        "emoji": "🏴‍☠️",
        "name": "Piratin",
        "price": 160,
        "category": "adventure",
        "gender": "female",
        "image": "/static/avatars/pirate_female.png",
        "description": "Abenteurerin der Meere"
    },

    # Premium Avatars (300-500 Coins)
    "robot_male": {
        "emoji": "🤖",
        "name": "Robot",
        "price": 300,
        "category": "tech",
        "gender": "male",
        "image": "/static/avatars/robot_male.png",
        "description": "Futuristische KI-Einheit"
    },
    "robot_female": {
        "emoji": "🤖",
        "name": "Robot",
        "price": 300,
        "category": "tech",
        "gender": "female",
        "image": "/static/avatars/robot_female.png",
        "description": "Futuristische KI-Einheit"
    },
    "alien_male": {
        "emoji": "👽",
        "name": "Alien",
        "price": 400,
        "category": "space",
        "gender": "male",
        "image": "/static/avatars/alien_male.png",
        "description": "Besucher aus dem All"
    },
    "alien_female": {
        "emoji": "👽",
        "name": "Alien",
        "price": 400,
        "category": "space",
        "gender": "female",
        "image": "/static/avatars/alien_female.png",
        "description": "Besucherin aus dem All"
    },
    "crown_male": {
        "emoji": "👑",
        "name": "König",
        "price": 500,
        "category": "luxury",
        "gender": "male",
        "image": "/static/avatars/crown_male.png",
        "description": "Majestätische Herrschaft"
    },
    "crown_female": {
        "emoji": "👑",
        "name": "Königin",
        "price": 500,
        "category": "luxury",
        "gender": "female",
        "image": "/static/avatars/crown_female.png",
        "description": "Majestätische Herrschaft"
    }
}

# Avatar-Rahmen Shop
FRAME_SHOP = {
    "frame_gold": {"name": "Goldrahmen", "description": "Eleganter goldener Rahmen", "price": 200, "rarity": "rare", "css_class": "ring-4 ring-yellow-400 shadow-lg shadow-yellow-400/50"},
    "frame_diamond": {"name": "Diamant", "description": "Funkelnder Diamant-Rahmen", "price": 500, "rarity": "epic", "css_class": "ring-4 ring-cyan-300 shadow-lg shadow-cyan-300/50"},
    "frame_fire": {"name": "Feuer", "description": "Brennender Rahmen", "price": 400, "rarity": "epic", "css_class": "ring-4 ring-orange-500 shadow-lg shadow-orange-500/50 animate-pulse"},
    "frame_neon": {"name": "Neon", "description": "Leuchtender Neon-Rahmen", "price": 300, "rarity": "rare", "css_class": "ring-4 ring-green-400 shadow-lg shadow-green-400/50"},
    "frame_rainbow": {"name": "Regenbogen", "description": "Schillernder Regenbogen-Rahmen", "price": 750, "rarity": "legendary", "css_class": "ring-4 ring-purple-400 shadow-lg shadow-purple-400/30"},
    "frame_frost": {"name": "Frost", "description": "Eisiger Frost-Rahmen", "price": 350, "rarity": "rare", "css_class": "ring-4 ring-blue-300 shadow-lg shadow-blue-300/50"},
    "frame_shadow": {"name": "Schatten", "description": "Mysterioeser Schatten-Rahmen", "price": 450, "rarity": "epic", "css_class": "ring-4 ring-gray-600 shadow-lg shadow-gray-900/70"},
    "frame_cherry": {"name": "Kirschbluete", "description": "Fruehlings-Rahmen", "price": 300, "rarity": "rare", "css_class": "ring-4 ring-pink-300 shadow-lg shadow-pink-300/50", "seasonal": "spring"},
    "frame_holly": {"name": "Stechpalme", "description": "Winter-Rahmen", "price": 300, "rarity": "rare", "css_class": "ring-4 ring-red-600 shadow-lg shadow-green-600/50", "seasonal": "winter"},
    "frame_starter": {"name": "Basis-Rahmen", "description": "Einfacher Rahmen fuer Einsteiger", "price": 50, "rarity": "common", "css_class": "ring-2 ring-base-content/30"},
    # Milestone-exclusive frames (NOT purchasable)
    "frame_centurion": {"name": "Centurion-Rahmen", "description": "Exklusiv: 100 Buchungen", "price": 0, "rarity": "epic", "css_class": "ring-4 ring-amber-500 shadow-lg shadow-amber-500/50", "milestone_exclusive": True},
}

# Animations/Effekte Shop
SPECIAL_EFFECTS = {
    "sparkle_trail": {
        "name": "✨ Glitzer-Spur",
        "price": 300,
        "description": "Hinterlässt Glitzer bei Mausklicks",
        "effect": "sparkle_cursor",
        "rarity": "rare"
    },
    "typing_sounds": {
        "name": "⌨️ Tipp-Geräusche",
        "price": 150,
        "description": "Mechanische Tastatur-Sounds",
        "effect": "keyboard_sounds",
        "rarity": "uncommon"
    },
    "success_fanfare": {
        "name": "🎺 Erfolgs-Fanfare",
        "price": 200,
        "description": "Epische Musik bei erfolgreichen Buchungen",
        "effect": "booking_fanfare",
        "rarity": "uncommon"
    },
    "confetti_explosion": {
        "name": "🎉 Konfetti-Explosion",
        "price": 400,
        "description": "Konfetti-Regen bei Achievements",
        "effect": "achievement_confetti",
        "rarity": "rare"
    },
    "screen_shake": {
        "name": "📳 Bildschirm-Beben",
        "price": 250,
        "description": "Screen Shake bei wichtigen Events",
        "effect": "screen_shake",
        "rarity": "uncommon"
    },
    "rainbow_glow": {
        "name": "🌈 Regenbogen-Leuchten",
        "price": 500,
        "description": "Dein Avatar leuchtet in Regenbogenfarben",
        "effect": "rainbow_glow",
        "rarity": "rare"
    },
    "particle_trail": {
        "name": "💫 Partikel-Spur",
        "price": 600,
        "description": "Leuchtende Partikel folgen deiner Maus",
        "effect": "particle_trail",
        "rarity": "epic"
    },
    "seasonal_snow": {
        "name": "❄️ Schneefall",
        "price": 350,
        "description": "Sanfter Schneefall auf deinem Profil",
        "effect": "seasonal_snow",
        "rarity": "rare"
    },
    "cherry_blossom": {
        "name": "🌸 Kirschblueten",
        "price": 350,
        "description": "Fallende Kirschblueten-Blätter",
        "effect": "cherry_blossom",
        "rarity": "rare"
    },
    # Milestone-exclusive effect (NOT purchasable)
    "legendary_aura": {
        "name": "🔮 Legendaere Aura",
        "price": 0,
        "description": "Exklusiv: 500 Buchungen",
        "effect": "legendary_aura",
        "rarity": "legendary",
        "milestone_exclusive": True
    },
}

class CosmeticsShop:
    def __init__(self):
        # Use correct server paths
        self.purchases_file = "persist/persistent/cosmetic_purchases.json"
        self.active_cosmetics_file = "persist/persistent/active_cosmetics.json"

        # Ensure directories exist
        os.makedirs("persist/persistent", exist_ok=True)

        # Initialize files
        for file_path in [self.purchases_file, self.active_cosmetics_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)

    # --- PostgreSQL Dual-Write Helpers ---

    def _get_item_shop(self, item_type):
        """Hole Shop-Dict fuer einen Item-Typ"""
        shops = {
            "title": TITLE_SHOP,
            "theme": COLOR_THEMES,
            "avatar": AVATAR_SHOP,
            "effect": SPECIAL_EFFECTS,
            "frame": FRAME_SHOP,
        }
        return shops.get(item_type, {})

    def _get_item_category(self, item_type):
        """Mappe item_type auf PG item_category"""
        categories = {
            "title": "visual",
            "theme": "visual",
            "avatar": "visual",
            "effect": "animation",
            "frame": "visual",
        }
        return categories.get(item_type, "visual")

    def _pg_sync_purchase(self, user, item_type, item_id, price):
        """Dual-Write: Kauf in PostgreSQL syncen"""
        try:
            from app.models.cosmetics import UserCosmetic
            from app.core.extensions import db

            item_data = self._get_item_shop(item_type).get(item_id, {})
            existing = UserCosmetic.query.filter_by(
                username=user, item_id=item_id
            ).first()

            if existing:
                existing.is_owned = True
                existing.purchase_price = price
                existing.unlock_date = datetime.now(TZ)
            else:
                cosmetic = UserCosmetic(
                    username=user,
                    item_id=item_id,
                    item_type=item_type,
                    item_category=self._get_item_category(item_type),
                    name=item_data.get("name", item_id),
                    description=item_data.get("description", ""),
                    rarity=item_data.get("rarity", "common"),
                    is_owned=True,
                    is_active=False,
                    unlock_date=datetime.now(TZ),
                    purchase_price=price,
                    config=item_data.get("colors"),
                )
                db.session.add(cosmetic)

            db.session.commit()
        except Exception as e:
            logger.debug(f"PG cosmetic purchase sync skipped: {e}")

    def _pg_sync_equip(self, user, item_type, item_id):
        """Dual-Write: Equip-Status in PostgreSQL syncen"""
        try:
            from app.models.cosmetics import UserCosmetic
            from app.core.extensions import db

            if item_type != "effect":
                # Deaktiviere alle Items desselben Typs
                UserCosmetic.query.filter_by(
                    username=user, item_type=item_type, is_active=True
                ).update({"is_active": False})

            # Aktiviere das neue Item
            item = UserCosmetic.query.filter_by(
                username=user, item_id=item_id
            ).first()
            if item:
                item.is_active = True
                db.session.commit()
        except Exception as e:
            logger.debug(f"PG cosmetic equip sync skipped: {e}")

    def _pg_sync_unequip(self, user, item_type, item_id=None):
        """Dual-Write: Unequip-Status in PostgreSQL syncen"""
        try:
            from app.models.cosmetics import UserCosmetic
            from app.core.extensions import db

            if item_type == "effect" and item_id:
                UserCosmetic.query.filter_by(
                    username=user, item_id=item_id
                ).update({"is_active": False})
            elif item_type == "effect":
                UserCosmetic.query.filter_by(
                    username=user, item_type="effect", is_active=True
                ).update({"is_active": False})
            else:
                UserCosmetic.query.filter_by(
                    username=user, item_type=item_type, is_active=True
                ).update({"is_active": False})

            db.session.commit()
        except Exception as e:
            logger.debug(f"PG cosmetic unequip sync skipped: {e}")
    
    def load_purchases(self):
        """Lade gekaufte Kosmetik-Items"""
        try:
            with open(self.purchases_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load purchases file", extra={'error': str(e)})
            return {}
    
    def save_purchases(self, data):
        """Speichere gekaufte Kosmetik-Items"""
        with open(self.purchases_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_active_cosmetics(self):
        """Lade aktive Kosmetik-Items"""
        try:
            with open(self.active_cosmetics_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load active cosmetics file", extra={'error': str(e)})
            return {}
    
    def save_active_cosmetics(self, data):
        """Speichere aktive Kosmetik-Items"""
        with open(self.active_cosmetics_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_user_cosmetics(self, user):
        """Hole alle Kosmetik-Daten für einen User"""
        purchases = self.load_purchases()
        active = self.load_active_cosmetics()

        user_purchases = purchases.get(user, {
            "titles": [],
            "themes": [],
            "avatars": [],
            "effects": [],
            "frames": [],
            "purchase_history": []
        })

        # Ensure frames key exists for older data
        if "frames" not in user_purchases:
            user_purchases["frames"] = []

        # Admin-Users bekommen automatisch alle Items freigeschaltet
        admin_users = ["Luke", "admin", "Jose", "Simon", "Alex", "David"]
        if user in admin_users:
            user_purchases = {
                "titles": list(TITLE_SHOP.keys()),
                "themes": list(COLOR_THEMES.keys()),
                "avatars": list(AVATAR_SHOP.keys()),
                "effects": list(SPECIAL_EFFECTS.keys()),
                "frames": list(FRAME_SHOP.keys()),
                "purchase_history": user_purchases.get("purchase_history", [])
            }

        user_active = active.get(user, {
            "title": None,
            "theme": "default",
            "avatar": "🧑‍💼",
            "effects": [],
            "frame": None
        })

        return {
            "owned": user_purchases,
            "active": user_active,
            "available_titles": self.get_available_items(user, "titles"),
            "available_themes": self.get_available_themes(user),
            "available_avatars": self.get_available_avatars(user),
            "available_effects": self.get_available_effects(user),
            "available_frames": self.get_available_frames(user)
        }
    
    def get_available_items(self, user, item_type):
        """Hole verfügbare Items zum Kauf"""
        purchases = self.load_purchases()
        user_purchases = purchases.get(user, {})
        owned_items = user_purchases.get(item_type, [])
        
        if item_type == "titles":
            return {k: v for k, v in TITLE_SHOP.items() if k not in owned_items}
        
        return {}
    
    def get_available_themes(self, user):
        """Hole verfügbare Themes zum Kauf"""
        purchases = self.load_purchases()
        user_purchases = purchases.get(user, {})
        owned_themes = user_purchases.get("themes", [])
        
        return {k: v for k, v in COLOR_THEMES.items() if k not in owned_themes}
    
    def get_available_avatars(self, user):
        """Hole verfügbare Avatars zum Kauf"""
        purchases = self.load_purchases()
        user_purchases = purchases.get(user, {})
        owned_avatars = user_purchases.get("avatars", [])

        return {k: v for k, v in AVATAR_SHOP.items() if k not in owned_avatars}
    
    def get_available_effects(self, user):
        """Hole verfügbare Effekte zum Kauf"""
        purchases = self.load_purchases()
        user_purchases = purchases.get(user, {})
        owned_effects = user_purchases.get("effects", [])
        
        return {k: v for k, v in SPECIAL_EFFECTS.items() if k not in owned_effects}
    
    def purchase_item(self, user, item_type, item_id, user_coins):
        """Kaufe Kosmetik-Item"""
        # Bestimme Item-Daten
        item_data = None
        price = 0
        
        if item_type == "title" and item_id in TITLE_SHOP:
            item_data = TITLE_SHOP[item_id]
            price = item_data["price"]
        elif item_type == "theme" and item_id in COLOR_THEMES:
            item_data = COLOR_THEMES[item_id]
            price = item_data["price"]
        elif item_type == "avatar" and item_id in AVATAR_SHOP:
            item_data = AVATAR_SHOP[item_id]
            price = item_data["price"]
        elif item_type == "effect" and item_id in SPECIAL_EFFECTS:
            item_data = SPECIAL_EFFECTS[item_id]
            price = item_data["price"]
        elif item_type == "frame" and item_id in FRAME_SHOP:
            item_data = FRAME_SHOP[item_id]
            if item_data.get("milestone_exclusive"):
                return {"success": False, "message": "Dieses Item ist exklusiv und nicht kaufbar"}
            price = item_data["price"]
        else:
            return {"success": False, "message": "Item nicht gefunden"}

        # Block milestone-exclusive effects
        if item_type == "effect" and item_id in SPECIAL_EFFECTS:
            if SPECIAL_EFFECTS[item_id].get("milestone_exclusive"):
                return {"success": False, "message": "Dieses Item ist exklusiv und nicht kaufbar"}
        
        # Prüfe Coins
        if user_coins < price:
            return {"success": False, "message": f"Nicht genug Coins! Benötigt: {price}, Verfügbar: {user_coins}"}
        
        # Prüfe ob bereits gekauft
        purchases = self.load_purchases()
        if user not in purchases:
            purchases[user] = {"titles": [], "themes": [], "avatars": [], "effects": [], "frames": [], "purchase_history": []}

        item_list_key = item_type + "s" if item_type != "effect" else "effects"
        # Ensure the list key exists (backwards compat for older data)
        if item_list_key not in purchases[user]:
            purchases[user][item_list_key] = []

        if item_id in purchases[user].get(item_list_key, []):
            return {"success": False, "message": "Item bereits gekauft"}

        # Kaufe Item
        purchases[user][item_list_key].append(item_id)
        purchases[user]["purchase_history"].append({
            "item_type": item_type,
            "item_id": item_id,
            "item_name": item_data["name"],
            "price": price,
            "purchased_at": datetime.now(TZ).isoformat()
        })
        
        self.save_purchases(purchases)
        self._pg_sync_purchase(user, item_type, item_id, price)

        return {
            "success": True,
            "message": f"'{item_data['name']}' erfolgreich gekauft!",
            "item": item_data,
            "price": price
        }
    
    def equip_item(self, user, item_type, item_id):
        """Rüste Kosmetik-Item aus"""
        # Prüfe ob User das Item besitzt
        purchases = self.load_purchases()
        user_purchases = purchases.get(user, {})

        item_list_key = item_type + "s" if item_type != "effect" else "effects"
        if item_id not in user_purchases.get(item_list_key, []):
            return {"success": False, "message": "Item nicht im Besitz"}

        # Aktiviere Item
        active = self.load_active_cosmetics()
        if user not in active:
            active[user] = {"title": None, "theme": "default", "avatar": "🧑‍💼", "effects": [], "frame": None}
        # Ensure frame key exists for older data
        if "frame" not in active[user]:
            active[user]["frame"] = None

        if item_type == "effect":
            # Effekte können mehrere aktiv sein
            if item_id not in active[user].get("effects", []):
                if "effects" not in active[user]:
                    active[user]["effects"] = []
                active[user]["effects"].append(item_id)
        else:
            # Andere Items ersetzen das aktuelle
            active[user][item_type] = item_id

        self.save_active_cosmetics(active)
        self._pg_sync_equip(user, item_type, item_id)

        # Hole Item-Daten für Response
        item_data = None
        if item_type == "title":
            item_data = TITLE_SHOP.get(item_id, {})
        elif item_type == "theme":
            item_data = COLOR_THEMES.get(item_id, {})
        elif item_type == "avatar":
            item_data = AVATAR_SHOP.get(item_id, {})
            # Sync avatar selection to avatar_service
            try:
                from app.services.avatar_service import avatar_service
                avatar_service.save_shop_avatar(user, item_id)
            except Exception as e:
                logger.debug(f"Avatar service sync skipped: {e}")
        elif item_type == "effect":
            item_data = SPECIAL_EFFECTS.get(item_id, {})
        elif item_type == "frame":
            item_data = FRAME_SHOP.get(item_id, {})

        return {
            "success": True,
            "message": f"'{item_data.get('name', item_id)}' ausgerüstet!",
            "item": item_data
        }
    
    def unequip_item(self, user, item_type, item_id=None):
        """Entferne Kosmetik-Item"""
        active = self.load_active_cosmetics()
        if user not in active:
            return {"success": False, "message": "Keine aktiven Items"}
        
        if item_type == "effect" and item_id:
            # Spezifischen Effekt entfernen
            if item_id in active[user].get("effects", []):
                active[user]["effects"].remove(item_id)
        elif item_type == "effect":
            # Alle Effekte entfernen
            active[user]["effects"] = []
        else:
            # Item auf Standard zurücksetzen
            defaults = {"title": None, "theme": "default", "avatar": "🧑‍💼", "frame": None}
            active[user][item_type] = defaults.get(item_type)
        
        self.save_active_cosmetics(active)
        self._pg_sync_unequip(user, item_type, item_id)

        return {"success": True, "message": f"{item_type.title()} entfernt"}
    
    # ------------------------------------------------------------------
    # Frame-specific methods
    # ------------------------------------------------------------------

    def get_available_frames(self, user):
        """Return frames available for purchase (excl. owned and milestone-exclusive)."""
        purchases = self.load_purchases()
        user_purchases = purchases.get(user, {})
        owned_frames = user_purchases.get("frames", [])

        available = {}
        for frame_id, frame in FRAME_SHOP.items():
            if frame_id in owned_frames:
                continue
            if frame.get("milestone_exclusive"):
                continue
            # Seasonal filter
            if frame.get("seasonal"):
                try:
                    from app.services.seasonal_events import seasonal_events
                    current_season = seasonal_events.get_current_season()
                    if frame["seasonal"] != current_season:
                        continue
                except Exception:
                    continue
            available[frame_id] = frame
        return available

    def equip_frame(self, username, frame_id):
        """Equip a frame for a user."""
        return self.equip_item(username, "frame", frame_id)

    def get_user_frame(self, username):
        """Return the CSS class for the user's active frame, or empty string."""
        active = self.load_active_cosmetics()
        user_active = active.get(username, {})
        frame_id = user_active.get("frame")
        if frame_id and frame_id in FRAME_SHOP:
            return FRAME_SHOP[frame_id]["css_class"]
        return ""

    def grant_milestone_cosmetic(self, username, item_type, item_id):
        """Grant a milestone-exclusive cosmetic to a user (no coin cost)."""
        shop = self._get_item_shop(item_type)
        if item_id not in shop:
            return {"success": False, "message": "Item nicht gefunden"}

        purchases = self.load_purchases()
        if username not in purchases:
            purchases[username] = {"titles": [], "themes": [], "avatars": [], "effects": [], "frames": [], "purchase_history": []}

        list_key = item_type + "s" if item_type not in ("effect", "frame") else (item_type + "s")
        if list_key not in purchases[username]:
            purchases[username][list_key] = []

        if item_id in purchases[username].get(list_key, []):
            return {"success": False, "message": "Item bereits im Besitz"}

        purchases[username][list_key].append(item_id)
        purchases[username]["purchase_history"].append({
            "item_type": item_type,
            "item_id": item_id,
            "item_name": shop[item_id].get("name", item_id),
            "price": 0,
            "source": "milestone",
            "purchased_at": datetime.now(TZ).isoformat(),
        })
        self.save_purchases(purchases)
        self._pg_sync_purchase(username, item_type, item_id, 0)

        logger.info(f"Milestone cosmetic granted: {username} -> {item_id}")
        return {"success": True, "message": f"Milestone-Belohnung '{shop[item_id]['name']}' freigeschaltet!"}

    def unlock_all_for_admin(self, user):
        """Schalte alle Kosmetik-Items für Admin frei (ohne Coins-Kosten)"""
        purchases = self.load_purchases()

        # Initialisiere User falls nicht vorhanden
        if user not in purchases:
            purchases[user] = {"titles": [], "themes": [], "avatars": [], "effects": [], "frames": [], "purchase_history": []}

        # Sammle alle verfügbaren Items
        all_titles = list(TITLE_SHOP.keys())
        all_themes = list(COLOR_THEMES.keys())
        all_avatars = list(AVATAR_SHOP.keys())
        all_effects = list(SPECIAL_EFFECTS.keys())
        all_frames = list(FRAME_SHOP.keys())

        # Ensure frames list exists
        if "frames" not in purchases[user]:
            purchases[user]["frames"] = []

        # Füge alle Items hinzu (ohne Duplikate)
        for title_id in all_titles:
            if title_id not in purchases[user]["titles"]:
                purchases[user]["titles"].append(title_id)

        for theme_id in all_themes:
            if theme_id not in purchases[user]["themes"]:
                purchases[user]["themes"].append(theme_id)

        for avatar_id in all_avatars:
            if avatar_id not in purchases[user]["avatars"]:
                purchases[user]["avatars"].append(avatar_id)

        for effect_id in all_effects:
            if effect_id not in purchases[user]["effects"]:
                purchases[user]["effects"].append(effect_id)

        for frame_id in all_frames:
            if frame_id not in purchases[user]["frames"]:
                purchases[user]["frames"].append(frame_id)

        # Füge Admin-Unlock-Eintrag zur Kaufhistorie hinzu
        purchases[user]["purchase_history"].append({
            "item_type": "admin_unlock",
            "item_id": "all_cosmetics",
            "item_name": "Admin Unlock All",
            "price": 0,
            "purchased_at": datetime.now(TZ).isoformat()
        })

        self.save_purchases(purchases)

        total_unlocked = len(all_titles) + len(all_themes) + len(all_avatars) + len(all_effects) + len(all_frames)

        return {
            "success": True,
            "message": f"Alle {total_unlocked} Kosmetik-Items für Admin freigeschaltet!",
            "unlocked": {
                "titles": len(all_titles),
                "themes": len(all_themes),
                "avatars": len(all_avatars),
                "effects": len(all_effects),
                "frames": len(all_frames)
            }
        }

# Globale Instanz
cosmetics_shop = CosmeticsShop()