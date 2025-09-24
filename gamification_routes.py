# -*- coding: utf-8 -*-
"""
Flask Routes für erweiterte Gamification-Features
Neue Routes für Prestige, Daily Quests, Analytics und Customization
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import traceback

# Import der neuen Systeme
try:
    from prestige_system import prestige_system
    from daily_quests import daily_quest_system
    from analytics_system import analytics_system
    from personalization_system import personalization_system
    from app.services.achievement_system import achievement_system
    from app.services.level_system import LevelSystem
    from cosmetics_shop import cosmetics_shop
except ImportError as e:
    print(f"Import Error in gamification_routes: {e}")
    # Set fallback objects to prevent further errors
    prestige_system = None
    daily_quest_system = None
    analytics_system = None
    personalization_system = None
    achievement_system = None
    LevelSystem = None
    cosmetics_shop = None

# Blueprint erstellen
gamification_bp = Blueprint('gamification', __name__)

def require_login(f):
    """Decorator für Login-Anforderung"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session.get('user'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# ===== DASHBOARD ROUTES =====

@gamification_bp.route('/daily-quests')
@require_login
def daily_quests():
    """Daily Quests Dashboard"""
    try:
        user = session.get('user')
        if not user:
            return redirect('/login')

        # Check if daily quest system is available
        if not daily_quest_system:
            return render_template('daily_quests.html',
                current_user=user,
                quests=[],
                bonus_multiplier=1.0,
                total_completed=0,
                total_claimed=0,
                user_coins=0,
                system_error="Daily Quest System ist derzeit nicht verfügbar."
            )

        # Hole User-Quests
        user_quests = daily_quest_system.get_user_daily_quests(user)
        user_coins = daily_quest_system.get_user_coins(user)
        
        return render_template('daily_quests.html',
            current_user=user,
            quests=user_quests['quests'],
            bonus_multiplier=user_quests['bonus_multiplier'],
            total_completed=user_quests['total_completed'],
            total_claimed=user_quests['total_claimed'],
            user_coins=user_coins
        )
    except Exception as e:
        print(f"Error in daily_quests route: {e}")
        traceback.print_exc()
        return render_template('daily_quests.html', 
            current_user=session.get('user', ''),
            quests=[], 
            user_coins=0,
            error="Fehler beim Laden der Daily Quests"
        )

@gamification_bp.route('/analytics-dashboard')
@require_login  
def analytics_dashboard():
    """Advanced Analytics Dashboard"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        
        # Generiere oder lade Analytics
        analytics = analytics_system.get_user_analytics(user)
        
        return render_template('analytics_dashboard.html',
            current_user=user,
            analytics=analytics
        )
    except Exception as e:
        print(f"Error in analytics_dashboard route: {e}")
        traceback.print_exc()
        return render_template('analytics_dashboard.html',
            current_user=session.get('user', ''),
            analytics={
                "overview": {},
                "booking_patterns": {},
                "performance_trends": {},
                "behavioral_insights": {},
                "achievements_analysis": {},
                "predictions": {},
                "recommendations": {},
                "comparisons": {}
            },
            error="Fehler beim Laden der Analytics"
        )

@gamification_bp.route('/prestige-dashboard')
@require_login
def prestige_dashboard():
    """Prestige & Mastery Dashboard"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        
        # Hole Prestige-Daten
        prestige_data = prestige_system.calculate_user_prestige(user)
        mastery_progress = prestige_data['mastery_progress']
        prestige_leaderboard = prestige_system.get_prestige_leaderboard()
        
        return render_template('prestige_dashboard.html',
            current_user=user,
            prestige_data=prestige_data,
            mastery_progress=mastery_progress,
            prestige_leaderboard=prestige_leaderboard
        )
    except Exception as e:
        print(f"Error in prestige_dashboard route: {e}")
        traceback.print_exc()
        return render_template('prestige_dashboard.html',
            current_user=session.get('user', ''),
            prestige_data={
                "current_level": 1,
                "prestige_level": 0,
                "prestige_points": 0,
                "can_prestige": False,
                "can_upgrade": False,
                "prestige_title": {"name": "Anfänger"},
                "prestige_benefits": []
            },
            mastery_progress={},
            prestige_leaderboard=[],
            error="Fehler beim Laden der Prestige-Daten"
        )

