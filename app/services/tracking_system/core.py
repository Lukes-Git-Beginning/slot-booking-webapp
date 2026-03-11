# -*- coding: utf-8 -*-
"""
BookingTracker facade class — delegates to submodules.
All external code interacts with this class; the submodules are implementation details.
"""

import os
import logging

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class BookingTracker:
    def __init__(self):
        self.data_dir = "data/tracking"
        os.makedirs(self.data_dir, exist_ok=True)

        # Persistent storage following dual-write pattern
        self.persistent_dir = "data/persistent"
        os.makedirs(self.persistent_dir, exist_ok=True)

        # Files für verschiedene Tracking-Arten (primary storage)
        self.bookings_file = os.path.join(self.data_dir, "bookings.jsonl")
        self.outcomes_file = os.path.join(self.data_dir, "outcomes.jsonl")
        self.metrics_file = os.path.join(self.data_dir, "daily_metrics.json")
        self.customer_file = os.path.join(self.data_dir, "customer_profiles.json")

        # Failed bookings queue (for recovery)
        self.failed_bookings_file = os.path.join(self.data_dir, "failed_bookings.jsonl")

        # Persistent files (secondary storage for compatibility)
        self.persistent_metrics_file = os.path.join(self.persistent_dir, "tracking_metrics.json")
        self.persistent_customer_file = os.path.join(self.persistent_dir, "customer_tracking.json")

        # Google Calendar Service
        from googleapiclient.discovery import build
        from app.utils.credentials import load_google_credentials
        creds = load_google_credentials(SCOPES)
        self.service = build("calendar", "v3", credentials=creds)

    # ---- booking_recorder ----
    def track_booking(self, customer_name, date, time_slot, user, color_id, description=""):
        from app.services.tracking_system.booking_recorder import track_booking
        return track_booking(self, customer_name, date, time_slot, user, color_id, description)

    def _queue_failed_booking(self, booking_data):
        from app.services.tracking_system.booking_recorder import _queue_failed_booking
        return _queue_failed_booking(self, booking_data)

    def get_failed_bookings(self):
        from app.services.tracking_system.booking_recorder import get_failed_bookings
        return get_failed_bookings(self)

    def recover_failed_booking(self, booking_id):
        from app.services.tracking_system.booking_recorder import recover_failed_booking
        return recover_failed_booking(self, booking_id)

    # ---- outcome_analyzer ----
    def check_daily_outcomes(self, check_date=None):
        from app.services.tracking_system.outcome_analyzer import check_daily_outcomes
        return check_daily_outcomes(self, check_date)

    # ---- customer_profiles ----
    def _update_customer_profiles(self):
        from app.services.tracking_system.customer_profiles import _update_customer_profiles
        return _update_customer_profiles(self)

    def get_customer_history(self, customer_name):
        from app.services.tracking_system.customer_profiles import get_customer_history
        return get_customer_history(self, customer_name)

    # ---- reporting ----
    def get_weekly_report(self, week_number=None):
        from app.services.tracking_system.reporting import get_weekly_report
        return get_weekly_report(self, week_number)

    def get_weekly_stats(self, year, week_number):
        from app.services.tracking_system.reporting import get_weekly_stats
        return get_weekly_stats(self, year, week_number)

    def get_monthly_stats(self, year, month):
        from app.services.tracking_system.reporting import get_monthly_stats
        return get_monthly_stats(self, year, month)

    def get_stats_for_period(self, start_date_str, end_date_str):
        from app.services.tracking_system.reporting import get_stats_for_period
        return get_stats_for_period(self, start_date_str, end_date_str)

    # ---- dashboard ----
    def get_performance_dashboard(self):
        from app.services.tracking_system.dashboard import get_performance_dashboard
        return get_performance_dashboard(self)

    def get_enhanced_dashboard(self):
        from app.services.tracking_system.dashboard import get_enhanced_dashboard
        return get_enhanced_dashboard(self)

    # ---- historical ----
    def get_user_bookings(self, user, start_date, end_date):
        from app.services.tracking_system.historical import get_user_bookings
        return get_user_bookings(self, user, start_date, end_date)

    def load_all_bookings(self):
        from app.services.tracking_system.historical import load_all_bookings
        return load_all_bookings(self)

    def load_historical_data(self):
        from app.services.tracking_system.historical import load_historical_data
        return load_historical_data(self)

    def get_last_n_workdays_stats(self, n=5):
        from app.services.tracking_system.historical import get_last_n_workdays_stats
        return get_last_n_workdays_stats(self, n)

    def get_stats_since_date(self, start_date_str="2025-09-01"):
        from app.services.tracking_system.historical import get_stats_since_date
        return get_stats_since_date(self, start_date_str)

    def get_bookings_by_creation_date(self, start_date_str, end_date_str):
        from app.services.tracking_system.historical import get_bookings_by_creation_date
        return get_bookings_by_creation_date(self, start_date_str, end_date_str)

    def get_consultant_performance(self, start_date_str, end_date_str):
        from app.services.tracking_system.historical import get_consultant_performance
        return get_consultant_performance(self, start_date_str, end_date_str)

    # ---- monitoring ----
    def detect_tracking_gaps(self, lookback_days=14):
        from app.services.tracking_system.monitoring import detect_tracking_gaps
        return detect_tracking_gaps(self, lookback_days)

    # ---- converters (kept as instance methods for backward compat) ----
    def _get_potential_type(self, color_id):
        from app.services.tracking_system.converters import _get_potential_type
        return _get_potential_type(color_id)

    def _get_outcome_from_title_and_color(self, title, color_id):
        from app.services.tracking_system.converters import _get_outcome_from_title_and_color
        return _get_outcome_from_title_and_color(title, color_id)

    def _extract_status_from_title(self, title):
        from app.services.tracking_system.converters import _extract_status_from_title
        return _extract_status_from_title(title)

    def _clean_customer_name(self, summary):
        from app.services.tracking_system.converters import _clean_customer_name
        return _clean_customer_name(summary)

    # ---- utils (kept as instance methods for backward compat) ----
    def _get_german_weekday(self, weekday_index):
        from app.services.tracking_system.utils import _get_german_weekday
        return _get_german_weekday(weekday_index)

    def _get_last_n_workdays(self, n=5):
        from app.services.tracking_system.historical import _get_last_n_workdays
        return _get_last_n_workdays(n)
