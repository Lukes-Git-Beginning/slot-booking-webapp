# -*- coding: utf-8 -*-
"""
API routes
JSON API endpoints for AJAX calls and external integrations
"""

from flask import Blueprint, jsonify, session, request
from datetime import datetime
import pytz

from app.config.base import slot_config
from app.core.extensions import data_persistence, level_system
from app.utils.decorators import require_login

api_bp = Blueprint('api', __name__)
TZ = pytz.timezone(slot_config.TIMEZONE)


@api_bp.route("/user/badges")
@require_login
def api_user_badges():
    """Get current user's badges"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    try:
        # Get user badges from achievement system
        from app.services.achievement_system import achievement_system
        user_badges = achievement_system.get_user_badges(user)
        return jsonify(user_badges)
    except Exception as e:
        return jsonify({"error": str(e), "badges": []}), 200  # Return empty badges on error


@api_bp.route("/user/<username>/badges")
@require_login
def api_user_badges_by_username(username):
    """Get specific user's badges"""
    try:
        from app.services.achievement_system import achievement_system
        user_badges = achievement_system.get_user_badges(username)
        print(f"DEBUG: Badge API for {username} returning: {user_badges}")
        return jsonify(user_badges)
    except ImportError as e:
        print(f"Achievement system import error: {e}")
        return jsonify({"badges": [], "total_badges": 0, "error": "Achievement system not available"}), 200
    except Exception as e:
        print(f"Badge API error for {username}: {e}")
        return jsonify({"badges": [], "total_badges": 0, "error": str(e)}), 200


@api_bp.route("/user/<username>/avatar")
@require_login
def api_user_avatar(username):
    """Get user's active avatar emoji"""
    try:
        from cosmetics_shop import CosmeticsShop
        cosmetics_shop = CosmeticsShop()
        user_cosmetics = cosmetics_shop.get_user_cosmetics(username)

        # Get active avatar or default
        active_avatar = user_cosmetics.get('active', {}).get('avatar', None)
        if active_avatar:
            return jsonify({"avatar": active_avatar})
        else:
            # Return first letter as fallback
            return jsonify({"avatar": username[0].upper() if username else "?"})

    except Exception as e:
        print(f"Avatar API error for {username}: {e}")
        # Return first letter as fallback
        return jsonify({"avatar": username[0].upper() if username else "?"})


@api_bp.route("/user/badges/mark-seen", methods=["POST"])
@require_login
def api_mark_badges_seen():
    """Mark user's badges as seen"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    try:
        # Mark badges as seen in the system
        # This would integrate with your badge system
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/user/badges/check-new")
@require_login
def api_check_new_badges():
    """Check for new badges"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    try:
        # Check for new badges
        new_badges = []  # This would come from your achievement system
        return jsonify({
            "has_new_badges": len(new_badges) > 0,
            "new_badges": new_badges
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/badges/check-new")
@require_login
def check_new_badges():
    """Check for new badges (alternative endpoint)"""
    return api_check_new_badges()


@api_bp.route("/level/check-up")
@require_login
def check_level_up():
    """Check if user has leveled up"""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    try:
        if level_system:
            user_level = level_system.calculate_user_level(user)
            return jsonify({
                "current_level": user_level.get("level", 1),
                "has_leveled_up": False,  # Would be calculated based on previous level
                "level_data": user_level
            })
        else:
            return jsonify({"error": "Level system not available"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/stream/updates")
@require_login
def stream_updates():
    """Server-sent events for real-time updates"""
    def generate():
        # This would be a real SSE implementation
        # For now, return empty response
        yield "data: {}\n\n"

    return generate(), 200, {
        'Content-Type': 'text/plain',
        'Cache-Control': 'no-cache'
    }