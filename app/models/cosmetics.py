# -*- coding: utf-8 -*-
"""
Cosmetics & Customization Models
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, JSON, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class UserCosmetic(Base):
    """
    User-Cosmetics (Themes, Effects, Customizations)

    Ersetzt: user_customizations.json, customization_achievements.json
    """

    __tablename__ = 'user_cosmetics'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Cosmetic-Item
    item_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'theme', 'effect', 'avatar', 'badge_frame'
    item_category: Mapped[str] = mapped_column(String(50), nullable=False)  # 'visual', 'audio', 'animation'

    # Item-Details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rarity: Mapped[str] = mapped_column(String(50), nullable=False)  # 'common', 'rare', 'epic', 'legendary'

    # Purchase/Unlock
    is_owned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlock_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    purchase_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # in coins

    # Config (z.B. Theme-Colors, Effect-Parameters)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Unique Constraint
    __table_args__ = (
        Index('idx_username_item', 'username', 'item_id', unique=True),
        Index('idx_item_type', 'item_type'),
        Index('idx_owned', 'is_owned'),
        Index('idx_active', 'is_active'),
    )

    def __repr__(self) -> str:
        return f"<UserCosmetic(username='{self.username}', item='{self.item_id}', active={self.is_active})>"


class CustomizationAchievement(Base):
    """
    Achievements für Customizations (Collector-Achievements)

    Ersetzt: customization_achievements.json
    """

    __tablename__ = 'customization_achievements'

    # Foreign Key
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Achievement-Details
    achievement_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    achievement_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'collector', 'fashionista', 'trendsetter'

    # Title & Description
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Progress
    current_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_progress: Mapped[int] = mapped_column(Integer, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Rewards
    reward_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_items: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Unique Constraint
    __table_args__ = (
        Index('idx_username_achievement', 'username', 'achievement_id', unique=True),
        Index('idx_completed', 'is_completed'),
    )

    def __repr__(self) -> str:
        return f"<CustomizationAchievement(username='{self.username}', title='{self.title}')>"
