# -*- coding: utf-8 -*-
"""
User Profile Routes - Detaillierte Benutzerprofile für Scoreboard
"""

from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from datetime import datetime, timedelta
import pytz

from app.config.base import slot_config
from app.core.extensions import cache_manager, data_persistence, level_system
from app.utils.decorators import require_login

user_profile_bp = Blueprint('user_profile', __name__)
TZ = pytz.timezone(slot_config.TIMEZONE)


@user_profile_bp.route("/profile/<username>")
@require_login
def user_profile(username):
    """Detailliertes User-Profil mit Stats und Achievements"""
    current_user = session.get("user")

    # Comprehensive User Data Collection
    profile_data = {
        'username': username,
        'is_own_profile': current_user == username,
        'basic_stats': get_user_basic_stats(username),
        'achievements': get_user_achievements(username),
        'cosmetics': get_user_cosmetics(username),
        'activity_timeline': get_user_activity_timeline(username),
        'performance_metrics': get_user_performance_metrics(username),
        'level_progression': get_user_level_progression(username),
        'social_stats': get_user_social_stats(username)
    }

    return render_template("user_profile.html",
                         profile=profile_data,
                         current_user=current_user)


def get_user_basic_stats(username):
    """Basic User Statistics"""
    stats = {}

    # Punkte-History
    scores = data_persistence.load_scores()
    user_scores = scores.get(username, {})

    current_month = datetime.now(TZ).strftime("%Y-%m")
    stats['current_points'] = user_scores.get(current_month, 0)
    stats['total_points'] = sum(user_scores.values())
    stats['active_months'] = len([m for m, p in user_scores.items() if p > 0])

    # Ranking berechnen
    month_ranking = sorted([(u, v.get(current_month, 0)) for u, v in scores.items()],
                          key=lambda x: x[1], reverse=True)
    stats['current_rank'] = next((i+1 for i, (u, _) in enumerate(month_ranking) if u == username), 999)
    stats['total_players'] = len(month_ranking)

    # Level-Info
    try:
        if level_system:
            level_data = level_system.calculate_user_level(username)
            stats['level'] = level_data.get('level', 1)
            stats['level_title'] = level_data.get('level_title', 'Anfänger')
            stats['xp'] = level_data.get('xp', 0)
            stats['next_level_xp'] = level_data.get('next_level_xp', 100)
        else:
            stats.update({'level': 1, 'level_title': 'Anfänger', 'xp': 0, 'next_level_xp': 100})
    except Exception:
        stats.update({'level': 1, 'level_title': 'Anfänger', 'xp': 0, 'next_level_xp': 100})

    return stats


def get_user_achievements(username):
    """User Achievement Data"""
    try:
        from app.services.achievement_system import achievement_system
        user_badges = achievement_system.get_user_badges(username)

        achievements = {
            'total_badges': user_badges.get('total_badges', 0),
            'badges': user_badges.get('badges', []),
            'rarity_breakdown': {},
            'recent_badges': []
        }

        # Rarity breakdown
        for badge in achievements['badges']:
            rarity = badge.get('rarity', 'common')
            achievements['rarity_breakdown'][rarity] = achievements['rarity_breakdown'].get(rarity, 0) + 1

        # Recent badges (last 30 days)
        cutoff = datetime.now(TZ) - timedelta(days=30)
        achievements['recent_badges'] = [
            badge for badge in achievements['badges']
            if badge.get('earned_at') and datetime.fromisoformat(badge['earned_at']) > cutoff
        ]

        return achievements

    except Exception as e:
        print(f"Achievement data error for {username}: {e}")
        return {'total_badges': 0, 'badges': [], 'rarity_breakdown': {}, 'recent_badges': []}


