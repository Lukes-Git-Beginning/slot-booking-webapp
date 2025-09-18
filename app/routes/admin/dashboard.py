# -*- coding: utf-8 -*-
"""
Admin dashboard routes
Main admin interface and overview
"""

from flask import render_template, session, redirect, url_for, flash
from datetime import datetime, timedelta
import pytz

from app.config.base import slot_config
from app.core.extensions import data_persistence, tracking_system
from app.utils.decorators import require_admin
from app.utils.helpers import get_app_runtime_days, get_color_mapping_status
from app.routes.admin import admin_bp

TZ = pytz.timezone(slot_config.TIMEZONE)


@admin_bp.route("/dashboard")
@require_admin
def admin_dashboard():
    """Main admin dashboard with overview metrics"""
    try:
        # Get tracking data
        tracker = tracking_system if tracking_system else None

        # Basic metrics
        total_bookings = 0
        total_customers = 0
        recent_activity = []

        if tracker:
            # Get dashboard data from tracking system
            dashboard_data = tracker.get_performance_dashboard()
            total_bookings = dashboard_data.get('total_bookings', 0)
            total_customers = dashboard_data.get('unique_customers', 0)
            recent_activity = dashboard_data.get('recent_bookings', [])

        # System metrics
        app_runtime_days = get_app_runtime_days()
        color_mapping_status = get_color_mapping_status()

        # User scores
        scores = data_persistence.load_scores()
        current_month = datetime.now(TZ).strftime("%Y-%m")
        monthly_scores = []

        for user, user_scores in scores.items():
            if current_month in user_scores:
                monthly_scores.append({
                    'user': user,
                    'score': user_scores[current_month]
                })

        monthly_scores.sort(key=lambda x: x['score'], reverse=True)

        # Badge statistics
        all_badges = data_persistence.load_all_user_badges()
        total_badges_awarded = sum(len(badges) for badges in all_badges.values())

        return render_template("admin_dashboard_enhanced.html",
                             total_bookings=total_bookings,
                             total_customers=total_customers,
                             recent_activity=recent_activity[:10],  # Last 10 activities
                             app_runtime_days=app_runtime_days,
                             color_mapping_status=color_mapping_status,
                             monthly_scores=monthly_scores[:10],  # Top 10 users
                             total_badges_awarded=total_badges_awarded,
                             current_month=current_month)

    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return redirect(url_for("main.index"))


@admin_bp.route("/insights")
@require_admin
def admin_insights():
    """Admin insights and analytics page"""
    try:
        # Get insights data
        insights_data = {
            "peak_hours": [],
            "popular_days": [],
            "customer_patterns": {},
            "booking_trends": []
        }

        if tracking_system:
            # Get enhanced dashboard with insights
            dashboard_data = tracking_system.get_enhanced_dashboard()
            insights_data.update(dashboard_data.get('insights', {}))

        return render_template("admin_insights.html",
                             insights=insights_data)

    except Exception as e:
        flash(f"Error loading insights: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))