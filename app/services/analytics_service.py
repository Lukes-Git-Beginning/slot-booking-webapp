# -*- coding: utf-8 -*-
"""
Analytics Service
Business Intelligence & Data Aggregation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from sqlalchemy import func, extract
from app.core.extensions import data_persistence
from app.utils.helpers import get_userlist

logger = logging.getLogger(__name__)


# Helper function for database access
def _get_db_session():
    """Get database session from Flask app context"""
    try:
        from app import db
        return db.session
    except Exception as e:
        logger.debug(f"Could not get database session: {e}")
        return None


# Helper function to get Booking models
def _get_booking_models():
    """Get Booking models (returns None if not available)"""
    try:
        from app.models.booking import Booking, BookingOutcome
        return Booking, BookingOutcome
    except Exception as e:
        logger.debug(f"Could not import Booking models: {e}")
        return None, None


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
        """Executive-Level KPIs with real PostgreSQL calculations"""
        scores = data_persistence.load_scores()
        current_month = datetime.now().strftime('%Y-%m')

        # Load real booking data from PostgreSQL
        try:
            from app.models.booking import Booking, BookingOutcome
            db_session = _get_db_session()

            if db_session:
                # Total Bookings (current month)
                month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                total_bookings = db_session.query(Booking).filter(
                    Booking.date >= month_start
                ).count()

                # Conversion-Rate (appeared / total)
                appeared = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= month_start,
                    BookingOutcome.outcome.in_(['completed'])
                ).count()

                conversion_rate = (appeared / total_bookings * 100) if total_bookings > 0 else 0

                # No-Show-Rate
                no_shows = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= month_start,
                    BookingOutcome.outcome == 'no_show'
                ).count()

                no_show_rate = (no_shows / total_bookings * 100) if total_bookings > 0 else 0

                # Avg Deal Value - Mock (no sales data available)
                avg_deal_value = 1850  # EUR

            else:
                # Fallback to scores calculation
                total_bookings = sum(months.get(current_month, 0) // 3 for user, months in scores.items())
                conversion_rate = 25.5  # Mock
                no_show_rate = 12.3  # Mock
                avg_deal_value = 1850  # Mock

        except Exception as e:
            logger.error(f"Error calculating executive KPIs: {e}")
            # Fallback
            total_bookings = sum(months.get(current_month, 0) // 3 for user, months in scores.items())
            conversion_rate = 25.5
            no_show_rate = 12.3
            avg_deal_value = 1850

        return {
            'total_bookings': total_bookings,
            'conversion_rate': round(conversion_rate, 1),
            'no_show_rate': round(no_show_rate, 1),
            'avg_deal_value': avg_deal_value,  # Mock (no sales data)
            'revenue_forecast': total_bookings * avg_deal_value * (conversion_rate / 100),
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
        """Berater-Statistiken für Charts mit echten PostgreSQL-Daten"""
        db = _get_db_session()
        Booking, BookingOutcome = _get_booking_models()

        # Fallback to scores if PostgreSQL not available
        if not db or not Booking:
            logger.warning("PostgreSQL not available, using scores fallback for berater stats")
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

        # Real PostgreSQL queries
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get bookings per user for current month
        bookings_by_user = db.query(
            Booking.username,
            func.count(Booking.id).label('booking_count')
        ).filter(
            Booking.date >= month_start
        ).group_by(Booking.username).all()

        berater_data = []
        for username, booking_count in bookings_by_user:
            # Calculate conversion rate from outcomes if available
            if BookingOutcome:
                completed_count = db.query(func.count(BookingOutcome.id)).filter(
                    BookingOutcome.date >= month_start,
                    BookingOutcome.outcome == 'completed',
                    extract('month', BookingOutcome.date) == now.month
                ).scalar() or 0

                total_outcomes = db.query(func.count(BookingOutcome.id)).filter(
                    BookingOutcome.date >= month_start,
                    extract('month', BookingOutcome.date) == now.month
                ).scalar() or 1

                conversion_rate = round((completed_count / total_outcomes) * 100, 1) if total_outcomes > 0 else 0
            else:
                # Fallback: estimate 70-85% conversion
                conversion_rate = 75.0

            berater_data.append({
                'name': username,
                'bookings': booking_count,
                'conversion_rate': conversion_rate,
                'revenue': booking_count * 1850 * 0.25  # Estimated revenue per booking
            })

        # Sort by bookings descending
        berater_data.sort(key=lambda x: x['bookings'], reverse=True)

        return {'berater': berater_data}

    # === Private Helper Methods ===

    def _get_overview_stats(self) -> Dict[str, Any]:
        """Übersichts-Statistiken with real PostgreSQL data"""
        db = _get_db_session()
        Booking, _ = _get_booking_models()

        # Fallback to scores if PostgreSQL not available
        if not db or not Booking:
            logger.warning("PostgreSQL not available, using scores fallback")
            scores = data_persistence.load_scores()
            current_month = datetime.now().strftime('%Y-%m')
            total_bookings = sum(months.get(current_month, 0) // 3 for user, months in scores.items())
            prev_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m')
            prev_bookings = sum(months.get(prev_month, 0) // 3 for user, months in scores.items())
            growth_rate = ((total_bookings - prev_bookings) / prev_bookings) * 100 if prev_bookings > 0 else 0.0
            return {
                'total_bookings_month': total_bookings,
                'total_users': len(scores),
                'avg_bookings_per_user': total_bookings / len(scores) if scores else 0,
                'growth_rate': round(growth_rate, 1)
            }

        # Real PostgreSQL queries
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # Current month bookings
        total_bookings = db.query(func.count(Booking.id)).filter(
            Booking.date >= month_start
        ).scalar() or 0

        # Previous month bookings
        prev_bookings = db.query(func.count(Booking.id)).filter(
            Booking.date >= prev_month_start,
            Booking.date < month_start
        ).scalar() or 0

        # Unique users who booked this month
        total_users = db.query(func.count(func.distinct(Booking.username))).filter(
            Booking.date >= month_start
        ).scalar() or 1  # Avoid division by zero

        # Calculate real growth rate
        if prev_bookings > 0:
            growth_rate = ((total_bookings - prev_bookings) / prev_bookings) * 100
        else:
            growth_rate = 0.0

        return {
            'total_bookings_month': total_bookings,
            'total_users': total_users,
            'avg_bookings_per_user': round(total_bookings / total_users, 1) if total_users > 0 else 0,
            'growth_rate': round(growth_rate, 1)
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
        """System-Warnungen with real no-show calculation"""
        alerts = []

        # Check No-Show-Rate (REAL CALCULATION from PostgreSQL)
        try:
            from app.models.booking import Booking, BookingOutcome
            db_session = _get_db_session()

            if db_session:
                # Last month
                one_month_ago = datetime.now() - timedelta(days=30)

                # Count total bookings
                total_bookings = db_session.query(Booking).filter(
                    Booking.date >= one_month_ago
                ).count()

                # Count no-shows
                no_shows = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= one_month_ago,
                    BookingOutcome.outcome == 'no_show'
                ).count()

                if total_bookings > 0:
                    no_show_rate = (no_shows / total_bookings) * 100

                    # Alert if no-show rate > 15%
                    if no_show_rate > 15:
                        alerts.append({
                            'type': 'warning',
                            'message': f'Hohe No-Show-Rate: {no_show_rate:.1f}% ({no_shows}/{total_bookings})',
                            'severity': 'high' if no_show_rate > 20 else 'medium'
                        })
        except Exception as e:
            logger.warning(f"Could not calculate no-show rate: {e}")

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
        """Marketing-Channel-Attribution (Demo data - no data source)"""
        # NOTE: This remains as demo data - no marketing channel data available in system
        return [
            {'channel': 'Google Ads', 'leads': 180, 'conversion_rate': 28.5, 'cost_per_lead': 45},
            {'channel': 'Facebook', 'leads': 120, 'conversion_rate': 22.3, 'cost_per_lead': 38},
            {'channel': 'Referral', 'leads': 95, 'conversion_rate': 35.2, 'cost_per_lead': 12},
            {'channel': 'Organic', 'leads': 55, 'conversion_rate': 18.7, 'cost_per_lead': 0}
        ]

    def _get_optimal_booking_times(self) -> Dict[str, int]:
        """Optimale Buchungszeiten from real booking data"""
        try:
            from app.models.booking import Booking
            db_session = _get_db_session()

            if db_session:
                # Last 3 months
                three_months_ago = datetime.now() - timedelta(days=90)

                # Load all bookings
                bookings = db_session.query(Booking).filter(
                    Booking.date >= three_months_ago
                ).all()

                # Count bookings per weekday + time slot
                heatmap = {}
                weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                hours = ['09', '11', '14', '16', '18', '20']

                # Initialize all slots with 0
                for day in weekdays:
                    for hour in hours:
                        heatmap[f"{day}_{hour}"] = 0

                # Count real bookings
                for booking in bookings:
                    weekday = weekdays[booking.date.weekday()] if booking.date.weekday() < 5 else None
                    hour = booking.time[:2] if booking.time else None

                    if weekday and hour:
                        key = f"{weekday}_{hour}"
                        if key in heatmap:
                            heatmap[key] += 1

                return heatmap
        except Exception as e:
            logger.warning(f"Could not calculate optimal booking times: {e}")

        # Fallback to mock data
        return {
            'Monday_09': 45, 'Monday_11': 32, 'Monday_14': 28, 'Monday_16': 38, 'Monday_18': 52, 'Monday_20': 48,
            'Tuesday_09': 50, 'Tuesday_11': 38, 'Tuesday_14': 35, 'Tuesday_16': 42, 'Tuesday_18': 58, 'Tuesday_20': 55,
            'Wednesday_09': 48, 'Wednesday_11': 35, 'Wednesday_14': 30, 'Wednesday_16': 40, 'Wednesday_18': 55, 'Wednesday_20': 50,
            'Thursday_09': 52, 'Thursday_11': 40, 'Thursday_14': 38, 'Thursday_16': 45, 'Thursday_18': 60, 'Thursday_20': 58,
            'Friday_09': 42, 'Friday_11': 30, 'Friday_14': 25, 'Friday_16': 35, 'Friday_18': 48, 'Friday_20': 45,
        }

    def _get_customer_segments(self) -> List[Dict]:
        """Kunden-Segmente (Demo data - no data source)"""
        # NOTE: This remains as demo data - no customer segmentation data available
        return [
            {'segment': 'Familie', 'count': 185, 'avg_value': 2100, 'conversion': 32.5},
            {'segment': 'Selbständige', 'count': 142, 'avg_value': 2800, 'conversion': 28.3},
            {'segment': 'Angestellte', 'count': 95, 'avg_value': 1600, 'conversion': 22.1},
            {'segment': 'Rentner', 'count': 28, 'avg_value': 1200, 'conversion': 18.5}
        ]


# Global instance
analytics_service = AnalyticsService()
