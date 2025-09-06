# -*- coding: utf-8 -*-
"""
Cache Manager für Slot Booking Webapp - Performance-optimiert
"""

import os
import json
import time
import pickle
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class CacheManager:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Cache-Konfiguration (in Sekunden)
        self.cache_times = {
            "availability": 300,      # 5 Minuten
            "calendar_events": 60,    # 1 Minute
            "user_scores": 600,       # 10 Minuten
            "customer_profiles": 1800, # 30 Minuten
            "analytics": 900,         # 15 Minuten
            "badges": 300             # 5 Minuten
        }
    
    def _get_cache_path(self, cache_type: str, key: str = "") -> str:
        """Generiert Cache-Dateipfad"""
        safe_key = key.replace("/", "_").replace(":", "_")
        return os.path.join(self.cache_dir, f"{cache_type}_{safe_key}.cache")
    
    def _is_cache_valid(self, cache_path: str, max_age: int) -> bool:
        """Prüft ob Cache noch gültig ist"""
        try:
            if not os.path.exists(cache_path):
                return False
            file_age = time.time() - os.path.getmtime(cache_path)
            return file_age < max_age
        except Exception:
            return False
    
    def get(self, cache_type: str, key: str = "") -> Optional[Any]:
        """Holt Daten aus Cache"""
        try:
            cache_path = self._get_cache_path(cache_type, key)
            max_age = self.cache_times.get(cache_type, 300)
            
            if not self._is_cache_valid(cache_path, max_age):
                return None
            
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
                
        except Exception:
            return None
    
    def set(self, cache_type: str, key: str, data: Any) -> bool:
        """Speichert Daten im Cache"""
        try:
            cache_path = self._get_cache_path(cache_type, key)
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception:
            return False
    
    def invalidate(self, cache_type: str, key: str = "") -> bool:
        """Löscht Cache-Eintrag"""
        try:
            cache_path = self._get_cache_path(cache_type, key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                return True
            return False
        except Exception:
            return False
    
    def clear_all(self) -> bool:
        """Löscht alle Cache-Dateien"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    os.remove(os.path.join(self.cache_dir, filename))
            return True
        except Exception:
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Gibt Cache-Statistiken zurück"""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.cache')]
            total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in cache_files)
            
            return {
                "total_files": len(cache_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_dir": self.cache_dir
            }
        except Exception:
            return {"error": "Stats nicht verfügbar"}

# Globaler Cache Manager
cache_manager = CacheManager()