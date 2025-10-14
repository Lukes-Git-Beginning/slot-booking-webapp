# -*- coding: utf-8 -*-
"""
T2 Bucket System - Probability-based Closer Assignment
Inspired by boat-drawing system with modern implementation

Features:
- Weighted probability mapping per closer
- Bucket system with automatic reset (max 10 draws)
- Timeout/cooldown between draws
- Admin-only configuration
- Persistent state management
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import random
import pytz

TZ = pytz.timezone("Europe/Berlin")

# T2-Only Closers (keine Opener!)
T2_CLOSERS = {
    "Alex": {
        "full_name": "Alexander",
        "color": "#2196F3",
        "default_probability": 1.0
    },
    "Christian": {
        "full_name": "Christian",
        "color": "#4CAF50",
        "default_probability": 1.0
    },
    "David": {
        "full_name": "David",
        "color": "#9C27B0",
        "default_probability": 1.0
    },
    "Jose": {
        "full_name": "José",
        "color": "#795548",
        "default_probability": 1.0
    },
    "Tim": {
        "full_name": "Tim",
        "color": "#FF9800",
        "default_probability": 1.0
    }
}

# System Configuration
BUCKET_CONFIG = {
    "max_draws_before_reset": 10,  # Bucket wird nach 10 Draws zurückgesetzt
    "t1_timeout_minutes": 0,        # T1: Kein Timeout
    "t2_timeout_minutes": 1,        # T2: 1 Minute Timeout
    "min_probability": 0.1,         # Minimum probability (kann nicht 0 sein!)
    "max_probability": 100.0,       # Maximum probability
    "probability_reduction_per_draw": 1.0  # Wahrscheinlichkeit sinkt um 1 pro Draw
}

# Data Persistence
PERSIST_BASE = os.getenv("PERSIST_BASE", "/opt/business-hub/data")
if not os.path.exists(PERSIST_BASE):
    PERSIST_BASE = "data"

DATA_DIR = os.path.join(PERSIST_BASE, "persistent")
BUCKET_FILE = os.path.join(DATA_DIR, "t2_bucket_system.json")


def _ensure_dirs():
    """Ensure data directories exist"""
    os.makedirs(DATA_DIR, exist_ok=True)


def load_bucket_data() -> Dict:
    """Load bucket system data"""
    _ensure_dirs()

    if not os.path.exists(BUCKET_FILE):
        return _initialize_bucket_data()

    try:
        with open(BUCKET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Validate structure
            if "probabilities" not in data:
                data["probabilities"] = {name: info["default_probability"] for name, info in T2_CLOSERS.items()}
            if "default_probabilities" not in data:
                data["default_probabilities"] = {name: info["default_probability"] for name, info in T2_CLOSERS.items()}
            if "bucket" not in data:
                data["bucket"] = _create_initial_bucket(data.get("probabilities", {}))
            if "draw_history" not in data:
                data["draw_history"] = []
            if "user_last_draw" not in data:
                data["user_last_draw"] = {}
            if "stats" not in data:
                data["stats"] = {name: 0 for name in T2_CLOSERS.keys()}
            return data
    except Exception as e:
        print(f"Error loading bucket data: {e}")
        return _initialize_bucket_data()


def save_bucket_data(data: Dict):
    """Save bucket system data"""
    _ensure_dirs()

    try:
        with open(BUCKET_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving bucket data: {e}")


def _initialize_bucket_data() -> Dict:
    """Initialize fresh bucket data"""
    probabilities = {name: info["default_probability"] for name, info in T2_CLOSERS.items()}

    return {
        "probabilities": probabilities,
        "default_probabilities": {name: info["default_probability"] for name, info in T2_CLOSERS.items()},  # Store defaults
        "bucket": _create_initial_bucket(probabilities),
        "draw_history": [],
        "user_last_draw": {},
        "stats": {name: 0 for name in T2_CLOSERS.keys()},
        "total_draws": 0,
        "last_reset": datetime.now(TZ).isoformat(),
        "created_at": datetime.now(TZ).isoformat()
    }


def _create_initial_bucket(probabilities: Dict[str, float]) -> List[str]:
    """
    Create bucket based on probabilities
    Each closer gets tickets proportional to their probability weight

    Example:
    - Jose: 2.0 → 2 tickets
    - David: 9.0 → 9 tickets
    - Alex: 9.0 → 9 tickets
    Total: 20 tickets in bucket
    """
    bucket = []

    for closer_name, probability in probabilities.items():
        # Round to int, minimum 1 ticket if probability > 0
        ticket_count = max(1, int(round(probability))) if probability >= BUCKET_CONFIG["min_probability"] else 0

        # Add tickets to bucket
        for _ in range(ticket_count):
            bucket.append(closer_name)

    # Shuffle bucket for randomness
    random.shuffle(bucket)

    return bucket


# ========== PUBLIC API ==========

def get_probabilities() -> Dict[str, float]:
    """Get current probability mappings"""
    data = load_bucket_data()
    return data.get("probabilities", {})


def update_probability(closer_name: str, new_probability: float) -> Dict:
    """
    Update probability for a closer (Admin only)

    Returns: {success: bool, message: str}
    """
    if closer_name not in T2_CLOSERS:
        return {"success": False, "message": f"Invalid closer: {closer_name}"}

    # Validate probability range
    if new_probability < BUCKET_CONFIG["min_probability"]:
        return {
            "success": False,
            "message": f"Probability must be at least {BUCKET_CONFIG['min_probability']}"
        }

    if new_probability > BUCKET_CONFIG["max_probability"]:
        return {
            "success": False,
            "message": f"Probability cannot exceed {BUCKET_CONFIG['max_probability']}"
        }

    data = load_bucket_data()
    data["probabilities"][closer_name] = new_probability

    # Rebuild bucket with new probabilities
    data["bucket"] = _create_initial_bucket(data["probabilities"])
    data["total_draws"] = 0  # Reset draw counter
    data["last_reset"] = datetime.now(TZ).isoformat()

    save_bucket_data(data)

    return {
        "success": True,
        "message": f"Probability updated for {closer_name}: {new_probability}"
    }


def get_bucket_composition() -> Dict:
    """Get current bucket composition (for admin view)"""
    data = load_bucket_data()
    bucket = data.get("bucket", [])

    # Get configured bucket size (use stored value if available)
    max_draws = data.get("bucket_size_config", BUCKET_CONFIG["max_draws_before_reset"])

    # Count tickets per closer
    composition = {}
    for closer_name in T2_CLOSERS.keys():
        count = bucket.count(closer_name)
        composition[closer_name] = count

    return {
        "composition": composition,
        "total_tickets": len(bucket),
        "draws_until_reset": max_draws - data.get("total_draws", 0),
        "max_draws_before_reset": max_draws,
        "probabilities": data.get("probabilities", {}),
        "default_probabilities": data.get("default_probabilities", {})
    }


def check_user_timeout(username: str, draw_type: str = "T2") -> Dict:
    """
    Check if user can draw or is in timeout

    Returns: {can_draw: bool, timeout_remaining_seconds: int, message: str}
    """
    data = load_bucket_data()
    user_last_draw = data.get("user_last_draw", {})

    if username not in user_last_draw:
        return {"can_draw": True, "timeout_remaining_seconds": 0, "message": "Ready to draw"}

    last_draw_iso = user_last_draw[username].get("timestamp")
    if not last_draw_iso:
        return {"can_draw": True, "timeout_remaining_seconds": 0, "message": "Ready to draw"}

    try:
        last_draw = datetime.fromisoformat(last_draw_iso)
        now = datetime.now(TZ)

        # Get timeout duration
        timeout_minutes = BUCKET_CONFIG.get(f"{draw_type.lower()}_timeout_minutes", 1)
        timeout_delta = timedelta(minutes=timeout_minutes)

        time_since_draw = now - last_draw

        if time_since_draw < timeout_delta:
            remaining = timeout_delta - time_since_draw
            remaining_seconds = int(remaining.total_seconds())

            return {
                "can_draw": False,
                "timeout_remaining_seconds": remaining_seconds,
                "message": f"Please wait {remaining_seconds} seconds before drawing again"
            }

        return {"can_draw": True, "timeout_remaining_seconds": 0, "message": "Ready to draw"}

    except Exception as e:
        print(f"Error checking timeout: {e}")
        return {"can_draw": True, "timeout_remaining_seconds": 0, "message": "Ready to draw"}


def draw_closer(username: str, draw_type: str = "T2", customer_name: str = None) -> Dict:
    """
    Draw a closer from the bucket

    Returns: {
        success: bool,
        closer: str,
        color: str,
        message: str,
        bucket_stats: dict
    }
    """
    # Check timeout
    timeout_check = check_user_timeout(username, draw_type)
    if not timeout_check["can_draw"]:
        return {
            "success": False,
            "error": timeout_check["message"],
            "timeout_remaining": timeout_check["timeout_remaining_seconds"]
        }

    data = load_bucket_data()
    bucket = data.get("bucket", [])

    if not bucket:
        # Bucket is empty - reset it
        data["bucket"] = _create_initial_bucket(data.get("probabilities", {}))
        data["total_draws"] = 0
        data["last_reset"] = datetime.now(TZ).isoformat()
        bucket = data["bucket"]

    # Draw random closer from bucket
    drawn_closer = random.choice(bucket)

    # Remove drawn ticket from bucket
    bucket.remove(drawn_closer)
    data["bucket"] = bucket

    # DEGRESSIVE PROBABILITY: Reduce the drawn closer's probability by 1
    reduction = BUCKET_CONFIG.get("probability_reduction_per_draw", 1.0)
    min_prob = BUCKET_CONFIG.get("min_probability", 0.1)

    current_prob = data["probabilities"].get(drawn_closer, 1.0)
    new_prob = max(min_prob, current_prob - reduction)
    data["probabilities"][drawn_closer] = new_prob

    # Update stats
    data["total_draws"] = data.get("total_draws", 0) + 1
    data["stats"][drawn_closer] = data["stats"].get(drawn_closer, 0) + 1

    # Record user's last draw
    data["user_last_draw"][username] = {
        "timestamp": datetime.now(TZ).isoformat(),
        "closer": drawn_closer,
        "draw_type": draw_type,
        "customer_name": customer_name
    }

    # Add to history
    data["draw_history"].append({
        "user": username,
        "closer": drawn_closer,
        "draw_type": draw_type,
        "customer_name": customer_name,
        "timestamp": datetime.now(TZ).isoformat(),
        "bucket_size_after": len(bucket),
        "probability_after": new_prob
    })

    # Check if bucket needs reset
    max_draws = data.get("bucket_size_config", BUCKET_CONFIG["max_draws_before_reset"])
    if data["total_draws"] >= max_draws:
        # Reset probabilities to default values
        data["probabilities"] = data.get("default_probabilities", {name: info["default_probability"] for name, info in T2_CLOSERS.items()}).copy()
        data["bucket"] = _create_initial_bucket(data["probabilities"])
        data["total_draws"] = 0
        data["last_reset"] = datetime.now(TZ).isoformat()

    save_bucket_data(data)

    return {
        "success": True,
        "closer": drawn_closer,
        "closer_full_name": T2_CLOSERS[drawn_closer]["full_name"],
        "color": T2_CLOSERS[drawn_closer]["color"],
        "message": f"You drew {drawn_closer}!",
        "bucket_stats": {
            "tickets_remaining": len(data["bucket"]),
            "draws_until_reset": max_draws - data["total_draws"]
        },
        "probability_info": {
            "old_probability": current_prob,
            "new_probability": new_prob
        }
    }


def reset_bucket() -> Dict:
    """Reset bucket manually (Admin only)"""
    data = load_bucket_data()

    # Reset probabilities to default values
    data["probabilities"] = data.get("default_probabilities", {name: info["default_probability"] for name, info in T2_CLOSERS.items()}).copy()

    data["bucket"] = _create_initial_bucket(data["probabilities"])
    data["total_draws"] = 0
    data["last_reset"] = datetime.now(TZ).isoformat()

    save_bucket_data(data)

    return {
        "success": True,
        "message": "Bucket reset successfully (probabilities restored to defaults)",
        "bucket_size": len(data["bucket"])
    }


def get_system_stats() -> Dict:
    """Get overall system statistics"""
    data = load_bucket_data()

    return {
        "total_all_time_draws": sum(data.get("stats", {}).values()),
        "closer_distribution": data.get("stats", {}),
        "current_bucket_size": len(data.get("bucket", [])),
        "draws_this_cycle": data.get("total_draws", 0),
        "last_reset": data.get("last_reset"),
        "probabilities": data.get("probabilities", {}),
        "recent_draws": data.get("draw_history", [])[-20:]  # Last 20 draws
    }


def get_available_closers() -> Dict[str, Dict]:
    """Get list of available T2 closers with their info"""
    return T2_CLOSERS


def update_bucket_size(new_size: int) -> Dict:
    """
    Update max draws before bucket reset (Admin only)

    Returns: {success: bool, message: str}
    """
    if new_size < 1:
        return {"success": False, "message": "Bucket size must be at least 1"}

    if new_size > 100:
        return {"success": False, "message": "Bucket size cannot exceed 100"}

    data = load_bucket_data()

    # Update config
    BUCKET_CONFIG["max_draws_before_reset"] = new_size

    # Reset bucket with new size
    data["probabilities"] = data.get("default_probabilities", {name: info["default_probability"] for name, info in T2_CLOSERS.items()}).copy()
    data["bucket"] = _create_initial_bucket(data["probabilities"])
    data["total_draws"] = 0
    data["last_reset"] = datetime.now(TZ).isoformat()
    data["bucket_size_config"] = new_size  # Store in data for persistence

    save_bucket_data(data)

    return {
        "success": True,
        "message": f"Bucket size updated to {new_size} draws"
    }


def get_bucket_config() -> Dict:
    """Get current bucket configuration"""
    data = load_bucket_data()
    return {
        "max_draws_before_reset": data.get("bucket_size_config", BUCKET_CONFIG["max_draws_before_reset"]),
        "t1_timeout_minutes": BUCKET_CONFIG["t1_timeout_minutes"],
        "t2_timeout_minutes": BUCKET_CONFIG["t2_timeout_minutes"],
        "min_probability": BUCKET_CONFIG["min_probability"],
        "max_probability": BUCKET_CONFIG["max_probability"],
        "probability_reduction_per_draw": BUCKET_CONFIG["probability_reduction_per_draw"]
    }


def add_closer(name: str, color: str, full_name: str, default_probability: float = 1.0) -> Dict:
    """
    Add a new closer to the system (Admin only)

    Returns: {success: bool, message: str}
    """
    if name in T2_CLOSERS:
        return {"success": False, "message": f"Closer '{name}' existiert bereits"}

    # Validate color format (hex)
    if not color.startswith('#') or len(color) != 7:
        return {"success": False, "message": "Farbe muss im Format #RRGGBB sein"}

    # Add to T2_CLOSERS dict
    T2_CLOSERS[name] = {
        "full_name": full_name,
        "color": color,
        "default_probability": default_probability
    }

    # Update data
    data = load_bucket_data()

    # Add to probabilities
    data["probabilities"][name] = default_probability
    data["default_probabilities"][name] = default_probability
    data["stats"][name] = 0

    # Rebuild bucket
    data["bucket"] = _create_initial_bucket(data["probabilities"])
    data["total_draws"] = 0
    data["last_reset"] = datetime.now(TZ).isoformat()

    save_bucket_data(data)

    return {
        "success": True,
        "message": f"Closer '{name}' erfolgreich hinzugefügt"
    }


def remove_closer(name: str) -> Dict:
    """
    Remove a closer from the system (Admin only)

    Returns: {success: bool, message: str}
    """
    if name not in T2_CLOSERS:
        return {"success": False, "message": f"Closer '{name}' nicht gefunden"}

    if len(T2_CLOSERS) <= 1:
        return {"success": False, "message": "Mindestens ein Closer muss vorhanden sein"}

    # Remove from T2_CLOSERS
    del T2_CLOSERS[name]

    # Update data
    data = load_bucket_data()

    # Remove from probabilities
    if name in data["probabilities"]:
        del data["probabilities"][name]
    if name in data["default_probabilities"]:
        del data["default_probabilities"][name]

    # Rebuild bucket
    data["bucket"] = _create_initial_bucket(data["probabilities"])
    data["total_draws"] = 0
    data["last_reset"] = datetime.now(TZ).isoformat()

    save_bucket_data(data)

    return {
        "success": True,
        "message": f"Closer '{name}' erfolgreich entfernt"
    }


def update_closer_info(name: str, new_color: str = None, new_full_name: str = None) -> Dict:
    """
    Update closer information (Admin only)

    Returns: {success: bool, message: str}
    """
    if name not in T2_CLOSERS:
        return {"success": False, "message": f"Closer '{name}' nicht gefunden"}

    # Update color if provided
    if new_color:
        if not new_color.startswith('#') or len(new_color) != 7:
            return {"success": False, "message": "Farbe muss im Format #RRGGBB sein"}
        T2_CLOSERS[name]["color"] = new_color

    # Update full name if provided
    if new_full_name:
        T2_CLOSERS[name]["full_name"] = new_full_name

    return {
        "success": True,
        "message": f"Closer '{name}' erfolgreich aktualisiert"
    }
