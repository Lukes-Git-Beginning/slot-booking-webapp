# -*- coding: utf-8 -*-
"""
T2 Models Tests
Comprehensive tests for T2 Booking and Bucket System models
"""

import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError


@pytest.mark.database
class TestT2BookingModel:
    """Test suite for T2Booking model"""

    def test_create_t2_booking_minimal(self, db_session):
        """Test creating a T2 booking with minimal required fields"""
        from app.models.t2_booking import T2Booking

        booking = T2Booking(
            booking_id='T2-ABC123',
            coach='David',
            berater='Christian',
            customer='Müller, Hans',
            date=date(2026, 1, 15),
            time='14:00',
            user='test.opener'
        )

        db_session.add(booking)
        db_session.commit()

        assert booking.id is not None
        assert booking.booking_id == 'T2-ABC123'
        assert booking.coach == 'David'
        assert booking.berater == 'Christian'
        assert booking.status == 'active'  # Default

    def test_create_t2_booking_all_fields(self, db_session):
        """Test creating a T2 booking with all fields"""
        from app.models.t2_booking import T2Booking

        booking = T2Booking(
            booking_id='T2-XYZ789',
            coach='Alexander',
            berater='Daniel',
            customer='Schmidt, Anna',
            date=date(2026, 1, 20),
            time='16:00',
            topic='Verkaufsgespräch Premium',
            email='schmidt@example.com',
            user='dominik.mikic',
            event_id='google_event_123',
            calendar_id='daniel@example.com',
            status='active'
        )

        db_session.add(booking)
        db_session.commit()

        assert booking.topic == 'Verkaufsgespräch Premium'
        assert booking.email == 'schmidt@example.com'
        assert booking.event_id == 'google_event_123'
        assert booking.calendar_id == 'daniel@example.com'

    def test_t2_booking_id_unique(self, db_session):
        """Test that booking_id must be unique"""
        from app.models.t2_booking import T2Booking

        booking1 = T2Booking(
            booking_id='T2-DUPLICATE',
            coach='David',
            berater='Christian',
            customer='Test 1',
            date=date(2026, 1, 15),
            time='14:00',
            user='user1'
        )

        db_session.add(booking1)
        db_session.commit()

        # Duplicate should fail
        booking2 = T2Booking(
            booking_id='T2-DUPLICATE',
            coach='Alexander',
            berater='Daniel',
            customer='Test 2',
            date=date(2026, 1, 16),
            time='16:00',
            user='user2'
        )

        db_session.add(booking2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_t2_booking_status_values(self, db_session):
        """Test different status values"""
        from app.models.t2_booking import T2Booking

        statuses = ['active', 'cancelled', 'rescheduled']

        for idx, status in enumerate(statuses):
            booking = T2Booking(
                booking_id=f'T2-STATUS{idx}',
                coach='David',
                berater='Christian',
                customer=f'Customer {idx}',
                date=date(2026, 1, 15 + idx),
                time='14:00',
                user='test.user',
                status=status
            )
            db_session.add(booking)

        db_session.commit()

        # Query each status
        for status in statuses:
            result = db_session.query(T2Booking).filter_by(status=status).first()
            assert result is not None
            assert result.status == status

    def test_query_t2_bookings_by_user(self, db_session):
        """Test querying T2 bookings by opener user"""
        from app.models.t2_booking import T2Booking

        # Create 3 bookings for user1
        for i in range(3):
            booking = T2Booking(
                booking_id=f'T2-USER1-{i}',
                coach='David',
                berater='Christian',
                customer=f'Customer {i}',
                date=date(2026, 1, 15 + i),
                time='14:00',
                user='user1'
            )
            db_session.add(booking)

        # Create 2 bookings for user2
        for i in range(2):
            booking = T2Booking(
                booking_id=f'T2-USER2-{i}',
                coach='Alexander',
                berater='Daniel',
                customer=f'Customer {i}',
                date=date(2026, 1, 20 + i),
                time='16:00',
                user='user2'
            )
            db_session.add(booking)

        db_session.commit()

        # Query user1's bookings
        user1_bookings = db_session.query(T2Booking).filter_by(user='user1').all()
        assert len(user1_bookings) == 3

        # Query user2's bookings
        user2_bookings = db_session.query(T2Booking).filter_by(user='user2').all()
        assert len(user2_bookings) == 2

    def test_query_t2_bookings_by_berater(self, db_session):
        """Test querying T2 bookings by berater"""
        from app.models.t2_booking import T2Booking

        # Create bookings for different berater
        for i, berater in enumerate(['Christian', 'Daniel', 'Tim']):
            booking = T2Booking(
                booking_id=f'T2-BERATER-{i}',
                coach='David',
                berater=berater,
                customer=f'Customer {i}',
                date=date(2026, 1, 15),
                time='14:00',
                user='test.user'
            )
            db_session.add(booking)

        db_session.commit()

        # Query Christian's bookings
        christian_bookings = db_session.query(T2Booking).filter_by(berater='Christian').all()
        assert len(christian_bookings) == 1
        assert christian_bookings[0].berater == 'Christian'

    def test_t2_booking_reschedule_tracking(self, db_session):
        """Test reschedule tracking functionality"""
        from app.models.t2_booking import T2Booking

        # Original booking
        original = T2Booking(
            booking_id='T2-ORIGINAL',
            coach='David',
            berater='Christian',
            customer='Test Customer',
            date=date(2026, 1, 15),
            time='14:00',
            user='test.user',
            status='rescheduled'  # Mark as rescheduled
        )

        db_session.add(original)
        db_session.commit()

        # Rescheduled booking (references original)
        rescheduled = T2Booking(
            booking_id='T2-RESCHEDULED',
            coach='David',
            berater='Christian',
            customer='Test Customer',
            date=date(2026, 1, 22),  # New date
            time='16:00',  # New time
            user='test.user',
            status='active',
            is_rescheduled_from='T2-ORIGINAL'  # Link to original
        )

        db_session.add(rescheduled)
        db_session.commit()

        # Verify relationship
        assert rescheduled.is_rescheduled_from == 'T2-ORIGINAL'
        assert original.status == 'rescheduled'

    def test_t2_booking_to_dict(self, db_session):
        """Test T2Booking to_dict() method"""
        from app.models.t2_booking import T2Booking

        booking = T2Booking(
            booking_id='T2-DICT-TEST',
            coach='David',
            berater='Christian',
            customer='Dict Test Customer',
            date=date(2026, 1, 15),
            time='14:00',
            topic='Test Topic',
            email='test@example.com',
            user='test.user',
            event_id='event123',
            calendar_id='cal@example.com',
            status='active'
        )

        db_session.add(booking)
        db_session.commit()

        dict_data = booking.to_dict()

        assert dict_data['id'] == 'T2-DICT-TEST'
        assert dict_data['coach'] == 'David'
        assert dict_data['berater'] == 'Christian'
        assert dict_data['customer'] == 'Dict Test Customer'
        assert dict_data['date'] == '2026-01-15'
        assert dict_data['time'] == '14:00'
        assert dict_data['topic'] == 'Test Topic'
        assert dict_data['email'] == 'test@example.com'
        assert dict_data['user'] == 'test.user'
        assert dict_data['event_id'] == 'event123'
        assert dict_data['status'] == 'active'


@pytest.mark.database
class TestT2CloserConfigModel:
    """Test suite for T2CloserConfig model"""

    def test_create_closer_config(self, db_session):
        """Test creating a closer configuration"""
        from app.models.t2_bucket import T2CloserConfig

        closer = T2CloserConfig(
            name='David',
            full_name='David Nehm',
            color='blue',
            default_probability=9.0,
            is_active=True
        )

        db_session.add(closer)
        db_session.commit()

        assert closer.id is not None
        assert closer.name == 'David'
        assert closer.default_probability == 9.0

    def test_closer_name_unique(self, db_session):
        """Test that closer name must be unique"""
        from app.models.t2_bucket import T2CloserConfig

        closer1 = T2CloserConfig(
            name='David',
            full_name='David Nehm',
            color='blue',
            default_probability=9.0
        )

        db_session.add(closer1)
        db_session.commit()

        # Duplicate name should fail
        closer2 = T2CloserConfig(
            name='David',  # Duplicate!
            full_name='Different Name',
            color='red',
            default_probability=5.0
        )

        db_session.add(closer2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_active_closers(self, db_session):
        """Test querying only active closers"""
        from app.models.t2_bucket import T2CloserConfig

        # Create active and inactive closers
        closers = [
            T2CloserConfig(name='David', full_name='David Nehm', color='blue', default_probability=9.0, is_active=True),
            T2CloserConfig(name='Alexander', full_name='Alexander Nehm', color='red', default_probability=9.0, is_active=True),
            T2CloserConfig(name='Jose', full_name='Jose Torspecken', color='green', default_probability=2.0, is_active=False),
        ]

        for closer in closers:
            db_session.add(closer)

        db_session.commit()

        # Query only active
        active = db_session.query(T2CloserConfig).filter_by(is_active=True).all()
        assert len(active) == 2

        # Query inactive
        inactive = db_session.query(T2CloserConfig).filter_by(is_active=False).all()
        assert len(inactive) == 1
        assert inactive[0].name == 'Jose'


@pytest.mark.database
class TestT2BucketStateModel:
    """Test suite for T2BucketState model"""

    def test_create_bucket_state(self, db_session):
        """Test creating bucket state"""
        from app.models.t2_bucket import T2BucketState

        state = T2BucketState(
            singleton_id=1,
            probabilities={'David': 9.0, 'Alexander': 9.0, 'Jose': 2.0},
            bucket=['David', 'Alexander', 'Jose'],
            total_draws=0,
            stats={'David': 0, 'Alexander': 0, 'Jose': 0},
            max_draws_before_reset=20,
            last_reset=datetime.utcnow()
        )

        db_session.add(state)
        db_session.commit()

        assert state.id is not None
        assert state.singleton_id == 1
        assert state.total_draws == 0
        assert len(state.bucket) == 3

    def test_bucket_singleton_constraint(self, db_session):
        """Test that only one bucket state can exist (singleton)"""
        from app.models.t2_bucket import T2BucketState

        state1 = T2BucketState(
            singleton_id=1,
            probabilities={'David': 9.0},
            bucket=['David'],
            total_draws=0,
            stats={'David': 0},
            max_draws_before_reset=20,
            last_reset=datetime.utcnow()
        )

        db_session.add(state1)
        db_session.commit()

        # Duplicate singleton_id should fail
        state2 = T2BucketState(
            singleton_id=1,  # Same singleton_id!
            probabilities={'Alexander': 9.0},
            bucket=['Alexander'],
            total_draws=5,
            stats={'Alexander': 5},
            max_draws_before_reset=20,
            last_reset=datetime.utcnow()
        )

        db_session.add(state2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_bucket_state_json_fields(self, db_session):
        """Test JSON fields (probabilities, bucket, stats)"""
        from app.models.t2_bucket import T2BucketState

        state = T2BucketState(
            singleton_id=1,
            probabilities={'David': 9.0, 'Alexander': 7.5, 'Jose': 1.5},
            bucket=['David'] * 9 + ['Alexander'] * 7 + ['Jose'] * 1,
            total_draws=5,
            stats={'David': 3, 'Alexander': 1, 'Jose': 1},
            max_draws_before_reset=20,
            last_reset=datetime.utcnow()
        )

        db_session.add(state)
        db_session.commit()

        # Verify JSON fields stored correctly
        assert state.probabilities['David'] == 9.0
        assert state.probabilities['Alexander'] == 7.5
        assert state.stats['David'] == 3
        assert len(state.bucket) == 17


@pytest.mark.database
class TestT2DrawHistoryModel:
    """Test suite for T2DrawHistory model"""

    def test_create_draw_history(self, db_session):
        """Test creating a draw history record"""
        from app.models.t2_bucket import T2DrawHistory

        draw = T2DrawHistory(
            username='dominik.mikic',
            closer_drawn='David',
            draw_type='T2',
            customer_name='Müller, Hans',
            bucket_size_after=19,
            probability_after=9.0,
            drawn_at=datetime.utcnow()
        )

        db_session.add(draw)
        db_session.commit()

        assert draw.id is not None
        assert draw.username == 'dominik.mikic'
        assert draw.closer_drawn == 'David'

    def test_query_draws_by_user(self, db_session):
        """Test querying draw history by username"""
        from app.models.t2_bucket import T2DrawHistory

        # Create draws for multiple users
        now = datetime.utcnow()

        for i in range(3):
            draw = T2DrawHistory(
                username='user1',
                closer_drawn='David',
                draw_type='T2',
                bucket_size_after=19,
                probability_after=9.0,
                drawn_at=now - timedelta(days=i)
            )
            db_session.add(draw)

        for i in range(2):
            draw = T2DrawHistory(
                username='user2',
                closer_drawn='Alexander',
                draw_type='T2',
                bucket_size_after=19,
                probability_after=9.0,
                drawn_at=now - timedelta(days=i)
            )
            db_session.add(draw)

        db_session.commit()

        # Query user1's draws
        user1_draws = db_session.query(T2DrawHistory).filter_by(username='user1').all()
        assert len(user1_draws) == 3

    def test_query_draws_by_closer(self, db_session):
        """Test querying draws by closer"""
        from app.models.t2_bucket import T2DrawHistory

        now = datetime.utcnow()

        for closer in ['David', 'Alexander', 'Jose']:
            draw = T2DrawHistory(
                username='test.user',
                closer_drawn=closer,
                draw_type='T2',
                bucket_size_after=19,
                probability_after=9.0,
                drawn_at=now
            )
            db_session.add(draw)

        db_session.commit()

        # Query David's draws
        david_draws = db_session.query(T2DrawHistory).filter_by(closer_drawn='David').all()
        assert len(david_draws) == 1
        assert david_draws[0].closer_drawn == 'David'

    def test_draw_history_to_dict(self, db_session):
        """Test DrawHistory to_dict() method"""
        from app.models.t2_bucket import T2DrawHistory

        now = datetime.utcnow()

        draw = T2DrawHistory(
            username='test.user',
            closer_drawn='David',
            draw_type='T2',
            customer_name='Test Customer',
            bucket_size_after=19,
            probability_after=9.0,
            drawn_at=now
        )

        db_session.add(draw)
        db_session.commit()

        dict_data = draw.to_dict()

        assert dict_data['user'] == 'test.user'
        assert dict_data['closer'] == 'David'
        assert dict_data['draw_type'] == 'T2'
        assert dict_data['customer_name'] == 'Test Customer'
        assert dict_data['bucket_size_after'] == 19


@pytest.mark.database
class TestT2UserLastDrawModel:
    """Test suite for T2UserLastDraw model"""

    def test_create_user_last_draw(self, db_session):
        """Test creating a user last draw record"""
        from app.models.t2_bucket import T2UserLastDraw

        now = datetime.utcnow()

        last_draw = T2UserLastDraw(
            username='dominik.mikic',
            last_draw_at=now,
            last_closer_drawn='David',
            last_draw_type='T2',
            last_customer_name='Test Customer'
        )

        db_session.add(last_draw)
        db_session.commit()

        assert last_draw.id is not None
        assert last_draw.username == 'dominik.mikic'
        assert last_draw.last_closer_drawn == 'David'

    def test_username_unique_constraint(self, db_session):
        """Test that username must be unique"""
        from app.models.t2_bucket import T2UserLastDraw

        now = datetime.utcnow()

        last_draw1 = T2UserLastDraw(
            username='duplicate.user',
            last_draw_at=now,
            last_closer_drawn='David',
            last_draw_type='T2'
        )

        db_session.add(last_draw1)
        db_session.commit()

        # Duplicate username should fail
        last_draw2 = T2UserLastDraw(
            username='duplicate.user',  # Duplicate!
            last_draw_at=now,
            last_closer_drawn='Alexander',
            last_draw_type='T2'
        )

        db_session.add(last_draw2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_update_last_draw(self, db_session):
        """Test updating user's last draw (simulates upsert)"""
        from app.models.t2_bucket import T2UserLastDraw

        now = datetime.utcnow()

        # Create initial record
        last_draw = T2UserLastDraw(
            username='test.user',
            last_draw_at=now,
            last_closer_drawn='David',
            last_draw_type='T2'
        )

        db_session.add(last_draw)
        db_session.commit()

        # Update the record (simulating a new draw)
        later = now + timedelta(minutes=5)
        last_draw.last_draw_at = later
        last_draw.last_closer_drawn = 'Alexander'

        db_session.commit()

        # Verify update
        updated = db_session.query(T2UserLastDraw).filter_by(username='test.user').first()
        assert updated.last_closer_drawn == 'Alexander'
        assert updated.last_draw_at > now

    def test_last_draw_to_dict(self, db_session):
        """Test UserLastDraw to_dict() method"""
        from app.models.t2_bucket import T2UserLastDraw

        now = datetime.utcnow()

        last_draw = T2UserLastDraw(
            username='test.user',
            last_draw_at=now,
            last_closer_drawn='David',
            last_draw_type='T2',
            last_customer_name='Test Customer'
        )

        db_session.add(last_draw)
        db_session.commit()

        dict_data = last_draw.to_dict()

        assert dict_data['closer'] == 'David'
        assert dict_data['draw_type'] == 'T2'
        assert dict_data['customer_name'] == 'Test Customer'
        assert 'timestamp' in dict_data
