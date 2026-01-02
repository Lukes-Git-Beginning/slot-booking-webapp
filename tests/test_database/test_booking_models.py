# -*- coding: utf-8 -*-
"""
Booking Models Tests
Comprehensive tests for Booking and BookingOutcome models
"""

import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError


@pytest.mark.database
class TestBookingModel:
    """Test suite for Booking model CRUD operations"""

    def test_create_booking_minimal(self, db_session):
        """Test creating a booking with minimal required fields"""
        from app.models.booking import Booking

        booking = Booking(
            booking_id='2026-01-15_14:00_mueller',
            username='test.user',
            customer='Müller, Hans',
            date=date(2026, 1, 15),
            time='14:00',
            weekday='Wednesday',
            week_number=3,
            potential_type='normal',
            color_id='9',
            description_length=0,
            has_description=False,
            booking_lead_time=7,
            booked_at_hour=10,
            booked_on_weekday='Wednesday'
        )

        db_session.add(booking)
        db_session.commit()

        assert booking.id is not None
        assert booking.booking_id == '2026-01-15_14:00_mueller'
        assert booking.username == 'test.user'
        assert booking.customer == 'Müller, Hans'

    def test_create_booking_all_fields(self, db_session):
        """Test creating a booking with all fields populated"""
        from app.models.booking import Booking

        now = datetime.utcnow()
        booking = Booking(
            booking_id='2026-01-20_16:00_schmidt',
            username='admin.user',
            customer='Schmidt, Anna',
            date=date(2026, 1, 20),
            time='16:00',
            weekday='Monday',
            week_number=4,
            potential_type='top',
            color_id='11',
            description_length=150,
            has_description=True,
            booking_lead_time=14,
            booked_at_hour=15,
            booked_on_weekday='Monday',
            booking_timestamp=now
        )

        db_session.add(booking)
        db_session.commit()

        assert booking.id is not None
        assert booking.potential_type == 'top'
        assert booking.color_id == '11'
        assert booking.has_description is True
        assert booking.description_length == 150

    def test_booking_id_unique_constraint(self, db_session):
        """Test that booking_id must be unique"""
        from app.models.booking import Booking

        booking1 = Booking(
            booking_id='duplicate_id',
            username='user1',
            customer='Test 1',
            date=date(2026, 1, 15),
            time='14:00',
            weekday='Wednesday',
            week_number=3,
            potential_type='normal',
            color_id='9',
            description_length=0,
            has_description=False,
            booking_lead_time=7,
            booked_at_hour=10,
            booked_on_weekday='Wednesday'
        )

        db_session.add(booking1)
        db_session.commit()

        # Duplicate booking_id should fail
        booking2 = Booking(
            booking_id='duplicate_id',  # Same ID!
            username='user2',
            customer='Test 2',
            date=date(2026, 1, 16),
            time='15:00',
            weekday='Thursday',
            week_number=3,
            potential_type='normal',
            color_id='9',
            description_length=0,
            has_description=False,
            booking_lead_time=7,
            booked_at_hour=10,
            booked_on_weekday='Thursday'
        )

        db_session.add(booking2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_booking_by_username(self, db_session):
        """Test querying bookings by username"""
        from app.models.booking import Booking

        # Create 3 bookings for user1
        for i in range(3):
            booking = Booking(
                booking_id=f'user1_booking_{i}',
                username='user1',
                customer=f'Customer {i}',
                date=date(2026, 1, 15 + i),
                time='14:00',
                weekday='Wednesday',
                week_number=3,
                potential_type='normal',
                color_id='9',
                description_length=0,
                has_description=False,
                booking_lead_time=7,
                booked_at_hour=10,
                booked_on_weekday='Wednesday'
            )
            db_session.add(booking)

        # Create 2 bookings for user2
        for i in range(2):
            booking = Booking(
                booking_id=f'user2_booking_{i}',
                username='user2',
                customer=f'Customer {i}',
                date=date(2026, 1, 20 + i),
                time='16:00',
                weekday='Monday',
                week_number=4,
                potential_type='normal',
                color_id='9',
                description_length=0,
                has_description=False,
                booking_lead_time=7,
                booked_at_hour=10,
                booked_on_weekday='Monday'
            )
            db_session.add(booking)

        db_session.commit()

        # Query user1's bookings
        user1_bookings = db_session.query(Booking).filter_by(username='user1').all()
        assert len(user1_bookings) == 3

        # Query user2's bookings
        user2_bookings = db_session.query(Booking).filter_by(username='user2').all()
        assert len(user2_bookings) == 2

    def test_query_booking_by_date_range(self, db_session):
        """Test querying bookings within a date range"""
        from app.models.booking import Booking

        # Create bookings across different dates
        dates = [date(2026, 1, 10), date(2026, 1, 15), date(2026, 1, 20), date(2026, 1, 25)]

        for idx, booking_date in enumerate(dates):
            booking = Booking(
                booking_id=f'booking_{idx}',
                username='test.user',
                customer=f'Customer {idx}',
                date=booking_date,
                time='14:00',
                weekday='Wednesday',
                week_number=3,
                potential_type='normal',
                color_id='9',
                description_length=0,
                has_description=False,
                booking_lead_time=7,
                booked_at_hour=10,
                booked_on_weekday='Wednesday'
            )
            db_session.add(booking)

        db_session.commit()

        # Query bookings between Jan 12 and Jan 22
        start_date = date(2026, 1, 12)
        end_date = date(2026, 1, 22)

        results = db_session.query(Booking).filter(
            Booking.date >= start_date,
            Booking.date <= end_date
        ).all()

        # Should get 2 bookings (Jan 15 and Jan 20)
        assert len(results) == 2
        assert all(start_date <= booking.date <= end_date for booking in results)

    def test_query_booking_by_customer(self, db_session):
        """Test querying bookings by customer name"""
        from app.models.booking import Booking

        booking = Booking(
            booking_id='customer_test',
            username='test.user',
            customer='Müller, Hans',
            date=date(2026, 1, 15),
            time='14:00',
            weekday='Wednesday',
            week_number=3,
            potential_type='normal',
            color_id='9',
            description_length=0,
            has_description=False,
            booking_lead_time=7,
            booked_at_hour=10,
            booked_on_weekday='Wednesday'
        )

        db_session.add(booking)
        db_session.commit()

        # Query by customer
        result = db_session.query(Booking).filter_by(customer='Müller, Hans').first()
        assert result is not None
        assert result.customer == 'Müller, Hans'
        assert result.booking_id == 'customer_test'

    def test_booking_indexes_exist(self, test_db_engine):
        """Verify that performance indexes are created"""
        from sqlalchemy import inspect

        inspector = inspect(test_db_engine)
        indexes = inspector.get_indexes('bookings')

        # Extract index names
        index_names = [idx['name'] for idx in indexes]

        # Check for expected indexes
        assert 'idx_booking_username_date' in index_names
        assert 'idx_booking_date' in index_names
        assert 'idx_booking_customer' in index_names
        assert 'idx_booking_week' in index_names

    def test_booking_repr(self, db_session):
        """Test Booking __repr__ method"""
        from app.models.booking import Booking

        booking = Booking(
            booking_id='repr_test',
            username='test.user',
            customer='Schmidt, Anna',
            date=date(2026, 1, 15),
            time='14:00',
            weekday='Wednesday',
            week_number=3,
            potential_type='normal',
            color_id='9',
            description_length=0,
            has_description=False,
            booking_lead_time=7,
            booked_at_hour=10,
            booked_on_weekday='Wednesday'
        )

        db_session.add(booking)
        db_session.flush()

        repr_string = repr(booking)
        assert "Booking(id='repr_test'" in repr_string
        assert "customer='Schmidt, Anna'" in repr_string
        assert "user='test.user'" in repr_string

    def test_delete_booking(self, db_session):
        """Test deleting a booking"""
        from app.models.booking import Booking

        booking = Booking(
            booking_id='delete_test',
            username='test.user',
            customer='Delete Test',
            date=date(2026, 1, 15),
            time='14:00',
            weekday='Wednesday',
            week_number=3,
            potential_type='normal',
            color_id='9',
            description_length=0,
            has_description=False,
            booking_lead_time=7,
            booked_at_hour=10,
            booked_on_weekday='Wednesday'
        )

        db_session.add(booking)
        db_session.commit()

        # Verify it exists
        assert db_session.query(Booking).filter_by(booking_id='delete_test').first() is not None

        # Delete it
        db_session.delete(booking)
        db_session.commit()

        # Verify it's gone
        assert db_session.query(Booking).filter_by(booking_id='delete_test').first() is None

    def test_update_booking(self, db_session):
        """Test updating a booking's fields"""
        from app.models.booking import Booking

        booking = Booking(
            booking_id='update_test',
            username='test.user',
            customer='Original Customer',
            date=date(2026, 1, 15),
            time='14:00',
            weekday='Wednesday',
            week_number=3,
            potential_type='normal',
            color_id='9',
            description_length=0,
            has_description=False,
            booking_lead_time=7,
            booked_at_hour=10,
            booked_on_weekday='Wednesday'
        )

        db_session.add(booking)
        db_session.commit()

        # Update customer
        booking.customer = 'Updated Customer'
        booking.potential_type = 'top'
        booking.color_id = '11'

        db_session.commit()

        # Verify update
        updated = db_session.query(Booking).filter_by(booking_id='update_test').first()
        assert updated.customer == 'Updated Customer'
        assert updated.potential_type == 'top'
        assert updated.color_id == '11'


@pytest.mark.database
class TestBookingOutcomeModel:
    """Test suite for BookingOutcome model"""

    def test_create_outcome_minimal(self, db_session):
        """Test creating an outcome with minimal fields"""
        from app.models.booking import BookingOutcome

        outcome = BookingOutcome(
            outcome_id='2026-01-15_14:00_mueller_outcome',
            customer='Müller, Hans',
            date=date(2026, 1, 15),
            time='14:00',
            outcome='completed',
            color_id='9',
            potential_type='normal',
            checked_at='21:00'
        )

        db_session.add(outcome)
        db_session.commit()

        assert outcome.id is not None
        assert outcome.outcome == 'completed'
        assert outcome.customer == 'Müller, Hans'

    def test_create_outcome_with_booking_reference(self, db_session):
        """Test creating an outcome linked to a booking"""
        from app.models.booking import Booking, BookingOutcome

        # Create a booking first
        booking = Booking(
            booking_id='booking_with_outcome',
            username='test.user',
            customer='Test Customer',
            date=date(2026, 1, 15),
            time='14:00',
            weekday='Wednesday',
            week_number=3,
            potential_type='normal',
            color_id='9',
            description_length=0,
            has_description=False,
            booking_lead_time=7,
            booked_at_hour=10,
            booked_on_weekday='Wednesday'
        )

        db_session.add(booking)
        db_session.commit()

        # Create outcome referencing the booking
        outcome = BookingOutcome(
            outcome_id='outcome_with_booking_ref',
            booking_id='booking_with_outcome',  # Reference!
            customer='Test Customer',
            date=date(2026, 1, 15),
            time='14:00',
            outcome='completed',
            color_id='9',
            potential_type='normal',
            checked_at='21:00'
        )

        db_session.add(outcome)
        db_session.commit()

        assert outcome.booking_id == 'booking_with_outcome'

    def test_outcome_types(self, db_session):
        """Test different outcome types"""
        from app.models.booking import BookingOutcome

        outcomes = ['completed', 'no_show', 'cancelled', 'rescheduled']

        for idx, outcome_type in enumerate(outcomes):
            outcome = BookingOutcome(
                outcome_id=f'outcome_{outcome_type}_{idx}',
                customer=f'Customer {idx}',
                date=date(2026, 1, 15),
                time='14:00',
                outcome=outcome_type,
                color_id='9',
                potential_type='normal',
                checked_at='21:00',
                is_alert=(outcome_type == 'no_show')  # Alert for no-shows
            )

            db_session.add(outcome)

        db_session.commit()

        # Verify all created
        all_outcomes = db_session.query(BookingOutcome).all()
        assert len(all_outcomes) == 4

        # Verify no-show has alert flag
        no_show = db_session.query(BookingOutcome).filter_by(outcome='no_show').first()
        assert no_show.is_alert is True

    def test_query_outcomes_by_type(self, db_session):
        """Test querying outcomes by type"""
        from app.models.booking import BookingOutcome

        # Create 2 completed, 1 no_show
        for i in range(2):
            outcome = BookingOutcome(
                outcome_id=f'completed_{i}',
                customer=f'Customer {i}',
                date=date(2026, 1, 15),
                time='14:00',
                outcome='completed',
                color_id='9',
                potential_type='normal',
                checked_at='21:00'
            )
            db_session.add(outcome)

        no_show = BookingOutcome(
            outcome_id='no_show_1',
            customer='No Show Customer',
            date=date(2026, 1, 15),
            time='16:00',
            outcome='no_show',
            color_id='9',
            potential_type='normal',
            checked_at='21:00',
            is_alert=True
        )
        db_session.add(no_show)

        db_session.commit()

        # Query completed outcomes
        completed = db_session.query(BookingOutcome).filter_by(outcome='completed').all()
        assert len(completed) == 2

        # Query no-shows
        no_shows = db_session.query(BookingOutcome).filter_by(outcome='no_show').all()
        assert len(no_shows) == 1
        assert no_shows[0].is_alert is True

    def test_query_outcomes_with_alerts(self, db_session):
        """Test querying outcomes flagged as alerts"""
        from app.models.booking import BookingOutcome

        # Create outcomes with and without alerts
        for i in range(3):
            outcome = BookingOutcome(
                outcome_id=f'alert_test_{i}',
                customer=f'Customer {i}',
                date=date(2026, 1, 15),
                time='14:00',
                outcome='no_show' if i % 2 == 0 else 'completed',
                color_id='9',
                potential_type='normal',
                checked_at='21:00',
                is_alert=(i % 2 == 0)  # Every other one
            )
            db_session.add(outcome)

        db_session.commit()

        # Query only alerts
        alerts = db_session.query(BookingOutcome).filter_by(is_alert=True).all()
        assert len(alerts) == 2  # 2 out of 3

    def test_outcome_with_description(self, db_session):
        """Test outcome with description field"""
        from app.models.booking import BookingOutcome

        outcome = BookingOutcome(
            outcome_id='outcome_with_desc',
            customer='Test Customer',
            date=date(2026, 1, 15),
            time='14:00',
            outcome='completed',
            color_id='9',
            potential_type='top',
            checked_at='21:00',
            description='Customer was very satisfied. Top quality lead.'
        )

        db_session.add(outcome)
        db_session.commit()

        # Verify description stored
        result = db_session.query(BookingOutcome).filter_by(outcome_id='outcome_with_desc').first()
        assert result.description == 'Customer was very satisfied. Top quality lead.'

    def test_outcome_indexes_exist(self, test_db_engine):
        """Verify that performance indexes are created for outcomes"""
        from sqlalchemy import inspect

        inspector = inspect(test_db_engine)
        indexes = inspector.get_indexes('booking_outcomes')

        # Extract index names
        index_names = [idx['name'] for idx in indexes]

        # Check for expected indexes
        assert 'idx_outcome_customer' in index_names
        assert 'idx_outcome_date' in index_names
        assert 'idx_outcome_outcome' in index_names
        assert 'idx_outcome_booking_id' in index_names
        assert 'idx_outcome_alert' in index_names

    def test_outcome_repr(self, db_session):
        """Test BookingOutcome __repr__ method"""
        from app.models.booking import BookingOutcome

        outcome = BookingOutcome(
            outcome_id='repr_test',
            customer='Schmidt, Anna',
            date=date(2026, 1, 15),
            time='14:00',
            outcome='completed',
            color_id='9',
            potential_type='normal',
            checked_at='21:00'
        )

        db_session.add(outcome)
        db_session.flush()

        repr_string = repr(outcome)
        assert "BookingOutcome(id='repr_test'" in repr_string
        assert "customer='Schmidt, Anna'" in repr_string
        assert "outcome='completed'" in repr_string

    def test_delete_outcome(self, db_session):
        """Test deleting an outcome"""
        from app.models.booking import BookingOutcome

        outcome = BookingOutcome(
            outcome_id='delete_outcome_test',
            customer='Delete Test',
            date=date(2026, 1, 15),
            time='14:00',
            outcome='completed',
            color_id='9',
            potential_type='normal',
            checked_at='21:00'
        )

        db_session.add(outcome)
        db_session.commit()

        # Verify exists
        assert db_session.query(BookingOutcome).filter_by(outcome_id='delete_outcome_test').first() is not None

        # Delete
        db_session.delete(outcome)
        db_session.commit()

        # Verify gone
        assert db_session.query(BookingOutcome).filter_by(outcome_id='delete_outcome_test').first() is None

    def test_update_outcome(self, db_session):
        """Test updating an outcome"""
        from app.models.booking import BookingOutcome

        outcome = BookingOutcome(
            outcome_id='update_outcome_test',
            customer='Original Customer',
            date=date(2026, 1, 15),
            time='14:00',
            outcome='completed',
            color_id='9',
            potential_type='normal',
            checked_at='21:00'
        )

        db_session.add(outcome)
        db_session.commit()

        # Update outcome type
        outcome.outcome = 'rescheduled'
        outcome.description = 'Customer requested different time'

        db_session.commit()

        # Verify update
        updated = db_session.query(BookingOutcome).filter_by(outcome_id='update_outcome_test').first()
        assert updated.outcome == 'rescheduled'
        assert updated.description == 'Customer requested different time'
