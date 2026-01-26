# -*- coding: utf-8 -*-
"""
Admin telefonie routes
Weekly points tracking and telefonie management
"""

from flask import render_template, request, redirect, url_for, flash, make_response
from datetime import datetime, timedelta
import pytz


def parse_german_decimal(value: str) -> float:
    """Parse German decimal format (comma as separator) to float."""
    if not value:
        return 0.0
    # Replace comma with dot for float conversion
    return float(str(value).replace(",", "."))

from app.config.base import slot_config
from app.utils.decorators import require_admin
from app.routes.admin import admin_bp
from app.services.weekly_points import (
    get_week_key,
    list_recent_weeks,
    is_in_commit_window,
    get_participants,
    set_participants,
    set_week_goal,
    record_activity,
    delete_activity,
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
                user = request.form.get("user")
                goal = parse_german_decimal(request.form.get("goal_points", "0"))
                result = set_week_goal(week_key, user, goal, "admin")
                if result["success"]:
                    flash(f"Ziel für {user} in Woche {week_key} auf {goal} gesetzt", "success")
                else:
                    flash(f"Fehler: {result['error']}", "danger")

            elif action == "record_activity":
                user = request.form.get("user")
                kind = request.form.get("kind", "telefonie")
                points = parse_german_decimal(request.form.get("points", "0"))
                note = request.form.get("note", "")
                result = record_activity(week_key, user, kind, points, "admin", note)
                if result["success"]:
                    flash(f"{points} {kind} Punkte für {user} in Woche {week_key} hinzugefügt", "success")
                else:
                    flash(f"Fehler: {result['error']}", "danger")

            elif action == "apply_pending":
                if is_in_commit_window():
                    apply_pending(week_key)
                    flash(f"Pending-Änderungen für Woche {week_key} angewendet", "success")
                else:
                    flash("Änderungen können nur im Commit-Fenster (18-21 Uhr) angewendet werden", "warning")

            elif action == "set_vacation":
                user = request.form.get("user")
                on_vacation = bool(int(request.form.get("on_vacation", 0)))
                set_on_vacation(week_key, user, on_vacation)
                status = "aktiviert" if on_vacation else "deaktiviert"
                flash(f"Urlaub für {user} in Woche {week_key} {status}", "success")

            elif action == "add_participant":
                name = request.form.get("name", "").strip()
                if name:
                    add_participant(name)
                    flash(f"Teilnehmer '{name}' hinzugefügt", "success")
                else:
                    flash("Name darf nicht leer sein", "danger")

            elif action == "remove_participant":
                name = request.form.get("name")
                if name:
                    remove_participant(name)
                    flash(f"Teilnehmer '{name}' entfernt", "success")

            elif action == "set_vacation_period":
                user = request.form.get("user")
                start_date = request.form.get("start_date")
                end_date = request.form.get("end_date")
                reason = request.form.get("reason", "Urlaub")
                if user and start_date and end_date:
                    result = set_vacation_period(user, start_date, end_date, reason)
                    if result["success"]:
                        flash(result["message"], "success")
                    else:
                        flash(f"Fehler: {result['message']}", "danger")
                else:
                    flash("Alle Felder sind erforderlich", "danger")

            elif action == "delete_activity":
                user = request.form.get("user")
                activity_index = request.form.get("activity_index")
                if user and activity_index is not None:
                    result = delete_activity(week_key, user, int(activity_index), "admin")
                    if result["success"]:
                        flash(f"Aktivität für {user} wurde gelöscht", "success")
                    else:
                        flash(f"Fehler: {result['error']}", "danger")
                else:
                    flash("User und Activity-Index sind erforderlich", "danger")

        except Exception as e:
            flash(f"Fehler: {str(e)}", "danger")

        return redirect(url_for("admin.admin_telefonie", week=week_key))

    # GET request - show telefonie management interface
    recent_weeks = list_recent_weeks(8)  # Last 8 weeks
    participants = get_participants()
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
                         in_window=is_in_commit_window(),
                         current_time=now.strftime("%H:%M"))


@admin_bp.route("/telefonie/export")
@require_admin
def admin_telefonie_export():
    """Export telefonie data as professional PDF"""
    week_key = request.args.get("week", get_week_key(datetime.now(TZ)))

    try:
        # Redirect to the professional PDF export route
        return redirect(url_for("admin.admin_telefonie_export_report",
                              report_type="weekly",
                              week=week_key))

    except Exception as e:
        flash(f"Export error: {str(e)}", "danger")
        return redirect(url_for("admin.admin_telefonie", week=week_key))