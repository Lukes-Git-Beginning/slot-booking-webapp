# -*- coding: utf-8 -*-
"""
Gamification Models - Scores, Badges, Achievements, Quests
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, JSON, Text, Float, Index, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Score(Base):
    """
    Monatliche Booking-Scores

    Ersetzt: scores.json
    Format: {username: {month: points}}
    """

    __tablename__ = 'scores'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Zeitraum (Format: "2025-01")
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)

    # Punkte
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Zusätzliche Metriken
    bookings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Composite Index für eindeutige Kombination
    __table_args__ = (
        Index('idx_username_month', 'username', 'month', unique=True),
    )

    def __repr__(self) -> str:
        return f"<Score(username='{self.username}', month='{self.month}', points={self.points})>"


class UserBadge(Base):
    """
    User-Badges mit Earned-Dates

    Ersetzt: user_badges.json
    """

    __tablename__ = 'user_badges'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Badge-ID (eindeutig per Badge-Typ)
    badge_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Badge-Details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    emoji: Mapped[str] = mapped_column(String(50), nullable=False)
    rarity: Mapped[str] = mapped_column(String(50), nullable=False)  # 'common', 'uncommon', 'rare', 'legendary'
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # 'daily', 'weekly', 'monthly', 'special'
    color: Mapped[str] = mapped_column(String(20), nullable=False, default='#3b82f6')

    # Earned-Date
    earned_date: Mapped[datetime] = mapped_column(nullable=False, index=True)

    # Zusätzliche Daten
    requirements_met: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    badge_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Unique Constraint: Ein User kann ein Badge nur einmal verdienen
    __table_args__ = (
        Index('idx_username_badge', 'username', 'badge_id', unique=True),
        Index('idx_earned_date', 'earned_date'),
        Index('idx_rarity', 'rarity'),
    )

    def __repr__(self) -> str:
        return f"<UserBadge(username='{self.username}', badge='{self.badge_id}', rarity='{self.rarity}')>"


class DailyQuest(Base):
    """
    Daily Quests System

    Ersetzt: daily_quests.json, quest_progress.json
    """

    __tablename__ = 'daily_quests'

    # Quest-Definition
    quest_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    quest_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)

    # Quest-Details
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # 'booking', 'social', 'performance'
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)  # 'easy', 'medium', 'hard'

    # Requirements
    target_value: Mapped[int] = mapped_column(Integer, nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'bookings', 'points', 'streak'

    # Rewards
    reward_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_items: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_quest_date', 'quest_date'),
        Index('idx_active', 'is_active'),
    )

    def __repr__(self) -> str:
        return f"<DailyQuest(id='{self.quest_id}', title='{self.title}', difficulty='{self.difficulty}')>"


class QuestProgress(Base):
    """
    User-Quest-Progress-Tracking

    Ersetzt: quest_progress.json
    """

    __tablename__ = 'quest_progress'

    # Foreign Keys
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quest_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Progress
    current_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_value: Mapped[int] = mapped_column(Integer, nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    is_claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Tracking
    started_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    last_progress_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Metadata
    progress_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Unique Constraint
    __table_args__ = (
        Index('idx_username_quest', 'username', 'quest_id', unique=True),
        Index('idx_completed', 'is_completed'),
    )

    def __repr__(self) -> str:
        return f"<QuestProgress(username='{self.username}', quest='{self.quest_id}', {self.current_value}/{self.target_value})>"


class PersonalGoal(Base):
    """
    User-Personal-Goals

    Ersetzt: personal_goals.json
    """

    __tablename__ = 'personal_goals'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Goal-Details
    goal_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Text] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # 'performance', 'learning', 'growth'

    # Target & Progress
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Motivation
    motivation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    milestones: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_username_goal', 'username', 'goal_id', unique=True),
        Index('idx_active_goals', 'is_active'),
    )

    def __repr__(self) -> str:
        return f"<PersonalGoal(username='{self.username}', title='{self.title}', {self.current_value}/{self.target_value})>"


class Champion(Base):
    """
    Weekly/Monthly Champions

    Ersetzt: champions.json
    """

    __tablename__ = 'champions'

    # Period (Format: "2025-W37" für Weekly, "2025-09" für Monthly)
    period: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'weekly', 'monthly'

    # Champion
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = Champion, 2 = Runner-up, 3 = Third

    # Stats
    total_points: Mapped[int] = mapped_column(Integer, nullable=False)
    total_bookings: Mapped[int] = mapped_column(Integer, nullable=False)
    show_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Rewards
    reward_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_badge: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metadata
    stats_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Unique Constraint
    __table_args__ = (
        Index('idx_period_rank', 'period', 'rank', unique=True),
        Index('idx_period_type', 'period_type'),
    )

    def __repr__(self) -> str:
        return f"<Champion(period='{self.period}', rank={self.rank}, username='{self.username}')>"


class MasteryData(Base):
    """
    User-Mastery-System

    Ersetzt: mastery_data.json
    """

    __tablename__ = 'mastery_data'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Mastery-Details
    skill_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(String(200), nullable=False)
    skill_category: Mapped[str] = mapped_column(String(50), nullable=False)  # 'booking', 'communication', 'closing'

    # Progress
    current_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_to_next_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # Stats
    practice_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mastery_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Unlocks
    unlocked_abilities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_practiced: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Unique Constraint
    __table_args__ = (
        Index('idx_username_skill', 'username', 'skill_id', unique=True),
        Index('idx_skill_category', 'skill_category'),
    )

    def __repr__(self) -> str:
        return f"<MasteryData(username='{self.username}', skill='{self.skill_name}', level={self.current_level})>"
