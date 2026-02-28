# -*- coding: utf-8 -*-
"""
Tests for Booking Service
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytz


TZ = pytz.timezone("Europe/Berlin")


class TestBookingServiceHelpers:
    """Tests for booking service helper functions"""

    @pytest.mark.unit
    def test_is_t1_bereit_event_true(self):
        """Test detection of T1-bereit events"""
        from app.services.booking_service import is_t1_bereit_event

        assert is_t1_bereit_event('T1-bereit Weber') is True
        assert is_t1_bereit_event('t1-bereit Müller') is True
        assert is_t1_bereit_event('T1 bereit Schmidt') is True

    @pytest.mark.unit
    def test_is_t1_bereit_event_false(self):
        """Test that regular events are not detected as T1-bereit"""
        from app.services.booking_service import is_t1_bereit_event

        assert is_t1_bereit_event('Müller, Hans') is False
        assert is_t1_bereit_event('Regular Booking') is False
        assert is_t1_bereit_event('') is False


class TestSlotPoints:
    """Tests for slot point calculation"""

    @pytest.mark.unit
    def test_get_slot_points_base_calculation(self):
        """Test base point calculation"""
        from app.services.booking_service import get_slot_points

        slot_date = datetime.now(TZ).date()
        points = get_slot_points("14:00", slot_date)

        # Base points + time bonus for 14:00
        assert points >= 3

    @pytest.mark.unit
    def test_get_slot_points_time_bonus(self):
        """Test time-based bonus for less popular slots"""
        from app.services.booking_service import get_slot_points

        slot_date = datetime.now(TZ).date()

        # 11:00 and 14:00 should get bonus
        points_11 = get_slot_points("11:00", slot_date)
        points_14 = get_slot_points("14:00", slot_date)
        points_18 = get_slot_points("18:00", slot_date)

        # 11:00 and 14:00 get +2 bonus
        assert points_11 >= points_18
        assert points_14 >= points_18

    @pytest.mark.unit
    def test_get_slot_points_rueckholung_modifier(self):
        """Test that Rückholung (color_id 3) gets half points"""
        from app.services.booking_service import get_slot_points

        slot_date = datetime.now(TZ).date()

        # Regular booking
        regular_points = get_slot_points("14:00", slot_date, color_id="9")

        # Rückholung (color_id 3) gets half points
        rueckholung_points = get_slot_points("14:00", slot_date, color_id="3")

        assert rueckholung_points < regular_points
        assert rueckholung_points >= 1  # Minimum 1 point


class TestEffectiveAvailability:
    """Tests for effective availability calculation"""

    @pytest.mark.unit
    def test_get_effective_availability_blocked_date(self):
        """Test that blocked dates return no availability"""
        from app.services.booking_service import get_effective_availability

        with patch('app.services.holiday_service.holiday_service') as mock:
            mock.is_blocked_date.return_value = True

            result = get_effective_availability('2025-01-15', '14:00')

            assert result == []

    @pytest.mark.unit
    def test_get_default_availability_blocked_date(self):
        """Test that blocked dates return no default availability"""
        from app.services.booking_service import get_default_availability

        with patch('app.services.holiday_service.holiday_service') as mock:
            mock.is_blocked_date.return_value = True

            result = get_default_availability('2025-01-15', '14:00')

            assert result == []

    @pytest.mark.unit
    def test_get_default_availability_future_date(self):
        """Test default availability for dates beyond generation period"""
        from app.services.booking_service import get_default_availability

        with patch('app.services.holiday_service.holiday_service') as mock:
            mock.is_blocked_date.return_value = False

            # Date 100 days in future (beyond AVAILABILITY_GENERATION_DAYS)
            future_date = (datetime.now(TZ).date() + timedelta(days=100))
            date_str = future_date.strftime('%Y-%m-%d')

            # Only test for valid weekday/hour combinations
            if future_date.weekday() < 4:  # Monday-Thursday
                result = get_default_availability(date_str, '14:00')
                # Should return default consultants
                assert isinstance(result, list)


class TestSlotStatus:
    """Tests for slot status retrieval"""

    @pytest.fixture
    def mock_calendar_service(self):
        """Mock Google Calendar service"""
        with patch('app.services.booking_service.get_google_calendar_service') as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    @pytest.mark.unit
    def test_get_slot_status_no_bookings(self, mock_calendar_service):
        """Test slot status with no bookings"""
        from app.services.booking_service import get_slot_status

        mock_calendar_service.get_events.return_value = {'items': []}

        slot_list, booked, total, free, overbooked = get_slot_status(
            '2025-01-15', '14:00', 3
        )

        assert booked == 0
        assert total == 9  # 3 consultants * 3 slots each
        assert free == 9
        assert overbooked is False

    @pytest.mark.unit
    def test_get_slot_status_with_bookings(self, mock_calendar_service):
        """Test slot status with some bookings"""
        from app.services.booking_service import get_slot_status

        mock_calendar_service.get_events.return_value = {
            'items': [
                {'summary': 'Müller, Hans', 'colorId': '2'},
                {'summary': 'Schmidt, Anna', 'colorId': '7'}
            ]
        }

        slot_list, booked, total, free, overbooked = get_slot_status(
            '2025-01-15', '14:00', 3
        )

        assert booked == 2
        assert total == 9
        assert free == 7
        assert overbooked is False

    @pytest.mark.unit
    def test_get_slot_status_9am_reduced_capacity(self, mock_calendar_service):
        """Test that 9am slots have reduced capacity (Mo-Do=1, Fr=2)"""
        from app.services.booking_service import get_slot_status

        mock_calendar_service.get_events.return_value = {'items': []}

        # Wednesday (Mo-Do): 1 per consultant
        slot_list, booked, total, free, overbooked = get_slot_status(
            '2025-01-15', '09:00', 3  # Wednesday
        )
        assert total == 3  # 3 consultants * 1 slot each (9am Mo-Do)

        # Friday: 2 per consultant
        slot_list, booked, total, free, overbooked = get_slot_status(
            '2025-01-17', '09:00', 3  # Friday
        )
        assert total == 6  # 3 consultants * 2 slots each (9am Friday)

    @pytest.mark.unit
    def test_get_slot_status_t1_bereit_not_counted(self, mock_calendar_service):
        """Test that T1-bereit events are not counted as booked"""
        from app.services.booking_service import get_slot_status

        mock_calendar_service.get_events.return_value = {
            'items': [
                {'summary': 'Müller, Hans', 'colorId': '2'},
                {'summary': 'T1-bereit Weber', 'colorId': '1'}
            ]
        }

        slot_list, booked, total, free, overbooked = get_slot_status(
            '2025-01-15', '14:00', 3
        )

        # Only regular booking should be counted
        assert booked == 1

    @pytest.mark.unit
    def test_get_slot_status_overbooked(self, mock_calendar_service):
        """Test detection of overbooked slots"""
        from app.services.booking_service import get_slot_status

        # Create 10 bookings for a slot with only 9 capacity
        mock_calendar_service.get_events.return_value = {
            'items': [{'summary': f'Customer {i}', 'colorId': '2'} for i in range(10)]
        }

        slot_list, booked, total, free, overbooked = get_slot_status(
            '2025-01-15', '14:00', 3
        )

        assert booked == 10
        assert total == 9
        assert overbooked is True

    @pytest.mark.unit
    def test_get_slot_status_calendar_unavailable(self, mock_calendar_service):
        """Test slot status when calendar service is unavailable"""
        from app.services.booking_service import get_slot_status

        # Return None to simulate unavailable service
        with patch('app.services.booking_service.get_google_calendar_service') as mock:
            mock.return_value = None

            slot_list, booked, total, free, overbooked = get_slot_status(
                '2025-01-15', '14:00', 3
            )

            # Should assume no bookings
            assert booked == 0
            assert free == total


class TestBookSlot:
    """Tests for booking slots"""

    @pytest.fixture
    def mock_calendar_service(self):
        """Mock Google Calendar service for booking"""
        with patch('app.services.booking_service.get_google_calendar_service') as mock:
            service = MagicMock()
            service.create_event.return_value = {'id': 'test-event-123'}
            mock.return_value = service
            yield service

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager"""
        with patch('app.services.booking_service.cache_manager') as mock:
            yield mock

    @pytest.fixture
    def mock_tracking_system(self):
        """Mock tracking system"""
        with patch('app.services.booking_service.tracking_system') as mock:
            yield mock

    @pytest.mark.unit
    def test_book_slot_success(self, mock_calendar_service, mock_cache_manager):
        """Test successful slot booking"""
        from app.services.booking_service import book_slot_for_user

        result = book_slot_for_user(
            user='test_user',
            date_str='2025-01-15',
            time_str='14:00',
            berater='Berater1',
            first_name='Hans',
            last_name='Müller',
            description='Test booking'
        )

        assert result['success'] is True
        assert 'event_id' in result
        mock_calendar_service.create_event.assert_called_once()

    @pytest.mark.unit
    def test_book_slot_missing_parameters(self):
        """Test booking with missing required parameters"""
        from app.services.booking_service import book_slot_for_user

        result = book_slot_for_user(
            user='',
            date_str='2025-01-15',
            time_str='14:00',
            berater='Berater1'
        )

        assert result['success'] is False
        assert 'Missing' in result['error']

    @pytest.mark.unit
    def test_book_slot_invalid_datetime(self, mock_calendar_service):
        """Test booking with invalid datetime format"""
        from app.services.booking_service import book_slot_for_user

        result = book_slot_for_user(
            user='test_user',
            date_str='invalid-date',
            time_str='14:00',
            berater='Berater1'
        )

        assert result['success'] is False
        assert 'Invalid' in result['error']

    @pytest.mark.unit
    def test_book_slot_calendar_unavailable(self, mock_cache_manager):
        """Test booking when calendar service is unavailable"""
        from app.services.booking_service import book_slot_for_user

        with patch('app.services.booking_service.get_google_calendar_service') as mock:
            mock.return_value = None

            result = book_slot_for_user(
                user='test_user',
                date_str='2025-01-15',
                time_str='14:00',
                berater='Berater1'
            )

            assert result['success'] is False
            assert 'not available' in result['error']

    @pytest.mark.unit
    def test_book_slot_creates_correct_summary(self, mock_calendar_service, mock_cache_manager):
        """Test that booking creates correct event summary"""
        from app.services.booking_service import book_slot_for_user

        book_slot_for_user(
            user='test_user',
            date_str='2025-01-15',
            time_str='14:00',
            berater='Berater1',
            first_name='Hans',
            last_name='Müller'
        )

        # Check the event data passed to create_event
        call_args = mock_calendar_service.create_event.call_args
        event_data = call_args[1]['event_data']

        assert event_data['summary'] == 'Müller, Hans'

    @pytest.mark.unit
    def test_book_slot_includes_booked_by_tag(self, mock_calendar_service, mock_cache_manager):
        """Test that booking includes [Booked by:] tag in description"""
        from app.services.booking_service import book_slot_for_user

        book_slot_for_user(
            user='test_user',
            date_str='2025-01-15',
            time_str='14:00',
            berater='Berater1',
            first_name='Hans',
            last_name='Müller',
            description='Original description'
        )

        call_args = mock_calendar_service.create_event.call_args
        event_data = call_args[1]['event_data']

        assert '[Booked by: test_user]' in event_data['description']
        assert 'Original description' in event_data['description']

    @pytest.mark.unit
    def test_book_slot_clears_cache(self, mock_calendar_service, mock_cache_manager):
        """Test that booking clears the cache"""
        from app.services.booking_service import book_slot_for_user

        book_slot_for_user(
            user='test_user',
            date_str='2025-01-15',
            time_str='14:00',
            berater='Berater1'
        )

        mock_cache_manager.clear_all.assert_called_once()


