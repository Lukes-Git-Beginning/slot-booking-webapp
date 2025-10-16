# -*- coding: utf-8 -*-
"""
Konfiguration für Slot Booking Webapp
Zentrale Sammlung aller Konfigurationswerte mit Umgebungsvariablen-Fallbacks
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
    SLOTS_PER_BERATER: int = int(os.getenv("SLOTS_PER_BERATER", "3"))
    
    # Zeitzone
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Berlin")
    
    # Maximale Buchungszeit im Voraus (Tage)
    MAX_BOOKING_DAYS_AHEAD: int = int(os.getenv("MAX_BOOKING_DAYS_AHEAD", "56"))
    
    # Cache-Konfiguration (Sekunden)
    CACHE_TIMES: Dict[str, int] = {
        "availability": int(os.getenv("CACHE_AVAILABILITY", "300")),        # 5 Minuten
        "calendar_events": int(os.getenv("CACHE_CALENDAR_EVENTS", "180")),  # 3 Minuten  
        "calendar_events_daily": int(os.getenv("CACHE_CALENDAR_DAILY", "1800")), # 30 Minuten
        "user_scores": int(os.getenv("CACHE_USER_SCORES", "300")),          # 5 Minuten
        "customer_profiles": int(os.getenv("CACHE_CUSTOMER_PROFILES", "3600")), # 1 Stunde
        "analytics": int(os.getenv("CACHE_ANALYTICS", "1800")),             # 30 Minuten
        "badges": int(os.getenv("CACHE_BADGES", "600")),                    # 10 Minuten
        "week_stats": int(os.getenv("CACHE_WEEK_STATS", "900")),            # 15 Minuten
        "consultant_calendars": int(os.getenv("CACHE_CONSULTANT_CALENDARS", "600")), # 10 Minuten
    }

# ========== GAMIFICATION KONFIGURATION ==========
class GamificationConfig:
    """Konfiguration für Achievement-System und Gamification"""
    
    # Benutzer, die von Champion-Wertung ausgeschlossen sind
    DEFAULT_EXCLUDE_CHAMPION_USERS: List[str] = ["callcenter", "admin"]
    
    @classmethod
    def get_excluded_champion_users(cls) -> List[str]:
        """Hole ausgeschlossene Champion-Benutzer"""
        excluded_env = os.getenv("EXCLUDE_CHAMPION_USERS")
        if excluded_env:
            return [user.strip() for user in excluded_env.split(",")]
        return cls.DEFAULT_EXCLUDE_CHAMPION_USERS
    
    # Punkte-Konfiguration
    POINTS_CONFIG: Dict[str, int] = {
        "base_points": int(os.getenv("BASE_BOOKING_POINTS", "5")),
        "early_booking_bonus": int(os.getenv("EARLY_BOOKING_BONUS", "3")),    # > 14 Tage vorher
        "late_booking_bonus": int(os.getenv("LATE_BOOKING_BONUS", "2")),      # < 7 Tage vorher
        "weekend_bonus": int(os.getenv("WEEKEND_BOOKING_BONUS", "2")),        # Weekend-Buchungen
        "evening_bonus": int(os.getenv("EVENING_BOOKING_BONUS", "1")),        # 18:00+ Buchungen
    }
    
    # Badge-Thresholds (können überschrieben werden)
    BADGE_THRESHOLDS: Dict[str, int] = {
        "daily_beginner": int(os.getenv("BADGE_DAILY_BEGINNER", "10")),
        "daily_advanced": int(os.getenv("BADGE_DAILY_ADVANCED", "20")),
        "daily_champion": int(os.getenv("BADGE_DAILY_CHAMPION", "40")),
        "weekly_warrior": int(os.getenv("BADGE_WEEKLY_WARRIOR", "50")),
        "monthly_legend": int(os.getenv("BADGE_MONTHLY_LEGEND", "200")),
        "streak_threshold": int(os.getenv("BADGE_STREAK_THRESHOLD", "7")),
    }

# ========== API KONFIGURATION ==========
class APIConfig:
    """Konfiguration für externe APIs und Limits"""
    
    # Google Calendar API Limits
    CALENDAR_API_MAX_RETRIES: int = int(os.getenv("CALENDAR_API_MAX_RETRIES", "3"))
    CALENDAR_API_RATE_LIMIT: int = int(os.getenv("CALENDAR_API_RATE_LIMIT", "100"))  # Requests pro Minute
    CALENDAR_API_TIMEOUT: int = int(os.getenv("CALENDAR_API_TIMEOUT", "30"))        # Sekunden
    
    # Request Deduplication
    REQUEST_DEDUP_EXPIRY: int = int(os.getenv("REQUEST_DEDUP_EXPIRY", "300"))       # 5 Minuten

# ========== BERATER KONFIGURATION ==========
class ConsultantConfig:
    """Konfiguration für Berater-Kalender"""
    
    # Standard-Berater (können durch Umgebungsvariable überschrieben werden)
    DEFAULT_CONSULTANTS: Dict[str, str] = {
        "Daniel": "daniel.herbort.zfa@gmail.com",
        "Simon": "simonmast9@gmail.com",
        "Jose": "jose@example.com",  # Placeholder
        "Alex": "alex@example.com",  # Placeholder
    }
    
    @classmethod
    def get_consultants(cls) -> Dict[str, str]:
        """Hole Berater-Konfiguration aus Umgebungsvariablen"""
        consultants_env = os.getenv("CONSULTANTS_CONFIG")
        if consultants_env:
            # Format: "Name1:email1,Name2:email2"
            consultants = {}
            for entry in consultants_env.split(","):
                if ":" in entry:
                    name, email = entry.split(":", 1)
                    consultants[name.strip()] = email.strip()
            return consultants
        return cls.DEFAULT_CONSULTANTS
    
    # Verfügbare Zeitslots (können konfiguriert werden)
    DEFAULT_TIME_SLOTS: Dict[str, List[str]] = {
        "Mo": ["11:00", "14:00", "16:00", "18:00", "20:00"],
        "Di": ["11:00", "14:00", "16:00", "18:00", "20:00"],
        "Mi": ["11:00", "14:00", "16:00", "18:00", "20:00"],
        "Do": ["11:00", "14:00", "16:00", "18:00", "20:00"],
        "Fr": ["11:00", "14:00", "16:00", "18:00", "20:00"],
        "Sa": ["11:00", "14:00", "16:00"],
        "So": ["14:00", "16:00", "18:00"]
    }

# ========== LOGGING KONFIGURATION ==========
class LoggingConfig:
    """Konfiguration für Logging"""
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")
    
    # Structured logging
    ENABLE_STRUCTURED_LOGGING: bool = os.getenv("ENABLE_STRUCTURED_LOGGING", "True").lower() in ["true", "1", "yes"]
    
    # Performance logging thresholds (Millisekunden)
    SLOW_QUERY_THRESHOLD: int = int(os.getenv("SLOW_QUERY_THRESHOLD", "1000"))     # 1 Sekunde
    SLOW_REQUEST_THRESHOLD: int = int(os.getenv("SLOW_REQUEST_THRESHOLD", "2000")) # 2 Sekunden

# ========== STORAGE KONFIGURATION ==========
class StorageConfig:
    """Konfiguration für Dateispeicherung"""
    
    # JSON Kompression
    ENABLE_JSON_COMPRESSION: bool = os.getenv("ENABLE_JSON_COMPRESSION", "True").lower() in ["true", "1", "yes"]
    JSON_COMPRESSION_THRESHOLD_MB: float = float(os.getenv("JSON_COMPRESSION_THRESHOLD_MB", "0.1"))  # 100KB
    
    # Backup-Aufbewahrung
    BACKUP_RETENTION_DAYS: int = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    MAX_BACKUPS_PER_FILE: int = int(os.getenv("MAX_BACKUPS_PER_FILE", "10"))

# ========== HILFSFUNKTIONEN ==========
def get_env_bool(key: str, default: bool = False) -> bool:
    """Hilfsfunktion für Boolean-Umgebungsvariablen"""
    return os.getenv(key, str(default)).lower() in ["true", "1", "yes", "on"]

def get_env_list(key: str, default: List[str], separator: str = ",") -> List[str]:
    """Hilfsfunktion für Listen-Umgebungsvariablen"""
    env_value = os.getenv(key)
    if env_value:
        return [item.strip() for item in env_value.split(separator)]
    return default

def get_env_dict(key: str, default: Dict[str, str], item_separator: str = ",", kv_separator: str = ":") -> Dict[str, str]:
    """Hilfsfunktion für Dictionary-Umgebungsvariablen"""
    env_value = os.getenv(key)
    if env_value:
        result = {}
        for item in env_value.split(item_separator):
            if kv_separator in item:
                k, v = item.split(kv_separator, 1)
                result[k.strip()] = v.strip()
        return result
    return default

# ========== GLOBALE KONFIGURATION ==========
# Diese können importiert und verwendet werden
config = Config()
slot_config = SlotConfig()
gamification_config = GamificationConfig()
api_config = APIConfig()
consultant_config = ConsultantConfig()
logging_config = LoggingConfig()
storage_config = StorageConfig()