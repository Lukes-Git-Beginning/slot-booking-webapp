# -*- coding: utf-8 -*-
"""
Tests for T2 Bucket System Service
"""

import pytest
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import tempfile
import shutil


class TestT2BucketSystem:
    """Tests for the T2 Bucket System"""

    @pytest.fixture(autouse=True)
    def setup_temp_data_dir(self, temp_data_dir):
        """Setup temporary data directory for each test"""
        # Set up temp directory for persistence
        self.temp_dir = temp_data_dir
        data_dir = temp_data_dir / "persistent"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Patch the module's DATA_DIR and BUCKET_FILE
        import app.services.t2_bucket_system as t2_module

        self.original_data_dir = t2_module.DATA_DIR
        self.original_bucket_file = t2_module.BUCKET_FILE

        t2_module.DATA_DIR = str(data_dir)
        t2_module.BUCKET_FILE = str(data_dir / "t2_bucket_system.json")

        # Reset T2_CLOSERS to default state for each test
        t2_module.T2_CLOSERS.clear()
        t2_module.T2_CLOSERS.update({
            "Alex": {
                "full_name": "Alexander",
                "color": "#2196F3",
                "default_probability": 9.0
            },
            "David": {
                "full_name": "David",
                "color": "#9C27B0",
                "default_probability": 9.0
            },
            "Jose": {
                "full_name": "José",
                "color": "#795548",
                "default_probability": 2.0
            }
        })

        yield

        # Restore original paths
        t2_module.DATA_DIR = self.original_data_dir
        t2_module.BUCKET_FILE = self.original_bucket_file

    @pytest.mark.unit
    def test_get_probabilities_returns_defaults(self):
        """Test getting default probabilities"""
        from app.services.t2_bucket_system import get_probabilities

        probs = get_probabilities()

        assert probs['Alex'] == 9.0
        assert probs['David'] == 9.0
        assert probs['Jose'] == 2.0

    @pytest.mark.unit
    def test_update_probability_valid(self):
        """Test updating probability with valid value"""
        from app.services.t2_bucket_system import update_probability, get_probabilities

        result = update_probability('Alex', 5.0)

        assert result['success'] is True
        probs = get_probabilities()
        assert probs['Alex'] == 5.0

    @pytest.mark.unit
    def test_update_probability_invalid_closer(self):
        """Test updating probability for non-existent closer"""
        from app.services.t2_bucket_system import update_probability

        result = update_probability('NonExistent', 5.0)

        assert result['success'] is False
        assert 'Invalid closer' in result['message']

    @pytest.mark.unit
    def test_update_probability_negative_rejected(self):
        """Test that negative probability is rejected"""
        from app.services.t2_bucket_system import update_probability

        result = update_probability('Alex', -1.0)

        assert result['success'] is False
        assert 'negative' in result['message'].lower()

    @pytest.mark.unit
    def test_update_probability_exceeds_max_rejected(self):
        """Test that probability exceeding max is rejected"""
        from app.services.t2_bucket_system import update_probability

        result = update_probability('Alex', 150.0)

        assert result['success'] is False
        assert 'exceed' in result['message'].lower()

    @pytest.mark.unit
    def test_update_probability_zero_allowed(self):
        """Test that zero probability is allowed (disables closer)"""
        from app.services.t2_bucket_system import update_probability, get_probabilities

        result = update_probability('Jose', 0.0)

        assert result['success'] is True
        probs = get_probabilities()
        assert probs['Jose'] == 0.0

    @pytest.mark.unit
    def test_get_bucket_composition(self):
        """Test getting bucket composition"""
        from app.services.t2_bucket_system import get_bucket_composition

        composition = get_bucket_composition()

        assert 'composition' in composition
        assert 'total_tickets' in composition
        assert 'draws_until_reset' in composition

        # Default: Alex=9, David=9, Jose=2 = 20 tickets
        assert composition['total_tickets'] == 20

    @pytest.mark.unit
    def test_draw_closer_returns_valid_closer(self):
        """Test that drawing returns a valid closer"""
        from app.services.t2_bucket_system import draw_closer, get_available_closers

        result = draw_closer('test_user', 'T2', 'Customer Name')

        assert result['success'] is True
        assert result['closer'] in get_available_closers()
        assert 'color' in result
        assert 'bucket_stats' in result

    @pytest.mark.unit
    def test_draw_closer_reduces_probability(self):
        """Test that drawing reduces the drawn closer's probability"""
        from app.services.t2_bucket_system import draw_closer, get_probabilities

        initial_probs = get_probabilities()
        result = draw_closer('test_user', 'T2')

        assert result['success'] is True
        drawn_closer = result['closer']

        new_probs = get_probabilities()
        # Probability should be reduced by 1 (probability_reduction_per_draw)
        assert new_probs[drawn_closer] == initial_probs[drawn_closer] - 1.0

    @pytest.mark.unit
    def test_draw_closer_updates_stats(self):
        """Test that drawing updates statistics"""
        from app.services.t2_bucket_system import draw_closer, get_system_stats

        initial_stats = get_system_stats()
        initial_total = initial_stats['total_all_time_draws']

        draw_closer('test_user', 'T2')
        new_stats = get_system_stats()

        assert new_stats['total_all_time_draws'] == initial_total + 1

    @pytest.mark.unit
    def test_draw_closer_timeout_enforced(self):
        """Test that timeout is enforced between draws"""
        from app.services.t2_bucket_system import draw_closer

        # First draw should succeed
        result1 = draw_closer('test_user', 'T2')
        assert result1['success'] is True

        # Second draw should fail (timeout)
        result2 = draw_closer('test_user', 'T2')
        assert result2['success'] is False
        assert 'timeout_remaining' in result2

    @pytest.mark.unit
    def test_draw_closer_different_users_no_timeout(self):
        """Test that different users don't share timeout"""
        from app.services.t2_bucket_system import draw_closer

        # First user draws
        result1 = draw_closer('user1', 'T2')
        assert result1['success'] is True

        # Second user should be able to draw immediately
        result2 = draw_closer('user2', 'T2')
        assert result2['success'] is True

    @pytest.mark.unit
    def test_check_user_timeout_ready(self):
        """Test timeout check for user who hasn't drawn"""
        from app.services.t2_bucket_system import check_user_timeout

        result = check_user_timeout('new_user')

        assert result['can_draw'] is True
        assert result['timeout_remaining_seconds'] == 0

    @pytest.mark.unit
    def test_check_user_timeout_in_cooldown(self):
        """Test timeout check for user in cooldown"""
        from app.services.t2_bucket_system import draw_closer, check_user_timeout

        draw_closer('test_user', 'T2')
        result = check_user_timeout('test_user')

        assert result['can_draw'] is False
        assert result['timeout_remaining_seconds'] > 0

    @pytest.mark.unit
    def test_reset_bucket(self):
        """Test manual bucket reset"""
        from app.services.t2_bucket_system import reset_bucket, get_bucket_composition, get_probabilities

        # Draw some closers first
        from app.services.t2_bucket_system import draw_closer
        draw_closer('user1', 'T2')
        draw_closer('user2', 'T2')

        # Reset
        result = reset_bucket()

        assert result['success'] is True
        assert result['bucket_size'] == 20  # Default total tickets

        # Probabilities should be reset to defaults
        probs = get_probabilities()
        assert probs['Alex'] == 9.0
        assert probs['David'] == 9.0
        assert probs['Jose'] == 2.0

    @pytest.mark.unit
    def test_bucket_auto_reset_after_max_draws(self):
        """Test that bucket automatically resets after max draws"""
        from app.services.t2_bucket_system import (
            draw_closer, get_system_stats, update_bucket_size
        )

        # Set small bucket size for testing
        update_bucket_size(3)

        # Draw until reset — use different users to avoid timeout
        for i in range(4):
            draw_closer(f'user_reset_{i}', 'T2')

        stats = get_system_stats()
        # After 3 draws, bucket should reset, then 1 more draw
        assert stats['draws_this_cycle'] <= 3

    @pytest.mark.unit
    def test_get_system_stats(self):
        """Test getting system statistics"""
        from app.services.t2_bucket_system import get_system_stats

        stats = get_system_stats()

        assert 'total_all_time_draws' in stats
        assert 'closer_distribution' in stats
        assert 'current_bucket_size' in stats
        assert 'draws_this_cycle' in stats
        assert 'probabilities' in stats

    @pytest.mark.unit
    def test_get_available_closers(self):
        """Test getting list of available closers"""
        from app.services.t2_bucket_system import get_available_closers

        closers = get_available_closers()

        assert 'Alex' in closers
        assert 'David' in closers
        assert 'Jose' in closers
        assert closers['Alex']['color'] == '#2196F3'

    @pytest.mark.unit
    def test_update_bucket_size_valid(self):
        """Test updating bucket size with valid value"""
        from app.services.t2_bucket_system import update_bucket_size, get_bucket_config

        result = update_bucket_size(15)

        assert result['success'] is True
        config = get_bucket_config()
        assert config['max_draws_before_reset'] == 15

    @pytest.mark.unit
    def test_update_bucket_size_too_small(self):
        """Test that bucket size below 1 is rejected"""
        from app.services.t2_bucket_system import update_bucket_size

        result = update_bucket_size(0)

        assert result['success'] is False
        assert 'at least 1' in result['message']

    @pytest.mark.unit
    def test_update_bucket_size_too_large(self):
        """Test that bucket size above 100 is rejected"""
        from app.services.t2_bucket_system import update_bucket_size

        result = update_bucket_size(101)

        assert result['success'] is False
        assert 'exceed' in result['message']

    @pytest.mark.unit
    def test_add_closer_valid(self):
        """Test adding a new closer"""
        from app.services.t2_bucket_system import add_closer, get_available_closers

        result = add_closer('NewCloser', '#FF5722', 'New Closer', 5.0)

        assert result['success'] is True
        closers = get_available_closers()
        assert 'NewCloser' in closers
        assert closers['NewCloser']['default_probability'] == 5.0

    @pytest.mark.unit
    def test_add_closer_duplicate_rejected(self):
        """Test that adding duplicate closer is rejected"""
        from app.services.t2_bucket_system import add_closer

        result = add_closer('Alex', '#FF5722', 'Another Alex', 5.0)

        assert result['success'] is False
        assert 'existiert bereits' in result['message']

    @pytest.mark.unit
    def test_add_closer_invalid_color(self):
        """Test that invalid color format is rejected"""
        from app.services.t2_bucket_system import add_closer

        result = add_closer('NewCloser', 'red', 'New Closer', 5.0)

        assert result['success'] is False
        assert '#RRGGBB' in result['message']

    @pytest.mark.unit
    def test_remove_closer_valid(self):
        """Test removing a closer"""
        from app.services.t2_bucket_system import remove_closer, get_available_closers

        result = remove_closer('Jose')

        assert result['success'] is True
        closers = get_available_closers()
        assert 'Jose' not in closers

    @pytest.mark.unit
    def test_remove_closer_nonexistent(self):
        """Test removing non-existent closer"""
        from app.services.t2_bucket_system import remove_closer

        result = remove_closer('NonExistent')

        assert result['success'] is False
        assert 'nicht gefunden' in result['message']

    @pytest.mark.unit
    def test_remove_last_closer_rejected(self):
        """Test that removing last closer is rejected"""
        from app.services.t2_bucket_system import remove_closer

        # Remove all but one
        remove_closer('Alex')
        remove_closer('David')

        # Try to remove last one
        result = remove_closer('Jose')

        assert result['success'] is False
        assert 'Mindestens ein' in result['message']

    @pytest.mark.unit
    def test_update_closer_info_color(self):
        """Test updating closer color"""
        from app.services.t2_bucket_system import update_closer_info, get_available_closers

        result = update_closer_info('Alex', new_color='#000000')

        assert result['success'] is True
        closers = get_available_closers()
        assert closers['Alex']['color'] == '#000000'

    @pytest.mark.unit
    def test_update_closer_info_full_name(self):
        """Test updating closer full name"""
        from app.services.t2_bucket_system import update_closer_info, get_available_closers

        result = update_closer_info('Alex', new_full_name='Alexander the Great')

        assert result['success'] is True
        closers = get_available_closers()
        assert closers['Alex']['full_name'] == 'Alexander the Great'

    @pytest.mark.unit
    def test_update_closer_info_nonexistent(self):
        """Test updating non-existent closer"""
        from app.services.t2_bucket_system import update_closer_info

        result = update_closer_info('NonExistent', new_color='#000000')

        assert result['success'] is False
        assert 'nicht gefunden' in result['message']

    @pytest.mark.unit
    def test_get_bucket_config(self):
        """Test getting bucket configuration"""
        from app.services.t2_bucket_system import get_bucket_config

        config = get_bucket_config()

        assert 'max_draws_before_reset' in config
        assert 't1_timeout_minutes' in config
        assert 't2_timeout_minutes' in config
        assert 'probability_reduction_per_draw' in config

    @pytest.mark.unit
    def test_zero_probability_closer_not_drawn(self):
        """Test that closer with 0 probability is not drawn"""
        from app.services.t2_bucket_system import (
            update_probability, draw_closer, get_bucket_composition
        )

        # Set Alex and David to 0, only Jose should be drawn
        update_probability('Alex', 0.0)
        update_probability('David', 0.0)
        update_probability('Jose', 5.0)

        composition = get_bucket_composition()
        assert composition['composition']['Alex'] == 0
        assert composition['composition']['David'] == 0
        assert composition['composition']['Jose'] == 5

        # All draws should return Jose
        result = draw_closer('user1', 'T2')
        assert result['closer'] == 'Jose'


