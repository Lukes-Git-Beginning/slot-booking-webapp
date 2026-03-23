# -*- coding: utf-8 -*-
"""Notification Models - User Notifications"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, JSON, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Notification(Base):
    """
    User Notifications

    Ersetzt: user_notifications.json
    Format: {username: [{id, type, title, message, ...}]}

    Wichtig: Jeder User hat seine eigene Row. notification_id-Format:
    "{base_notification_id}-{username}" (eindeutig pro User)
    """

    __tablename__ = 'notifications'

    notification_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, default='info')
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_popup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    roles: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    actions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_notification_username_read', 'username', 'is_read'),
        Index('idx_notification_username_dismissed', 'username', 'is_dismissed'),
    )

    def __repr__(self) -> str:
        return f"<Notification(notification_id='{self.notification_id}', username='{self.username}', read={self.is_read})>"
