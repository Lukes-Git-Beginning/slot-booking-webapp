# -*- coding: utf-8 -*-
"""
Request Deduplication System für Slot Booking Webapp
Verhindert gleichzeitige Buchungen auf denselben Slot
"""

import time
import hashlib
import threading
import logging
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
import json

# Setup logger
logger = logging.getLogger(__name__)

class RequestDeduplicator:
    def __init__(self, expiry_seconds: int = 300):
        """
        Initialize request deduplicator
        
        Args:
            expiry_seconds: How long to keep request locks (default 5 minutes)
        """
        self.expiry_seconds = expiry_seconds
        self.active_requests: Dict[str, float] = {}  # request_id -> timestamp
        self.slot_locks: Dict[str, Set[str]] = {}  # slot_key -> set of request_ids
        self._lock = threading.RLock()
    
    def _generate_request_id(self, user_id: str, slot_key: str) -> str:
        """Generate unique request ID"""
        timestamp = str(time.time())
        data = f"{user_id}:{slot_key}:{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _generate_slot_key(self, date: str, hour: str, consultant: str = "") -> str:
        """Generate slot key for locking"""
        return f"{date}_{hour}_{consultant}".strip('_')
    
    def _cleanup_expired(self):
        """Remove expired requests"""
        current_time = time.time()
        expired_requests = [
            req_id for req_id, timestamp in self.active_requests.items()
            if current_time - timestamp > self.expiry_seconds
        ]
        
        for req_id in expired_requests:
            del self.active_requests[req_id]
            
            # Remove from slot locks
            for slot_key, request_set in self.slot_locks.items():
                request_set.discard(req_id)
                
        # Remove empty slot locks
        empty_slots = [slot for slot, reqs in self.slot_locks.items() if not reqs]
        for slot in empty_slots:
            del self.slot_locks[slot]
    
    def is_slot_available(self, date: str, hour: str, consultant: str = "") -> bool:
        """
        Check if slot is available for booking (not locked by other requests)
        
        Args:
            date: Slot date (YYYY-MM-DD)
            hour: Slot hour (HH:MM)
            consultant: Optional consultant name
            
        Returns:
            bool: True if slot is available
        """
        with self._lock:
            self._cleanup_expired()
            slot_key = self._generate_slot_key(date, hour, consultant)
            return len(self.slot_locks.get(slot_key, set())) == 0
    
    def acquire_slot_lock(self, user_id: str, date: str, hour: str, consultant: str = "") -> Optional[str]:
        """
        Acquire a lock on a slot for booking
        
        Args:
            user_id: User making the request
            date: Slot date (YYYY-MM-DD)
            hour: Slot hour (HH:MM)
            consultant: Optional consultant name
            
        Returns:
            str: Request ID if lock acquired, None if slot unavailable
        """
        with self._lock:
            self._cleanup_expired()
            
            slot_key = self._generate_slot_key(date, hour, consultant)
            
            # Check if slot is already locked
            if slot_key in self.slot_locks and self.slot_locks[slot_key]:
                return None
            
            # Generate request ID and acquire lock
            request_id = self._generate_request_id(user_id, slot_key)
            current_time = time.time()
            
            self.active_requests[request_id] = current_time
            
            if slot_key not in self.slot_locks:
                self.slot_locks[slot_key] = set()
            self.slot_locks[slot_key].add(request_id)
            
            logger.debug(f"Slot locked: {slot_key} by {user_id} ({request_id[:8]})")
            return request_id
    
    def release_slot_lock(self, request_id: str) -> bool:
        """
        Release a slot lock
        
        Args:
            request_id: Request ID from acquire_slot_lock
            
        Returns:
            bool: True if lock was released
        """
        with self._lock:
            if request_id not in self.active_requests:
                return False
            
            # Remove from active requests
            del self.active_requests[request_id]
            
            # Remove from slot locks
            for slot_key, request_set in self.slot_locks.items():
                if request_id in request_set:
                    request_set.remove(request_id)
                    logger.debug(f"Slot unlocked: {slot_key} ({request_id[:8]})")
                    
                    # Clean up empty slot locks
                    if not request_set:
                        del self.slot_locks[slot_key]
                    break
            
            return True
    
    def extend_lock(self, request_id: str) -> bool:
        """
        Extend a slot lock (reset timestamp)
        
        Args:
            request_id: Request ID to extend
            
        Returns:
            bool: True if lock was extended
        """
        with self._lock:
            if request_id in self.active_requests:
                self.active_requests[request_id] = time.time()
                return True
            return False
    
    def get_stats(self) -> Dict[str, any]:
        """Get current deduplication stats"""
        with self._lock:
            self._cleanup_expired()
            return {
                "active_requests": len(self.active_requests),
                "locked_slots": len(self.slot_locks),
                "total_locks": sum(len(reqs) for reqs in self.slot_locks.values()),
                "expiry_seconds": self.expiry_seconds
            }
    
    def clear_all_locks(self) -> int:
        """Clear all locks (emergency function)"""
        with self._lock:
            count = len(self.active_requests)
            self.active_requests.clear()
            self.slot_locks.clear()
            logger.debug(f"Cleared {count} active locks")
            return count

# Context manager for automatic lock management
class SlotLockContext:
    def __init__(self, deduplicator: RequestDeduplicator, user_id: str, 
                 date: str, hour: str, consultant: str = ""):
        self.deduplicator = deduplicator
        self.user_id = user_id
        self.date = date
        self.hour = hour
        self.consultant = consultant
        self.request_id: Optional[str] = None
    
    def __enter__(self) -> Optional[str]:
        """Acquire slot lock"""
        self.request_id = self.deduplicator.acquire_slot_lock(
            self.user_id, self.date, self.hour, self.consultant
        )
        return self.request_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release slot lock"""
        if self.request_id:
            self.deduplicator.release_slot_lock(self.request_id)

# Global deduplicator instance
request_deduplicator = RequestDeduplicator()