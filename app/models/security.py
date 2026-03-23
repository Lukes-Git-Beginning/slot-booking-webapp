# -*- coding: utf-8 -*-
"""Security Models - Account Lockout, Audit Logging"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, JSON, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AccountLockout(Base):
    """
    Account-Lockout-Daten fuer Brute-Force-Schutz

    Ersetzt: account_lockouts.json
    Format: {username: {failed_attempts, first_attempt, last_attempt, locked_until}}
    """

    __tablename__ = 'account_lockouts'

    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_attempt: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_attempt: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    lockout_tier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index('idx_lockout_locked_until', 'locked_until'),
    )

    def __repr__(self) -> str:
        return f"<AccountLockout(username='{self.username}', attempts={self.failed_attempts}, locked_until='{self.locked_until}')>"


class AuditLog(Base):
    """
    Audit-Log fuer Admin-Aktionen und Security-Events

    Ersetzt: audit_log.json
    """

    __tablename__ = 'audit_logs'

    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(500), nullable=False)
    user: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default='info', index=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_audit_timestamp_desc', 'timestamp'),
        Index('idx_audit_event_type_severity', 'event_type', 'severity'),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(timestamp='{self.timestamp}', event_type='{self.event_type}', user='{self.user}')>"
