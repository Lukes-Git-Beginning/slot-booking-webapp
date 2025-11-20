# -*- coding: utf-8 -*-
"""
Weekly Points System Models - Komplexes wöchentliches Punkte-System
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, JSON, Text, Float, Index, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class WeeklyPointsParticipant(Base):
    """
    Wöchentliche Teilnehmer-Liste

    Ersetzt: weekly_points.json['participants']
    """

    __tablename__ = 'weekly_participants'

    # Participant-Name (Display-Name)
    participant_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

    # Verknüpfung zu User (optional)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_date: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Stats
    total_weeks_participated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_goal_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<WeeklyParticipant(name='{self.participant_name}', weeks={self.total_weeks_participated})>"


class WeeklyPoints(Base):
    """
    Wöchentliche Punkte-Daten pro User

    Ersetzt: weekly_points.json['weeks'][week_id]['users'][username]
    """

    __tablename__ = 'weekly_points'

    # Woche (Format: "2025-37")
    week_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Participant
    participant_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Punkte
    goal_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bonus_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status
    on_vacation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_goal_set: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Activities & Pending (als JSON-Arrays)
    activities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # [{"type": "booking", "points": 10, ...}]
    pending_activities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # [{"type": "booking", "points": 10, ...}]
    pending_goal: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"value": 50, "timestamp": "..."}

    # Audit-Log (alle Änderungen)
    audit: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # [{"action": "add", "timestamp": "...", ...}]

    # Unique Constraint: Ein User pro Woche
    __table_args__ = (
        Index('idx_week_participant', 'week_id', 'participant_name', unique=True),
        Index('idx_week', 'week_id'),
    )

    def __repr__(self) -> str:
        return f"<WeeklyPoints(week='{self.week_id}', user='{self.participant_name}', points={self.total_points})>"


class WeeklyActivity(Base):
    """
    Einzelne Aktivitäten im Weekly-Points-System

    Ersetzt: weekly_points.json['weeks'][week_id]['users'][username]['activities']
    """

    __tablename__ = 'weekly_activities'

    # Woche & Participant
    week_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    participant_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Activity-Details
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'booking', 'quest', 'bonus'
    activity_date: Mapped[datetime] = mapped_column(nullable=False, index=True)

    # Punkte
    points_earned: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    is_pending: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Metadata
    activity_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Zusätzliche Infos

    # Indexes
    __table_args__ = (
        Index('idx_week_participant_activity', 'week_id', 'participant_name'),
        Index('idx_pending', 'is_pending'),
    )

    def __repr__(self) -> str:
        return f"<WeeklyActivity(week='{self.week_id}', user='{self.participant_name}', points={self.points_earned})>"


class PrestigeData(Base):
    """
    User-Prestige-System

    Ersetzt: prestige_data.json
    """

    __tablename__ = 'prestige_data'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

    # Prestige-Level
    prestige_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prestige_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Stats vor Prestige-Reset
    pre_prestige_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pre_prestige_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Prestige-Boni
    prestige_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    unlocked_perks: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # ["double_xp", "faster_cooldowns", ...]

    # History
    prestige_history: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # [{"date": "...", "level": 5, ...}]
    last_prestige_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Total Stats (lifetime)
    lifetime_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_bookings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<PrestigeData(username='{self.username}', prestige_level={self.prestige_level})>"


class MinigameData(Base):
    """
    Minigame-Stats & Progress

    Ersetzt: minigame_data.json
    """

    __tablename__ = 'minigame_data'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Minigame-ID
    minigame_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    minigame_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Stats
    times_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Achievements
    achievements_unlocked: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # ["speed_demon", "perfectionist", ...]
    last_played: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Rewards
    total_coins_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Unique Constraint
    __table_args__ = (
        Index('idx_username_minigame', 'username', 'minigame_id', unique=True),
        Index('idx_high_score', 'high_score'),
    )

    def __repr__(self) -> str:
        return f"<MinigameData(username='{self.username}', game='{self.minigame_name}', high_score={self.high_score})>"


class PersistentData(Base):
    """
    Allgemeine persistente Daten (Key-Value-Store für Misc-Daten)

    Ersetzt: persistent_data.json
    """

    __tablename__ = 'persistent_data'

    # Key-Value-Pair
    data_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    data_value: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Metadata
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'config', 'cache', 'system'
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Expiry (optional, für Cache-Daten)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_data_type', 'data_type'),
        Index('idx_expires', 'expires_at'),
    )

    def __repr__(self) -> str:
        return f"<PersistentData(key='{self.data_key}', type='{self.data_type}')>"