def get_user_cosmetics(username):
    """User Cosmetic Items"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from cosmetics_shop import CosmeticsShop

        shop = CosmeticsShop()
        result = shop.get_user_cosmetics(username)

        # Debug-Output für Admin-User
        admin_users = ["Luke", "admin", "Jose", "Simon", "Alex", "David"]
        if username in admin_users:
            print(f"DEBUG: Admin-User {username} Cosmetics-Daten:")
            print(f"  - Result structure: {result.keys()}")
            print(f"  - Owned: {result.get('owned', {})}")
            print(f"  - Active: {result.get('active', {})}")

        # Sicherstellen dass owned richtig strukturiert ist
        if 'owned' not in result:
            result['owned'] = {'titles': [], 'themes': [], 'avatars': [], 'effects': []}
        elif not result['owned']:
            result['owned'] = {'titles': [], 'themes': [], 'avatars': [], 'effects': []}

        return result
    except Exception as e:
        print(f"Cosmetics data error for {username}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'owned': {'titles': [], 'themes': [], 'avatars': [], 'effects': []},
            'active': {'title': None, 'theme': 'default', 'avatar': '🧑‍💼', 'effects': []}
        }


def get_user_activity_timeline(username):
    """User Activity Timeline (last 30 days)"""
    timeline = []

    try:
        # Load daily stats
        daily_stats = data_persistence.load_daily_user_stats()

        # Get last 30 days
        for days_back in range(30):
            check_date = datetime.now(TZ) - timedelta(days=days_back)
            date_str = check_date.strftime("%Y-%m-%d")

            if username in daily_stats and date_str in daily_stats[username]:
                day_data = daily_stats[username][date_str]
                timeline.append({
                    'date': date_str,
                    'bookings': day_data.get('bookings', 0),
                    'points': day_data.get('points', 0),
                    'badges_earned': day_data.get('badges_earned', 0),
                    'first_booking': day_data.get('first_booking', False)
                })

        timeline.reverse()  # Chronological order

    except Exception as e:
        print(f"Activity timeline error for {username}: {e}")

    return timeline


def get_user_performance_metrics(username):
    """Advanced Performance Metrics"""
    metrics = {
        'booking_patterns': {},
        'success_rates': {},
        'streak_info': {},
        'comparative_stats': {}
    }

    try:
        # Analyze booking patterns from tracking data
        tracking_data = data_persistence.load_data('daily_metrics', {})

        user_bookings_by_hour = {}
        user_bookings_by_day = {}
        total_bookings = 0

        for date_str, day_data in tracking_data.items():
            if 'by_user' in day_data and username in day_data['by_user']:
                user_day_data = day_data['by_user'][username]
                bookings = user_day_data.get('bookings', 0)
                total_bookings += bookings

                # Day of week analysis
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    day_name = date_obj.strftime("%A")
                    user_bookings_by_day[day_name] = user_bookings_by_day.get(day_name, 0) + bookings
                except ValueError:
                    pass

        metrics['booking_patterns'] = {
            'by_hour': user_bookings_by_hour,
            'by_day': user_bookings_by_day,
            'total_bookings': total_bookings,
            'favorite_day': max(user_bookings_by_day.items(), key=lambda x: x[1])[0] if user_bookings_by_day else 'Unbekannt'
        }

        # Add more performance calculations here...

    except Exception as e:
        print(f"Performance metrics error for {username}: {e}")

    return metrics


def get_user_level_progression(username):
    """Level Progression History"""
    try:
        # This would track level progression over time
        # For now, return current level info
        if level_system:
            return level_system.calculate_user_level(username)
        else:
            return {'level': 1, 'level_title': 'Anfänger', 'xp': 0}
    except Exception:
        return {'level': 1, 'level_title': 'Anfänger', 'xp': 0}


def get_user_social_stats(username):
    """Social/Comparative Statistics"""
    stats = {}

    try:
        # Compare with other users
        scores = data_persistence.load_scores()
        current_month = datetime.now(TZ).strftime("%Y-%m")

        all_scores = [score.get(current_month, 0) for score in scores.values()]
        user_score = scores.get(username, {}).get(current_month, 0)

        if all_scores:
            stats['percentile'] = (sum(1 for s in all_scores if s < user_score) / len(all_scores)) * 100
            stats['above_average'] = user_score > (sum(all_scores) / len(all_scores))
            stats['top_10_percent'] = user_score >= sorted(all_scores, reverse=True)[min(len(all_scores)//10, len(all_scores)-1)]

    except Exception as e:
        print(f"Social stats error for {username}: {e}")

    return stats


@user_profile_bp.route("/api/user/<username>/profile")
@require_login
def api_user_profile(username):
    """JSON API für User-Profil-Daten"""
    try:
        profile_data = {
            'basic_stats': get_user_basic_stats(username),
            'achievements': get_user_achievements(username),
            'performance_metrics': get_user_performance_metrics(username)
        }

        return jsonify({
            'success': True,
            'data': profile_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500