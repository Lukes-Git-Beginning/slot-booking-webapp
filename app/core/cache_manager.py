# -*- coding: utf-8 -*-
"""
Cache Manager für Slot Booking Webapp
- Reduziert Google API Calls
- Verbessert Performance
- Speichert häufig abgerufene Daten
- Unterstützt Redis und File-based Caching
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
import pickle
from app.config.base import slot_config

# Redis-Support (optional)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class CacheManager:
    def __init__(self, cache_dir: str = "cache") -> None:
        self.cache_dir: str = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        # Cache-Konfiguration - aus zentraler Konfiguration
        self.cache_times: Dict[str, int] = slot_config.CACHE_TIMES

        # Redis-Client (falls REDIS_URL gesetzt ist)
        self.redis_client = None
        self.use_redis = False

        if REDIS_AVAILABLE:
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                try:
                    self.redis_client = redis.from_url(
                        redis_url,
                        decode_responses=False,  # Wir verwenden Pickle
                        socket_connect_timeout=5,
                        socket_timeout=5
                    )
                    # Test connection
                    self.redis_client.ping()
                    self.use_redis = True
                    print("Redis cache activated")
                except Exception as e:
                    print(f"WARNING: Redis unavailable, falling back to file cache: {e}")
                    self.redis_client = None
                    self.use_redis = False

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
        # Redis-Modus
        if self.use_redis and self.redis_client:
            try:
                redis_key = f"{cache_type}:{key}"
                cached_data_bytes = self.redis_client.get(redis_key)

                if cached_data_bytes is None:
                    return None

                cached_data = pickle.loads(cached_data_bytes)
                print(f"Redis cache hit: {cache_type}_{key}")
                return cached_data

            except Exception as e:
                print(f"WARNING: Redis error, falling back to file cache: {e}")
                # Fallback zu File-Cache

        # File-based Cache (Fallback oder Default)
        try:
            cache_path = self._get_cache_path(cache_type, key)
            max_age = self.cache_times.get(cache_type, 300)

            if not self._is_cache_valid(cache_path, max_age):
                return None

            # Verwende optimierte Pickle-Einstellungen für bessere Performance
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)

            print(f"Cache hit: {cache_type}_{key}")
            return cached_data

        except (FileNotFoundError, pickle.PickleError):
            # Stumm für normale Cache-Misses
            return None
        except Exception as e:
            print(f"ERROR: Cache error: {e}")
            return None

    def set(self, cache_type: str, key: str, data: Any) -> bool:
        """Speichert Daten im Cache mit optimierter Performance"""
        # Redis-Modus
        if self.use_redis and self.redis_client:
            try:
                redis_key = f"{cache_type}:{key}"
                max_age = self.cache_times.get(cache_type, 300)

                # Pickle-Serialisierung
                pickled_data = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

                # Mit TTL speichern
                self.redis_client.setex(redis_key, max_age, pickled_data)
                print(f"Redis cached: {cache_type}_{key} (TTL: {max_age}s)")
                return True

            except Exception as e:
                print(f"WARNING: Redis error, falling back to file cache: {e}")
                # Fallback zu File-Cache

        # File-based Cache (Fallback oder Default)
        try:
            cache_path = self._get_cache_path(cache_type, key)

            # Verwende höchstes Protokoll für bessere Performance und kleinere Dateien
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            print(f"Cached: {cache_type}_{key}")
            return True

        except Exception as e:
            print(f"ERROR: Cache save error: {e}")
            return False

    def invalidate(self, cache_type: str, key: str = "") -> bool:
        """Löscht Cache-Eintrag"""
        # Redis-Modus
        if self.use_redis and self.redis_client:
            try:
                redis_key = f"{cache_type}:{key}"
                deleted = self.redis_client.delete(redis_key)
                if deleted:
                    print(f"Redis cache invalidated: {cache_type}_{key}")
                return bool(deleted)
            except Exception as e:
                print(f"WARNING: Redis error: {e}")

        # File-based Cache
        try:
            cache_path = self._get_cache_path(cache_type, key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                print(f"Cache invalidated: {cache_type}")
                return True
            return False
        except Exception as e:
            print(f"ERROR: Cache invalidation error: {e}")
            return False

    def clear_all(self) -> bool:
        """Löscht alle Cache-Dateien"""
        success = True

        # Redis-Modus: Flush database
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.flushdb()
                print("Redis cache cleared")
            except Exception as e:
                print(f"WARNING: Redis clear error: {e}")
                success = False

        # File-based Cache
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    os.remove(os.path.join(self.cache_dir, filename))
            print("File cache cleared")
        except Exception as e:
            print(f"ERROR: Cache clear error: {e}")
            success = False

        return success

    def get_cache_stats(self) -> Dict[str, Any]:
        """Gibt Cache-Statistiken zurück"""
        stats = {
            "mode": "redis" if self.use_redis else "file",
            "redis_available": REDIS_AVAILABLE
        }

        # Redis-Stats
        if self.use_redis and self.redis_client:
            try:
                info = self.redis_client.info('stats')
                stats["redis"] = {
                    "total_keys": self.redis_client.dbsize(),
                    "hits": info.get('keyspace_hits', 0),
                    "misses": info.get('keyspace_misses', 0),
                    "memory_used_mb": round(self.redis_client.info('memory').get('used_memory', 0) / (1024 * 1024), 2)
                }
            except Exception as e:
                stats["redis_error"] = str(e)

        # File-Cache-Stats
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.cache')]
            total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in cache_files)

            cache_types = {}
            for filename in cache_files:
                cache_type = filename.split('_')[0]
                cache_types[cache_type] = cache_types.get(cache_type, 0) + 1

            stats["file_cache"] = {
                "total_files": len(cache_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_types": cache_types,
                "cache_dir": self.cache_dir
            }
        except Exception as e:
            stats["file_cache_error"] = str(e)

        return stats

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