@gamification_bp.route('/customization-shop')
@require_login
def customization_shop():
    """Customization & Personalization Shop"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        
        # Hole User-Profil und Shop-Daten
        profile = personalization_system.load_user_profile(user)
        shop = personalization_system.get_customization_shop(user)
        personal_goals = personalization_system.get_personal_goals(user)
        customization = personalization_system.get_user_customization(user)
        
        return render_template('customization_shop.html',
            current_user=user,
            profile=profile,
            shop=shop,
            personal_goals=personal_goals,
            customization=customization
        )
    except Exception as e:
        print(f"Error in customization_shop route: {e}")
        traceback.print_exc()
        return render_template('customization_shop.html',
            current_user=session.get('user', ''),
            profile={"display_name": session.get('user', ''), "theme": "default"},
            shop={"avatar_components": {}, "themes": {}, "unlocked_count": 0, "locked_count": 0},
            personal_goals=[],
            customization={"avatar": {"background": "gradient_blue", "border": "simple", "effect": "none", "title": "none"}},
            error="Fehler beim Laden des Customization Shops"
        )

# ===== API ROUTES =====

@gamification_bp.route('/api/claim-quest', methods=['POST'])
@require_login
def api_claim_quest():
    """API: Quest-Belohnung einlösen"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        data = request.get_json()
        quest_id = data.get('quest_id')
        
        if not quest_id:
            return jsonify({"success": False, "message": "Quest ID fehlt"})
        
        result = daily_quest_system.claim_quest_reward(user, quest_id)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in api_claim_quest: {e}")
        return jsonify({"success": False, "message": "Server-Fehler beim Einlösen der Quest-Belohnung"})

@gamification_bp.route('/api/spin-wheel', methods=['POST'])
@require_login
def api_spin_wheel():
    """API: Glücksrad drehen"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        result = daily_quest_system.spin_wheel(user)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in api_spin_wheel: {e}")
        return jsonify({"success": False, "message": "Server-Fehler beim Drehen des Glücksrads"})

@gamification_bp.route('/api/perform-prestige', methods=['POST'])
@require_login
def api_perform_prestige():
    """API: Prestige durchführen"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        result = prestige_system.perform_prestige(user)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in api_perform_prestige: {e}")
        return jsonify({"success": False, "message": "Server-Fehler beim Prestige-Upgrade"})

@gamification_bp.route('/api/upgrade-mastery', methods=['POST'])
@require_login
def api_upgrade_mastery():
    """API: Mastery-Level upgraden"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        data = request.get_json()
        category_id = data.get('category_id')
        
        if not category_id:
            return jsonify({"success": False, "message": "Category ID fehlt"})
        
        result = prestige_system.upgrade_mastery(user, category_id)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in api_upgrade_mastery: {e}")
        return jsonify({"success": False, "message": "Server-Fehler beim Mastery-Upgrade"})

@gamification_bp.route('/api/update-customization', methods=['POST'])
@require_login
def api_update_customization():
    """API: Avatar-Customization updaten"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        data = request.get_json()
        
        # Update Avatar-Customization
        if 'avatar' in data:
            result = personalization_system.update_user_customization(user, data)
            if not result['success']:
                return jsonify(result)
        
        # Update Theme
        if 'theme' in data:
            updates = {"theme": data['theme']}
            personalization_system.update_user_profile(user, updates)
        
        return jsonify({"success": True, "message": "Anpassungen gespeichert"})
        
    except Exception as e:
        print(f"Error in api_update_customization: {e}")
        return jsonify({"success": False, "message": "Server-Fehler beim Speichern der Anpassungen"})

@gamification_bp.route('/api/create-personal-goal', methods=['POST'])
@require_login
def api_create_personal_goal():
    """API: Persönliches Ziel erstellen"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        data = request.get_json()
        
        template = data.get('template')
        target = data.get('target')
        
        if not template or not target:
            return jsonify({"success": False, "message": "Template und Target sind erforderlich"})
        
        result = personalization_system.create_personal_goal(user, template, target)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in api_create_personal_goal: {e}")
        return jsonify({"success": False, "message": "Server-Fehler beim Erstellen des Ziels"})

@gamification_bp.route('/api/claim-goal-reward', methods=['POST'])
@require_login
def api_claim_goal_reward():
    """API: Persönliches Ziel Belohnung einlösen"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        data = request.get_json()
        goal_id = data.get('goal_id')
        
        if not goal_id:
            return jsonify({"success": False, "message": "Goal ID fehlt"})
        
        result = personalization_system.claim_goal_reward(user, goal_id)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in api_claim_goal_reward: {e}")
        return jsonify({"success": False, "message": "Server-Fehler beim Einlösen der Belohnung"})

