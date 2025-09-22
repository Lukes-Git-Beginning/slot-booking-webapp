# -*- coding: utf-8 -*-
"""
Base configuration for Slot Booking Webapp
Migrated from config.py with enhanced structure
"""

import os
from typing import List, Dict, Any

# ========== GRUNDLEGENDE KONFIGURATION ==========
class Config:
    """Basis-Konfiguration mit Umgebungsvariablen"""

    # Flask Konfiguration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() in ["true", "1", "yes"]

    # Google Calendar API
    GOOGLE_CREDS_BASE64: str = os.getenv("GOOGLE_CREDS_BASE64", "")
    CENTRAL_CALENDAR_ID: str = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")
    SCOPES: List[str] = ["https://www.googleapis.com/auth/calendar"]

    # Datenbank/Persistenz
    PERSIST_BASE: str = os.getenv("PERSIST_BASE", "/opt/render/project/src/persist")

    # Benutzer-Management
    USERLIST: str = os.getenv("USERLIST", "")

    # Admin-Benutzer (kann durch ADMIN_USERS env-var überschrieben werden)
    DEFAULT_ADMIN_USERS: List[str] = ["admin", "administrator", "Jose", "Simon", "Alex", "David"]

    @classmethod
    def get_admin_users(cls) -> List[str]:
        """Hole Admin-Benutzer aus Umgebungsvariablen oder verwende Default"""
        admin_users_env = os.getenv("ADMIN_USERS")
        if admin_users_env:
            return [user.strip() for user in admin_users_env.split(",")]
        return cls.DEFAULT_ADMIN_USERS


# ========== SLOT-BUCHUNG KONFIGURATION ==========
class SlotConfig:
    """Konfiguration für Slot-Buchungen"""

    # Slots pro Berater und Zeitslot
    SLOTS_PER_BERATER: int = int(os.getenv("SLOTS_PER_BERATER", "4"))

    # Zeitzone
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Berlin")

    # Maximale Buchungszeit im Voraus (Tage) - 8 Wochen
    MAX_BOOKING_DAYS_AHEAD: int = int(os.getenv("MAX_BOOKING_DAYS_AHEAD", "56"))

    # Buchungszeiten
    BOOKING_HOURS: List[str] = [
        "09:00", "11:00", "14:00", "16:00", "18:00", "20:00"
    ]

    # Wochentage (1=Montag, 7=Sonntag)
    BOOKING_WEEKDAYS: List[int] = [1, 2, 3, 4, 5, 6, 7]  # Alle Wochentage


# ========== GAMIFICATION KONFIGURATION ==========
class GamificationConfig:
    """Konfiguration für Gamification-Features"""

    # Ausgeschlossene Benutzer für Champion-Bestimmung
    DEFAULT_EXCLUDED_CHAMPION_USERS: List[str] = ["admin", "test"]

    @classmethod
    def get_excluded_champion_users(cls) -> List[str]:
        """Hole ausgeschlossene Champion-Benutzer"""
        excluded_env = os.getenv("EXCLUDED_CHAMPION_USERS")
        if excluded_env:
            return [user.strip() for user in excluded_env.split(",")]
        return cls.DEFAULT_EXCLUDED_CHAMPION_USERS

    # Badge-System
    BADGE_RARITY_COLORS: Dict[str, str] = {
        "common": "#95a5a6",
        "uncommon": "#27ae60",
        "rare": "#3498db",
        "epic": "#9b59b6",
        "legendary": "#f39c12",
        "mythic": "#e74c3c"
    }

    # Level-System
    BASE_XP_REQUIREMENT: int = 100
    XP_MULTIPLIER: float = 1.5
    MAX_LEVEL: int = 100


# ========== API KONFIGURATION ==========
class APIConfig:
    """Konfiguration für API-Endpunkte"""

    # Rate Limiting
    DEFAULT_RATE_LIMIT: str = "100/hour"
    API_RATE_LIMIT: str = "200/hour"

    # Cache-Einstellungen
    CACHE_TIMEOUT: int = int(os.getenv("CACHE_TIMEOUT", "300"))  # 5 Minuten

    # Export-Limits
    MAX_EXPORT_RECORDS: int = int(os.getenv("MAX_EXPORT_RECORDS", "10000"))


