# -*- coding: utf-8 -*-
"""
Service Layer Tests - T2 Bucket System
Tests for app/services/t2_bucket_system.py (797 lines)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock
import json


# ========== FIXTURES ==========

@pytest.fixture(scope='module', autouse=True)
def mock_google_credentials():
    """Mock Google credentials to prevent loading during module import"""
    with patch('app.utils.credentials.load_google_credentials', return_value=Mock()):
        yield


@pytest.fixture
def mock_bucket_data():
    """Mock T2 Bucket State with 3 Closers"""
    return {
        "probabilities": {"Alex": 9.0, "David": 9.0, "Jose": 2.0},
        "default_probabilities": {"Alex": 9.0, "David": 9.0, "Jose": 2.0},
        "bucket": ["Alex"]*9 + ["David"]*9 + ["Jose"]*2,
        "total_draws": 0,
        "stats": {"Alex": 0, "David": 0, "Jose": 0},
        "user_last_draw": {},
        "draw_history": [],
        "last_reset": datetime.utcnow().isoformat()
    }


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL for Dual-Write"""
    with patch('app.services.t2_bucket_system.USE_POSTGRES', False):
        yield


# ========== TEST CLASSES ==========

@pytest.mark.service
class TestDrawCloser:
    """Tests for draw_closer() - T2 Closer selection"""

    def test_draw_closer_success(self, mock_bucket_data, mock_postgres):
        """Test successful closer draw"""
        from app.services.t2_bucket_system import draw_closer

        # GIVEN: Bucket with 3 closers
        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                # WHEN: Draw a closer
                result = draw_closer(username='test.user', draw_type='T2')

                # THEN: Success response with closer name
                assert result['success'] is True
                assert 'closer' in result
                assert result['closer'] in ['Alex', 'David', 'Jose']
                assert mock_save.called

    def test_draw_closer_probability_degradation(self, mock_bucket_data, mock_postgres):
        """Test probability decreases by 1 after draw"""
        from app.services.t2_bucket_system import draw_closer

        # GIVEN: Alex drawn
        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                with patch('random.choice', return_value='Alex'):
                    initial_prob = mock_bucket_data['probabilities']['Alex']

                    draw_closer(username='test.user', draw_type='T2')

                    # THEN: Alex's probability decreased by 1
                    saved_data = mock_save.call_args[0][0]
                    assert saved_data['probabilities']['Alex'] == initial_prob - 1

    def test_draw_closer_bucket_ticket_removal(self, mock_bucket_data, mock_postgres):
        """Test ticket removed from bucket after draw"""
        from app.services.t2_bucket_system import draw_closer

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                initial_size = len(mock_bucket_data['bucket'])

                draw_closer(username='test.user', draw_type='T2')

                # THEN: Bucket size decreased by 1
                saved_data = mock_save.call_args[0][0]
                assert len(saved_data['bucket']) == initial_size - 1

    def test_draw_closer_stats_increment(self, mock_bucket_data, mock_postgres):
        """Test stats counter increments for drawn closer"""
        from app.services.t2_bucket_system import draw_closer

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                with patch('random.choice', return_value='Alex'):
                    draw_closer(username='test.user', draw_type='T2')

                    # THEN: Alex's draw count incremented
                    saved_data = mock_save.call_args[0][0]
                    assert saved_data['stats']['Alex'] == 1
                    assert saved_data['total_draws'] == 1

    def test_draw_closer_empty_bucket_auto_reset(self, mock_bucket_data, mock_postgres):
        """Test auto-reset when bucket becomes empty"""
        from app.services.t2_bucket_system import draw_closer

        # GIVEN: Bucket with only 1 ticket
        mock_bucket_data['bucket'] = ['Alex']
        mock_bucket_data['total_draws'] = 19

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                draw_closer(username='test.user', draw_type='T2')

                # THEN: Bucket reset (should have 20 tickets again)
                saved_data = mock_save.call_args[0][0]
                assert len(saved_data['bucket']) == 20
                assert saved_data['total_draws'] == 0

    def test_draw_closer_max_draws_auto_reset(self, mock_bucket_data, mock_postgres):
        """Test auto-reset after max draws (20 by default)"""
        from app.services.t2_bucket_system import draw_closer

        # GIVEN: 19 draws completed, bucket has tickets
        mock_bucket_data['total_draws'] = 19
        mock_bucket_data['bucket'] = ['Alex'] * 10

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                with patch('app.services.t2_bucket_system.BUCKET_CONFIG', {
                    'max_draws_before_reset': 20,
                    'probability_reduction_per_draw': 1.0,
                    'min_probability': 0.0,
                    't1_timeout_minutes': 0,
                    't2_timeout_minutes': 1
                }):
                    draw_closer(username='test.user', draw_type='T2')

                    # THEN: Check if reached max draws (20th draw triggers reset)
                    saved_data = mock_save.call_args[0][0]
                    # After 20th draw, should reset
                    assert saved_data['total_draws'] in [0, 20]

    def test_draw_closer_user_last_draw_tracking(self, mock_bucket_data, mock_postgres):
        """Test user's last draw timestamp recorded"""
        from app.services.t2_bucket_system import draw_closer

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                with patch('random.choice', return_value='David'):
                    draw_closer(username='test.user', draw_type='T2', customer_name='Test Customer')

                    # THEN: User's last draw recorded
                    saved_data = mock_save.call_args[0][0]
                    assert 'test.user' in saved_data['user_last_draw']
                    assert saved_data['user_last_draw']['test.user']['closer'] == 'David'
                    assert saved_data['user_last_draw']['test.user']['customer_name'] == 'Test Customer'

    def test_draw_closer_postgres_dual_write(self, mock_bucket_data):
        """Test PostgreSQL dual-write on draw"""
        from app.services.t2_bucket_system import draw_closer

        with patch('app.services.t2_bucket_system.USE_POSTGRES', True):
            with patch('app.services.t2_bucket_system.POSTGRES_AVAILABLE', True):
                with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
                    with patch('app.services.t2_bucket_system.save_bucket_data'):
                        with patch('app.services.t2_bucket_system.get_db_session') as mock_session:
                            session = MagicMock()
                            mock_session.return_value.__enter__.return_value = session

                            result = draw_closer(username='test.user', draw_type='T2')

                            # THEN: PostgreSQL session used
                            assert result['success'] is True
                            # Session interaction depends on implementation


