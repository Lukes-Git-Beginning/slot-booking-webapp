# -*- coding: utf-8 -*-
"""
Cache Manager für Slot Booking Webapp
- Reduziert Google API Calls
- Verbessert Performance
- Speichert häufig abgerufene Daten
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
import pickle
from config import slot_config

class CacheManager:
    def __init__(self, cache_dir: str = "cache") -> None:
        self.cache_dir: str = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Cache-Konfiguration - aus zentraler Konfiguration
        self.cache_times: Dict[str, int] = slot_config.CACHE_TIMES
    
    def _get_cache_path(self, cache_type: str, key: str = "") -> str:
        """Generiert Cache-Dateipfad"""
        safe_key = key.replace("/", "_").replace(":", "_")
        return os.path.join(self.cache_dir, f"{cache_type}_{safe_key}.cache")
    
    def _is_cache_valid(self, cache_path: str, max_age: int) -> bool:
        """Prüft ob Cache noch gültig ist"""
        try:
            if not os.path.exists(cache_path):
                return False
            
            # Prüfe Datei-Alter
            file_age = time.time() - os.path.getmtime(cache_path)
            return file_age < max_age
        except Exception:
            return False
    
    def get(self, cache_type: str, key: str = "") -> Optional[Any]:
        """Holt Daten aus Cache mit verbesserter Performance"""
        try:
            cache_path = self._get_cache_path(cache_type, key)
            max_age = self.cache_times.get(cache_type, 300)
            
            if not self._is_cache_valid(cache_path, max_age):
                return None
            
            # Verwende optimierte Pickle-Einstellungen für bessere Performance
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
            
            print(f"✅ Cache hit: {cache_type}_{key}")
            return cached_data
            
        except (FileNotFoundError, pickle.PickleError):
            # Stumm für normale Cache-Misses
            return None
        except Exception as e:
            print(f"❌ Cache error: {e}")
            return None
    
    def set(self, cache_type: str, key: str, data: Any) -> bool:
        """Speichert Daten im Cache mit optimierter Performance"""
        try:
            cache_path = self._get_cache_path(cache_type, key)
            
            # Verwende höchstes Protokoll für bessere Performance und kleinere Dateien
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            print(f"💾 Cached: {cache_type}_{key}")
            return True
            
        except Exception as e:
            print(f"❌ Cache save error: {e}")
            return False
    
    def invalidate(self, cache_type: str, key: str = "") -> bool:
        """Löscht Cache-Eintrag"""
        try:
            cache_path = self._get_cache_path(cache_type, key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                print(f"🗑️ Cache invalidated: {cache_type}")
                return True
            return False
        except Exception as e:
            print(f"❌ Cache invalidation error: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Löscht alle Cache-Dateien"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    os.remove(os.path.join(self.cache_dir, filename))
            print("🗑️ All cache cleared")
            return True
        except Exception as e:
            print(f"❌ Cache clear error: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Gibt Cache-Statistiken zurück"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.cache')]
            total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in cache_files)
            
            cache_types = {}
            for filename in cache_files:
                cache_type = filename.split('_')[0]
                cache_types[cache_type] = cache_types.get(cache_type, 0) + 1
            
            return {
                "total_files": len(cache_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_types": cache_types,
                "cache_dir": self.cache_dir
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_calendar_events(self, date_start: str, date_end: str) -> Optional[Any]:
        """Spezielle Methode für Calendar Events mit Datums-Schlüssel"""
        date_key = f"{date_start}_{date_end}"
        return self.get("calendar_events_daily", date_key)
    
    def set_calendar_events(self, date_start: str, date_end: str, events: Any) -> bool:
        """Spezielle Methode zum Speichern von Calendar Events"""
        date_key = f"{date_start}_{date_end}"
        return self.set("calendar_events_daily", date_key, events)
    
    def get_consultant_events(self, consultant_email: str, date_start: str, date_end: str) -> Optional[Any]:
        """Cache für spezifische Berater-Kalender"""
        key = f"{consultant_email}_{date_start}_{date_end}"
        return self.get("consultant_calendars", key)
    
    def set_consultant_events(self, consultant_email: str, date_start: str, date_end: str, events: Any) -> bool:
        """Cache für spezifische Berater-Kalender setzen"""
        key = f"{consultant_email}_{date_start}_{date_end}"
        return self.set("consultant_calendars", key, events)

# Globaler Cache Manager
cache_manager = CacheManager()
