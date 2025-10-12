# -*- coding: utf-8 -*-
"""
Analytics Service
Business Intelligence & Data Aggregation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from app.core.extensions import data_persistence
from app.utils.helpers import get_userlist

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service für Business Intelligence & Analytics"""

    def __init__(self):
        pass

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Haupt-Dashboard-Daten"""
        return {
            'overview': self._get_overview_stats(),
            'recent_activity': self._get_recent_activity(),
            'alerts': self._get_system_alerts()
        }

    def get_executive_kpis(self) -> Dict[str, Any]:
        """Executive-Level KPIs"""
        scores = data_persistence.load_scores()

        # Aktueller Monat
        current_month = datetime.now().strftime('%Y-%m')

        # Total Bookings berechnen
        total_bookings = 0
        for user, months in scores.items():
            if current_month in months:
                total_bookings += months[current_month] // 3  # Durchschnittlich 3 Punkte pro Buchung

        # Conversion-Rate (Mock - später echte Berechnung)
        conversion_rate = 25.5  # %

        # No-Show-Rate (Mock)
        no_show_rate = 12.3  # %

        return {
            'total_bookings': total_bookings,
            'conversion_rate': conversion_rate,
            'no_show_rate': no_show_rate,
            'avg_deal_value': 1850,  # EUR (Mock)
            'revenue_forecast': total_bookings * 1850 * (conversion_rate / 100),
            'active_users': len([u for u, m in scores.items() if current_month in m])
        }

    def get_team_performance(self) -> Dict[str, Any]:
        """Team-Performance-Daten"""
        scores = data_persistence.load_scores()
        current_month = datetime.now().strftime('%Y-%m')

        # Berater-Rankings
        berater_stats = []
        for user, months in scores.items():
            month_points = months.get(current_month, 0)
            berater_stats.append({
                'name': user,
                'points': month_points,
                'bookings': month_points // 3,  # Approx
                'conversion_rate': 20 + (month_points % 15),  # Mock variabel
                'avg_deal_value': 1500 + (month_points % 1000)  # Mock variabel
            })

        # Sortieren nach Punkten
        berater_stats.sort(key=lambda x: x['points'], reverse=True)

        return {
            'berater_rankings': berater_stats,
            'top_performer': berater_stats[0] if berater_stats else None,
            'team_avg_conversion': sum(b['conversion_rate'] for b in berater_stats) / len(berater_stats) if berater_stats else 0
        }

    def get_lead_insights(self) -> Dict[str, Any]:
        """Lead-Analytics & Attribution"""
        return {
            'channel_attribution': self._get_channel_attribution(),
            'optimal_booking_times': self._get_optimal_booking_times(),
            'customer_segments': self._get_customer_segments()
        }

    def get_funnel_data(self) -> Dict[str, Any]:
        """Lead-to-Close-Funnel"""
        scores = data_persistence.load_scores()
        current_month = datetime.now().strftime('%Y-%m')

        # Funnel-Berechnung (Mock mit realen Zahlen als Basis)
        total_leads = 450  # Mock
        total_bookings = sum(months.get(current_month, 0) // 3 for user, months in scores.items())
        total_showed = int(total_bookings * 0.85)  # 85% Show-Rate
        total_closed = int(total_showed * 0.28)  # 28% Conversion

        return {
            'stages': [
                {'name': 'Leads', 'count': total_leads, 'percentage': 100},
                {'name': 'Buchungen', 'count': total_bookings, 'percentage': round(total_bookings/total_leads*100, 1)},
                {'name': 'Erschienen', 'count': total_showed, 'percentage': round(total_showed/total_leads*100, 1)},
                {'name': 'Abgeschlossen', 'count': total_closed, 'percentage': round(total_closed/total_leads*100, 1)}
            ],
            'conversion_rate': round(total_closed/total_leads*100, 1)
        }

    def get_trends(self, timeframe: str = 'month') -> Dict[str, Any]:
        """Trend-Daten"""
        scores = data_persistence.load_scores()

        # Zeitraum berechnen
        if timeframe == 'week':
            days = 7
        elif timeframe == 'quarter':
            days = 90
        else:  # month
            days = 30

        # Trend-Daten generieren
        trend_data = []
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i-1)
            # Mock-Daten basierend auf realen Scores
            bookings = sum(1 for u, m in scores.items() if date.strftime('%Y-%m') in m) + (i % 5)
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'bookings': bookings,
                'conversions': int(bookings * 0.25),
                'revenue': bookings * 1850 * 0.25
            })

        return {'data': trend_data}

    def get_berater_stats(self) -> Dict[str, List]:
        """Berater-Statistiken für Charts"""
        scores = data_persistence.load_scores()
        current_month = datetime.now().strftime('%Y-%m')

        berater_data = []
        for user, months in scores.items():
            month_points = months.get(current_month, 0)
            berater_data.append({
                'name': user,
                'bookings': month_points // 3,
                'conversion_rate': 20 + (month_points % 15),
                'revenue': (month_points // 3) * 1850 * 0.25
            })

        return {'berater': berater_data}

    # === Private Helper Methods ===

    def _get_overview_stats(self) -> Dict[str, Any]:
        """Übersichts-Statistiken"""
        scores = data_persistence.load_scores()
        current_month = datetime.now().strftime('%Y-%m')

        total_bookings = sum(months.get(current_month, 0) // 3 for user, months in scores.items())

        return {
            'total_bookings_month': total_bookings,
            'total_users': len(scores),
            'avg_bookings_per_user': total_bookings / len(scores) if scores else 0,
            'growth_rate': 15.3  # % Mock
        }

    def _get_recent_activity(self) -> List[Dict]:
        """Letzte Aktivitäten"""
        # Aus Audit-Log holen
        try:
            from app.services.audit_service import audit_service
            return audit_service.get_recent_events(limit=10)
        except:
            return []

    def _get_system_alerts(self) -> List[Dict]:
        """System-Warnungen"""
        alerts = []

        # Check No-Show-Rate
        # TODO: Echte Berechnung

        # Check Performance
        scores = data_persistence.load_scores()
        if len(scores) < 5:
            alerts.append({
                'type': 'info',
                'message': 'Weniger als 5 aktive Berater',
                'severity': 'low'
            })

        return alerts

    def _get_channel_attribution(self) -> List[Dict]:
        """Marketing-Channel-Attribution (Mock)"""
        return [
            {'channel': 'Google Ads', 'leads': 180, 'conversion_rate': 28.5, 'cost_per_lead': 45},
            {'channel': 'Facebook', 'leads': 120, 'conversion_rate': 22.3, 'cost_per_lead': 38},
            {'channel': 'Referral', 'leads': 95, 'conversion_rate': 35.2, 'cost_per_lead': 12},
            {'channel': 'Organic', 'leads': 55, 'conversion_rate': 18.7, 'cost_per_lead': 0}
        ]

    def _get_optimal_booking_times(self) -> Dict[str, int]:
        """Optimale Buchungszeiten (Heatmap-Daten)"""
        # Mock-Daten - später echte Analyse
        return {
            'Monday_09': 45, 'Monday_11': 32, 'Monday_14': 28, 'Monday_16': 38, 'Monday_18': 52, 'Monday_20': 48,
            'Tuesday_09': 50, 'Tuesday_11': 38, 'Tuesday_14': 35, 'Tuesday_16': 42, 'Tuesday_18': 58, 'Tuesday_20': 55,
            'Wednesday_09': 48, 'Wednesday_11': 35, 'Wednesday_14': 30, 'Wednesday_16': 40, 'Wednesday_18': 55, 'Wednesday_20': 50,
            'Thursday_09': 52, 'Thursday_11': 40, 'Thursday_14': 38, 'Thursday_16': 45, 'Thursday_18': 60, 'Thursday_20': 58,
            'Friday_09': 42, 'Friday_11': 30, 'Friday_14': 25, 'Friday_16': 35, 'Friday_18': 48, 'Friday_20': 45,
        }

    def _get_customer_segments(self) -> List[Dict]:
        """Kunden-Segmente (Mock)"""
        return [
            {'segment': 'Familie', 'count': 185, 'avg_value': 2100, 'conversion': 32.5},
            {'segment': 'Selbständige', 'count': 142, 'avg_value': 2800, 'conversion': 28.3},
            {'segment': 'Angestellte', 'count': 95, 'avg_value': 1600, 'conversion': 22.1},
            {'segment': 'Rentner', 'count': 28, 'avg_value': 1200, 'conversion': 18.5}
        ]


# Global instance
analytics_service = AnalyticsService()