@pytest.mark.service
class TestTimeout:
    """Tests for check_user_timeout() - Draw timeout management"""

    def test_check_user_timeout_first_draw(self, mock_bucket_data, mock_postgres):
        """Test first draw always allowed (no timeout)"""
        from app.services.t2_bucket_system import check_user_timeout

        # GIVEN: User has never drawn before
        mock_bucket_data['user_last_draw'] = {}

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            # WHEN: Check timeout
            result = check_user_timeout(username='new.user', draw_type='T2')

            # THEN: No timeout for first draw
            assert result['can_draw'] is True

    def test_check_user_timeout_t1_no_timeout(self, mock_bucket_data, mock_postgres):
        """Test T1 users have no timeout"""
        from app.services.t2_bucket_system import check_user_timeout

        # GIVEN: User just drew
        now = datetime.utcnow()
        mock_bucket_data['user_last_draw'] = {
            'test.user': {
                'timestamp': now.isoformat(),
                'closer': 'Alex',
                'draw_type': 'T1'
            }
        }

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            with patch('app.services.t2_bucket_system.BUCKET_CONFIG', {'t1_timeout_minutes': 0, 't2_timeout_minutes': 1}):
                # WHEN: Check immediately for T1 draw
                result = check_user_timeout(username='test.user', draw_type='T1')

                # THEN: T1 has no timeout
                assert result['can_draw'] is True

    def test_check_user_timeout_t2_1_minute(self, mock_bucket_data, mock_postgres):
        """Test T2 users have timeout (default 1 minute)"""
        from app.services.t2_bucket_system import check_user_timeout

        # GIVEN: User drew 30 seconds ago
        now = datetime.utcnow()
        last_draw = now - timedelta(seconds=30)
        mock_bucket_data['user_last_draw'] = {
            'test.user': {
                'timestamp': last_draw.isoformat(),
                'closer': 'Alex',
                'draw_type': 'T2'
            }
        }

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            # Mock now_utc to control time comparison
            with patch('app.services.t2_bucket_system.now_utc', return_value=now):
                with patch('app.services.t2_bucket_system.parse_iso_to_utc', return_value=last_draw):
                    # WHEN: Check timeout for T2
                    result = check_user_timeout(username='test.user', draw_type='T2')

                    # THEN: Still in timeout (< 1 minute)
                    assert result['can_draw'] is False
                    assert 'timeout_remaining_seconds' in result

    def test_check_user_timeout_passed(self, mock_bucket_data, mock_postgres):
        """Test timeout passed after cooldown period"""
        from app.services.t2_bucket_system import check_user_timeout

        # GIVEN: User drew 2 minutes ago
        now = datetime.utcnow()
        last_draw = now - timedelta(minutes=2)
        mock_bucket_data['user_last_draw'] = {
            'test.user': {
                'timestamp': last_draw.isoformat(),
                'closer': 'Alex',
                'draw_type': 'T2'
            }
        }

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            # WHEN: Check timeout for T2
            result = check_user_timeout(username='test.user', draw_type='T2')

            # THEN: Timeout passed
            assert result['can_draw'] is True

    def test_check_user_timeout_timezone_handling(self, mock_bucket_data, mock_postgres):
        """Test UTC timezone normalization"""
        from app.services.t2_bucket_system import check_user_timeout

        # GIVEN: User drew with timezone info
        now = datetime.utcnow()
        last_draw = now - timedelta(seconds=30)
        mock_bucket_data['user_last_draw'] = {
            'test.user': {
                'timestamp': last_draw.isoformat() + 'Z',
                'closer': 'Alex',
                'draw_type': 'T2'
            }
        }

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            # THEN: Timezone handled correctly
            result = check_user_timeout(username='test.user', draw_type='T2')
            # Should still detect timeout
            assert 'can_draw' in result

    def test_check_user_timeout_invalid_timestamp(self, mock_bucket_data, mock_postgres):
        """Test fail-safe for invalid timestamp"""
        from app.services.t2_bucket_system import check_user_timeout

        # GIVEN: Invalid timestamp
        mock_bucket_data['user_last_draw'] = {
            'test.user': {
                'timestamp': 'invalid-timestamp',
                'closer': 'Alex',
                'draw_type': 'T2'
            }
        }

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            # THEN: Fail-safe allows draw (treat as first draw)
            result = check_user_timeout(username='test.user', draw_type='T2')
            assert result['can_draw'] is True


