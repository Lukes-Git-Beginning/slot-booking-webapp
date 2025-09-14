# -*- coding: utf-8 -*-
"""
Cosmetics Shop System für Slot Booking Webapp
Lustige Titel, Themes und Personalisierungsoptionen mit Coins kaufen
"""

import os
import json
import pytz
from datetime import datetime, timedelta

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

# Avatar-Emojis Shop
AVATAR_EMOJIS = {
    # Tiere (50-100 Coins)
    "cat_face": {"emoji": "🐱", "name": "Katzen-Gesicht", "price": 50, "category": "animals"},
    "dog_face": {"emoji": "🐶", "name": "Hunde-Gesicht", "price": 50, "category": "animals"},
    "panda_face": {"emoji": "🐼", "name": "Panda-Gesicht", "price": 75, "category": "animals"},
    "lion_face": {"emoji": "🦁", "name": "Löwen-Gesicht", "price": 100, "category": "animals"},
    "unicorn_face": {"emoji": "🦄", "name": "Einhorn-Gesicht", "price": 150, "category": "fantasy"},
    
    # Berufe (100-200 Coins)
    "office_worker": {"emoji": "🧑‍💼", "name": "Büro-Worker", "price": 100, "category": "professions"},
    "scientist": {"emoji": "🧑‍🔬", "name": "Wissenschaftler", "price": 120, "category": "professions"},
    "astronaut": {"emoji": "🧑‍🚀", "name": "Astronaut", "price": 200, "category": "professions"},
    "ninja": {"emoji": "🥷", "name": "Ninja", "price": 180, "category": "professions"},
    
    # Fantasy (200-500 Coins)
    "wizard": {"emoji": "🧙‍♂️", "name": "Zauberer", "price": 300, "category": "fantasy"},
    "vampire": {"emoji": "🧛‍♂️", "name": "Vampir", "price": 350, "category": "fantasy"},
    "robot": {"emoji": "🤖", "name": "Roboter", "price": 250, "category": "tech"},
    "alien": {"emoji": "👽", "name": "Alien", "price": 400, "category": "sci-fi"},
    
    # Legendary (500+ Coins)
    "crown": {"emoji": "👑", "name": "Krone", "price": 500, "category": "royal"},
    "crystal_ball": {"emoji": "🔮", "name": "Kristallkugel", "price": 600, "category": "mystical"},
    "diamond": {"emoji": "💎", "name": "Diamant", "price": 800, "category": "luxury"}
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
    }
}

class CosmeticsShop:
    def __init__(self):
        self.purchases_file = "data/persistent/cosmetic_purchases.json"
        self.active_cosmetics_file = "data/persistent/active_cosmetics.json"
        
        # Ensure directories exist
        os.makedirs("data/persistent", exist_ok=True)
        
        # Initialize files
        for file_path in [self.purchases_file, self.active_cosmetics_file]:
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
    
    def load_purchases(self):
        """Lade gekaufte Kosmetik-Items"""
        try:
            with open(self.purchases_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
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
        except:
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
            "purchase_history": []
        })
        
        user_active = active.get(user, {
            "title": None,
            "theme": "default",
            "avatar": "🧑‍💼",
            "effects": []
        })
        
        return {
            "owned": user_purchases,
            "active": user_active,
            "available_titles": self.get_available_items(user, "titles"),
            "available_themes": self.get_available_themes(user),
            "available_avatars": self.get_available_avatars(user),
            "available_effects": self.get_available_effects(user)
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
        
        return {k: v for k, v in AVATAR_EMOJIS.items() if k not in owned_avatars}
    
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
        elif item_type == "avatar" and item_id in AVATAR_EMOJIS:
            item_data = AVATAR_EMOJIS[item_id]
            price = item_data["price"]
        elif item_type == "effect" and item_id in SPECIAL_EFFECTS:
            item_data = SPECIAL_EFFECTS[item_id]
            price = item_data["price"]
        else:
            return {"success": False, "message": "Item nicht gefunden"}
        
        # Prüfe Coins
        if user_coins < price:
            return {"success": False, "message": f"Nicht genug Coins! Benötigt: {price}, Verfügbar: {user_coins}"}
        
        # Prüfe ob bereits gekauft
        purchases = self.load_purchases()
        if user not in purchases:
            purchases[user] = {"titles": [], "themes": [], "avatars": [], "effects": [], "purchase_history": []}
        
        item_list_key = item_type + "s" if item_type != "effect" else "effects"
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
            active[user] = {"title": None, "theme": "default", "avatar": "🧑‍💼", "effects": []}
        
        if item_type == "effect":
            # Effekte können mehrere aktiv sein
            if item_id not in active[user]["effects"]:
                active[user]["effects"].append(item_id)
        else:
            # Andere Items ersetzen das aktuelle
            active[user][item_type] = item_id
        
        self.save_active_cosmetics(active)
        
        # Hole Item-Daten für Response
        item_data = None
        if item_type == "title":
            item_data = TITLE_SHOP.get(item_id, {})
        elif item_type == "theme":
            item_data = COLOR_THEMES.get(item_id, {})
        elif item_type == "avatar":
            item_data = AVATAR_EMOJIS.get(item_id, {})
        elif item_type == "effect":
            item_data = SPECIAL_EFFECTS.get(item_id, {})
        
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
            defaults = {"title": None, "theme": "default", "avatar": "🧑‍💼"}
            active[user][item_type] = defaults.get(item_type)
        
        self.save_active_cosmetics(active)
        
        return {"success": True, "message": f"{item_type.title()} entfernt"}

# Globale Instanz
cosmetics_shop = CosmeticsShop()