class TestSlotSuggestions:
    """Tests for slot suggestion functionality"""

    @pytest.mark.unit
    def test_get_slot_suggestions_returns_list(self):
        """Test that slot suggestions returns a list"""
        from app.services.booking_service import get_slot_suggestions

        # Create sample availability
        availability = {
            '2025-01-15': {
                '14:00': ['Berater1', 'Berater2', 'Berater3'],
                '16:00': ['Berater1', 'Berater2']
            },
            '2025-01-16': {
                '11:00': ['Berater1', 'Berater2', 'Berater3'],
            }
        }

        suggestions = get_slot_suggestions(availability, n=3)

        assert isinstance(suggestions, list)
        assert len(suggestions) <= 3

    @pytest.mark.unit
    def test_get_slot_suggestions_prefers_good_availability(self):
        """Test that suggestions prefer slots with multiple consultants"""
        from app.services.booking_service import get_slot_suggestions

        # Create availability with varying consultant counts
        tomorrow = (datetime.now(TZ).date() + timedelta(days=1)).strftime('%Y-%m-%d')

        availability = {
            tomorrow: {
                '14:00': ['Berater1', 'Berater2', 'Berater3'],  # Good availability
                '16:00': ['Berater1']  # Poor availability
            }
        }

        suggestions = get_slot_suggestions(availability, n=5)

        # Should suggest slots with 2+ consultants
        for suggestion in suggestions:
            assert suggestion['consultants'] >= 2


