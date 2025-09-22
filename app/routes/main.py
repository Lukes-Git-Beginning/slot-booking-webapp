# -*- coding: utf-8 -*-
"""
Main application routes
Index, day view, and core functionality
"""

from flask import Blueprint, redirect, url_for, render_template, session
from datetime import datetime, timedelta
import pytz

from app.config.base import slot_config
from app.services.booking_service import (
    load_availability,
    get_effective_availability,
    get_slot_status,
    extract_weekly_summary,
    extract_detailed_summary,
    get_slot_suggestions
)
from app.utils.helpers import get_week_days, get_week_start, get_current_kw
from app.core.extensions import cache_manager, level_system
from app.utils.decorators import require_login

main_bp = Blueprint('main', __name__)
TZ = pytz.timezone(slot_config.TIMEZONE)


@main_bp.route("/")
def index():
    """Redirect to today's day view"""
    return redirect(url_for("main.day_view", date_str=datetime.today().strftime("%Y-%m-%d")))


@main_bp.route("/favicon.ico")
def favicon():
    """Serve favicon to prevent 404 errors"""
    return '', 204


@main_bp.route("/day/<date_str>")
@require_login
def day_view(date_str):
    """Display day view with available slots"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for("main.day_view", date_str=datetime.today().strftime("%Y-%m-%d")))

    # Load availability data (needed for summary calculations regardless of caching)
    availability = load_availability()

    # Try to get cached day view data (cache for 5 minutes to balance freshness vs performance)
    # v2: Fixed calendar API fallback logic for booking availability
    day_cache_key = f"day_view_v2_{date_str}_{datetime.now(TZ).strftime('%H_%M')[:-1]}5"
    cached_slots = cache_manager.get("day_view", day_cache_key)

    if cached_slots:
        slots = cached_slots
    else:
        slots = {}

        for hour in ["09:00", "11:00", "14:00", "16:00", "18:00", "20:00"]:
            # Use effective availability (loaded data + fallback defaults)
            effective_beraters = get_effective_availability(date_str, hour)
            berater_count = len(effective_beraters)
            slot_list, booked, total, freie_count, overbooked = get_slot_status(date_str, hour, berater_count)

            # Check if this slot uses loaded data or default fallback
            key = f"{date_str} {hour}"
            using_default = key not in availability and berater_count > 0

            slots[hour] = {
                "events": slot_list,
                "booked": booked,
                "total": total,
                "free_count": freie_count,
                "available_beraters": berater_count,
                "overbooked": overbooked,
                "using_default": using_default,
            }

        # Cache the computed slots for 5 minutes
        cache_manager.set("day_view", day_cache_key, slots)

    # Berechne Level-Daten für User (with caching)
    user = session.get("user")
    user_level = None
    if user:
        # Cache user level calculation for 10 minutes
        level_cache_key = f"user_level_{user}_{datetime.now(TZ).strftime('%Y-%m-%d_%H_%M')[:-1]}0"
        cached_level = cache_manager.get("user_level", level_cache_key)

        if cached_level:
            user_level = cached_level
        else:
            user_level = level_system.calculate_user_level(user)
            # Füge Farben hinzu
            user_level["progress_color"] = level_system.get_level_progress_color(user_level["progress_to_next"])
            if user_level["best_badge"]:
                user_level["best_badge_color"] = level_system.get_rarity_color(user_level["best_badge"]["rarity"])

            # Cache the user level data
            cache_manager.set("user_level", level_cache_key, user_level)

    return render_template(
        "index.html",
        slots=slots,
        date=date_obj,
        days=get_week_days(date_obj),
        week_start=get_week_start(date_obj),
        current_kw=get_current_kw(date_obj),
        weekly_summary=extract_weekly_summary(availability, current_date=date_obj),
        weekly_detailed=extract_detailed_summary(availability),
        timedelta=timedelta,
        get_week_start=get_week_start,
        slot_suggestions=get_slot_suggestions(availability),
        user_level=user_level
    )