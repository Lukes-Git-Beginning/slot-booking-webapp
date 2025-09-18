# -*- coding: utf-8 -*-
"""
Admin telefonie routes
Weekly points tracking and telefonie management
"""

from flask import render_template, request, redirect, url_for, flash, make_response
from datetime import datetime, timedelta
import pytz

from app.config.base import slot_config
from app.utils.decorators import require_admin
from app.routes.admin import admin_bp
from weekly_points import (
    get_week_key,
    list_recent_weeks,
    is_in_commit_window,
    get_participants,
    set_participants,
    set_week_goal,
    record_activity,
    apply_pending,
    compute_week_stats,
    set_vacation_period,
    get_user_vacation_periods,
    is_user_on_vacation,
    add_participant,
    remove_participant,
    set_on_vacation,
    get_week_audit,
)

TZ = pytz.timezone(slot_config.TIMEZONE)


@admin_bp.route("/telefonie", methods=["GET", "POST"])
@require_admin
def admin_telefonie():
    """Telefonie points management"""
    now = datetime.now(TZ)
    week_key = request.args.get("week", get_week_key(now))

    if request.method == "POST":
        action = request.form.get("action")

        try:
            if action == "set_participants":
                participants_str = request.form.get("participants", "")
                participants = [p.strip() for p in participants_str.split(",") if p.strip()]
                set_participants(week_key, participants)
                flash(f"Teilnehmer für Woche {week_key} gesetzt", "success")

            elif action == "set_goal":
                goal = int(request.form.get("goal", 0))
                set_week_goal(week_key, goal)
                flash(f"Ziel für Woche {week_key} auf {goal} gesetzt", "success")

            elif action == "record_activity":
                user = request.form.get("user")
                points = int(request.form.get("points", 0))
                description = request.form.get("description", "")
                record_activity(week_key, user, points, description)
                flash(f"{points} Punkte für {user} in Woche {week_key} hinzugefügt", "success")

            elif action == "apply_pending":
                if is_in_commit_window():
                    apply_pending(week_key)
                    flash(f"Pending-Änderungen für Woche {week_key} angewendet", "success")
                else:
                    flash("Änderungen können nur im Commit-Fenster (18-21 Uhr) angewendet werden", "warning")

            elif action == "set_vacation":
                user = request.form.get("user")
                start_date = request.form.get("start_date")
                end_date = request.form.get("end_date")
                if user and start_date and end_date:
                    set_vacation_period(user, start_date, end_date)
                    flash(f"Urlaubszeit für {user} gesetzt: {start_date} bis {end_date}", "success")

        except Exception as e:
            flash(f"Fehler: {str(e)}", "danger")

        return redirect(url_for("admin.admin_telefonie", week=week_key))

    # GET request - show telefonie management interface
    recent_weeks = list_recent_weeks(8)  # Last 8 weeks
    participants = get_participants(week_key)
    stats = compute_week_stats(week_key)
    audit = get_week_audit(week_key)

    # Get vacation periods for all users
    vacation_periods = {}
    for user in participants:
        vacation_periods[user] = get_user_vacation_periods(user)

    return render_template("admin_telefonie.html",
                         week=week_key,
                         recent_weeks=recent_weeks,
                         participants=participants,
                         stats=stats,
                         audit=audit,
                         vacation_periods=vacation_periods,
                         is_commit_window=is_in_commit_window(),
                         current_time=now.strftime("%H:%M"))


@admin_bp.route("/telefonie/export")
@require_admin
def admin_telefonie_export():
    """Export telefonie data"""
    week_key = request.args.get("week", get_week_key(datetime.now(TZ)))

    try:
        # Get week data
        participants = get_participants(week_key)
        stats = compute_week_stats(week_key)
        audit = get_week_audit(week_key)

        # Create export data
        export_data = {
            'week': week_key,
            'participants': participants,
            'stats': stats,
            'audit': audit,
            'exported_at': datetime.now(TZ).isoformat()
        }

        # For now, return JSON - could be enhanced to PDF
        response = make_response(str(export_data))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=telefonie_week_{week_key}.json'

        return response

    except Exception as e:
        flash(f"Export error: {str(e)}", "danger")
        return redirect(url_for("admin.admin_telefonie", week=week_key))