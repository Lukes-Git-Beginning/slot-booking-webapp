# -*- coding: utf-8 -*-
"""
Tracking Models - Daily Metrics & Customer Profiles

Ersetzt: data/tracking/daily_metrics.json, data/tracking/customer_profiles.json
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, Text, Date, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class DailyMetrics(Base):
    """
    Daily Metrics Model

    Ersetzt: data/tracking/daily_metrics.json
    Tagesstatistiken fuer Slot-Outcomes (No-Shows, Completed, etc.)
    """

    __tablename__ = 'daily_metrics'

    date: Mapped[datetime] = mapped_column(Date, unique=True, nullable=False, index=True)

    # Outcome counts
    total_slots: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_shows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ghosts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rescheduled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overhang: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Rates
    no_show_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ghost_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cancellation_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # JSON-Blobs for nested breakdowns
    by_hour: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    by_user: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    by_potential: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_daily_metrics_date', 'date'),
    )

    def __repr__(self) -> str:
        return f"<DailyMetrics(date={self.date}, total={self.total_slots}, completed={self.completed})>"


class CustomerProfile(Base):
    """
    Customer Profile Model

    Ersetzt: data/tracking/customer_profiles.json
    Aggregierte Kundendaten fuer Zuverlaessigkeits-Analyse
    """

    __tablename__ = 'customer_profiles'

    customer: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Dates as strings (YYYY-MM-DD format from JSON)
    first_seen: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    last_seen: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Counts
    total_appointments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_shows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Score & Risk
    reliability_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default='low', nullable=False)

    __table_args__ = (
        Index('idx_customer_profile_customer', 'customer'),
        Index('idx_customer_profile_risk', 'risk_level'),
    )

    def __repr__(self) -> str:
        return f"<CustomerProfile(customer='{self.customer}', risk='{self.risk_level}', score={self.reliability_score})>"