class TestT2BucketSystemPersistence:
    """Tests for T2 Bucket System persistence"""

    @pytest.fixture(autouse=True)
    def setup_temp_data_dir(self, temp_data_dir):
        """Setup temporary data directory for each test"""
        self.temp_dir = temp_data_dir
        data_dir = temp_data_dir / "persistent"
        data_dir.mkdir(parents=True, exist_ok=True)

        import app.services.t2_bucket_system as t2_module

        self.original_data_dir = t2_module.DATA_DIR
        self.original_bucket_file = t2_module.BUCKET_FILE

        t2_module.DATA_DIR = str(data_dir)
        t2_module.BUCKET_FILE = str(data_dir / "t2_bucket_system.json")

        yield

        t2_module.DATA_DIR = self.original_data_dir
        t2_module.BUCKET_FILE = self.original_bucket_file

    @pytest.mark.unit
    def test_data_persists_between_loads(self):
        """Test that data persists between save/load cycles"""
        from app.services.t2_bucket_system import (
            update_probability, load_bucket_data, get_probabilities
        )

        # Update probability
        update_probability('Alex', 7.0)

        # Force reload
        data = load_bucket_data()

        probs = get_probabilities()
        assert probs['Alex'] == 7.0

    @pytest.mark.unit
    def test_closers_persist_between_loads(self):
        """Test that closers configuration persists"""
        from app.services.t2_bucket_system import (
            add_closer, load_bucket_data, get_available_closers
        )

        # Add new closer
        add_closer('TestCloser', '#123456', 'Test', 3.0)

        # Force reload
        load_bucket_data()

        closers = get_available_closers()
        assert 'TestCloser' in closers

    @pytest.mark.unit
    def test_draw_history_preserved(self):
        """Test that draw history is preserved"""
        from app.services.t2_bucket_system import draw_closer, get_system_stats

        # Make some draws
        draw_closer('user1', 'T2', 'Customer1')
        draw_closer('user2', 'T2', 'Customer2')

        stats = get_system_stats()
        assert len(stats['recent_draws']) >= 2


