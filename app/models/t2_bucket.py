# -*- coding: utf-8 -*-
"""
T2 Bucket System - PostgreSQL Models

Prevents race conditions in draw_closer() with row-level locking.
Critical for multi-worker environments (4 Gunicorn workers).
"""

from datetime import datetime
from typing import Dict, Any
from sqlalchemy import String, Float, Integer, JSON, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class T2CloserConfig(Base):
    """
    T2 Closer configuration (static data)

    Stores: name, full_name, color, default_probability
    Primary key: id (auto-increment), name is unique
    """
    __tablename__ = "t2_closer_config"

    # Inherits id as primary key from Base
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False)
    default_probability: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format (compatible with existing code)"""
        return {
            "full_name": self.full_name,
            "color": self.color,
            "default_probability": self.default_probability,
            "is_active": self.is_active
        }

    def __repr__(self) -> str:
        return f"<T2CloserConfig({self.name}, prob={self.default_probability})>"


class T2BucketState(Base):
    """
    Current bucket state (single row with row-level locking)

    Stores:
    - Current probabilities for each closer
    - Bucket composition (list of closer names)
    - Draw statistics
    - Last reset timestamp

    Uses SELECT FOR UPDATE for atomic read-modify-write operations.
    """
    __tablename__ = "t2_bucket_state"

    # Inherits id as primary key from Base
    singleton_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, default=1, index=True)

    # Current state
    probabilities: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    bucket: Mapped[list] = mapped_column(JSON, nullable=False)  # List of closer names
    total_draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Statistics
    stats: Mapped[Dict[str, int]] = mapped_column(JSON, nullable=False)  # Draw counts per closer

    # Configuration
    max_draws_before_reset: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    # Timestamps
    last_reset: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint('singleton_id', name='uq_bucket_singleton'),
        Index('idx_bucket_singleton', 'singleton_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format (compatible with existing code)"""
        return {
            "probabilities": self.probabilities,
            "bucket": self.bucket,
            "total_draws": self.total_draws,
            "stats": self.stats,
            "max_draws_before_reset": self.max_draws_before_reset,
            "last_reset": self.last_reset.isoformat()
        }

    def __repr__(self) -> str:
        return f"<T2BucketState(draws={self.total_draws}/{self.max_draws_before_reset}, bucket_size={len(self.bucket)})>"


class T2DrawHistory(Base):
    """
    Historical record of all draws

    Stores each draw event for analytics and audit trail.
    """
    __tablename__ = "t2_draw_history"

    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    closer_drawn: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    draw_type: Mapped[str] = mapped_column(String(10), nullable=False, default="T2")
    customer_name: Mapped[str] = mapped_column(String(200), nullable=True)

    bucket_size_after: Mapped[int] = mapped_column(Integer, nullable=False)
    probability_after: Mapped[float] = mapped_column(Float, nullable=False)

    drawn_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    __table_args__ = (
        Index('idx_draw_history_user', 'username'),
        Index('idx_draw_history_closer', 'closer_drawn'),
        Index('idx_draw_history_timestamp', 'drawn_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format"""
        return {
            "id": self.id,
            "user": self.username,
            "closer": self.closer_drawn,
            "draw_type": self.draw_type,
            "customer_name": self.customer_name,
            "bucket_size_after": self.bucket_size_after,
            "probability_after": self.probability_after,
            "timestamp": self.drawn_at.isoformat()
        }

    def __repr__(self) -> str:
        return f"<T2DrawHistory({self.username} -> {self.closer_drawn} at {self.drawn_at})>"


class T2UserLastDraw(Base):
    """
    Tracks last draw timestamp per user (for timeout enforcement)

    One row per user, updated on each draw.
    Uses ON CONFLICT UPDATE pattern for upserts.
    """
    __tablename__ = "t2_user_last_draw"

    # Inherits id as primary key from Base
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    last_draw_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    last_closer_drawn: Mapped[str] = mapped_column(String(50), nullable=False)
    last_draw_type: Mapped[str] = mapped_column(String(10), nullable=False)
    last_customer_name: Mapped[str] = mapped_column(String(200), nullable=True)

    __table_args__ = (
        UniqueConstraint('username', name='uq_user_last_draw'),
        Index('idx_user_last_draw_username', 'username'),
        Index('idx_user_last_draw_timestamp', 'last_draw_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format"""
        return {
            "timestamp": self.last_draw_at.isoformat(),
            "closer": self.last_closer_drawn,
            "draw_type": self.last_draw_type,
            "customer_name": self.last_customer_name
        }

    def __repr__(self) -> str:
        return f"<T2UserLastDraw({self.username} at {self.last_draw_at})>"