class TestDayAvailability:
    """Tests for day availability retrieval"""

    @pytest.mark.unit
    def test_get_day_availability_blocked_day(self):
        """Test that blocked days return empty availability"""
        from app.services.booking_service import get_day_availability

        with patch('app.services.holiday_service.holiday_service') as mock:
            mock.is_blocked_date.return_value = True

            result = get_day_availability('2025-01-15')

            assert result == {}

    @pytest.mark.unit
    def test_get_day_availability_returns_dict(self):
        """Test that day availability returns a dictionary"""
        from app.services.booking_service import get_day_availability

        with patch('app.services.holiday_service.holiday_service') as mock_holiday:
            mock_holiday.is_blocked_date.return_value = False

            with patch('app.services.booking_service.get_effective_availability') as mock:
                mock.return_value = ['Berater1', 'Berater2']

                result = get_day_availability('2025-01-15')

                assert isinstance(result, dict)


class TestDetailedSummary:
    """Tests for detailed summary extraction"""

    @pytest.mark.unit
    def test_extract_detailed_summary_empty(self):
        """Test detailed summary with empty data"""
        from app.services.booking_service import extract_detailed_summary

        result = extract_detailed_summary({})

        assert result == {}

    @pytest.mark.unit
    def test_extract_detailed_summary_counts_correctly(self):
        """Test that detailed summary counts correctly"""
        from app.services.booking_service import extract_detailed_summary

        availability = {
            '2025-01-15': {
                '14:00': ['Berater1', 'Berater2'],
                '16:00': ['Berater1']
            }
        }

        result = extract_detailed_summary(availability)

        assert result['total_slots'] == 2
        assert result['total_days'] == 1
        assert result['consultant_frequency']['Berater1'] == 2
        assert result['consultant_frequency']['Berater2'] == 1


