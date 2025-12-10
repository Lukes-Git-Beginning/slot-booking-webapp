# -*- coding: utf-8 -*-
"""
T2 Booking Model - T2 Closer Booking Tracking

Ersetzt: data/persistent/t2_bookings.json
Trackt T2 Closer Buchungen mit Google Calendar Integration
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Date, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class T2Booking(Base):
    """
    T2 Booking Model

    Ersetzt: data/persistent/t2_bookings.json
    Trackt jede T2-Buchung mit Coach/Berater-Assignment und Google Calendar Event-ID

    Features:
    - Dual-Write: PostgreSQL + JSON Fallback
    - Google Calendar Integration (event_id, calendar_id)
    - Reschedule-Tracking (is_rescheduled_from)
    - Status-Tracking (active, cancelled, rescheduled)
    """

    __tablename__ = 't2_bookings'

    # Booking-ID (Format: T2-ABC123DE) - Note: Base class provides auto-increment 'id'
    booking_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Coach & Berater Assignment
    coach: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Gewürfelter Coach
    berater: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Ausführender Berater

    # Booking-Details
    customer: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[str] = mapped_column(String(10), nullable=False)  # "14:00"

    # Optionale Details
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # User (wer hat gebucht - Opener)
    user: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Google Calendar Integration (NEU seit 2025-12-10)
    event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)  # Google Calendar Event ID
    calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Google Calendar Calendar ID

    # Status-Tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='active',
        index=True
    )  # "active", "cancelled", "rescheduled"

    # Reschedule-Tracking
    is_rescheduled_from: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Original Booking-ID

    # Note: created_at and updated_at are provided by Base class

    # Indexes für Performance
    __table_args__ = (
        Index('idx_t2_booking_user_date', 'user', 'date'),
        Index('idx_t2_booking_berater_date', 'berater', 'date'),
        Index('idx_t2_booking_status', 'status'),
        Index('idx_t2_booking_event_id', 'event_id'),
    )

    def to_dict(self) -> dict:
        """Convert to dict format (compatible with existing JSON structure)"""
        return {
            'id': self.booking_id,
            'coach': self.coach,
            'berater': self.berater,
            'customer': self.customer,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'time': self.time,
            'topic': self.topic or '',
            'email': self.email or '',
            'user': self.user,
            'event_id': self.event_id,
            'calendar_id': self.calendar_id,
            'status': self.status,
            'is_rescheduled_from': self.is_rescheduled_from,
            'created_at': self.created_at.isoformat() if self.created_at else datetime.utcnow().isoformat()
        }

    def __repr__(self) -> str:
        return f"<T2Booking(booking_id='{self.booking_id}', customer='{self.customer}', berater='{self.berater}', date={self.date}, status='{self.status}')>"
