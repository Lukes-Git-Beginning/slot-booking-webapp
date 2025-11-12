# -*- coding: utf-8 -*-
"""
T2 Analytics Service - User-specific Analytics für T2-Würfel-Historie
Bietet kombinierte Statistiken aus T1-Slots, T2-Buchungen und Würfel-Activity
"""

import os
import json
import pytz
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")

# Data Persistence Paths
PERSIST_BASE = os.getenv("PERSIST_BASE", "/opt/business-hub/data")
if not os.path.exists(PERSIST_BASE):
    PERSIST_BASE = "data"

DATA_DIR = os.path.join(PERSIST_BASE, "persistent")
BUCKET_FILE = os.path.join(DATA_DIR, "t2_bucket_system.json")
T2_BOOKINGS_FILE = os.path.join(DATA_DIR, "t2_bookings.json")


class T2AnalyticsService:
    """Service für T2-spezifische Analytics und Würfel-Historie"""

    def __init__(self):
        self.data_dir = DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_bucket_data(self) -> Dict:
        """Load T2 bucket system data with draw history"""
        try:
            if not os.path.exists(BUCKET_FILE):
                return {"draw_history": [], "probabilities": {}, "bucket": []}

            with open(BUCKET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading bucket data: {e}")
            return {"draw_history": [], "probabilities": {}, "bucket": []}

    def _load_t2_bookings(self) -> List[Dict]:
        """Load T2 bookings data"""
        try:
            if not os.path.exists(T2_BOOKINGS_FILE):
                return []

            with open(T2_BOOKINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("bookings", [])
        except Exception as e:
            logger.error(f"Error loading T2 bookings: {e}")
            return []

    def _load_tracking_bookings(self) -> List[Dict]:
        """Load T1 Slot bookings from tracking system"""
        try:
            bookings_file = "data/tracking/bookings.jsonl"
            if not os.path.exists(bookings_file):
                return []

            bookings = []
            with open(bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        bookings.append(json.loads(line))
            return bookings
        except Exception as e:
            logger.error(f"Error loading tracking bookings: {e}")
            return []

    def get_user_draw_history(
        self,
        username: str,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        closer_filter: Optional[str] = None
    ) -> Dict:
        """
        Get user-specific draw history with pagination and filters

        Args:
            username: Username to filter draws
            limit: Maximum number of draws to return
            offset: Number of draws to skip (for pagination)
            start_date: ISO date string to filter from (optional)
            end_date: ISO date string to filter to (optional)
            closer_filter: Closer name to filter by (optional)

        Returns:
            Dict with draws, total_count, has_more
        """
        bucket_data = self._load_bucket_data()
        all_draws = bucket_data.get("draw_history", [])

        # Filter by username
        user_draws = [d for d in all_draws if d.get("user") == username]

        # Apply date filters
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            user_draws = [d for d in user_draws if datetime.fromisoformat(d["timestamp"]) >= start_dt]

        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            user_draws = [d for d in user_draws if datetime.fromisoformat(d["timestamp"]) <= end_dt]

        # Apply closer filter
        if closer_filter:
            user_draws = [d for d in user_draws if d.get("closer") == closer_filter]

        # Sort by timestamp descending (newest first)
        user_draws.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Pagination
        total_count = len(user_draws)
        paginated_draws = user_draws[offset:offset + limit]

        # Format timestamps for display
        for draw in paginated_draws:
            try:
                dt = datetime.fromisoformat(draw["timestamp"])
                draw["formatted_date"] = dt.strftime("%d.%m.%Y")
                draw["formatted_time"] = dt.strftime("%H:%M")
                draw["formatted_datetime"] = dt.strftime("%d.%m.%Y %H:%M")
            except:
                draw["formatted_date"] = "N/A"
                draw["formatted_time"] = "N/A"
                draw["formatted_datetime"] = "N/A"

        return {
            "draws": paginated_draws,
            "total_count": total_count,
            "returned_count": len(paginated_draws),
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total_count
        }

    def get_user_draw_stats(self, username: str) -> Dict:
        """
        Get aggregated statistics for user's draw history

        Returns:
            Dict with total_draws, closer_distribution, favorite_closer,
            recent_activity, weekly_average, etc.
        """
        bucket_data = self._load_bucket_data()
        all_draws = bucket_data.get("draw_history", [])

        # Filter user draws
        user_draws = [d for d in all_draws if d.get("user") == username]

        if not user_draws:
            return {
                "total_draws": 0,
                "closer_distribution": {},
                "favorite_closer": None,
                "this_week": 0,
                "this_month": 0,
                "average_per_week": 0.0,
                "last_draw": None,
                "draw_types": {}
            }

        # Calculate distributions
        closer_counter = Counter(d.get("closer") for d in user_draws)
        draw_type_counter = Counter(d.get("draw_type") for d in user_draws)

        # Favorite closer (most drawn)
        favorite_closer = closer_counter.most_common(1)[0][0] if closer_counter else None

        # Time-based filters
        now = datetime.now(TZ)
        week_start = now - timedelta(days=now.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        this_week_draws = [
            d for d in user_draws
            if datetime.fromisoformat(d["timestamp"]) >= week_start
        ]

        this_month_draws = [
            d for d in user_draws
            if datetime.fromisoformat(d["timestamp"]) >= month_start
        ]

        # Calculate weekly average (if user has been active for more than 1 week)
        if user_draws:
            first_draw = min(datetime.fromisoformat(d["timestamp"]) for d in user_draws)
            weeks_active = max(1, (now - first_draw).days / 7)
            average_per_week = len(user_draws) / weeks_active
        else:
            average_per_week = 0.0

        # Last draw
        last_draw = max(user_draws, key=lambda x: x.get("timestamp", ""))
        try:
            last_draw_dt = datetime.fromisoformat(last_draw["timestamp"])
            last_draw_formatted = last_draw_dt.strftime("%d.%m.%Y %H:%M")
        except:
            last_draw_formatted = "N/A"

        return {
            "total_draws": len(user_draws),
            "closer_distribution": dict(closer_counter),
            "favorite_closer": favorite_closer,
            "this_week": len(this_week_draws),
            "this_month": len(this_month_draws),
            "average_per_week": round(average_per_week, 1),
            "last_draw": {
                "closer": last_draw.get("closer"),
                "customer_name": last_draw.get("customer_name"),
                "timestamp": last_draw.get("timestamp"),
                "formatted": last_draw_formatted
            } if last_draw else None,
            "draw_types": dict(draw_type_counter)
        }

    def search_draws(self, username: str, query: str) -> List[Dict]:
        """
        Search draws by customer name or closer name

        Args:
            username: Username to filter draws
            query: Search query (case-insensitive)

        Returns:
            List of matching draws
        """
        bucket_data = self._load_bucket_data()
        all_draws = bucket_data.get("draw_history", [])

        # Filter by username
        user_draws = [d for d in all_draws if d.get("user") == username]

        # Search in customer_name and closer
        query_lower = query.lower()
        matches = [
            d for d in user_draws
            if (d.get("customer_name", "").lower().find(query_lower) != -1 or
                d.get("closer", "").lower().find(query_lower) != -1)
        ]

        # Sort by timestamp descending
        matches.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Format timestamps
        for draw in matches:
            try:
                dt = datetime.fromisoformat(draw["timestamp"])
                draw["formatted_datetime"] = dt.strftime("%d.%m.%Y %H:%M")
            except:
                draw["formatted_datetime"] = "N/A"

        return matches

    def get_combined_user_stats(self, username: str) -> Dict:
        """
        Get combined statistics from T1-Slots, T2-Bookings, and Draw-Activity

        Returns:
            Dict with aggregated KPIs across all systems
        """
        # T1 Slot-Buchungen
        t1_bookings = self._load_tracking_bookings()
        user_t1_bookings = [b for b in t1_bookings if b.get("user") == username]

        # T2-Buchungen
        t2_bookings = self._load_t2_bookings()
        user_t2_bookings = [b for b in t2_bookings if b.get("booked_by") == username]

        # Draw-Activity
        draw_stats = self.get_user_draw_stats(username)

        # Time filters
        now = datetime.now(TZ)
        week_start = now - timedelta(days=now.weekday())

        # T1 This Week
        t1_this_week = [
            b for b in user_t1_bookings
            if datetime.strptime(b.get("date", "1970-01-01"), "%Y-%m-%d").replace(tzinfo=TZ) >= week_start
        ]

        # T2 This Week
        t2_this_week = [
            b for b in user_t2_bookings
            if datetime.fromisoformat(b.get("booking_time", "1970-01-01T00:00:00")).replace(tzinfo=TZ) >= week_start
        ]

        # Calculate success rate (T1 only, based on color tracking)
        # Note: This is simplified - real implementation would check outcomes
        total_activities = len(user_t1_bookings) + len(user_t2_bookings) + draw_stats["total_draws"]

        return {
            "t1_slots": {
                "total": len(user_t1_bookings),
                "this_week": len(t1_this_week)
            },
            "t2_bookings": {
                "total": len(user_t2_bookings),
                "this_week": len(t2_this_week)
            },
            "draw_activity": {
                "total": draw_stats["total_draws"],
                "this_week": draw_stats["this_week"],
                "favorite_closer": draw_stats["favorite_closer"]
            },
            "combined": {
                "total_activities": total_activities,
                "this_week_activities": len(t1_this_week) + len(t2_this_week) + draw_stats["this_week"]
            }
        }

    def get_draw_timeline_data(self, username: str, days: int = 30) -> Dict:
        """
        Get draw timeline data for charts (last N days)

        Args:
            username: Username to filter draws
            days: Number of days to look back

        Returns:
            Dict with timeline data for Line Chart
        """
        bucket_data = self._load_bucket_data()
        all_draws = bucket_data.get("draw_history", [])

        # Filter user draws
        user_draws = [d for d in all_draws if d.get("user") == username]

        # Filter last N days
        now = datetime.now(TZ)
        cutoff_date = now - timedelta(days=days)

        recent_draws = [
            d for d in user_draws
            if datetime.fromisoformat(d["timestamp"]) >= cutoff_date
        ]

        # Group by date
        draws_by_date = defaultdict(int)
        for draw in recent_draws:
            try:
                dt = datetime.fromisoformat(draw["timestamp"])
                date_key = dt.strftime("%Y-%m-%d")
                draws_by_date[date_key] += 1
            except:
                pass

        # Fill in missing dates with 0
        date_list = []
        count_list = []
        for i in range(days):
            date = (now - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
            date_list.append(date)
            count_list.append(draws_by_date.get(date, 0))

        return {
            "dates": date_list,
            "counts": count_list,
            "total_draws": len(recent_draws)
        }


# Singleton instance
t2_analytics_service = T2AnalyticsService()
