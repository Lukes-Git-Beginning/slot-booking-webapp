# -*- coding: utf-8 -*-
"""Performance dashboard data generation."""

import os
import json
import logging
from datetime import datetime, timedelta

import pytz

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")

# PostgreSQL Models
try:
    from app.models import DailyMetrics, is_postgres_enabled
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


def get_performance_dashboard(tracker):
    """Generiere Dashboard-Daten fuer Visualisierung (PG-First, JSON-Fallback)"""
    # 1. PostgreSQL-First
    if POSTGRES_AVAILABLE and is_postgres_enabled():
        try:
            result = _get_performance_dashboard_pg()
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"PG get_performance_dashboard failed, falling back to JSON: {e}")

    # 2. JSON-Fallback
    return _get_performance_dashboard_json(tracker)


def _get_performance_dashboard_pg():
    """PG: Generiere Dashboard aus DailyMetrics Tabelle"""
    from app.utils.db_utils import db_session_scope_no_commit
    from sqlalchemy import func

    with db_session_scope_no_commit() as session:
        today = datetime.now(TZ).date()

        dashboard = {
            "generated_at": datetime.now(TZ).isoformat(),
            "current_week": {
                "number": datetime.now(TZ).isocalendar()[1],
                "year": datetime.now(TZ).year
            },
            "last_7_days": {"total_bookings": 0, "appearance_rate": 0, "success_rate": 0, "no_show_rate": 0},
            "last_30_days": {"total_bookings": 0, "appearance_rate": 0, "success_rate": 0, "no_show_rate": 0},
            "current_totals": {"total_slots": 0, "total_appeared": 0, "total_not_appeared": 0, "total_cancelled": 0, "appearance_rate": 0, "days_tracked": 0},
            "trends": {},
            "alerts": []
        }

        # Check if we have any DailyMetrics data
        count = session.query(func.count(DailyMetrics.id)).scalar()
        if not count:
            return None

        # Last 7 days
        last_7_start = today - timedelta(days=6)
        rows_7 = session.query(
            func.sum(DailyMetrics.total_slots),
            func.sum(DailyMetrics.completed),
            func.sum(DailyMetrics.no_shows),
            func.sum(DailyMetrics.cancelled)
        ).filter(DailyMetrics.date >= last_7_start, DailyMetrics.date <= today).first()

        if rows_7 and rows_7[0]:
            ts = rows_7[0] or 0
            tc = rows_7[1] or 0
            tns = rows_7[2] or 0
            if ts > 0:
                dashboard["last_7_days"] = {
                    "total_bookings": ts,
                    "appearance_rate": min(100, round((tc / ts) * 100, 2)),
                    "success_rate": min(100, round((tc / ts) * 100, 2)),
                    "no_show_rate": min(100, round((tns / ts) * 100, 2))
                }

        # Since September 2025
        start_date = datetime(2025, 9, 1).date()
        rows_all = session.query(
            func.sum(DailyMetrics.total_slots),
            func.sum(DailyMetrics.completed),
            func.sum(DailyMetrics.no_shows),
            func.sum(DailyMetrics.cancelled),
            func.count(DailyMetrics.id)
        ).filter(DailyMetrics.date >= start_date, DailyMetrics.date <= today).first()

        if rows_all and rows_all[0]:
            ts = rows_all[0] or 0
            tc = rows_all[1] or 0
            tns = rows_all[2] or 0
            tca = rows_all[3] or 0
            days = rows_all[4] or 0
            if ts > 0:
                ar = min(100, round((tc / ts) * 100, 2))
                dashboard["since_september"] = {
                    "total_bookings": ts,
                    "appearance_rate": ar,
                    "success_rate": ar,
                    "no_show_rate": min(100, round((tns / ts) * 100, 2))
                }
                dashboard["current_totals"] = {
                    "total_slots": ts,
                    "total_appeared": tc,
                    "total_not_appeared": tns,
                    "total_cancelled": tca,
                    "appearance_rate": round((tc / ts) * 100, 2),
                    "days_tracked": days
                }

        # Trend: compare last 7 vs previous 7 days
        prev_7_start = today - timedelta(days=13)
        prev_7_end = today - timedelta(days=7)
        rows_prev = session.query(
            func.avg(DailyMetrics.no_show_rate)
        ).filter(
            DailyMetrics.date >= prev_7_start,
            DailyMetrics.date <= prev_7_end,
            DailyMetrics.total_slots > 0
        ).scalar()

        if rows_prev is not None:
            current_nsr = dashboard["last_7_days"].get("no_show_rate", 0)
            prev_nsr = round(rows_prev, 2)
            dashboard["trends"]["no_show_trend"] = {
                "current": current_nsr,
                "previous": prev_nsr,
                "change": round(current_nsr - prev_nsr, 2),
                "direction": "up" if current_nsr > prev_nsr else "down"
            }

        # Alerts
        if dashboard["last_7_days"].get("no_show_rate", 0) > 20:
            dashboard["alerts"].append({
                "type": "warning",
                "message": f"Hohe No-Show Rate: {dashboard['last_7_days']['no_show_rate']}%",
                "severity": "high"
            })

        return dashboard