# ========== BERATER KONFIGURATION ==========
class ConsultantConfig:
    """Konfiguration für Berater/Consultants"""

    # Standard-Berater IDs für Google Calendar
    DEFAULT_CONSULTANTS: Dict[str, str] = {
        "Sara": "sara@zfa.com",
        "Patrick": "patrick@zfa.com",
        "Dominik": "dominik@zfa.com",
        "Tim": "tim@zfa.com",
        "Ann-Kathrin": "ann-kathrin@zfa.com"
    }

    @classmethod
    def get_consultants(cls) -> Dict[str, str]:
        """Hole Berater-Mapping aus Umgebungsvariablen oder verwende Default"""
        consultants_env = os.getenv("CONSULTANTS")
        if consultants_env:
            # Format: "Name1:email1,Name2:email2"
            consultants = {}
            for pair in consultants_env.split(","):
                if ":" in pair:
                    name, email = pair.split(":", 1)
                    consultants[name.strip()] = email.strip()
            return consultants
        return cls.DEFAULT_CONSULTANTS

    # Fallback-Berater für Verfügbarkeit
    DEFAULT_STANDARD_CONSULTANTS: List[str] = ["Sara", "Patrick"]
    EXTENDED_CONSULTANTS: List[str] = ["Sara", "Patrick", "Dominik", "Tim", "Ann-Kathrin"]


# ========== LOGGING KONFIGURATION ==========
class LoggingConfig:
    """Konfiguration für Logging"""

    # Log Level
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Log-Dateien
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    APP_LOG_FILE: str = "app.log"
    CALENDAR_LOG_FILE: str = "calendar.log"
    BOOKING_LOG_FILE: str = "booking.log"

    # Log Rotation
    MAX_LOG_SIZE: int = int(os.getenv("MAX_LOG_SIZE", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))


# ========== STORAGE KONFIGURATION ==========
class StorageConfig:
    """Konfiguration für Daten-Storage"""

    # Backup-Einstellungen
    MAX_BACKUPS: int = int(os.getenv("MAX_BACKUPS", "10"))
    BACKUP_RETENTION_DAYS: int = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

    # JSON-Optimierung
    ENABLE_JSON_OPTIMIZATION: bool = os.getenv("ENABLE_JSON_OPTIMIZATION", "True").lower() in ["true", "1", "yes"]
    JSON_COMPRESSION_THRESHOLD: int = int(os.getenv("JSON_COMPRESSION_THRESHOLD", "1048576"))  # 1MB


# ========== HILFSFUNKTIONEN ==========
def get_env_bool(key: str, default: bool = False) -> bool:
    """Hilfsfunktion zum Parsen von Boolean-Umgebungsvariablen"""
    return os.getenv(key, str(default)).lower() in ["true", "1", "yes"]


def get_env_list(key: str, default: List[str], separator: str = ",") -> List[str]:
    """Hilfsfunktion zum Parsen von Listen aus Umgebungsvariablen"""
    env_value = os.getenv(key)
    if env_value:
        return [item.strip() for item in env_value.split(separator)]
    return default


def get_env_dict(key: str, default: Dict[str, str], item_separator: str = ",", kv_separator: str = ":") -> Dict[str, str]:
    """Hilfsfunktion zum Parsen von Dictionaries aus Umgebungsvariablen"""
    env_value = os.getenv(key)
    if env_value:
        result = {}
        for item in env_value.split(item_separator):
            if kv_separator in item:
                k, v = item.split(kv_separator, 1)
                result[k.strip()] = v.strip()
        return result
    return default


# ========== KONFIGURATION INSTANZEN ==========
# Singleton-Instanzen für einfachen Import
config = Config()
slot_config = SlotConfig()
gamification_config = GamificationConfig()
api_config = APIConfig()
consultant_config = ConsultantConfig()
logging_config = LoggingConfig()
storage_config = StorageConfig()