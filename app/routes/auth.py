# -*- coding: utf-8 -*-
"""
Authentication routes
Login, logout, and session management
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from app.utils.helpers import get_userlist
from app.core.extensions import data_persistence, limiter
from app.config.base import gamification_config
from app.services.security_service import security_service
from app.services.audit_service import audit_service
from datetime import datetime, timedelta
import pytz
from app.config.base import slot_config

auth_bp = Blueprint('auth', __name__)

TZ = pytz.timezone(slot_config.TIMEZONE)
EXCLUDE_CHAMPION_USERS = gamification_config.get_excluded_champion_users()


def check_and_set_champion():
    """Check and set monthly champion"""
    now = datetime.now(TZ)
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    champions = data_persistence.load_champions()

    if last_month in champions:
        return champions[last_month]

    scores = data_persistence.load_scores()

    month_scores = [(u, v.get(last_month, 0)) for u, v in scores.items() if u.lower() not in EXCLUDE_CHAMPION_USERS]
    month_scores = [x for x in month_scores if x[1] > 0]
    month_scores.sort(key=lambda x: x[1], reverse=True)

    if month_scores:
        champion_user = month_scores[0][0]
        champions[last_month] = champion_user
        data_persistence.save_champions(champions)
        return champion_user
    return None


def apply_rate_limit(route_func):
    """Apply rate limiting decorator if limiter is available"""
    if limiter:
        return limiter.limit("5 per minute", methods=["POST"])(route_func)
    return route_func

@auth_bp.route("/login", methods=["GET", "POST"])
@apply_rate_limit
def login():
    """Handle user login with rate limiting (max 5 attempts per minute)"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        totp_code = request.form.get("totp_code", "").strip()

        # Input validation
        if not username or not password:
            flash("Benutzername und Passwort sind erforderlich.", "danger")
            return redirect(url_for("auth.login"))

        if len(username) > 50 or len(password) > 100:
            flash("Eingabe zu lang.", "danger")
            return redirect(url_for("auth.login"))

        # Verify password using security service
        if security_service.verify_password(username, password):
            # Check if 2FA is enabled
            if security_service.is_2fa_enabled(username):
                if not totp_code:
                    # Show 2FA input
                    return render_template("login.html", show_2fa=True, username=username)

                # Verify 2FA code
                if not security_service.verify_2fa(username, totp_code):
                    flash("Ungültiger 2FA-Code.", "danger")
                    return render_template("login.html", show_2fa=True, username=username)

            # Login successful
            session.update({"logged_in": True, "user": username})
            champ = check_and_set_champion()
            session["is_champion"] = (champ == username)

            # Audit-Log: Erfolgreicher Login
            audit_service.log_login_success(username)

            if champ == username:
                flash("🏆 Glückwunsch! Du warst Top-Telefonist des letzten Monats!", "success")

            # Redirect to next page or hub dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for("hub.dashboard"))

        # Audit-Log: Fehlgeschlagener Login
        audit_service.log_login_failure(username, reason='invalid_credentials')

        flash("Falscher Benutzername oder Passwort.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Handle user logout"""
    # Audit-Log: Logout
    username = session.get('user')
    if username:
        audit_service.log_logout(username)

    session.clear()
    return redirect(url_for("auth.login"))