def _get_performance_dashboard_json(tracker):
    """JSON-Fallback: Generiere Dashboard aus daily_metrics.json"""
    dashboard = {
        "generated_at": datetime.now(TZ).isoformat(),
        "current_week": {
            "number": datetime.now(TZ).isocalendar()[1],
            "year": datetime.now(TZ).year
        },
        "last_7_days": {"total_bookings": 0, "appearance_rate": 0, "success_rate": 0, "no_show_rate": 0},
        "last_30_days": {"total_bookings": 0, "appearance_rate": 0, "success_rate": 0, "no_show_rate": 0},
        "current_totals": {"total_slots": 0, "total_appeared": 0, "total_not_appeared": 0, "total_cancelled": 0, "appearance_rate": 0, "days_tracked": 0},
        "trends": {},
        "alerts": []
    }

    try:
        if os.path.exists(tracker.metrics_file):
            with open(tracker.metrics_file, "r", encoding="utf-8") as f:
                all_metrics = json.load(f)

                today = datetime.now(TZ).date()
                last_7_days_list = [str(today - timedelta(days=i)) for i in range(7)]

                total_slots = 0
                total_no_shows = 0
                total_completed = 0
                total_cancelled = 0

                for date_str in last_7_days_list:
                    if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                        metrics = all_metrics[date_str]
                        total_slots += metrics.get("total_slots", 0)
                        total_no_shows += metrics.get("no_shows", 0)
                        total_completed += metrics.get("completed", 0)
                        total_cancelled += metrics.get("cancelled", 0)

                if total_slots > 0:
                    appearance_rate = min(100, round((total_completed / total_slots) * 100, 2))
                    success_rate = min(100, round((total_completed / total_slots) * 100, 2))
                    no_show_rate = min(100, round((total_no_shows / total_slots) * 100, 2))
                    dashboard["last_7_days"] = {
                        "total_bookings": total_slots,
                        "appearance_rate": appearance_rate,
                        "success_rate": success_rate,
                        "no_show_rate": no_show_rate
                    }

                # Since September 2025
                start_date = datetime(2025, 9, 1).date()
                days_since_start = (today - start_date).days + 1
                date_range = [str(start_date + timedelta(days=i)) for i in range(days_since_start) if start_date + timedelta(days=i) <= today]

                total_slots_30 = 0
                total_no_shows_30 = 0
                total_completed_30 = 0
                total_cancelled_30 = 0

                for date_str in date_range:
                    if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                        metrics = all_metrics[date_str]
                        total_slots_30 += metrics.get("total_slots", 0)
                        total_no_shows_30 += metrics.get("no_shows", 0)
                        total_completed_30 += metrics.get("completed", 0)
                        total_cancelled_30 += metrics.get("cancelled", 0)

                if total_slots_30 > 0:
                    appearance_rate_30 = min(100, round((total_completed_30 / total_slots_30) * 100, 2))
                    success_rate_30 = min(100, round((total_completed_30 / total_slots_30) * 100, 2))
                    no_show_rate_30 = min(100, round((total_no_shows_30 / total_slots_30) * 100, 2))
                    dashboard["since_september"] = {
                        "total_bookings": total_slots_30,
                        "appearance_rate": appearance_rate_30,
                        "success_rate": success_rate_30,
                        "no_show_rate": no_show_rate_30
                    }

                # Current totals
                tracking_start_date = datetime(2025, 9, 1).date()
                all_total_slots = 0
                all_total_completed = 0
                all_total_no_shows = 0
                all_total_cancelled = 0
                days_tracked = 0

                for date_str, metrics in all_metrics.items():
                    try:
                        metric_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        if metric_date >= tracking_start_date and isinstance(metrics, dict) and 'total_slots' in metrics:
                            all_total_slots += metrics.get("total_slots", 0)
                            all_total_completed += metrics.get("completed", 0)
                            all_total_no_shows += metrics.get("no_shows", 0)
                            all_total_cancelled += metrics.get("cancelled", 0)
                            days_tracked += 1
                    except Exception:
                        pass

                if all_total_slots > 0:
                    all_appearance_rate = round((all_total_completed / all_total_slots) * 100, 2)
                    dashboard["current_totals"] = {
                        "total_slots": all_total_slots,
                        "total_appeared": all_total_completed,
                        "total_not_appeared": all_total_no_shows,
                        "total_cancelled": all_total_cancelled,
                        "appearance_rate": all_appearance_rate,
                        "days_tracked": days_tracked
                    }

                # Trend
                if len(all_metrics) >= 14:
                    prev_7_days = [str(today - timedelta(days=i)) for i in range(7, 14)]
                    prev_no_show_rate = 0
                    prev_count = 0
                    for date_str in prev_7_days:
                        if date_str in all_metrics and isinstance(all_metrics[date_str], dict):
                            metrics = all_metrics[date_str]
                            if metrics.get("total_slots", 0) > 0:
                                prev_no_show_rate += metrics.get("no_show_rate", 0)
                                prev_count += 1
                    if prev_count > 0:
                        prev_no_show_rate = prev_no_show_rate / prev_count
                        current_no_show_rate = dashboard["last_7_days"].get("no_show_rate", 0)
                        dashboard["trends"]["no_show_trend"] = {
                            "current": current_no_show_rate,
                            "previous": round(prev_no_show_rate, 2),
                            "change": round(current_no_show_rate - prev_no_show_rate, 2),
                            "direction": "up" if current_no_show_rate > prev_no_show_rate else "down"
                        }

                # Alerts
                if dashboard["last_7_days"].get("no_show_rate", 0) > 20:
                    dashboard["alerts"].append({
                        "type": "warning",
                        "message": f"Hohe No-Show Rate: {dashboard['last_7_days']['no_show_rate']}%",
                        "severity": "high"
                    })

    except Exception as e:
        logger.error(f"Fehler beim Laden der Dashboard-Daten: {e}")

    return dashboard


