# -*- coding: utf-8 -*-
"""
Scoreboard and badge routes
Player rankings, achievements, and gamification features
"""

from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from datetime import datetime, timedelta
import pytz
import json
import time

from app.config.base import slot_config, config, gamification_config
from app.core.extensions import cache_manager, data_persistence, level_system
from app.utils.decorators import require_login

scoreboard_bp = Blueprint('scoreboard', __name__)
TZ = pytz.timezone(slot_config.TIMEZONE)


def get_champion_for_month(month):
    """Get champion for specific month"""
    champions = data_persistence.load_champions()
    return champions.get(month)


def check_for_updates():
    """Check for real-time updates"""
    # This would check for new badges, level ups, etc.
    # For now, return empty updates
    return {}


@scoreboard_bp.route("/scoreboard")
@require_login
def scoreboard():
    """Display scoreboard with user rankings"""
    user = session.get("user")

    # Auto-unlock all cosmetics for admin users
    if user and user in config.get_admin_users():
        try:
            from cosmetics_shop import cosmetics_shop
            unlock_result = cosmetics_shop.unlock_all_for_admin(user)
            if unlock_result.get("success"):
                print(f"Admin cosmetics unlocked for {user}")
        except Exception as e:
            print(f"Failed to unlock admin cosmetics for {user}: {e}")

    # Try to get cached scoreboard data first
    cache_key = f"scoreboard_{datetime.now(TZ).strftime('%Y-%m-%d_%H')}"
    cached_data = cache_manager.get("scoreboard", cache_key)

    if cached_data:
        scores = cached_data["scores"]
        badge_leaderboard = cached_data["badge_leaderboard"]
    else:
        scores = data_persistence.load_scores()

        # Get badge data for leaderboard (persistent)
        try:
            from app.services.achievement_system import achievement_system
            badge_leaderboard = achievement_system.get_badge_leaderboard()
        except Exception as e:
            print(f"Badge Leaderboard Error: {e}")
            badge_leaderboard = []

        # Cache the data for 1 hour
        cache_manager.set("scoreboard", cache_key, {
            "scores": scores,
            "badge_leaderboard": badge_leaderboard
        })

    month = datetime.now(TZ).strftime("%Y-%m")

    # Exclude admin users from scoreboard
    admin_users = config.get_admin_users()
    excluded_users = gamification_config.get_excluded_champion_users()
    all_excluded = set(admin_users + excluded_users)

    # Filter out excluded users
    filtered_scores = {u: v for u, v in scores.items() if u not in all_excluded}

    ranking = sorted([(u, v.get(month, 0)) for u, v in filtered_scores.items()], key=lambda x: x[1], reverse=True)
    user_score = scores.get(user, {}).get(month, 0) if user else 0
    champion = get_champion_for_month((datetime.now(TZ).replace(day=1) - timedelta(days=1)).strftime("%Y-%m"))

    # Get level data for all users in ranking
    user_levels = {}
    for username, _ in ranking:
        try:
            if level_system:
                user_level_data = level_system.calculate_user_level(username)
                user_levels[username] = user_level_data
            else:
                user_levels[username] = {"level": 1, "level_title": "Anfänger", "xp": 0}
        except Exception as e:
            print(f"Level calculation error for {username}: {e}")
            user_levels[username] = {"level": 1, "level_title": "Anfänger", "xp": 0}

    return render_template("scoreboard.html",
                         ranking=ranking,
                         user_score=user_score,
                         month=month,
                         current_user=user,
                         champion=champion,
                         badge_leaderboard=badge_leaderboard,
                         user_levels=user_levels)


@scoreboard_bp.route("/badges")
@require_login
def badges():
    """Badge overview for all users"""
    user = session.get("user")
    if not user:
        return redirect(url_for("auth.login"))

    # Get badge data
    try:
        from app.services.achievement_system import achievement_system, ACHIEVEMENT_DEFINITIONS
        user_badges = achievement_system.get_user_badges(user)
        leaderboard = achievement_system.get_badge_leaderboard()

        # Prepare template variables
        total_badges = user_badges.get("total_badges", 0)
        available_badges = ACHIEVEMENT_DEFINITIONS
        badge_progress = achievement_system.get_badge_progress(user)

    except Exception as e:
        print(f"Badge System Error: {e}")
        user_badges = {"badges": [], "total_badges": 0}
        leaderboard = []
        total_badges = 0
        try:
            from app.services.achievement_system import ACHIEVEMENT_DEFINITIONS
            available_badges = ACHIEVEMENT_DEFINITIONS
        except ImportError:
            available_badges = {}
        badge_progress = {}

    return render_template("badges.html",
                         user_badges=user_badges,
                         leaderboard=leaderboard,
                         current_user=user,
                         total_badges=total_badges,
                         available_badges=available_badges,
                         badge_progress=badge_progress)


@scoreboard_bp.route("/stream/updates")
@require_login
def stream_updates():
    """Server-Sent Events for real-time updates"""
    def generate():
        """Generate event stream"""
        while True:
            try:
                # Check for new updates (every 5 seconds)
                updates = check_for_updates()
                if updates:
                    yield f"data: {json.dumps(updates)}\n\n"

                time.sleep(5)
            except Exception as e:
                print(f"Stream error: {e}")
                break

    return generate(), 200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    }


@scoreboard_bp.route("/gamification")
@require_login
def gamification_dashboard():
    """Main gamification dashboard"""
    user = session.get("user")

    # Get comprehensive gamification data
    gamification_data = {
        'user_level': None,
        'recent_badges': [],
        'daily_quests': [],
        'weekly_progress': {},
        'achievements': []
    }

    try:
        # Get user level data
        if level_system:
            gamification_data['user_level'] = level_system.calculate_user_level(user)

        # Get recent badges
        from achievement_system import achievement_system
        user_badges = achievement_system.get_user_badges(user)
        gamification_data['recent_badges'] = user_badges.get('badges', [])[-5:]  # Last 5 badges

    except Exception as e:
        print(f"Gamification data error: {e}")

    # Get user badges for template
    try:
        from achievement_system import achievement_system
        user_badges = achievement_system.get_user_badges(user)
    except Exception as e:
        print(f"Error getting user badges for gamification: {e}")
        user_badges = {"badges": [], "total_badges": 0}

    # Add missing streak info
    streak_info = {
        'work_streak': 0,
        'current_streak': 0,
        'best_streak': 0
    }

    # Calculate badge statistics
    badge_stats = {
        'total': len(user_badges.get('badges', [])),
        'by_rarity': {}
    }

    # Count badges by rarity
    for badge in user_badges.get('badges', []):
        rarity = badge.get('rarity', 'common')
        badge_stats['by_rarity'][rarity] = badge_stats['by_rarity'].get(rarity, 0) + 1

    # Add rarity colors for template
    rarity_colors = {
        'common': '#6b7280',
        'uncommon': '#10b981',
        'rare': '#3b82f6',
        'epic': '#8b5cf6',
        'legendary': '#f59e0b',
        'mythic': '#ef4444'
    }

    return render_template("gamification.html",
                         user=user,
                         gamification_data=gamification_data,
                         user_level=gamification_data.get('user_level', {}),
                         user_badges=user_badges,
                         badge_stats=badge_stats,
                         rarity_colors=rarity_colors,
                         streak_info=streak_info,
                         user_rank=0)  # Default rank until we implement ranking system