class TestAwardBookingPoints:
    """Tests for award_booking_points service function"""

    @pytest.fixture(autouse=True)
    def mock_deps(self):
        """Mock all dependencies for award_booking_points"""
        with patch('app.services.booking_service.data_persistence') as mock_dp, \
             patch('app.services.booking_service.safe_import') as mock_si, \
             patch('app.services.booking_service.booking_logger'):
            mock_dp.load_scores.return_value = {"test_user": {"2026-02": 10}}
            mock_si.return_value = None  # No achievement system
            self.mock_dp = mock_dp
            self.mock_si = mock_si
            yield

    @pytest.mark.unit
    def test_award_points_adds_to_scores(self):
        """Test that points are added to user scores"""
        from app.services.booking_service import award_booking_points

        with patch('app.services.daily_quests.daily_quest_system') as mock_dq:
            mock_dq.load_user_coins.return_value = {"test_user": 100}

            result = award_booking_points("test_user", 5)

            assert isinstance(result, list)
            self.mock_dp.save_scores.assert_called_once()

    @pytest.mark.unit
    def test_award_points_adds_coins(self):
        """Test that coins are also awarded"""
        from app.services.booking_service import award_booking_points

        with patch('app.services.booking_service.safe_import') as mock_si:
            mock_si.return_value = None

            with patch('app.services.daily_quests.daily_quest_system') as mock_dq:
                mock_dq.load_user_coins.return_value = {"test_user": 100}

                award_booking_points("test_user", 5)

                mock_dq.save_user_coins.assert_called_once()
                saved = mock_dq.save_user_coins.call_args[0][0]
                assert saved["test_user"] == 105

    @pytest.mark.unit
    def test_award_points_returns_empty_on_error(self):
        """Test graceful handling of errors"""
        from app.services.booking_service import award_booking_points

        self.mock_dp.load_scores.side_effect = Exception("DB error")

        result = award_booking_points("test_user", 5)

        assert result == []

    @pytest.mark.unit
    def test_award_points_new_user(self):
        """Test point award for user not yet in scores"""
        from app.services.booking_service import award_booking_points

        self.mock_dp.load_scores.return_value = {}

        with patch('app.services.daily_quests.daily_quest_system') as mock_dq:
            mock_dq.load_user_coins.return_value = {}

            result = award_booking_points("new_user", 3)

            assert isinstance(result, list)
            self.mock_dp.save_scores.assert_called_once()


