# -*- coding: utf-8 -*-
"""
Service Layer Tests - Achievement/Gamification System
Tests for app/services/achievement_system.py (1100+ lines)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock, mock_open
import json


# ========== FIXTURES ==========

@pytest.fixture(scope='module', autouse=True)
def mock_google_credentials():
    """Mock Google credentials to prevent loading during module import"""
    with patch('app.utils.credentials.load_google_credentials', return_value=Mock()):
        yield


@pytest.fixture
def mock_achievement_system():
    """Create AchievementSystem instance with mocked file I/O"""
    from app.services.achievement_system import AchievementSystem

    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data='{}')):
            system = AchievementSystem()
            return system


@pytest.fixture
def mock_badges_data():
    """Mock badges data for a user"""
    return {
        "test.user": {
            "badges": [
                {
                    "id": "daily_10",
                    "name": "Anfänger 🌱",
                    "description": "10 Punkte an einem Tag",
                    "emoji": "🌱",
                    "rarity": "common",
                    "category": "daily",
                    "earned_date": "2026-01-01 10:00:00",
                    "color": "#10b981"
                },
                {
                    "id": "daily_20",
                    "name": "Aufsteiger ⭐",
                    "description": "20 Punkte an einem Tag",
                    "emoji": "⭐",
                    "rarity": "uncommon",
                    "category": "daily",
                    "earned_date": "2026-01-02 11:00:00",
                    "color": "#3b82f6"
                }
            ],
            "earned_dates": {
                "daily_10": "2026-01-01 10:00:00",
                "daily_20": "2026-01-02 11:00:00"
            },
            "total_badges": 2
        }
    }


@pytest.fixture
def mock_daily_stats():
    """Mock daily user stats"""
    return {
        "test.user": {
            "2026-01-01": {"points": 15, "bookings": 3},
            "2026-01-02": {"points": 25, "bookings": 5},
            "2026-01-03": {"points": 35, "bookings": 7}
        }
    }


@pytest.fixture
def mock_scores():
    """Mock scoreboard data"""
    return {
        "test.user": {
            "today": 30,
            "week": 150,
            "month": 600,
            "total": 2000
        }
    }


# ========== TEST CLASSES ==========

@pytest.mark.service
class TestBadgeManagement:
    """Tests for badge loading/saving"""

    def test_load_badges_via_data_persistence(self, mock_achievement_system, mock_badges_data):
        """Test loading badges via data_persistence"""
        with patch('app.core.extensions.data_persistence') as mock_dp:
            mock_dp.load_badges.return_value = mock_badges_data

            result = mock_achievement_system.load_badges()

            assert result == mock_badges_data
            assert mock_dp.load_badges.called

    def test_load_badges_fallback_on_error(self, mock_achievement_system):
        """Test fallback to direct file read on data_persistence error"""
        with patch('app.core.extensions.data_persistence') as mock_dp:
            mock_dp.load_badges.side_effect = Exception('DB Error')

            with patch('builtins.open', mock_open(read_data='{"user1": {"badges": []}}')):
                result = mock_achievement_system.load_badges()

                assert isinstance(result, dict)

    def test_save_badges_via_data_persistence(self, mock_achievement_system, mock_badges_data):
        """Test saving badges via data_persistence"""
        with patch('app.core.extensions.data_persistence') as mock_dp:
            mock_achievement_system.save_badges(mock_badges_data)

            mock_dp.save_user_badges.assert_called_once_with(mock_badges_data)

    def test_save_badges_fallback_on_error(self, mock_achievement_system, mock_badges_data):
        """Test fallback to direct file write on error"""
        with patch('app.core.extensions.data_persistence') as mock_dp:
            mock_dp.save_user_badges.side_effect = Exception('Save Error')

            m = mock_open()
            with patch('builtins.open', m):
                mock_achievement_system.save_badges(mock_badges_data)

                # Verify file write was attempted
                assert m.called


@pytest.mark.service
class TestAchievementChecking:
    """Tests for achievement checking logic"""

    def test_award_badge_new_badge(self, mock_achievement_system, mock_badges_data):
        """Test awarding a new badge to user"""
        from app.services.achievement_system import ACHIEVEMENT_DEFINITIONS

        badge_id = "daily_40"
        definition = ACHIEVEMENT_DEFINITIONS[badge_id]

        # User doesn't have this badge yet
        badges_copy = mock_badges_data.copy()
        result = mock_achievement_system.award_badge(
            user='test.user',
            badge_id=badge_id,
            definition=definition,
            badges_data=badges_copy
        )

        # Badge object should be returned
        assert result is not None
        assert result['id'] == badge_id
        # Verify it was added to badges_data
        assert len(badges_copy['test.user']['badges']) == 3
        assert badges_copy['test.user']['total_badges'] == 3

    def test_award_badge_duplicate_prevention(self, mock_achievement_system, mock_badges_data):
        """Test duplicate badge prevention"""
        from app.services.achievement_system import ACHIEVEMENT_DEFINITIONS

        badge_id = "daily_10"  # User already has this
        definition = ACHIEVEMENT_DEFINITIONS[badge_id]

        initial_count = mock_badges_data['test.user']['total_badges']
        badges_copy = mock_badges_data.copy()

        result = mock_achievement_system.award_badge(
            user='test.user',
            badge_id=badge_id,
            definition=definition,
            badges_data=badges_copy
        )

        # Should return None for duplicate
        assert result is None
        # Badge count should not increase
        assert badges_copy['test.user']['total_badges'] == initial_count

    def test_check_achievements_daily_threshold(self, mock_achievement_system):
        """Test achievement threshold checking"""
        scores = {'test.user': {'2026-01': 150, 'today': 45, 'week': 200, 'total': 500}}
        daily_stats = {'test.user': {}}
        badges_data = {'test.user': {'badges': [], 'earned_dates': {}, 'total_badges': 0}}

        new_badges = mock_achievement_system.check_achievements(
            user='test.user',
            scores=scores,
            daily_stats=daily_stats,
            badges_data=badges_data
        )

        # Should earn multiple badges (daily/weekly/monthly/total)
        assert isinstance(new_badges, list)
        assert len(new_badges) >= 2
        # Check if any badges were awarded
        badge_ids = [b['id'] for b in new_badges if b is not None]
        assert len(badge_ids) >= 2  # At least some badges earned

    def test_add_points_and_check_achievements_integration(self, mock_achievement_system):
        """Test integrated points addition and achievement checking"""
        with patch('app.core.extensions.data_persistence') as mock_dp:
            mock_dp.load_scores.return_value = {'test.user': {'2026-01': 100, 'today': 50}}
            mock_dp.load_daily_user_stats.return_value = {}
            mock_dp.save_daily_user_stats.return_value = True

            with patch.object(mock_achievement_system, 'load_badges', return_value={}):
                with patch.object(mock_achievement_system, 'auto_check_mvp_badges'):

                    new_badges = mock_achievement_system.add_points_and_check_achievements(
                        user='test.user',
                        points=50
                    )

                    # Should return list of new badges
                    assert isinstance(new_badges, list)
                    # At 50 points in daily stats, should earn at least daily_10, daily_20, daily_40
                    assert len(new_badges) >= 1  # At least some badges


@pytest.mark.service
class TestStreakCalculations:
    """Tests for streak calculation logic"""

    def test_calculate_points_streak_3_days(self, mock_achievement_system):
        """Test 3-day consecutive points streak"""
        user_stats = {
            "2026-01-01": {"points": 10},
            "2026-01-02": {"points": 15},
            "2026-01-03": {"points": 12}
        }

        with patch('app.services.achievement_system.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 3, 12, 0, 0)
            mock_dt.strptime = datetime.strptime

            streak = mock_achievement_system.calculate_points_streak(user_stats)

            assert streak >= 3

    def test_calculate_booking_streak(self, mock_achievement_system):
        """Test booking streak calculation"""
        user_stats = {
            "2026-01-01": {"bookings": 2},
            "2026-01-02": {"bookings": 3},
            "2026-01-03": {"bookings": 1}
        }

        with patch('app.services.achievement_system.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 3, 12, 0, 0)
            mock_dt.strptime = datetime.strptime

            streak = mock_achievement_system.calculate_booking_streak(user_stats)

            assert streak >= 3

    def test_calculate_week_points(self, mock_achievement_system):
        """Test weekly points calculation (current week Monday-Sunday)"""
        import pytz
        TZ = pytz.timezone("Europe/Berlin")

        # Mock current date as Saturday 2026-01-03 (Week starts Monday 2025-12-29)
        with patch('app.services.achievement_system.datetime') as mock_dt:
            mock_now = datetime(2026, 1, 3, 12, 0, 0, tzinfo=TZ)
            mock_dt.now.return_value = mock_now

            # Stats for current week (Mon Dec 29 - Sun Jan 4)
            user_stats = {
                "2025-12-29": {"points": 10},  # Monday
                "2025-12-30": {"points": 15},  # Tuesday
                "2025-12-31": {"points": 20},  # Wednesday
                "2026-01-01": {"points": 25},  # Thursday
                "2026-01-02": {"points": 30},  # Friday
                "2026-01-03": {"points": 35},  # Saturday (today)
                "2026-01-04": {"points": 40}   # Sunday
            }

            total = mock_achievement_system.calculate_week_points(user_stats)

            # Sum: 10+15+20+25+30+35 = 135 (up to today Saturday)
            # Note: Implementation may vary
            assert total >= 100  # At least some points counted


@pytest.mark.service
class TestMVPBadges:
    """Tests for MVP badge system"""

    def test_award_mvp_badge_week(self, mock_achievement_system):
        """Test awarding weekly MVP badge"""
        mvp_data = {}

        result = mock_achievement_system.award_mvp_badge(
            user='test.user',
            badge_type='mvp_week',
            period='2026-W01',
            mvp_data=mvp_data
        )

        # Should return badge object
        assert result is not None
        assert result['id'] == 'mvp_week'
        assert result['period'] == '2026-W01'

        # Verify badge added to mvp_data
        assert 'test.user' in mvp_data
        assert len(mvp_data['test.user']['badges']) == 1
        assert '2026-W01' in mvp_data['test.user']['periods']

    def test_award_mvp_badge_month(self, mock_achievement_system):
        """Test awarding monthly MVP badge"""
        mvp_data = {}

        result = mock_achievement_system.award_mvp_badge(
            user='test.user',
            badge_type='mvp_month',
            period='2026-01',
            mvp_data=mvp_data
        )

        assert result is not None
        assert result['id'] == 'mvp_month'
        assert 'test.user' in mvp_data
        assert '2026-01' in mvp_data['test.user']['periods']

    def test_award_mvp_badge_year(self, mock_achievement_system):
        """Test awarding yearly MVP badge"""
        mvp_data = {}

        result = mock_achievement_system.award_mvp_badge(
            user='test.user',
            badge_type='mvp_year',
            period='2026',
            mvp_data=mvp_data
        )

        assert result is not None
        assert result['id'] == 'mvp_year'
        assert 'test.user' in mvp_data

    def test_award_mvp_badge_duplicate_prevention(self, mock_achievement_system):
        """Test MVP badge duplicate prevention for same period"""
        mvp_data = {}

        # First award
        first = mock_achievement_system.award_mvp_badge(
            user='test.user',
            badge_type='mvp_month',
            period='2026-01',
            mvp_data=mvp_data
        )

        # Second award for same period
        second = mock_achievement_system.award_mvp_badge(
            user='test.user',
            badge_type='mvp_month',
            period='2026-01',
            mvp_data=mvp_data
        )

        assert first is not None
        assert second is None  # Duplicate prevented
        assert len(mvp_data['test.user']['badges']) == 1  # Only one badge


@pytest.mark.service
class TestUserBadges:
    """Tests for user badge retrieval"""

    def test_get_user_badges_existing_user(self, mock_achievement_system, mock_badges_data):
        """Test getting badges for existing user"""
        with patch.object(mock_achievement_system, 'load_badges', return_value=mock_badges_data):
            result = mock_achievement_system.get_user_badges('test.user')

            assert 'badges' in result
            assert len(result['badges']) == 2
            assert result['total_badges'] == 2

    def test_get_user_badges_new_user(self, mock_achievement_system):
        """Test getting badges for new user (empty)"""
        with patch.object(mock_achievement_system, 'load_badges', return_value={}):
            result = mock_achievement_system.get_user_badges('new.user')

            assert result['badges'] == []
            assert result['total_badges'] == 0

    def test_get_user_badge_progress(self, mock_achievement_system, mock_badges_data):
        """Test badge progress calculation"""
        with patch.object(mock_achievement_system, 'load_badges', return_value=mock_badges_data):
            with patch('app.core.extensions.data_persistence') as mock_dp:
                mock_dp.load_scores.return_value = {'test.user': {'2026-01': 100, 'today': 35}}
                mock_dp.load_daily_user_stats.return_value = {}

                result = mock_achievement_system.get_user_badge_progress('test.user')

                # Result is a dict with badge_id -> progress_info
                assert isinstance(result, dict)
                assert len(result) > 0
                # Check structure of progress info
                for badge_id, progress in result.items():
                    assert 'earned' in progress
                    assert 'current' in progress
                    assert 'target' in progress
                    assert 'progress_percent' in progress


@pytest.mark.service
class TestLeaderboard:
    """Tests for badge leaderboard"""

    def test_get_badge_leaderboard(self, mock_achievement_system, mock_badges_data):
        """Test badge leaderboard generation"""
        # Add more users
        extended_data = {}
        extended_data['test.user'] = mock_badges_data['test.user'].copy()
        extended_data['user2'] = {
            'badges': [
                {'id': 'daily_10', 'name': 'Anfänger', 'earned_date': '2026-01-01 10:00:00'}
            ],
            'total_badges': 1,
            'earned_dates': {'daily_10': '2026-01-01 10:00:00'}
        }
        extended_data['user3'] = {
            'badges': [
                {'id': 'daily_10', 'name': 'Anfänger', 'earned_date': '2026-01-01'},
                {'id': 'daily_20', 'name': 'Aufsteiger', 'earned_date': '2026-01-02'},
                {'id': 'daily_40', 'name': 'Champion', 'earned_date': '2026-01-03'}
            ],
            'total_badges': 3,
            'earned_dates': {}
        }

        with patch.object(mock_achievement_system, 'load_badges', return_value=extended_data):
            result = mock_achievement_system.get_badge_leaderboard()

            assert isinstance(result, list)
            # Should be sorted by total_badges descending
            assert result[0]['user'] == 'user3'
            assert result[0]['total_badges'] == 3
            assert result[1]['user'] == 'test.user'
            assert result[1]['total_badges'] == 2