def get_enhanced_dashboard(tracker):
    """Erweiterte Dashboard-Daten mit historischen Daten"""
    try:
        from app.services.tracking_system.historical import load_historical_data

        # Hole aktuelle Dashboard-Daten
        current_dashboard = get_performance_dashboard(tracker)

        # Lade historische Daten
        historical_data = load_historical_data(tracker)

        # Kombiniere die Daten
        enhanced_dashboard = {
            "current": current_dashboard,
            "historical": historical_data["stats"],
            "combined_insights": _generate_combined_insights(current_dashboard, historical_data)
        }

        return enhanced_dashboard

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des erweiterten Dashboards: {e}")
        return get_performance_dashboard(tracker)


def _generate_combined_insights(current_dashboard, historical_data):
    """Generiert kombinierte Erkenntnisse aus aktuellen und historischen Daten"""
    try:
        insights = {
            "trends": {},
            "comparisons": {},
            "recommendations": []
        }

        # Vergleiche aktuelle vs. historische Quoten
        if historical_data["stats"]:
            hist_stats = historical_data["stats"]

            # Auftauchquote Vergleich (neue Klassifizierung)
            current_appearance = current_dashboard.get("last_30_days", {}).get("appearance_rate", 0) / 100.0
            hist_appearance = hist_stats.get("appearance_rate", 0)

            insights["comparisons"]["appearance_rate"] = {
                "current": current_appearance,
                "historical": hist_appearance,
                "difference": current_appearance - hist_appearance,
                "trend": "improving" if current_appearance > hist_appearance else "declining"
            }

            # Beste Zeiten basierend auf historischen Daten
            best_times = []
            if "by_time" in hist_stats:
                time_stats = hist_stats["by_time"]
                sorted_times = sorted(time_stats.items(),
                                    key=lambda x: x[1]["appearance_rate"],
                                    reverse=True)
                best_times = [time for time, _ in sorted_times[:3]]

            # Beste Wochentage basierend auf historischen Daten
            best_weekdays = []
            if "by_weekday" in hist_stats:
                weekday_stats = hist_stats["by_weekday"]
                sorted_weekdays = sorted(weekday_stats.items(),
                                       key=lambda x: x[1]["appearance_rate"],
                                       reverse=True)
                best_weekdays = [day for day, _ in sorted_weekdays[:3]]

            insights["recommendations"] = [
                f"Beste historische Auftauchquoten nach Uhrzeit: {', '.join(best_times)}",
                f"Beste historische Auftauchquoten nach Wochentag: {', '.join(best_weekdays)}",
                f"Historische Auftauchquote: {hist_appearance:.1%}",
                f"Aktuelle Auftauchquote: {current_appearance:.1%}"
            ]

        return insights

    except Exception as e:
        logger.error(f"Fehler bei der Generierung von Erkenntnissen: {e}")
        return {"trends": {}, "comparisons": {}, "recommendations": []}