@gamification_bp.route('/api/refresh-analytics', methods=['POST'])
@require_login
def api_refresh_analytics():
    """API: Analytics neu generieren"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        analytics = analytics_system.get_user_analytics(user, force_refresh=True)
        return jsonify({"success": True, "analytics": analytics})
        
    except Exception as e:
        print(f"Error in api_refresh_analytics: {e}")
        return jsonify({"success": False, "message": "Server-Fehler beim Aktualisieren der Analytics"})

@gamification_bp.route('/api/user/<username>/badges')
@require_login  
def api_user_badges(username):
    """API: User-Badges für Scoreboard laden"""
    try:
        user_badges = achievement_system.get_user_badges(username)
        return jsonify(user_badges)
        
    except Exception as e:
        print(f"Error in api_user_badges: {e}")
        return jsonify({"badges": [], "total_badges": 0})

@gamification_bp.route('/api/user/<username>/avatar')
@require_login
def api_user_avatar(username):
    """API: User-Avatar-Customization für Scoreboard laden"""
    try:
        customization = personalization_system.get_user_customization(username)
        avatar_data = customization.get('avatar', {
            "background": "gradient_blue",
            "border": "simple", 
            "effect": "none",
            "title": "none"
        })
        return jsonify(avatar_data)
        
    except Exception as e:
        print(f"Error in api_user_avatar: {e}")
        return jsonify({
            "background": "gradient_blue",
            "border": "simple",
            "effect": "none",
            "title": "none"
        })

@gamification_bp.route('/api/user/<username>/cosmetics')
@require_login
def api_user_cosmetics(username):
    """API: Vollständige User-Cosmetics für Theme/Avatar-Anwendung"""
    try:
        from cosmetics_shop import cosmetics_shop
        cosmetics_data = cosmetics_shop.get_user_cosmetics(username)
        return jsonify({
            'success': True,
            'data': cosmetics_data
        })
    except Exception as e:
        print(f"Error in api_user_cosmetics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {'owned': {}, 'active': {'theme': 'default', 'avatar': '🧑‍💼'}}
        })

# ===== QUEST PROGRESS UPDATES =====

def update_quest_progress_for_booking(user, booking_data):
    """Update Quest-Fortschritt für Buchungen"""
    try:
        # Quest-Updates
        daily_quest_system.update_quest_progress(user, "booking", booking_data)
        
        # Check für zeitbasierte Quests
        daily_quest_system.update_quest_progress(user, "time_based", booking_data)
        
        # Streak-Quests (täglich ausgeführt)
        daily_quest_system.update_quest_progress(user, "streak", booking_data)
        
        print(f"Quest progress updated for user {user}")
        
    except Exception as e:
        print(f"Error updating quest progress: {e}")

def update_quest_progress_for_minigame(user, game_data):
    """Update Quest-Fortschritt für Mini-Games"""
    try:
        daily_quest_system.update_quest_progress(user, "minigame", game_data)
        print(f"Minigame quest progress updated for user {user}")
        
    except Exception as e:
        print(f"Error updating minigame quest progress: {e}")

# ===== INTEGRATION HELPERS =====

def get_enhanced_user_level(user):
    """Hole erweiterte Level-Daten inklusive Prestige"""
    try:
        level_system = LevelSystem()
        user_level = level_system.calculate_user_level(user)
        
        # Füge Prestige-Daten hinzu
        prestige_data = prestige_system.calculate_user_prestige(user)
        user_level['prestige'] = prestige_data
        
        return user_level
        
    except Exception as e:
        print(f"Error getting enhanced user level: {e}")
        return {
            "user": user,
            "level": 1,
            "xp": 0,
            "level_title": "Anfänger",
            "prestige": {"prestige_level": 0, "prestige_title": {"name": ""}}
        }

def check_and_unlock_customizations(user):
    """Prüfe und schalte neue Customization-Items frei"""
    try:
        unlock_result = personalization_system.check_unlock_progress(user)
        
        if unlock_result['newly_unlocked']:
            print(f"New customization items unlocked for {user}: {unlock_result['newly_unlocked']}")
            
        return unlock_result
        
    except Exception as e:
        print(f"Error checking customization unlocks: {e}")
        return {"newly_unlocked": [], "total_unlocked": []}

# ===== COSMETICS SHOP ROUTES =====

@gamification_bp.route('/cosmetics-shop')
@require_login
def cosmetics_shop_view():
    """Cosmetics Shop Dashboard"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
        
        # Hole User-Coins aus Daily Quest System
        user_coins = daily_quest_system.get_user_coins(user)
        
        # Hole Kosmetik-Daten
        user_cosmetics = cosmetics_shop.get_user_cosmetics(user)
        
        return render_template('cosmetics_shop.html',
            current_user=user,
            user_coins=user_coins,
            cosmetics=user_cosmetics
        )
        
    except Exception as e:
        print(f"Error in cosmetics_shop route: {e}")
        traceback.print_exc()
        return render_template('cosmetics_shop.html', 
            current_user=user,
            error="Fehler beim Laden des Cosmetics Shops",
            user_coins=0,
            cosmetics={"owned": {}, "active": {}, "available_titles": {}, "available_themes": {}, "available_avatars": {}, "available_effects": {}}
        )

