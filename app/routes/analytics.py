# -*- coding: utf-8 -*-
"""
Analytics Blueprint
Business Intelligence Dashboard für Admins
"""

from flask import Blueprint, render_template, session, jsonify
from app.utils.decorators import require_login
from app.utils.helpers import is_admin
from datetime import datetime, timedelta

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.before_request
def require_admin():
    """Analytics nur für Admins"""
    user = session.get('user')
    if not user or not is_admin(user):
        from flask import abort
        abort(403)


@analytics_bp.route("/")
@require_login
def dashboard():
    """Haupt-Analytics-Dashboard"""
    from app.services.analytics_service import analytics_service

    user = session.get('user')

    # Dashboard-Daten laden
    dashboard_data = analytics_service.get_dashboard_data()

    return render_template(
        'analytics/dashboard.html',
        user=user,
        **dashboard_data
    )


@analytics_bp.route("/executive")
@require_login
def executive():
    """Executive KPI Dashboard"""
    from app.services.analytics_service import analytics_service

    user = session.get('user')

    # Executive-KPIs laden
    executive_data = analytics_service.get_executive_kpis()

    return render_template(
        'analytics/executive.html',
        user=user,
        **executive_data
    )


@analytics_bp.route("/team")
@require_login
def team_performance():
    """Team-Performance-Dashboard"""
    from app.services.analytics_service import analytics_service

    user = session.get('user')

    # Team-Performance-Daten laden
    team_data = analytics_service.get_team_performance()

    return render_template(
        'analytics/team_performance.html',
        user=user,
        **team_data
    )


@analytics_bp.route("/leads")
@require_login
def lead_insights():
    """Lead-Insights & Attribution"""
    from app.services.analytics_service import analytics_service

    user = session.get('user')

    # Lead-Analytics laden
    lead_data = analytics_service.get_lead_insights()

    return render_template(
        'analytics/lead_insights.html',
        user=user,
        **lead_data
    )


# API Endpoints für AJAX/Charts

@analytics_bp.route("/api/funnel")
@require_login
def api_funnel():
    """Lead-to-Close-Funnel-Daten"""
    from app.services.analytics_service import analytics_service

    funnel_data = analytics_service.get_funnel_data()
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

    stats = analytics_service.get_berater_stats()
    return jsonify(stats)
