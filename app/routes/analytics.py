# -*- coding: utf-8 -*-
"""
Analytics Blueprint
Business Intelligence Dashboard für Admins
"""

import os
import logging
from flask import Blueprint, render_template, session, jsonify, request
from app.utils.decorators import require_login
from app.utils.helpers import is_admin
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

ALLOWED_DAYS = {28, 90, 180, 365}
DEFAULT_DAYS = 28

# Analytics access from env: comma-separated usernames (beyond admins)
ANALYTICS_ACCESS = [u.strip() for u in os.getenv('ANALYTICS_ACCESS', 'moritz.schimanko').split(',') if u.strip()]


def _get_days() -> int:
    """Read and validate days query parameter."""
    days = request.args.get('days', DEFAULT_DAYS, type=int)
    return days if days in ALLOWED_DAYS else DEFAULT_DAYS


@analytics_bp.before_request
def require_analytics_access():
    """Analytics für Admins und berechtigte User"""
    user = session.get('user')
    if not user:
        from flask import abort
        abort(403)
    if not is_admin(user) and user not in ANALYTICS_ACCESS:
        from flask import abort
        abort(403)


@analytics_bp.route("/")
@require_login
def dashboard():
    """Haupt-Analytics-Dashboard"""
    from app.services.analytics_service import analytics_service

    user = session.get('user')
    days = _get_days()

    # Dashboard-Daten laden
    dashboard_data = analytics_service.get_dashboard_data(days=days)

    return render_template(
        'analytics/dashboard.html',
        user=user,
        days=days,
        **dashboard_data
    )


@analytics_bp.route("/executive")
@require_login
def executive():
    """Executive KPI Dashboard"""
    from app.services.analytics_service import analytics_service

    user = session.get('user')
    days = _get_days()

    # Executive-KPIs laden
    executive_data = analytics_service.get_executive_kpis(days=days)

    return render_template(
        'analytics/executive.html',
        user=user,
        days=days,
        **executive_data
    )


@analytics_bp.route("/team")
@require_login
def team_performance():
    """Team-Performance-Dashboard"""
    from app.services.analytics_service import analytics_service

    user = session.get('user')
    days = _get_days()

    # Team-Performance-Daten laden
    team_data = analytics_service.get_team_performance(days=days)

    return render_template(
        'analytics/team_performance.html',
        user=user,
        days=days,
        **team_data
    )


@analytics_bp.route("/leads")
@require_login
def lead_insights():
    """Lead-Insights & Attribution"""
    from app.services.analytics_service import analytics_service

    user = session.get('user')
    days = _get_days()

    # Lead-Analytics laden
    try:
        lead_data = analytics_service.get_lead_insights(days=days)
    except Exception as e:
        logger.error(f"Lead insights failed: {e}", exc_info=True)
        lead_data = {
            'channel_attribution': [],
            'optimal_booking_times': {},
            'customer_segments': [],
        }

    return render_template(
        'analytics/lead_insights.html',
        user=user,
        days=days,
        **lead_data
    )


@analytics_bp.route("/campaigns")
@require_login
def campaigns():
    """Kampagnen-Performance-Dashboard"""
    from app.services.analytics_service import analytics_service

    user = session.get('user')
    days = _get_days()
    data = analytics_service.get_campaign_analytics(days=days)

    return render_template(
        'analytics/campaigns.html',
        user=user,
        days=days,
        **data
    )


# API Endpoints für AJAX/Charts

@analytics_bp.route("/api/funnel")
@require_login
def api_funnel():
    """Lead-to-Close-Funnel-Daten"""
    from app.services.analytics_service import analytics_service

    days = _get_days()
    funnel_data = analytics_service.get_funnel_data(days=days)
    return jsonify(funnel_data)


@analytics_bp.route("/api/trends/<timeframe>")
@require_login
def api_trends(timeframe):
    """Trend-Daten (week/month/quarter)"""
    from app.services.analytics_service import analytics_service

    trends = analytics_service.get_trends(timeframe)
    return jsonify(trends)


@analytics_bp.route("/api/berater-stats")
@require_login
def api_berater_stats():
    """Berater-Statistiken"""
    from app.services.analytics_service import analytics_service

    days = _get_days()
    stats = analytics_service.get_berater_stats(days=days)
    return jsonify(stats)
