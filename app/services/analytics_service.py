# -*- coding: utf-8 -*-
"""
Analytics Service
Business Intelligence & Data Aggregation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
from sqlalchemy import func, extract
from app.core.extensions import data_persistence
from app.utils.helpers import get_userlist

logger = logging.getLogger(__name__)

DEFAULT_DAYS = 28


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


def _start_date(days: int) -> datetime:
    """Calculate start date from days parameter."""
    return datetime.now() - timedelta(days=days)


def _months_in_range(days: int) -> List[str]:
    """Return list of YYYY-MM strings covered by the days range."""
    months = set()
    now = datetime.now()
    for d in range(days + 1):
        dt = now - timedelta(days=d)
        months.add(dt.strftime('%Y-%m'))
    return sorted(months)


class AnalyticsService:
    """Service für Business Intelligence & Analytics"""

    def __init__(self):
        pass

    def get_dashboard_data(self, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
        """Haupt-Dashboard-Daten"""
        return {
            'overview': self._get_overview_stats(days),
            'recent_activity': self._get_recent_activity(),
            'alerts': self._get_system_alerts(days)
        }

    def get_executive_kpis(self, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
        """Executive-Level KPIs with real PostgreSQL calculations"""
        scores = data_persistence.load_scores()
        months = _months_in_range(days)
        start = _start_date(days)

        # Load real booking data from PostgreSQL
        try:
            from app.models.booking import Booking, BookingOutcome
            db_session = _get_db_session()

            if db_session:
                total_bookings = db_session.query(Booking).filter(
                    Booking.date >= start
                ).count()

                # Conversion-Rate (appeared / total)
                appeared = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= start,
                    BookingOutcome.outcome.in_(['completed'])
                ).count()

                conversion_rate = (appeared / total_bookings * 100) if total_bookings > 0 else 0

                # No-Show-Rate
                no_shows = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= start,
                    BookingOutcome.outcome == 'no_show'
                ).count()

                no_show_rate = (no_shows / total_bookings * 100) if total_bookings > 0 else 0

                # Avg Deal Value - HubSpot only, None if unavailable
                avg_deal_value = self._get_hubspot_avg_deal_value()

            else:
                # No PostgreSQL: only show what we can calculate
                total_bookings = sum(
                    sum(m_data.get(m, 0) for m in months) // 3
                    for user, m_data in scores.items()
                )
                conversion_rate = None
                no_show_rate = None
                avg_deal_value = self._get_hubspot_avg_deal_value()

        except Exception as e:
            logger.error(f"Error calculating executive KPIs: {e}")
            total_bookings = sum(
                sum(m_data.get(m, 0) for m in months) // 3
                for user, m_data in scores.items()
            )
            conversion_rate = None
            no_show_rate = None
            avg_deal_value = self._get_hubspot_avg_deal_value()

        # Calculate revenue forecast only if all data available
        if conversion_rate is not None and avg_deal_value is not None:
            revenue_forecast = total_bookings * avg_deal_value * (conversion_rate / 100)
        else:
            revenue_forecast = None

        # Active users: users with points in any month of the range
        active_users = len([
            u for u, m_data in scores.items()
            if any(m_data.get(m, 0) > 0 for m in months)
        ])

        return {
            'total_bookings': total_bookings,
            'conversion_rate': round(conversion_rate, 1) if conversion_rate is not None else None,
            'no_show_rate': round(no_show_rate, 1) if no_show_rate is not None else None,
            'avg_deal_value': avg_deal_value,
            'revenue_forecast': revenue_forecast,
            'active_users': active_users
        }

    def get_team_performance(self, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
        """Team-Performance-Daten"""
        scores = data_persistence.load_scores()
        months = _months_in_range(days)

        # Berater-Rankings
        # HubSpot conversion rates (cached, single call)
        hs_conversion = self._get_hubspot_conversion_rates()
        hs_avg_value = self._get_hubspot_avg_deal_value()

        berater_stats = []
        for user, m_data in scores.items():
            period_points = sum(m_data.get(m, 0) for m in months)

            # Per-berater HubSpot conversion rate, None if unavailable
            if hs_conversion and user in hs_conversion:
                conv_rate = hs_conversion[user]
            else:
                conv_rate = None

            berater_stats.append({
                'name': user,
                'points': period_points,
                'bookings': period_points // 3,  # Approx
                'conversion_rate': conv_rate,
                'avg_deal_value': hs_avg_value,
            })

        # Sortieren nach Punkten
        berater_stats.sort(key=lambda x: x['points'], reverse=True)

        return {
            'berater_rankings': berater_stats,
            'top_performer': berater_stats[0] if berater_stats else None,
            'team_avg_conversion': (
                round(sum(b['conversion_rate'] for b in berater_stats if b['conversion_rate'] is not None) /
                      len([b for b in berater_stats if b['conversion_rate'] is not None]), 1)
                if any(b['conversion_rate'] is not None for b in berater_stats) else None
            )
        }

    def get_lead_insights(self, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
        """Lead-Analytics & Attribution"""
        try:
            channel = self._get_hubspot_channel_attribution() or self._get_channel_attribution()
        except Exception as e:
            logger.warning(f"Channel attribution failed: {e}")
            channel = self._get_channel_attribution()

        try:
            booking_times = self._get_optimal_booking_times(days)
        except Exception as e:
            logger.warning(f"Optimal booking times failed: {e}")
            booking_times = {}

        try:
            segments = self._get_hubspot_customer_segments() or self._get_customer_segments()
        except Exception as e:
            logger.warning(f"Customer segments failed: {e}")
            segments = self._get_customer_segments()

        return {
            'channel_attribution': channel,
            'optimal_booking_times': booking_times if booking_times is not None else {},
            'customer_segments': segments,
        }

    def get_funnel_data(self, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
        """Lead-to-Close-Funnel with real data only"""
        scores = data_persistence.load_scores()
        months = _months_in_range(days)
        start = _start_date(days)

        total_leads = self._get_hubspot_total_deals()
        total_bookings = sum(
            sum(m_data.get(m, 0) for m in months) // 3
            for user, m_data in scores.items()
        )

        # Get real show/close counts from PostgreSQL
        total_showed = None
        total_closed = None
        try:
            from app.models.booking import BookingOutcome
            db_session = _get_db_session()
            if db_session:
                total_showed = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= start,
                    BookingOutcome.outcome.in_(['completed', 'no_show'])
                ).count()
                total_closed = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= start,
                    BookingOutcome.outcome == 'completed'
                ).count()
        except Exception as e:
            logger.warning(f"Could not get funnel outcomes: {e}")

        # Build funnel stages with available data
        stages = [
            {'name': 'Buchungen', 'count': total_bookings, 'percentage': 100},
        ]
        if total_showed is not None:
            stages.append({
                'name': 'Erschienen',
                'count': total_showed,
                'percentage': round(total_showed / total_bookings * 100, 1) if total_bookings > 0 else 0
            })
        if total_closed is not None:
            stages.append({
                'name': 'Abgeschlossen',
                'count': total_closed,
                'percentage': round(total_closed / total_bookings * 100, 1) if total_bookings > 0 else 0
            })

        # Prepend leads if HubSpot data available
        if total_leads is not None:
            stages.insert(0, {'name': 'Leads', 'count': total_leads, 'percentage': 100})
            # Recalculate percentages relative to leads
            for stage in stages[1:]:
                stage['percentage'] = round(stage['count'] / total_leads * 100, 1) if total_leads > 0 else 0

        return {
            'stages': stages,
            'conversion_rate': round(total_closed / total_bookings * 100, 1) if total_closed is not None and total_bookings > 0 else None
        }

    def get_trends(self, timeframe: str = 'month') -> Dict[str, Any]:
        """Trend-Daten from real PostgreSQL booking data"""
        # Zeitraum berechnen
        if timeframe == 'week':
            days = 7
        elif timeframe == 'quarter':
            days = 90
        else:  # month
            days = 30

        trend_data = []

        try:
            from app.models.booking import Booking
            db_session = _get_db_session()

            if db_session:
                start_date = datetime.now() - timedelta(days=days)
                bookings = db_session.query(Booking).filter(
                    Booking.date >= start_date
                ).all()

                # Group by date
                by_date = defaultdict(int)
                for b in bookings:
                    by_date[b.date.strftime('%Y-%m-%d')] += 1

                for i in range(days):
                    date = datetime.now() - timedelta(days=days-i-1)
                    date_str = date.strftime('%Y-%m-%d')
                    trend_data.append({
                        'date': date_str,
                        'bookings': by_date.get(date_str, 0),
                    })

                return {'data': trend_data}
        except Exception as e:
            logger.warning(f"Could not get trend data from PostgreSQL: {e}")

        # Fallback: empty trend data
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i-1)
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'bookings': 0,
            })

        return {'data': trend_data}

    def get_berater_stats(self, days: int = DEFAULT_DAYS) -> Dict[str, List]:
        """Berater-Statistiken für Charts mit echten PostgreSQL-Daten"""
        db = _get_db_session()
        Booking, BookingOutcome = _get_booking_models()
        start = _start_date(days)

        # Fallback to scores if PostgreSQL not available
        if not db or not Booking:
            logger.warning("PostgreSQL not available, using scores fallback for berater stats")
            scores = data_persistence.load_scores()
            months = _months_in_range(days)
            berater_data = []
            for user, m_data in scores.items():
                period_points = sum(m_data.get(m, 0) for m in months)
                berater_data.append({
                    'name': user,
                    'bookings': period_points // 3,
                    'conversion_rate': None,
                    'revenue': None
                })
            return {'berater': berater_data}

        # Real PostgreSQL queries
        bookings_by_user = db.query(
            Booking.username,
            func.count(Booking.id).label('booking_count')
        ).filter(
            Booking.date >= start
        ).group_by(Booking.username).all()

        berater_data = []
        for username, booking_count in bookings_by_user:
            # Calculate conversion rate from outcomes per consultant
            if BookingOutcome:
                completed_count = db.query(func.count(BookingOutcome.id)).filter(
                    BookingOutcome.date >= start,
                    BookingOutcome.outcome == 'completed',
                    BookingOutcome.consultant == username
                ).scalar() or 0

                total_outcomes = db.query(func.count(BookingOutcome.id)).filter(
                    BookingOutcome.date >= start,
                    BookingOutcome.consultant == username
                ).scalar() or 1

                conversion_rate = round((completed_count / total_outcomes) * 100, 1) if total_outcomes > 0 else 0
            else:
                conversion_rate = 75.0

            berater_data.append({
                'name': username,
                'bookings': booking_count,
                'conversion_rate': conversion_rate,
                'revenue': None
            })

        # Sort by bookings descending
        berater_data.sort(key=lambda x: x['bookings'], reverse=True)

        return {'berater': berater_data}

    def get_campaign_analytics(self, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
        """Kampagnen-Analytics: HubSpot-Kampagnendaten + interne Booking-Outcomes.

        Returns:
            Dict mit campaigns, summary, period_days
        """
        hs = self._get_hubspot_service()
        campaigns = []

        if hs:
            try:
                campaigns = hs.get_campaign_stats(days=days) or []
                logger.info(f"Campaign analytics: {len(campaigns)} campaigns loaded from HubSpot")
            except Exception as e:
                logger.warning(f"HubSpot campaign stats unavailable: {e}")
        else:
            logger.info("Campaign analytics: HubSpot service not available")

        # Cross-reference with internal booking outcomes for show rates
        try:
            from app.models.booking import BookingOutcome
            db_session = _get_db_session()

            if db_session and campaigns:
                start = _start_date(days)
                total_outcomes = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= start,
                ).count() or 1

                completed = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= start,
                    BookingOutcome.outcome == 'completed',
                ).count()

                overall_show_rate = round((completed / total_outcomes) * 100, 1) if total_outcomes > 0 else 0
            else:
                overall_show_rate = None
        except Exception:
            overall_show_rate = None

        # Summary
        total_deals = sum(c.get('deals', 0) for c in campaigns)
        total_revenue = sum(c.get('revenue', 0) for c in campaigns)

        return {
            'campaigns': campaigns,
            'period_days': days,
            'summary': {
                'total_campaigns': len(campaigns),
                'total_deals': total_deals,
                'total_revenue': round(total_revenue, 2),
                'avg_deal_value': round(total_revenue / total_deals, 2) if total_deals > 0 else 0,
                'overall_show_rate': overall_show_rate,
            }
        }

    # === HubSpot Integration Helpers ===

    def _get_hubspot_service(self):
        """Get HubSpot service instance (lazy import)."""
        try:
            from app.services.hubspot_service import hubspot_service
            return hubspot_service
        except Exception:
            return None

    def _get_hubspot_avg_deal_value(self) -> Optional[float]:
        hs = self._get_hubspot_service()
        if hs:
            try:
                return hs.get_avg_deal_value()
            except Exception as e:
                logger.debug(f"HubSpot avg deal value unavailable: {e}")
        return None

    def _get_hubspot_total_deals(self) -> Optional[int]:
        hs = self._get_hubspot_service()
        if hs:
            try:
                return hs.get_total_deals_count()
            except Exception as e:
                logger.debug(f"HubSpot total deals unavailable: {e}")
        return None

    def _get_hubspot_conversion_rates(self) -> Optional[Dict[str, float]]:
        """Per-user conversion rates from HubSpot owner data.

        Maps HubSpot owner full names (e.g. 'Tanja Brinster') to internal
        usernames (e.g. 'Tanja') by matching first names case-insensitively.
        """
        hs = self._get_hubspot_service()
        if not hs:
            return None
        try:
            owner_rates = hs.get_per_owner_conversion()
            if not owner_rates:
                return None

            # Map owner full names to internal usernames
            userlist = get_userlist()
            username_rates = {}
            for owner_name, rate in owner_rates.items():
                # Try exact username match first
                if owner_name in userlist:
                    username_rates[owner_name] = rate
                    continue
                # Match by first name (case-insensitive)
                first_name = owner_name.split()[0] if owner_name else ''
                for username in userlist:
                    if username.lower() == first_name.lower():
                        username_rates[username] = rate
                        break

            return username_rates if username_rates else None
        except Exception as e:
            logger.debug(f"HubSpot conversion rates unavailable: {e}")
        return None

    def _get_hubspot_channel_attribution(self) -> Optional[List[Dict]]:
        hs = self._get_hubspot_service()
        if hs:
            try:
                return hs.get_lead_source_attribution()
            except Exception as e:
                logger.debug(f"HubSpot channel attribution unavailable: {e}")
        return None

    def _get_hubspot_customer_segments(self) -> Optional[List[Dict]]:
        hs = self._get_hubspot_service()
        if hs:
            try:
                return hs.get_customer_segments()
            except Exception as e:
                logger.debug(f"HubSpot customer segments unavailable: {e}")
        return None

    # === Private Helper Methods ===

    def _get_overview_stats(self, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
        """Übersichts-Statistiken with real PostgreSQL data"""
        db = _get_db_session()
        Booking, _ = _get_booking_models()
        start = _start_date(days)

        # Fallback to scores if PostgreSQL not available
        if not db or not Booking:
            logger.warning("PostgreSQL not available, using scores fallback")
            scores = data_persistence.load_scores()
            months = _months_in_range(days)
            total_bookings = sum(
                sum(m_data.get(m, 0) for m in months) // 3
                for user, m_data in scores.items()
            )
            # Compare against previous period of same length
            prev_start = start - timedelta(days=days)
            prev_months = set()
            for d in range(days):
                dt = prev_start + timedelta(days=d)
                prev_months.add(dt.strftime('%Y-%m'))
            prev_bookings = sum(
                sum(m_data.get(m, 0) for m in prev_months) // 3
                for user, m_data in scores.items()
            )
            growth_rate = ((total_bookings - prev_bookings) / prev_bookings) * 100 if prev_bookings > 0 else 0.0
            return {
                'total_bookings_month': total_bookings,
                'total_users': len(scores),
                'avg_bookings_per_user': total_bookings / len(scores) if scores else 0,
                'growth_rate': round(growth_rate, 1)
            }

        # Real PostgreSQL queries
        prev_start = start - timedelta(days=days)

        # Current period bookings
        total_bookings = db.query(func.count(Booking.id)).filter(
            Booking.date >= start
        ).scalar() or 0

        # Previous period bookings
        prev_bookings = db.query(func.count(Booking.id)).filter(
            Booking.date >= prev_start,
            Booking.date < start
        ).scalar() or 0

        # Unique users who booked in period
        total_users = db.query(func.count(func.distinct(Booking.username))).filter(
            Booking.date >= start
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

    def _get_system_alerts(self, days: int = DEFAULT_DAYS) -> List[Dict]:
        """System-Warnungen with real no-show calculation"""
        alerts = []
        start = _start_date(days)

        # Check No-Show-Rate (REAL CALCULATION from PostgreSQL)
        try:
            from app.models.booking import Booking, BookingOutcome
            db_session = _get_db_session()

            if db_session:
                total_bookings = db_session.query(Booking).filter(
                    Booking.date >= start
                ).count()

                no_shows = db_session.query(BookingOutcome).filter(
                    BookingOutcome.date >= start,
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

    def _get_optimal_booking_times(self, days: int = DEFAULT_DAYS) -> Dict[str, int]:
        """Optimale Buchungszeiten from real booking data"""
        try:
            from app.models.booking import Booking
            db_session = _get_db_session()

            if db_session:
                start = _start_date(days)

                # Load all bookings
                bookings = db_session.query(Booking).filter(
                    Booking.date >= start
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