class TestExecutePostBookingChain:
    """Tests for execute_post_booking_chain service function"""

    @pytest.fixture(autouse=True)
    def mock_deps(self):
        """Mock all dependencies for execute_post_booking_chain"""
        with patch('app.services.booking_service.tracking_system') as mock_ts, \
             patch('app.services.booking_service.data_persistence') as mock_dp, \
             patch('app.services.booking_service.booking_logger'), \
             patch('app.services.booking_service.award_booking_points') as mock_abp:
            mock_ts.track_booking.return_value = {"id": "booking-123"}
            mock_dp.load_daily_user_stats.return_value = {}
            mock_abp.return_value = []
            self.mock_ts = mock_ts
            self.mock_dp = mock_dp
            self.mock_abp = mock_abp
            yield

    @pytest.mark.unit
    def test_chain_returns_correct_structure(self):
        """Test that chain returns dict with expected keys"""
        from app.services.booking_service import execute_post_booking_chain

        result = execute_post_booking_chain(
            user="test_user", customer_name="Müller, Hans",
            date="2026-02-15", hour="14:00", color_id="9",
            description="Test", points=5, calendar_event_id="evt-123"
        )

        assert "tracking_ok" in result
        assert "new_badges" in result
        assert "flash_messages" in result
        assert isinstance(result["flash_messages"], list)

    @pytest.mark.unit
    def test_chain_tracking_success(self):
        """Test chain with successful tracking"""
        from app.services.booking_service import execute_post_booking_chain

        result = execute_post_booking_chain(
            user="test_user", customer_name="Müller, Hans",
            date="2026-02-15", hour="14:00", color_id="9",
            description="Test", points=5, calendar_event_id="evt-123"
        )

        assert result["tracking_ok"] is True
        self.mock_ts.track_booking.assert_called_once()
        # Should have success flash with points
        messages = [msg for msg, cat in result["flash_messages"] if cat == "success"]
        assert any("5 Punkt(e)" in msg for msg in messages)

    @pytest.mark.unit
    def test_chain_tracking_failure(self):
        """Test chain with tracking failure"""
        from app.services.booking_service import execute_post_booking_chain

        self.mock_ts.track_booking.return_value = None

        result = execute_post_booking_chain(
            user="test_user", customer_name="Müller, Hans",
            date="2026-02-15", hour="14:00", color_id="9",
            description="Test", points=5, calendar_event_id="evt-123"
        )

        assert result["tracking_ok"] is False
        warnings = [msg for msg, cat in result["flash_messages"] if cat == "warning"]
        assert len(warnings) >= 1

    @pytest.mark.unit
    def test_chain_tracking_exception(self):
        """Test chain handles tracking exception gracefully"""
        from app.services.booking_service import execute_post_booking_chain

        self.mock_ts.track_booking.side_effect = Exception("Connection error")

        result = execute_post_booking_chain(
            user="test_user", customer_name="Müller, Hans",
            date="2026-02-15", hour="14:00", color_id="9",
            description="Test", points=5, calendar_event_id="evt-123"
        )

        assert result["tracking_ok"] is False

    @pytest.mark.unit
    def test_chain_with_badges(self):
        """Test chain includes badge flash messages"""
        from app.services.booking_service import execute_post_booking_chain

        self.mock_abp.return_value = [{"name": "Erster Termin"}]

        result = execute_post_booking_chain(
            user="test_user", customer_name="Müller, Hans",
            date="2026-02-15", hour="14:00", color_id="9",
            description="Test", points=5, calendar_event_id="evt-123"
        )

        assert result["new_badges"] == [{"name": "Erster Termin"}]
        badge_msgs = [msg for msg, cat in result["flash_messages"] if "Badge" in msg]
        assert len(badge_msgs) == 1

    @pytest.mark.unit
    def test_chain_unknown_user_skips_points(self):
        """Test that unknown users don't get points"""
        from app.services.booking_service import execute_post_booking_chain

        result = execute_post_booking_chain(
            user="unknown", customer_name="Müller, Hans",
            date="2026-02-15", hour="14:00", color_id="9",
            description="Test", points=5, calendar_event_id="evt-123"
        )

        self.mock_abp.assert_not_called()

    @pytest.mark.unit
    def test_chain_updates_daily_stats_evening(self):
        """Test that evening bookings update daily stats"""
        from app.services.booking_service import execute_post_booking_chain

        execute_post_booking_chain(
            user="test_user", customer_name="Müller, Hans",
            date="2026-02-15", hour="20:00", color_id="9",
            description="Test", points=3, calendar_event_id="evt-123"
        )

        self.mock_dp.save_daily_user_stats.assert_called_once()

    @pytest.mark.unit
    def test_chain_calls_audit_log(self):
        """Test that audit log is called"""
        from app.services.booking_service import execute_post_booking_chain

        with patch('app.services.audit_service.audit_service') as mock_audit:
            execute_post_booking_chain(
                user="test_user", customer_name="Müller, Hans",
                date="2026-02-15", hour="14:00", color_id="9",
                description="Test", points=5, calendar_event_id="evt-123"
            )

            mock_audit.log_event.assert_called_once()
            call_kwargs = mock_audit.log_event.call_args[1]
            assert call_kwargs["event_type"] == "booking"
            assert call_kwargs["action"] == "booking_created"
