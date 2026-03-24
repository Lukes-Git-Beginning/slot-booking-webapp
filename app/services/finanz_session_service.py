# -*- coding: utf-8 -*-
"""
Finanzberatung Session Service - Session CRUD and Lifecycle Management

Provides business logic for financial advisory sessions:
- Create, list, get, update sessions
- Status transitions with validation
- Notes management (opener: t1_notes, closer: t2_notes)
- Opener/closer assignment
- Document listing per session

All database access through get_db_session() pattern.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.models import get_db_session
from app.models.finanzberatung import (
    FinanzSession,
    FinanzDocument,
    FinanzUploadToken,
    SessionStatus,
    TokenType,
)

logger = logging.getLogger(__name__)


class FinanzSessionService:
    """Service for managing financial advisory sessions."""

    def create_session(
        self,
        opener_username: str,
        customer_name: str,
        session_type: str = 'standard',
        appointment_date: Optional[datetime] = None,
    ) -> FinanzSession:
        """
        Create a new financial advisory session.

        Args:
            opener_username: Username of the opener (consultant who initiated)
            customer_name: Customer's display name
            session_type: Session type (default: 'standard')
            appointment_date: Optional appointment datetime

        Returns:
            The created FinanzSession object
        """
        db = get_db_session()
        try:
            session = FinanzSession(
                opener_username=opener_username,
                customer_name=customer_name,
                session_type=session_type,
                appointment_date=appointment_date,
                status=SessionStatus.ACTIVE,
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            logger.info(
                "Session created: id=%s, opener=%s, customer=%s",
                session.id, opener_username, customer_name,
            )
            return session
        except Exception as e:
            db.rollback()
            logger.error("Failed to create session: %s", e, exc_info=True)
            raise
        finally:
            db.close()

    def get_session(
        self,
        session_id: int,
        username: Optional[str] = None,
    ) -> Optional[FinanzSession]:
        """
        Get a session by ID.

        Args:
            session_id: The session's primary key
            username: If provided, filter by opener_username (own sessions only).
                      Pass None for admin access (bypasses filter).

        Returns:
            FinanzSession or None if not found
        """
        db = get_db_session()
        try:
            query = db.query(FinanzSession).options(
                joinedload(FinanzSession.foerderfragebogen),
                joinedload(FinanzSession.tokens),
            ).filter(FinanzSession.id == session_id)
            if username is not None:
                query = query.filter(
                    or_(
                        FinanzSession.opener_username == username,
                        FinanzSession.closer_username == username,
                    )
                )
            result = query.first()
            if result:
                db.expunge(result)
            return result
        except Exception as e:
            logger.error("Failed to get session %s: %s", session_id, e, exc_info=True)
            return None
        finally:
            db.close()

    def list_sessions(
        self,
        username: Optional[str] = None,
        status: Optional[SessionStatus] = None,
    ) -> list:
        """
        List sessions with optional filters.

        Args:
            username: If provided, filter by opener_username
            status: If provided, filter by session status

        Returns:
            List of FinanzSession objects ordered by appointment_date DESC
        """
        db = get_db_session()
        try:
            query = db.query(FinanzSession).options(
                joinedload(FinanzSession.foerderfragebogen),
            )
            if username is not None:
                query = query.filter(
                    or_(
                        FinanzSession.opener_username == username,
                        FinanzSession.closer_username == username,
                    )
                )
            if status is not None:
                query = query.filter(FinanzSession.status == status)
            results = query.order_by(FinanzSession.appointment_date.desc()).all()
            db.expunge_all()
            return results
        except Exception as e:
            logger.error("Failed to list sessions: %s", e, exc_info=True)
            return []
        finally:
            db.close()

    def update_notes(
        self,
        session_id: int,
        field: str,
        content: str,
        username: str,
    ) -> bool:
        """
        Update t1_notes or t2_notes on a session.

        Authorization rules:
        - Only the opener can edit t1_notes
        - Only the closer can edit t2_notes

        Args:
            session_id: The session's primary key
            field: 't1_notes' or 't2_notes'
            content: The new notes content
            username: The requesting user's username

        Returns:
            True if updated successfully, False otherwise
        """
        if field not in ('t1_notes', 't2_notes'):
            logger.warning("Invalid notes field: %s", field)
            return False

        db = get_db_session()
        try:
            session = db.query(FinanzSession).filter(
                FinanzSession.id == session_id
            ).first()
            if session is None:
                logger.warning("Session not found: %s", session_id)
                return False

            # Authorization check
            if field == 't1_notes' and session.opener_username != username:
                logger.warning(
                    "User %s not authorized to edit t1_notes on session %s (opener: %s)",
                    username, session_id, session.opener_username,
                )
                return False
            if field == 't2_notes' and session.closer_username != username:
                logger.warning(
                    "User %s not authorized to edit t2_notes on session %s (closer: %s)",
                    username, session_id, session.closer_username,
                )
                return False

            setattr(session, field, content)
            db.commit()
            logger.info(
                "Notes updated: session=%s, field=%s, user=%s",
                session_id, field, username,
            )
            return True
        except Exception as e:
            db.rollback()
            logger.error(
                "Failed to update notes on session %s: %s", session_id, e, exc_info=True
            )
            return False
        finally:
            db.close()

    def transition_status(
        self,
        session_id: int,
        new_status: SessionStatus,
        username: str,
    ) -> FinanzSession:
        """
        Transition a session to a new status.

        Uses the model's transition_to() method which validates allowed transitions.

        Args:
            session_id: The session's primary key
            new_status: The target SessionStatus
            username: The requesting user's username (for audit trail)

        Returns:
            The updated FinanzSession

        Raises:
            ValueError: If the transition is not allowed
            LookupError: If session not found
        """
        db = get_db_session()
        try:
            session = db.query(FinanzSession).filter(
                FinanzSession.id == session_id
            ).first()
            if session is None:
                raise LookupError(f"Session {session_id} not found")

            old_status = session.status
            session.transition_to(new_status)
            db.commit()
            db.refresh(session)
            logger.info(
                "Status transition: session=%s, %s -> %s, user=%s",
                session_id, old_status, new_status.value, username,
            )
            return session
        except (ValueError, LookupError):
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(
                "Failed to transition session %s: %s", session_id, e, exc_info=True
            )
            raise
        finally:
            db.close()

    def assign_closer(
        self,
        session_id: int,
        closer_username: str,
    ) -> FinanzSession:
        """
        Assign a closer to a session.

        Args:
            session_id: The session's primary key
            closer_username: Username of the closer to assign

        Returns:
            The updated FinanzSession

        Raises:
            LookupError: If session not found
        """
        db = get_db_session()
        try:
            session = db.query(FinanzSession).filter(
                FinanzSession.id == session_id
            ).first()
            if session is None:
                raise LookupError(f"Session {session_id} not found")

            session.closer_username = closer_username
            db.commit()
            db.refresh(session)
            logger.info(
                "Closer assigned: session=%s, closer=%s",
                session_id, closer_username,
            )
            return session
        except LookupError:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(
                "Failed to assign closer on session %s: %s", session_id, e, exc_info=True
            )
            raise
        finally:
            db.close()

    def get_session_documents(self, session_id: int) -> list:
        """
        Get all documents for a session.

        Args:
            session_id: The session's primary key

        Returns:
            List of FinanzDocument objects ordered by created_at DESC
        """
        db = get_db_session()
        try:
            return (
                db.query(FinanzDocument)
                .filter(FinanzDocument.session_id == session_id)
                .order_by(FinanzDocument.created_at.desc())
                .all()
            )
        except Exception as e:
            logger.error(
                "Failed to get documents for session %s: %s",
                session_id, e, exc_info=True,
            )
            return []
        finally:
            db.close()
