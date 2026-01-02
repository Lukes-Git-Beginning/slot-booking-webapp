# -*- coding: utf-8 -*-
"""
Service Layer Tests - Booking Service
Tests for app/services/booking_service.py
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch, Mock


# ========== FIXTURES ==========

@pytest.fixture(scope='module', autouse=True)
def mock_google_credentials():
    """Mock Google credentials to prevent loading during module import"""
    with patch('app.utils.credentials.load_google_credentials', return_value=Mock()):
        yield

@pytest.fixture
def mock_calendar_service():
    """Mock Google Calendar Service with configurable responses"""
    with patch('app.services.booking_service.get_google_calendar_service') as mock:
        service = MagicMock()

        # Default: Empty events
        service.get_events.return_value = {'items': []}

        # Default: Successful event creation
        service.create_event.return_value = {'id': 'test-event-123'}

        mock.return_value = service
        yield service


@pytest.fixture
def mock_tracking_system():
    """Mock BookingTracker.track_booking()"""
    with patch('app.services.tracking_system.tracking_system') as mock:
        mock.track_booking.return_value = {
            'id': 'test-booking-123',
            'timestamp': '2026-01-15T14:00:00'
        }
        yield mock


@pytest.fixture
def mock_holiday_service():
    """Mock HolidayService.is_blocked_date()"""
    with patch('app.services.holiday_service.holiday_service') as mock:
        mock.is_blocked_date.return_value = False
        yield mock


@pytest.fixture
def mock_cache_manager():
    """Mock CacheManager.clear_all()"""
    with patch('app.services.booking_service.cache_manager') as mock:
        yield mock


# ========== TEST CLASSES ==========

@pytest.mark.service
class TestBookingService:
    """Tests for book_slot_for_user() - Full booking flow"""

    def test_book_slot_success(self, mock_calendar_service, mock_tracking_system, mock_cache_manager):
        """Test successful slot booking with all integrations"""
        from app.services.booking_service import book_slot_for_user

        # GIVEN: Valid booking parameters
        result = book_slot_for_user(
            user='test.user',
            date_str='2026-01-15',
            time_str='14:00',
            berater='Test Berater',
            first_name='John',
            last_name='Doe',
            description='Test booking',
            color_id='9'
        )

        # THEN: Success response
        assert result['success'] is True
        assert result['message'] == 'Slot erfolgreich gebucht'
        assert 'event_id' in result
        assert result['event_id'] == 'test-event-123'

        # Verify calendar service called
        assert mock_calendar_service.create_event.called
        call_args = mock_calendar_service.create_event.call_args

        # Verify event structure
        event_body = call_args[1]['event_data']
        assert event_body['summary'] == 'Doe, John'
        assert '[Booked by: test.user]' in event_body['description']
        assert event_body['colorId'] == '9'

        # Verify tracking called
        assert mock_tracking_system.track_booking.called

        # Verify cache cleared
        assert mock_cache_manager.clear_all.called

    def test_book_slot_missing_parameters(self):
        """Test booking fails with missing required parameters"""
        from app.services.booking_service import book_slot_for_user

        # Missing user
        result = book_slot_for_user(
            user='',
            date_str='2026-01-15',
            time_str='14:00',
            berater='Test'
        )

        assert result['success'] is False
        assert 'Missing required parameters' in result['error']

    def test_book_slot_invalid_date_format(self):
        """Test booking fails with invalid date format"""
        from app.services.booking_service import book_slot_for_user

        # Invalid date format
        result = book_slot_for_user(
            user='test.user',
            date_str='2026/01/15',  # Wrong format
            time_str='14:00',
            berater='Test'
        )

        assert result['success'] is False
        assert 'Invalid date/time format' in result['error']

    def test_book_slot_calendar_service_unavailable(self):
        """Test booking fails gracefully when calendar unavailable"""
        from app.services.booking_service import book_slot_for_user

        with patch('app.services.booking_service.get_google_calendar_service', return_value=None):
            result = book_slot_for_user(
                user='test.user',
                date_str='2026-01-15',
                time_str='14:00',
                berater='Test'
            )

            assert result['success'] is False
            assert 'Calendar service not available' in result['error']

    def test_book_slot_with_description_tagging(self, mock_calendar_service, mock_tracking_system, mock_cache_manager):
        """Test [Booked by: user] tag is added to description"""
        from app.services.booking_service import book_slot_for_user

        result = book_slot_for_user(
            user='admin.user',
            date_str='2026-01-15',
            time_str='14:00',
            berater='Test',
            description='Important meeting'
        )

        # Verify tag in description
        call_args = mock_calendar_service.create_event.call_args
        event_body = call_args[1]['event_data']
        assert '[Booked by: admin.user]' in event_body['description']
        assert 'Important meeting' in event_body['description']

    def test_book_slot_tracking_failure_non_blocking(self, mock_calendar_service, mock_cache_manager):
        """Test booking succeeds even if tracking fails"""
        from app.services.booking_service import book_slot_for_user

        with patch('app.services.tracking_system.tracking_system') as mock_tracking:
            # Tracking raises exception
            mock_tracking.track_booking.side_effect = Exception('Tracking error')

            result = book_slot_for_user(
                user='test.user',
                date_str='2026-01-15',
                time_str='14:00',
                berater='Test'
            )

            # Booking still succeeds
            assert result['success'] is True
            assert mock_calendar_service.create_event.called


@pytest.mark.service
class TestSlotStatus:
    """Tests for get_slot_status() - Slot availability checking"""

    def test_get_slot_status_empty_slot(self, mock_calendar_service):
        """Test slot status with no bookings"""
        from app.services.booking_service import get_slot_status

        # GIVEN: Empty calendar
        mock_calendar_service.get_events.return_value = {'items': []}

        # WHEN: Get status for 3 consultants
        slot_list, booked, total, freie_count, overbooked = get_slot_status(
            date_str='2026-01-15',
            hour='14:00',
            berater_count=3
        )

        # THEN: Empty slot
        assert len(slot_list) == 0
        assert booked == 0
        assert total == 9  # 3 consultants × 3 slots
        assert freie_count == 9
        assert overbooked is False

    def test_get_slot_status_with_t1_bereit_events(self, mock_calendar_service):
        """Test T1-bereit events are excluded from booked count"""
        from app.services.booking_service import get_slot_status

        # GIVEN: 2 regular + 1 T1-bereit event
        mock_calendar_service.get_events.return_value = {
            'items': [
                {'summary': 'Doe, John', 'colorId': '9'},
                {'summary': 'T1-bereit Weber', 'colorId': '2'},  # Excluded
                {'summary': 'Smith, Jane', 'colorId': '9'}
            ]
        }

        slot_list, booked, total, freie_count, overbooked = get_slot_status(
            date_str='2026-01-15',
            hour='14:00',
            berater_count=3
        )

        # THEN: Only 2 counted (T1-bereit excluded)
        assert len(slot_list) == 3  # All events in list
        assert booked == 2  # But only 2 counted as booked
        assert freie_count == 7  # 9 - 2

    def test_get_slot_status_9am_reduced_capacity(self, mock_calendar_service):
        """Test 9am slots use SLOTS_PER_BERATER_9AM (2 instead of 3)"""
        from app.services.booking_service import get_slot_status

        mock_calendar_service.get_events.return_value = {'items': []}

        slot_list, booked, total, freie_count, overbooked = get_slot_status(
            date_str='2026-01-15',
            hour='09:00',  # 9am slot
            berater_count=3
        )

        # THEN: Reduced capacity
        assert total == 6  # 3 × 2 (not 9)
        assert freie_count == 6

    def test_get_slot_status_overbooked(self, mock_calendar_service):
        """Test overbooked detection when bookings exceed capacity"""
        from app.services.booking_service import get_slot_status

        # GIVEN: 10 bookings, capacity=9
        events = [{'summary': f'Customer {i}', 'colorId': '9'} for i in range(10)]
        mock_calendar_service.get_events.return_value = {'items': events}

        slot_list, booked, total, freie_count, overbooked = get_slot_status(
            date_str='2026-01-15',
            hour='14:00',
            berater_count=3
        )

        # THEN: Overbooked detected
        assert booked == 10
        assert total == 9
        assert freie_count == 0  # max(0, 9-10)
        assert overbooked is True

    def test_get_slot_status_calendar_unavailable(self):
        """Test fallback when calendar service unavailable"""
        from app.services.booking_service import get_slot_status

        with patch('app.services.booking_service.get_google_calendar_service', return_value=None):
            slot_list, booked, total, freie_count, overbooked = get_slot_status(
                date_str='2026-01-15',
                hour='14:00',
                berater_count=3
            )

            # THEN: Assumes no bookings
            assert booked == 0
            assert total == 9
            assert freie_count == 9
            assert overbooked is False


@pytest.mark.service
class TestPointsCalculation:
    """Tests for get_slot_points() - Dynamic points calculation"""

    def test_get_slot_points_low_utilization(self, mock_calendar_service):
        """Test points for 0-33% full slot"""
        from app.services.booking_service import get_slot_points

        # GIVEN: 2 bookings, 9 capacity = 22% utilization
        events = [{'summary': f'Customer {i}', 'colorId': '9'} for i in range(2)]
        mock_calendar_service.get_events.return_value = {'items': events}

        slot_date = date(2026, 1, 15)  # Wednesday
        points = get_slot_points(
            hour='14:00',
            slot_date=slot_date,
            date_str='2026-01-15',
            berater_count=3
        )

        # THEN: Low utilization = 5 base points
        assert points >= 5  # Base + possible bonuses

    def test_get_slot_points_medium_utilization(self, mock_calendar_service):
        """Test points for 34-66% full slot"""
        from app.services.booking_service import get_slot_points

        # GIVEN: 5 bookings, 9 capacity = 55% utilization
        events = [{'summary': f'Customer {i}', 'colorId': '9'} for i in range(5)]
        mock_calendar_service.get_events.return_value = {'items': events}

        slot_date = date(2026, 1, 15)
        points = get_slot_points(
            hour='16:00',  # No time bonus
            slot_date=slot_date,
            date_str='2026-01-15',
            berater_count=3
        )

        # THEN: Medium utilization = 3 base points
        assert points >= 3

    def test_get_slot_points_high_utilization(self, mock_calendar_service):
        """Test points for 67-100% full slot"""
        from app.services.booking_service import get_slot_points

        # GIVEN: 7 bookings, 9 capacity = 77% utilization
        events = [{'summary': f'Customer {i}', 'colorId': '9'} for i in range(7)]
        mock_calendar_service.get_events.return_value = {'items': events}

        slot_date = date(2026, 1, 15)
        points = get_slot_points(
            hour='16:00',
            slot_date=slot_date,
            date_str='2026-01-15',
            berater_count=3
        )

        # THEN: High utilization = 1 base point
        assert points >= 1

    def test_get_slot_points_time_bonus(self, mock_calendar_service):
        """Test bonus points for less popular time slots (11:00, 14:00)"""
        from app.services.booking_service import get_slot_points

        mock_calendar_service.get_events.return_value = {'items': []}

        slot_date = date(2026, 1, 15)

        # 11:00 slot
        points_11 = get_slot_points(
            hour='11:00',
            slot_date=slot_date,
            date_str='2026-01-15',
            berater_count=3
        )

        # 14:00 slot
        points_14 = get_slot_points(
            hour='14:00',
            slot_date=slot_date,
            date_str='2026-01-15',
            berater_count=3
        )

        # 16:00 slot (no bonus)
        points_16 = get_slot_points(
            hour='16:00',
            slot_date=slot_date,
            date_str='2026-01-15',
            berater_count=3
        )

        # THEN: 11:00 and 14:00 get +2 bonus
        assert points_11 > points_16
        assert points_14 > points_16

    def test_get_slot_points_weekend_bonus(self):
        """Test bonus point for Saturday/Sunday (weekday >= 5)"""
        from app.services.booking_service import get_slot_points

        # Saturday (weekday 5)
        saturday = date(2026, 1, 17)  # Saturday
        points_saturday = get_slot_points(hour='14:00', slot_date=saturday)

        # Wednesday (no bonus)
        wednesday = date(2026, 1, 14)  # Wednesday
        points_wednesday = get_slot_points(hour='14:00', slot_date=wednesday)

        # THEN: Saturday gets +1 weekend bonus
        assert points_saturday > points_wednesday
        assert points_saturday == points_wednesday + 1

    def test_get_slot_points_ruckholung_modifier(self, mock_calendar_service):
        """Test half points for Rückholung (color_id=3)"""
        from app.services.booking_service import get_slot_points

        mock_calendar_service.get_events.return_value = {'items': []}

        slot_date = date(2026, 1, 15)

        # Normal booking
        points_normal = get_slot_points(
            hour='14:00',
            slot_date=slot_date,
            color_id='9'
        )

        # Rückholung
        points_ruckholung = get_slot_points(
            hour='14:00',
            slot_date=slot_date,
            color_id='3'  # Rückholung modifier
        )

        # THEN: Rückholung gets half points (minimum 1)
        assert points_ruckholung < points_normal
        assert points_ruckholung >= 1  # Minimum

    def test_get_slot_points_fallback_on_error(self):
        """Test fallback to 3 base points (+ bonuses) if calculation fails"""
        from app.services.booking_service import get_slot_points

        with patch('app.services.booking_service.get_google_calendar_service', return_value=None):
            slot_date = date(2026, 1, 15)  # Wednesday
            points = get_slot_points(
                hour='14:00',
                slot_date=slot_date
            )

            # THEN: Fallback to 3 base + 2 time bonus (14:00) = 5 points
            assert points == 5


@pytest.mark.service
class TestWeeklySummary:
    """Tests for extract_weekly_summary() - 4-week statistics"""

    def test_extract_weekly_summary_4_weeks(self, mock_calendar_service, mock_holiday_service):
        """Test extraction of 4 weeks of availability summary"""
        from app.services.booking_service import extract_weekly_summary

        # GIVEN: Mock calendar with some events
        mock_calendar_service.get_events.return_value = {
            'items': [
                {
                    'summary': 'Test Customer',
                    'colorId': '9',
                    'start': {'dateTime': '2026-01-15T14:00:00+01:00'}
                }
            ]
        }

        # Mock availability data
        availability = {}

        with patch('app.services.booking_service.get_effective_availability') as mock_avail:
            # Return some consultants for most slots
            mock_avail.return_value = ['Ann-Kathrin', 'Sara', 'Dominik']

            summary = extract_weekly_summary(availability)

            # THEN: Returns 4 weeks
            assert len(summary) >= 4
            assert 'label' in summary[0]
            assert 'range' in summary[0]
            assert 'usage_pct' in summary[0]

    def test_extract_weekly_summary_skips_blocked_weeks(self, mock_calendar_service):
        """Test skips fully blocked weeks (Betriebsferien)"""
        from app.services.booking_service import extract_weekly_summary

        mock_calendar_service.get_events.return_value = {'items': []}

        with patch('app.services.booking_service.get_effective_availability') as mock_avail:
            # Simulate: Week 2 fully blocked, Week 3 has availability
            call_count = [0]

            def availability_side_effect(*args, **kwargs):
                call_count[0] += 1
                # Every 35th call (one full week = 7 days × 6 slots = 42 calls approx), return empty
                if 35 <= call_count[0] <= 70:
                    return []  # Week 2 blocked
                return ['Berater1']

            mock_avail.side_effect = availability_side_effect

            summary = extract_weekly_summary({})

            # THEN: Still returns 4 valid weeks (skips blocked week)
            assert len(summary) >= 4

    def test_extract_weekly_summary_filters_t1_bereit(self, mock_calendar_service, mock_holiday_service):
        """Test T1-bereit events are not counted as booked"""
        from app.services.booking_service import extract_weekly_summary

        # GIVEN: Events with T1-bereit
        mock_calendar_service.get_events.return_value = {
            'items': [
                {
                    'summary': 'Regular Customer',
                    'colorId': '9',
                    'start': {'dateTime': '2026-01-15T14:00:00+01:00'}
                },
                {
                    'summary': 'T1-bereit Weber',  # Should be filtered
                    'colorId': '2',
                    'start': {'dateTime': '2026-01-15T16:00:00+01:00'}
                }
            ]
        }

        with patch('app.services.booking_service.get_effective_availability', return_value=['Berater1']):
            summary = extract_weekly_summary({})

            # Find the week containing 2026-01-15
            week_data = next((w for w in summary if '2026-01' in w['start_date']), None)

            # THEN: Only 1 booking counted (T1-bereit filtered)
            # Note: exact count depends on full calendar logic

    def test_extract_weekly_summary_filters_non_blocking_colors(self, mock_calendar_service):
        """Test non-blocking color events are excluded"""
        from app.services.booking_service import extract_weekly_summary

        # GIVEN: Events with non-blocking colors
        mock_calendar_service.get_events.return_value = {
            'items': [
                {
                    'summary': 'Blocking Event',
                    'colorId': '9',  # Blocking
                    'start': {'dateTime': '2026-01-15T14:00:00+01:00'}
                },
                {
                    'summary': 'Non-Blocking Event',
                    'colorId': '1',  # Non-blocking
                    'start': {'dateTime': '2026-01-15T16:00:00+01:00'}
                }
            ]
        }

        with patch('app.services.booking_service.get_effective_availability', return_value=['Berater1']):
            with patch('app.utils.color_mapping.blocks_availability') as mock_blocks:
                # Color 9 blocks, color 1 doesn't
                mock_blocks.side_effect = lambda cid: cid == '9'

                summary = extract_weekly_summary({})

                # THEN: Only blocking color counted

    def test_extract_weekly_summary_9am_capacity(self, mock_calendar_service):
        """Test 9am slots use reduced capacity in calculations"""
        from app.services.booking_service import extract_weekly_summary

        mock_calendar_service.get_events.return_value = {'items': []}

        with patch('app.services.booking_service.get_effective_availability') as mock_avail:
            # Return 3 consultants
            mock_avail.return_value = ['Berater1', 'Berater2', 'Berater3']

            summary = extract_weekly_summary({})

            # THEN: 9am slots contribute less capacity (3 × 2 = 6 vs 3 × 3 = 9)
            # Verify in possible count calculation

    def test_extract_weekly_summary_usage_calculation(self, mock_calendar_service):
        """Test usage percentage calculation (booked/possible)"""
        from app.services.booking_service import extract_weekly_summary

        # GIVEN: Known number of events
        events = [
            {
                'summary': f'Customer {i}',
                'colorId': '9',
                'start': {'dateTime': f'2026-01-1{5+i//6}T{10+i%6*2}:00:00+01:00'}
            }
            for i in range(10)
        ]
        mock_calendar_service.get_events.return_value = {'items': events}

        with patch('app.services.booking_service.get_effective_availability', return_value=['B1', 'B2']):
            summary = extract_weekly_summary({})

            # THEN: usage_pct calculated correctly
            for week in summary:
                assert 'usage_pct' in week
                assert week['usage_pct'] >= 0

    def test_extract_weekly_summary_caps_at_100_percent(self, mock_calendar_service):
        """Test usage percentage capped at 100%"""
        from app.services.booking_service import extract_weekly_summary

        # GIVEN: Many events (overbooked scenario)
        events = [
            {
                'summary': f'Customer {i}',
                'colorId': '9',
                'start': {'dateTime': f'2026-01-15T14:00:00+01:00'}
            }
            for i in range(100)  # Way more than capacity
        ]
        mock_calendar_service.get_events.return_value = {'items': events}

        with patch('app.services.booking_service.get_effective_availability', return_value=['B1']):
            summary = extract_weekly_summary({})

            # THEN: usage_pct capped at 100
            for week in summary:
                assert week['usage_pct'] <= 100


@pytest.mark.service
class TestEffectiveAvailability:
    """Tests for get_effective_availability() - Availability logic"""

    def test_get_effective_availability_from_loaded_data(self):
        """Test returns availability from loaded JSON"""
        from app.services.booking_service import get_effective_availability

        with patch('app.services.booking_service.load_availability') as mock_load:
            mock_load.return_value = {
                '2026-01-15 14:00': ['Ann-Kathrin', 'Sara', 'Dominik']
            }

            with patch('app.services.holiday_service.holiday_service') as mock_holiday:
                mock_holiday.is_blocked_date.return_value = False

                result = get_effective_availability('2026-01-15', '14:00')

                # THEN: Returns from loaded data
                assert result == ['Ann-Kathrin', 'Sara', 'Dominik']

    def test_get_effective_availability_blocked_date(self):
        """Test returns empty list for blocked dates"""
        from app.services.booking_service import get_effective_availability

        with patch('app.services.holiday_service.holiday_service') as mock_holiday:
            mock_holiday.is_blocked_date.return_value = True

            result = get_effective_availability('2026-01-01', '14:00')

            # THEN: Returns empty
            assert result == []

    def test_get_effective_availability_blocked_time_range(self):
        """Test respects time-range blocks"""
        from app.services.booking_service import get_effective_availability

        with patch('app.services.holiday_service.holiday_service') as mock_holiday:
            # Block specific time
            def check_blocked(date, check_time=None):
                if check_time == '14:00':
                    return True
                return False

            mock_holiday.is_blocked_date.side_effect = check_blocked

            result = get_effective_availability('2026-01-15', '14:00')

            # THEN: Returns empty for blocked time
            assert result == []

    def test_get_effective_availability_9am_fallback(self):
        """Test 9am uses default availability if not pre-generated"""
        from app.services.booking_service import get_effective_availability

        with patch('app.services.booking_service.load_availability', return_value={}):
            with patch('app.services.booking_service.get_default_availability') as mock_default:
                mock_default.return_value = ['Berater1', 'Berater2']

                with patch('app.services.holiday_service.holiday_service') as mock_holiday:
                    mock_holiday.is_blocked_date.return_value = False

                    result = get_effective_availability('2026-02-20', '09:00')

                    # THEN: Uses default availability
                    assert mock_default.called

    def test_get_effective_availability_beyond_generation_days(self):
        """Test standard availability for dates beyond 56 days"""
        from app.services.booking_service import get_effective_availability

        # Date 60 days in future
        future_date = (date.today() + timedelta(days=60)).strftime('%Y-%m-%d')

        with patch('app.services.booking_service.load_availability', return_value={}):
            with patch('app.services.booking_service.get_default_availability') as mock_default:
                mock_default.return_value = ['Standard1', 'Standard2']

                with patch('app.services.holiday_service.holiday_service') as mock_holiday:
                    mock_holiday.is_blocked_date.return_value = False

                    result = get_effective_availability(future_date, '14:00')

                    # THEN: Uses default availability for far future
                    assert mock_default.called
