# -*- coding: utf-8 -*-
"""
Booking Models - Booking Tracking & Outcomes

Ersetzt: bookings.jsonl, outcomes.jsonl
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, Text, Date, Time, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Booking(Base):
    """
    Booking Tracking Model

    Ersetzt: data/tracking/bookings.jsonl
    Trackt jede neue Buchung mit Metadaten für Analytics
    """

    __tablename__ = 'bookings'

    # Booking-ID (Format: date_time_customer)
    booking_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Booking-Details
    customer: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[str] = mapped_column(String(10), nullable=False)  # "14:00"
    weekday: Mapped[str] = mapped_column(String(20), nullable=False)  # "Monday", "Tuesday"
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)  # ISO week number

    # User (wer hat gebucht)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Potential & Color
    potential_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "normal", "top", "closer_needed"
    color_id: Mapped[str] = mapped_column(String(10), nullable=False)  # Google Calendar Color ID

    # Description-Metadaten
    description_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_description: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Booking-Timing-Analyse
    booking_lead_time: Mapped[int] = mapped_column(Integer, nullable=False)  # Tage im Voraus gebucht
    booked_at_hour: Mapped[int] = mapped_column(Integer, nullable=False)  # Stunde der Buchung (0-23)
    booked_on_weekday: Mapped[str] = mapped_column(String(20), nullable=False)  # Wochentag der Buchung

    # Timestamp (wann wurde Booking getrackt)
    booking_timestamp: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Indexes für Performance
    __table_args__ = (
        Index('idx_booking_username_date', 'username', 'date'),
        Index('idx_booking_date', 'date'),
        Index('idx_booking_customer', 'customer'),
        Index('idx_booking_week', 'week_number'),
    )

    def __repr__(self) -> str:
        return f"<Booking(id='{self.booking_id}', customer='{self.customer}', date={self.date}, user='{self.username}')>"


class BookingOutcome(Base):
    """
    Booking Outcome Tracking Model

    Ersetzt: data/tracking/outcomes.jsonl
    Trackt das Ergebnis eines Termins (No-Show, Completed, Cancelled, etc.)
    """

    __tablename__ = 'booking_outcomes'

    # Outcome-ID (Format: date_time_customer)
    outcome_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Referenz zum Booking (falls vorhanden)
    booking_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Outcome-Details
    customer: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    time: Mapped[str] = mapped_column(String(10), nullable=False)  # "14:00"

    # Outcome-Typ
    outcome: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # "completed", "no_show", "cancelled", "rescheduled"

    # Color & Potential
    color_id: Mapped[str] = mapped_column(String(10), nullable=False)
    potential_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Event-Description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Alert-Flag (für No-Shows)
    is_alert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Checked-Timestamp (wann wurde Outcome getrackt)
    checked_at: Mapped[str] = mapped_column(String(10), nullable=False)  # "21:00"
    outcome_timestamp: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Indexes für Performance
    __table_args__ = (
        Index('idx_outcome_customer', 'customer'),
        Index('idx_outcome_date', 'date'),
        Index('idx_outcome_outcome', 'outcome'),
        Index('idx_outcome_booking_id', 'booking_id'),
        Index('idx_outcome_alert', 'is_alert'),
    )

    def __repr__(self) -> str:
        return f"<BookingOutcome(id='{self.outcome_id}', customer='{self.customer}', outcome='{self.outcome}', date={self.date})>"