class TestTimezoneBugFix:
    """Integration tests for timezone bug fix"""

    @pytest.fixture(autouse=True)
    def setup_temp_data_dir(self, temp_data_dir):
        """Setup temporary data directory for each test"""
        self.temp_dir = temp_data_dir
        data_dir = temp_data_dir / "persistent"
        data_dir.mkdir(parents=True, exist_ok=True)

        import app.services.t2_bucket_system as t2_module

        self.original_data_dir = t2_module.DATA_DIR
        self.original_bucket_file = t2_module.BUCKET_FILE

        t2_module.DATA_DIR = str(data_dir)
        t2_module.BUCKET_FILE = str(data_dir / "t2_bucket_system.json")

        yield

        t2_module.DATA_DIR = self.original_data_dir
        t2_module.BUCKET_FILE = self.original_bucket_file

    @pytest.mark.unit
    def test_old_timestamp_format_compatibility(self):
        """Test that old timestamp format (+01:00 offset) works correctly"""
        from app.services.t2_bucket_system import check_user_timeout, load_bucket_data, save_bucket_data

        # Simulate old timestamp format (before timezone utils)
        old_timestamp = "2025-12-05T16:43:51.610017+01:00"

        # Manually create user_last_draw with old format
        data = load_bucket_data()
        data['user_last_draw'] = {
            'ann-kathrin.welge': {
                'timestamp': old_timestamp,
                'closer': 'Alex',
                'draw_type': 'T2',
                'customer_name': 'Marco Menn'
            }
        }
        save_bucket_data(data)

        # Check timeout - should work correctly with old format
        result = check_user_timeout('ann-kathrin.welge', 'T2')

        # Timeout should have expired (3+ days old)
        assert result['can_draw'] is True
        assert result['timeout_remaining_seconds'] == 0

    @pytest.mark.unit
    def test_multi_day_old_timestamp_allows_draw(self):
        """Test that timestamps from 3+ days ago allow drawing"""
        from app.services.t2_bucket_system import check_user_timeout, load_bucket_data, save_bucket_data
        from app.utils.timezone_utils import now_utc, format_berlin_iso

        # Create a timestamp from 3 days ago
        three_days_ago = now_utc() - timedelta(days=3)
        old_timestamp = format_berlin_iso(three_days_ago)

        # Set user's last draw to 3 days ago
        data = load_bucket_data()
        data['user_last_draw'] = {
            'test.user': {
                'timestamp': old_timestamp,
                'closer': 'David',
                'draw_type': 'T2'
            }
        }
        save_bucket_data(data)

        # Check timeout
        result = check_user_timeout('test.user', 'T2')

        # Should definitely be able to draw
        assert result['can_draw'] is True
        assert result['timeout_remaining_seconds'] == 0
        assert 'Ready to draw' in result['message']

    @pytest.mark.unit
    def test_recent_draw_blocks_correctly(self):
        """Test that recent draws (within timeout) still block correctly"""
        from app.services.t2_bucket_system import check_user_timeout, load_bucket_data, save_bucket_data
        from app.utils.timezone_utils import now_utc, format_berlin_iso

        # Create a timestamp from 30 seconds ago (within 1 minute timeout)
        thirty_seconds_ago = now_utc() - timedelta(seconds=30)
        recent_timestamp = format_berlin_iso(thirty_seconds_ago)

        # Set user's last draw to 30 seconds ago
        data = load_bucket_data()
        data['user_last_draw'] = {
            'test.user': {
                'timestamp': recent_timestamp,
                'closer': 'Jose',
                'draw_type': 'T2'
            }
        }
        save_bucket_data(data)

        # Check timeout
        result = check_user_timeout('test.user', 'T2')

        # Should still be blocked
        assert result['can_draw'] is False
        assert result['timeout_remaining_seconds'] > 0
        assert result['timeout_remaining_seconds'] <= 35  # Should be ~30 seconds or less

    @pytest.mark.unit
    def test_mixed_timezone_representations(self):
        """Test that different timezone representations compare correctly"""
        from app.services.t2_bucket_system import check_user_timeout, load_bucket_data, save_bucket_data
        import pytz

        # Test with explicit offset format (old system)
        explicit_offset = "2025-12-05T16:43:51+01:00"

        # Test with Berlin TZ format (new system)
        berlin_tz = pytz.timezone("Europe/Berlin")
        berlin_dt = berlin_tz.localize(datetime(2025, 12, 5, 16, 43, 51))
        berlin_iso = berlin_dt.isoformat()

        # Both should work
        for timestamp_format, format_name in [(explicit_offset, "explicit"), (berlin_iso, "berlin")]:
            data = load_bucket_data()
            data['user_last_draw'] = {
                f'user.{format_name}': {
                    'timestamp': timestamp_format,
                    'closer': 'Alex',
                    'draw_type': 'T2'
                }
            }
            save_bucket_data(data)

            result = check_user_timeout(f'user.{format_name}', 'T2')

            # Both should allow draw (old timestamps)
            assert result['can_draw'] is True, f"Failed for {format_name} format"
            assert result['timeout_remaining_seconds'] == 0, f"Failed for {format_name} format"
