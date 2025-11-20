# -*- coding: utf-8 -*-
"""
User Models - Zentrale User-Verwaltung & User-Stats
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, JSON, Text, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class User(Base):
    """
    Zentrale User-Tabelle

    Ersetzt: user_profiles.json, user_stats.json, user_coins.json
    """

    __tablename__ = 'users'

    # Basics
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Authentication (falls später benötigt)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # User-Profile
    consultant_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    consultant_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'consultant', 't2_closer', etc.

    # Gamification-Stats
    total_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Prestige-System
    prestige_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prestige_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Tracking
    last_login: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_activity: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    on_vacation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # JSON-Fields für komplexe Daten (Fallback für Migration)
    profile_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships (werden später definiert)
    # badges = relationship("UserBadge", back_populates="user")
    # scores = relationship("Score", back_populates="user")

    # Indexes für Performance
    __table_args__ = (
        Index('idx_username', 'username'),
        Index('idx_email', 'email'),
        Index('idx_active', 'is_active'),
        Index('idx_role', 'role'),
    )

    def __repr__(self) -> str:
        return f"<User(username='{self.username}', level={self.level}, coins={self.total_coins})>"


class UserStats(Base):
    """
    Detaillierte User-Statistiken (Daily & Analytics)

    Ersetzt: user_stats.json, daily_user_stats.json, user_analytics.json
    """

    __tablename__ = 'user_stats'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Datum für Stats
    stat_date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    stat_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'daily', 'weekly', 'monthly'

    # Booking-Stats
    bookings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bookings_erschienen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bookings_nicht_erschienen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bookings_verschoben: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Performance-Metrics
    show_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    points_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Activity-Tracking
    activities_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quests_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    achievements_unlocked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # JSON-Field für erweiterte Metriken
    metrics_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Composite Index für schnelle Abfragen
    __table_args__ = (
        Index('idx_username_date', 'username', 'stat_date'),
        Index('idx_stat_type', 'stat_type'),
    )

    def __repr__(self) -> str:
        return f"<UserStats(username='{self.username}', date={self.stat_date}, points={self.points_earned})>"


class UserPrediction(Base):
    """
    User-Predictions für Analytics

    Ersetzt: user_predictions.json
    """

    __tablename__ = 'user_predictions'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Prediction-Daten
    prediction_date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'performance', 'churn', 'growth'

    # Predicted Values
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Model-Info
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    features_used: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_prediction_username_date', 'username', 'prediction_date'),
        Index('idx_prediction_type', 'prediction_type'),
    )

    def __repr__(self) -> str:
        return f"<UserPrediction(username='{self.username}', type='{self.prediction_type}', value={self.predicted_value})>"


class BehaviorPattern(Base):
    """
    User-Behavior-Patterns für ML-Analytics

    Ersetzt: behavior_patterns.json
    """

    __tablename__ = 'behavior_patterns'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Pattern-Daten
    pattern_date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    pattern_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'login', 'booking', 'activity'

    # Pattern-Metrics
    frequency: Mapped[float] = mapped_column(Float, nullable=False)
    avg_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    peak_hours: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Behavior-Flags
    is_consistent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Raw-Data
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_behavior_username_date', 'username', 'pattern_date'),
        Index('idx_pattern_type', 'pattern_type'),
    )

    def __repr__(self) -> str:
        return f"<BehaviorPattern(username='{self.username}', type='{self.pattern_type}', freq={self.frequency})>"


class PersonalInsight(Base):
    """
    Personal Insights für User-Dashboard

    Ersetzt: personal_insights.json
    """

    __tablename__ = 'personal_insights'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Insight-Daten
    insight_date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'strength', 'improvement', 'achievement'
    insight_category: Mapped[str] = mapped_column(String(50), nullable=False)  # 'performance', 'growth', 'social'

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Metadata
    source_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_insight_username_date', 'username', 'insight_date'),
        Index('idx_insight_type', 'insight_type'),
    )

    def __repr__(self) -> str:
        return f"<PersonalInsight(username='{self.username}', type='{self.insight_type}', title='{self.title}')>"
