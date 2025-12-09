# -*- coding: utf-8 -*-
"""
Database Utilities - Safe Session Management for PostgreSQL

Provides context managers for database sessions to prevent connection pool exhaustion.
Critical for production with 4 Gunicorn workers sharing a connection pool.
"""

import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


@contextmanager
def db_session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup.

    Usage:
        from app.utils.db_utils import db_session_scope

        with db_session_scope() as session:
            booking = Booking(...)
            session.add(booking)
            session.commit()

    Features:
    - Automatic commit on success
    - Automatic rollback on exception
    - Guaranteed session.close() in finally block
    - Connection pool safe (prevents leaks)

    Yields:
        Session: SQLAlchemy database session

    Raises:
        RuntimeError: If database not initialized
        SQLAlchemyError: If database operation fails
    """
    from app.models import get_db_session

    session = get_db_session()

    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error in database session: {e}", exc_info=True)
        raise
    finally:
        session.close()


@contextmanager
def db_session_scope_no_commit() -> Generator[Session, None, None]:
    """
    Context manager for database sessions WITHOUT automatic commit.

    Use this when you need manual control over transactions:
    - Multiple operations with conditional commit
    - Read-only queries
    - Complex transaction logic

    Usage:
        from app.utils.db_utils import db_session_scope_no_commit

        with db_session_scope_no_commit() as session:
            user = session.query(User).filter_by(username='test').first()
            if user.can_book():
                booking = Booking(...)
                session.add(booking)
                session.commit()  # Manual commit
            # else: no commit, transaction rolls back

    Features:
    - NO automatic commit
    - Automatic rollback on exception
    - Guaranteed session.close() in finally block
    - Connection pool safe (prevents leaks)

    Yields:
        Session: SQLAlchemy database session

    Raises:
        RuntimeError: If database not initialized
        SQLAlchemyError: If database operation fails
    """
    from app.models import get_db_session

    session = get_db_session()

    try:
        yield session
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database session error (no-commit): {e}", exc_info=True)
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error in database session (no-commit): {e}", exc_info=True)
        raise
    finally:
        session.close()


def execute_in_session(func, *args, **kwargs):
    """
    Execute a function within a database session context.

    Utility function for wrapping database operations without explicit 'with' blocks.

    Usage:
        def create_booking(session, booking_data):
            booking = Booking(**booking_data)
            session.add(booking)
            return booking

        booking = execute_in_session(create_booking, booking_data={'customer': 'Test'})

    Args:
        func: Function to execute (must accept session as first argument)
        *args: Additional positional arguments for func
        **kwargs: Additional keyword arguments for func

    Returns:
        Return value of func

    Raises:
        RuntimeError: If database not initialized
        SQLAlchemyError: If database operation fails
    """
    with db_session_scope() as session:
        return func(session, *args, **kwargs)