@gamification_bp.route('/cosmetics/purchase', methods=['POST'])
@require_login
def purchase_cosmetic():
    """Kaufe Kosmetik-Item"""
    try:
        user = session.get('user')
        data = request.get_json()
        
        item_type = data.get('item_type')
        item_id = data.get('item_id')
        
        if not item_type or not item_id:
            return jsonify({"success": False, "message": "Unvollständige Daten"})
        
        # Prüfe User-Coins
        user_coins = daily_quest_system.get_user_coins(user)
        
        # Kaufe Item
        result = cosmetics_shop.purchase_item(user, item_type, item_id, user_coins)
        
        if result["success"]:
            # Deduct coins from user
            coins_data = daily_quest_system.load_user_coins()
            coins_data[user] = coins_data.get(user, 0) - result["price"]
            daily_quest_system.save_user_coins(coins_data)
            
            result["remaining_coins"] = coins_data.get(user, 0)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error purchasing cosmetic: {e}")
        return jsonify({"success": False, "message": "Fehler beim Kauf"})

@gamification_bp.route('/cosmetics/equip', methods=['POST'])
@require_login  
def equip_cosmetic():
    """Rüste Kosmetik-Item aus"""
    try:
        user = session.get('user')
        data = request.get_json()
        
        item_type = data.get('item_type')
        item_id = data.get('item_id')
        
        if not item_type or not item_id:
            return jsonify({"success": False, "message": "Unvollständige Daten"})
        
        result = cosmetics_shop.equip_item(user, item_type, item_id)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error equipping cosmetic: {e}")
        return jsonify({"success": False, "message": "Fehler beim Ausrüsten"})

@gamification_bp.route('/cosmetics/unequip', methods=['POST'])
@require_login
def unequip_cosmetic():
    """Entferne Kosmetik-Item"""
    try:
        user = session.get('user')
        data = request.get_json()
        
        item_type = data.get('item_type')
        item_id = data.get('item_id')  # Optional für Effekte
        
        if not item_type:
            return jsonify({"success": False, "message": "Item-Typ fehlt"})
        
        result = cosmetics_shop.unequip_item(user, item_type, item_id)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error unequipping cosmetic: {e}")
        return jsonify({"success": False, "message": "Fehler beim Entfernen"})

@gamification_bp.route('/admin/unlock-all-cosmetics', methods=['POST'])
@require_login
def admin_unlock_all_cosmetics():
    """Admin Route: Schalte alle Kosmetik-Items frei"""
    try:
        user = session.get('user')
        
        # Prüfe ob User Admin ist (du kannst hier deine Admin-Logik einfügen)
        # Für jetzt nehme ich an, dass der erste User oder "admin" der Admin ist
        if user not in ["Luke", "admin"]:  # Passe diese Liste an deine Admins an
            return jsonify({"success": False, "message": "Keine Admin-Berechtigung"})
        
        result = cosmetics_shop.unlock_all_for_admin(user)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in admin unlock all cosmetics: {e}")
        return jsonify({"success": False, "message": "Fehler beim Admin-Unlock"})

# ===== DAILY MAINTENANCE =====

def run_daily_maintenance():
    """Tägliche Wartungsroutinen für Gamification-Features"""
    try:
        print("Running daily gamification maintenance...")
        
        # Generiere neue Daily Quests
        daily_quest_system.generate_daily_quests()
        
        # Prüfe MVP-Badges
        achievement_system.auto_check_mvp_badges()
        
        # Analytics-Cache leeren (wird bei nächstem Zugriff neu generiert)
        # analytics_system könnte hier Cache-Cleanup machen
        
        print("Daily maintenance completed successfully")
        
    except Exception as e:
        print(f"Error in daily maintenance: {e}")

# ===== ERROR HANDLERS =====

@gamification_bp.errorhandler(404)
def not_found_error(error):
    """404 Error Handler für Gamification-Routes"""
    return render_template('error.html', 
        error_code=404,
        error_message="Seite nicht gefunden",
        current_user=session.get('user', '')
    ), 404

@gamification_bp.errorhandler(500)
def internal_error(error):
    """500 Error Handler für Gamification-Routes"""
    return render_template('error.html',
        error_code=500, 
        error_message="Interner Server-Fehler",
        current_user=session.get('user', '')
    ), 500