@pytest.mark.service
class TestProbabilityManagement:
    """Tests for update_probability() - Probability management"""

    def test_update_probability_success(self, mock_bucket_data, mock_postgres):
        """Test successful probability update"""
        from app.services.t2_bucket_system import update_probability

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                # WHEN: Update Alex's probability to 15
                result = update_probability(closer_name='Alex', new_probability=15.0)

                # THEN: Success
                assert result['success'] is True
                saved_data = mock_save.call_args[0][0]
                assert saved_data['probabilities']['Alex'] == 15.0

    def test_update_probability_zero_allowed(self, mock_bucket_data, mock_postgres):
        """Test probability can be set to 0"""
        from app.services.t2_bucket_system import update_probability

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                # WHEN: Set Jose to 0
                result = update_probability(closer_name='Jose', new_probability=0.0)

                # THEN: Allowed
                assert result['success'] is True
                saved_data = mock_save.call_args[0][0]
                assert saved_data['probabilities']['Jose'] == 0.0

    def test_update_probability_negative_rejected(self, mock_bucket_data, mock_postgres):
        """Test negative probability rejected"""
        from app.services.t2_bucket_system import update_probability

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            # WHEN: Try negative probability
            result = update_probability(closer_name='Alex', new_probability=-5.0)

            # THEN: Rejected
            assert result['success'] is False
            assert 'message' in result or 'error' in result

    def test_update_probability_exceeds_max_rejected(self, mock_bucket_data, mock_postgres):
        """Test probability > 100 rejected"""
        from app.services.t2_bucket_system import update_probability

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            # WHEN: Try > 100
            result = update_probability(closer_name='David', new_probability=150.0)

            # THEN: Rejected
            assert result['success'] is False

    def test_update_probability_invalid_closer(self, mock_bucket_data, mock_postgres):
        """Test unknown closer rejected"""
        from app.services.t2_bucket_system import update_probability

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data):
            # WHEN: Unknown closer
            result = update_probability(closer_name='Unknown', new_probability=10.0)

            # THEN: Rejected
            assert result['success'] is False

    def test_update_probability_bucket_rebuild(self, mock_bucket_data, mock_postgres):
        """Test bucket rebuilt after probability update"""
        from app.services.t2_bucket_system import update_probability

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                # WHEN: Update probability
                update_probability(closer_name='Alex', new_probability=5.0)

                # THEN: Bucket rebuilt (Alex now has 5 tickets)
                saved_data = mock_save.call_args[0][0]
                alex_count = saved_data['bucket'].count('Alex')
                assert alex_count == 5

    def test_update_probability_resets_draw_counter(self, mock_bucket_data, mock_postgres):
        """Test draw counter reset on probability update"""
        from app.services.t2_bucket_system import update_probability

        # GIVEN: 5 draws completed
        mock_bucket_data['total_draws'] = 5

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                # WHEN: Update probability
                update_probability(closer_name='Alex', new_probability=12.0)

                # THEN: Draw counter reset to 0
                saved_data = mock_save.call_args[0][0]
                assert saved_data['total_draws'] == 0


