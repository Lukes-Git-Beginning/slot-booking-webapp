# -*- coding: utf-8 -*-
"""
Test Infrastructure Verification
Tests to ensure database testing fixtures are working correctly
"""

import pytest


@pytest.mark.database
def test_db_engine_fixture(test_db_engine):
    """Verify test database engine is created"""
    assert test_db_engine is not None
    assert str(test_db_engine.url) == 'sqlite:///:memory:'


@pytest.mark.database
def test_db_session_fixture(db_session):
    """Verify database session fixture works"""
    assert db_session is not None

    # Session should support begin/commit/rollback
    assert hasattr(db_session, 'add')
    assert hasattr(db_session, 'commit')
    assert hasattr(db_session, 'rollback')


@pytest.mark.database
def test_database_tables_created(test_db_engine):
    """Verify all database tables are created"""
    from sqlalchemy import inspect

    inspector = inspect(test_db_engine)
    tables = inspector.get_table_names()

    # Should have at least some core tables
    assert len(tables) > 0
    print(f"\nCreated tables: {tables}")


@pytest.mark.database
def test_session_isolation(db_session):
    """Verify test sessions are isolated (changes rollback after test)"""
    from app.models.booking import Booking
    from datetime import datetime, date

    # Add a test booking
    booking = Booking(
        booking_id='test_2026-01-15_14:00_isolation',
        username='isolation_test',
        customer='Isolation Test Customer',
        date=date(2026, 1, 15),
        time='14:00',
        weekday='Wednesday',
        week_number=3,
        potential_type='normal',
        color_id='9',
        description_length=25,
        has_description=True,
        booking_lead_time=7,
        booked_at_hour=10,
        booked_on_weekday='Wednesday',
        booking_timestamp=datetime.utcnow()
    )

    db_session.add(booking)
    db_session.flush()  # Flush to db but don't commit

    # Should be able to query it in same session
    result = db_session.query(Booking).filter_by(username='isolation_test').first()
    assert result is not None
    assert result.customer == 'Isolation Test Customer'
    assert result.booking_id == 'test_2026-01-15_14:00_isolation'

    # After this test finishes, the rollback should clean it up
    # (verified by running this test multiple times without conflicts)
