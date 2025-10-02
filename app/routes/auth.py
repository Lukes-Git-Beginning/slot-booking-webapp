# -*- coding: utf-8 -*-
"""
Authentication routes
Login, logout, and session management
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from app.utils.helpers import get_userlist
from app.core.extensions import data_persistence
from app.config.base import gamification_config
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


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login"""
    userlist = get_userlist()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Input validation
        if not username or not password:
            flash("Benutzername und Passwort sind erforderlich.", "danger")
            return redirect(url_for("auth.login"))

        if len(username) > 50 or len(password) > 100:
            flash("Eingabe zu lang.", "danger")
            return redirect(url_for("auth.login"))

        if username in userlist and password == userlist[username]:
            session.update({"logged_in": True, "user": username})
            champ = check_and_set_champion()
            session["is_champion"] = (champ == username)
            if champ == username:
                flash("🏆 Glückwunsch! Du warst Top-Telefonist des letzten Monats!", "success")

            # Redirect to next page or hub dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for("hub.dashboard"))
        flash("Falscher Benutzername oder Passwort.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Handle user logout"""
    session.clear()
    return redirect(url_for("auth.login"))