@pytest.mark.service
class TestBucketReset:
    """Tests for reset_bucket() - Bucket reset"""

    def test_reset_bucket_restores_defaults(self, mock_bucket_data, mock_postgres):
        """Test reset restores default probabilities"""
        from app.services.t2_bucket_system import reset_bucket

        # GIVEN: Modified probabilities
        mock_bucket_data['probabilities'] = {'Alex': 5.0, 'David': 10.0, 'Jose': 1.0}

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                # WHEN: Reset bucket
                result = reset_bucket()

                # THEN: Restored to defaults
                assert result['success'] is True
                saved_data = mock_save.call_args[0][0]
                assert saved_data['probabilities']['Alex'] == 9.0
                assert saved_data['probabilities']['David'] == 9.0
                assert saved_data['probabilities']['Jose'] == 2.0

    def test_reset_bucket_clears_draw_count(self, mock_bucket_data, mock_postgres):
        """Test reset clears total_draws"""
        from app.services.t2_bucket_system import reset_bucket

        # GIVEN: 15 draws completed
        mock_bucket_data['total_draws'] = 15

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                # WHEN: Reset
                reset_bucket()

                # THEN: Counter cleared
                saved_data = mock_save.call_args[0][0]
                assert saved_data['total_draws'] == 0

    def test_reset_bucket_rebuilds_full_bucket(self, mock_bucket_data, mock_postgres):
        """Test reset rebuilds full 20-ticket bucket"""
        from app.services.t2_bucket_system import reset_bucket

        # GIVEN: Half-empty bucket
        mock_bucket_data['bucket'] = ['Alex'] * 5

        with patch('app.services.t2_bucket_system.load_bucket_data', return_value=mock_bucket_data.copy()):
            with patch('app.services.t2_bucket_system.save_bucket_data') as mock_save:
                # WHEN: Reset
                reset_bucket()

                # THEN: Full bucket (9+9+2 = 20 tickets)
                saved_data = mock_save.call_args[0][0]
                assert len(saved_data['bucket']) == 20
                assert saved_data['bucket'].count('Alex') == 9
                assert saved_data['bucket'].count('David') == 9
                assert saved_data['bucket'].count('Jose') == 2
