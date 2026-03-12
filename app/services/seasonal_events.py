# -*- coding: utf-8 -*-
"""
Seasonal Events Service - Time-limited events with XP/Coin multipliers and exclusive items
"""

import logging
from datetime import datetime

import pytz

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Europe/Berlin")

SEASONAL_EVENTS = {
    "spring_fever": {
        "name": "Fruehlings-Fieber",
        "start_month": 3, "start_day": 20,
        "end_month": 4, "end_day": 30,
        "xp_multiplier": 1.2,
        "coin_multiplier": 1.1,
        "theme_color": "pink",
        "icon": "flower",
    },
    "summer_heat": {
        "name": "Sommer-Hitze",
        "start_month": 6, "start_day": 21,
        "end_month": 8, "end_day": 31,
        "xp_multiplier": 1.3,
        "coin_multiplier": 1.2,
        "theme_color": "yellow",
        "icon": "sun",
    },
    "autumn_harvest": {
        "name": "Herbst-Ernte",
        "start_month": 9, "start_day": 22,
        "end_month": 11, "end_day": 20,
        "xp_multiplier": 1.15,
        "coin_multiplier": 1.15,
        "theme_color": "orange",
        "icon": "leaf",
    },
    "winter_magic": {
        "name": "Winter-Zauber",
        "start_month": 12, "start_day": 1,
        "end_month": 2, "end_day": 28,
        "xp_multiplier": 1.25,
        "coin_multiplier": 1.2,
        "theme_color": "blue",
        "icon": "snowflake",
    },
}

# Map season names to months for seasonal shop item filtering
SEASON_MAP = {
    "spring": (3, 4, 5),
    "summer": (6, 7, 8),
    "autumn": (9, 10, 11),
    "winter": (12, 1, 2),
}


def _is_date_in_range(now, start_month, start_day, end_month, end_day):
    """Check if a date falls within a month/day range (handles year wraparound)."""
    month = now.month
    day = now.day

    if start_month <= end_month:
        # Normal range (e.g. March-April)
        if month < start_month or month > end_month:
            return False
        if month == start_month and day < start_day:
            return False
        if month == end_month and day > end_day:
            return False
        return True
    else:
        # Wraps around year (e.g. December-February)
        if month > end_month and month < start_month:
            return False
        if month == start_month and day < start_day:
            return False
        if month == end_month and day > end_day:
            return False
        return True


class SeasonalEvents:
    def get_active_event(self):
        """Return the currently active seasonal event or None."""
        now = datetime.now(TZ)
        for event_id, event in SEASONAL_EVENTS.items():
            if _is_date_in_range(
                now,
                event["start_month"], event["start_day"],
                event["end_month"], event["end_day"],
            ):
                return {"id": event_id, **event}
        return None

    def get_event_multipliers(self):
        """Return XP/Coin multipliers for active event. Defaults to 1.0/1.0."""
        event = self.get_active_event()
        if event:
            return {
                "xp": event["xp_multiplier"],
                "coin": event["coin_multiplier"],
                "event_name": event["name"],
                "event_id": event["id"],
            }
        return {"xp": 1.0, "coin": 1.0, "event_name": None, "event_id": None}

    def get_seasonal_shop_items(self):
        """Return seasonal cosmetic items available during the current event."""
        now = datetime.now(TZ)
        current_month = now.month

        # Determine current season
        current_season = None
        for season, months in SEASON_MAP.items():
            if current_month in months:
                current_season = season
                break

        if not current_season:
            return []

        # Collect seasonal items from frame shop
        from app.services.cosmetics_shop import FRAME_SHOP
        items = []
        for frame_id, frame in FRAME_SHOP.items():
            if frame.get("seasonal") == current_season:
                items.append({"id": frame_id, "type": "frame", **frame})

        return items

    def is_event_active(self, event_id):
        """Check whether a specific event is currently active."""
        if event_id not in SEASONAL_EVENTS:
            return False
        event = SEASONAL_EVENTS[event_id]
        now = datetime.now(TZ)
        return _is_date_in_range(
            now,
            event["start_month"], event["start_day"],
            event["end_month"], event["end_day"],
        )

    def get_current_season(self):
        """Return the current season string."""
        now = datetime.now(TZ)
        for season, months in SEASON_MAP.items():
            if now.month in months:
                return season
        return None


seasonal_events = SeasonalEvents()
