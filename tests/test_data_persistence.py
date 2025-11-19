# -*- coding: utf-8 -*-
"""
Tests for DataPersistence Service
"""

import pytest
import json
import os
from pathlib import Path
from datetime import datetime


class TestDataPersistence:
    """Tests for the DataPersistence class"""

    @pytest.mark.unit
    def test_init_creates_directories(self, mock_data_persistence):
        """Test that initialization creates required directories"""
        assert mock_data_persistence.data_dir.exists()
        assert mock_data_persistence.backup_dir.exists()
        assert mock_data_persistence.static_dir.exists()

    @pytest.mark.unit
    def test_save_data_creates_file(self, mock_data_persistence):
        """Test saving data creates a JSON file"""
        test_data = {'key': 'value', 'number': 42}

        result = mock_data_persistence.save_data('test_file', test_data)

        assert result is True
        assert (mock_data_persistence.data_dir / 'test_file.json').exists()

    @pytest.mark.unit
    def test_save_data_with_json_extension(self, mock_data_persistence):
        """Test saving data with .json extension in filename"""
        test_data = {'key': 'value'}

        result = mock_data_persistence.save_data('test_file.json', test_data)

        assert result is True
        # Should not create test_file.json.json
        assert (mock_data_persistence.data_dir / 'test_file.json').exists()
        assert not (mock_data_persistence.data_dir / 'test_file.json.json').exists()

    @pytest.mark.unit
    def test_load_data_returns_saved_data(self, mock_data_persistence):
        """Test loading data returns previously saved data"""
        test_data = {'key': 'value', 'list': [1, 2, 3]}

        mock_data_persistence.save_data('test_file', test_data)
        loaded_data = mock_data_persistence.load_data('test_file')

        assert loaded_data == test_data

    @pytest.mark.unit
    def test_load_data_returns_default_when_missing(self, mock_data_persistence):
        """Test loading non-existent data returns default value"""
        result = mock_data_persistence.load_data('nonexistent', default={'default': True})

        assert result == {'default': True}

    @pytest.mark.unit
    def test_load_data_returns_empty_dict_when_missing_no_default(self, mock_data_persistence):
        """Test loading non-existent data returns empty dict when no default"""
        result = mock_data_persistence.load_data('nonexistent')

        assert result == {}

    @pytest.mark.unit
    def test_save_data_creates_backup(self, mock_data_persistence):
        """Test saving data creates a backup file"""
        test_data = {'key': 'value'}

        mock_data_persistence.save_data('test_file', test_data)

        backup_files = list(mock_data_persistence.backup_dir.glob('test_file.json.*.backup'))
        assert len(backup_files) >= 1

    @pytest.mark.unit
    def test_save_data_creates_static_copy(self, mock_data_persistence):
        """Test saving data also saves to static directory for compatibility"""
        test_data = {'key': 'value'}

        mock_data_persistence.save_data('test_file', test_data)

        assert (mock_data_persistence.static_dir / 'test_file.json').exists()
        with open(mock_data_persistence.static_dir / 'test_file.json', 'r') as f:
            static_data = json.load(f)
        assert static_data == test_data

    @pytest.mark.unit
    def test_save_scores(self, mock_data_persistence, sample_scores_data):
        """Test saving scores data"""
        result = mock_data_persistence.save_scores(sample_scores_data)

        assert result is True
        assert (mock_data_persistence.data_dir / 'scores.json').exists()

    @pytest.mark.unit
    def test_load_scores_returns_saved_scores(self, mock_data_persistence, sample_scores_data):
        """Test loading scores returns previously saved data"""
        mock_data_persistence.save_scores(sample_scores_data)
        loaded_scores = mock_data_persistence.load_scores()

        assert loaded_scores == sample_scores_data

    @pytest.mark.unit
    def test_load_scores_returns_empty_when_missing(self, mock_data_persistence):
        """Test loading scores returns empty dict when no file exists"""
        result = mock_data_persistence.load_scores()

        assert result == {}

    @pytest.mark.unit
    def test_save_badges(self, mock_data_persistence, sample_badges_data):
        """Test saving badges data"""
        result = mock_data_persistence.save_badges(sample_badges_data)

        assert result is True
        assert (mock_data_persistence.data_dir / 'user_badges.json').exists()

    @pytest.mark.unit
    def test_load_badges_returns_saved_badges(self, mock_data_persistence, sample_badges_data):
        """Test loading badges returns previously saved data"""
        mock_data_persistence.save_badges(sample_badges_data)
        loaded_badges = mock_data_persistence.load_badges()

        assert loaded_badges == sample_badges_data

    @pytest.mark.unit
    def test_path_traversal_protection(self, mock_data_persistence):
        """Test that path traversal attacks are prevented"""
        malicious_filename = '../../../etc/passwd'
        test_data = {'malicious': True}

        result = mock_data_persistence.save_data(malicious_filename, test_data)

        # Should save with sanitized filename, not traverse paths
        assert result is True
        # Should only create passwd.json in data_dir, not traverse up
        assert (mock_data_persistence.data_dir / 'passwd.json').exists()
        # Verify no file was created outside data_dir
        assert not Path('/etc/passwd.json').exists()

    @pytest.mark.unit
    def test_backup_cleanup_keeps_latest_ten(self, mock_data_persistence):
        """Test that backup cleanup keeps only the latest 10 backups"""
        test_data = {'key': 'value'}

        # Create 15 backups
        for i in range(15):
            mock_data_persistence.save_data('test_file', test_data)

        backup_files = list(mock_data_persistence.backup_dir.glob('test_file.json.*.backup'))
        assert len(backup_files) <= 10

    @pytest.mark.unit
    def test_validate_data_integrity_no_issues(self, mock_data_persistence):
        """Test data integrity validation with valid data"""
        # Create required files
        mock_data_persistence.save_scores({})
        mock_data_persistence.save_badges({})
        mock_data_persistence.save_champions({})
        mock_data_persistence.save_daily_user_stats({})

        is_valid, issues = mock_data_persistence.validate_data_integrity()

        assert is_valid is True
        assert len(issues) == 0

    @pytest.mark.unit
    def test_validate_data_integrity_missing_files(self, mock_data_persistence):
        """Test data integrity validation with missing files"""
        # Don't create any files
        is_valid, issues = mock_data_persistence.validate_data_integrity()

        assert is_valid is False
        assert len(issues) > 0
        assert any('fehlt' in issue for issue in issues)

    @pytest.mark.unit
    def test_validate_data_integrity_invalid_json(self, mock_data_persistence):
        """Test data integrity validation with invalid JSON"""
        # Create file with invalid JSON
        scores_file = mock_data_persistence.data_dir / 'scores.json'
        scores_file.write_text('not valid json {{{')

        is_valid, issues = mock_data_persistence.validate_data_integrity()

        assert is_valid is False
        assert any('JSON' in issue for issue in issues)

    @pytest.mark.unit
    def test_restore_from_latest_backup(self, mock_data_persistence):
        """Test restoring data from the latest backup"""
        original_data = {'original': True}
        mock_data_persistence.save_scores(original_data)

        # Overwrite with different data
        new_data = {'new': True}
        mock_data_persistence.save_scores(new_data)

        # Restore from backup
        success, message = mock_data_persistence.restore_from_latest_backup('scores')

        assert success is True
        assert 'Wiederhergestellt' in message

    @pytest.mark.unit
    def test_restore_from_backup_no_backups(self, mock_data_persistence):
        """Test restoring when no backups exist"""
        success, message = mock_data_persistence.restore_from_latest_backup('nonexistent')

        assert success is False
        assert 'Keine Backups' in message

    @pytest.mark.unit
    def test_get_backup_statistics(self, mock_data_persistence):
        """Test getting backup statistics"""
        # Create some backups
        mock_data_persistence.save_scores({'test': 1})
        mock_data_persistence.save_badges({'test': 2})

        stats = mock_data_persistence.get_backup_statistics()

        assert 'scores.json' in stats
        assert 'user_badges.json' in stats
        assert stats['scores.json']['count'] >= 1

    @pytest.mark.unit
    def test_auto_backup_all(self, mock_data_persistence):
        """Test automatic backup of all data files"""
        # Create data files first
        mock_data_persistence.save_scores({'test': 1})
        mock_data_persistence.save_badges({'test': 2})
        mock_data_persistence.save_champions({'test': 3})
        mock_data_persistence.save_daily_user_stats({'test': 4})

        backed_up = mock_data_persistence.auto_backup_all()

        assert len(backed_up) >= 4

    @pytest.mark.unit
    def test_save_and_load_unicode_data(self, mock_data_persistence):
        """Test saving and loading Unicode data (German characters)"""
        unicode_data = {
            'name': 'Müller',
            'city': 'Düsseldorf',
            'description': 'Größe und Wärme'
        }

        mock_data_persistence.save_data('unicode_test', unicode_data)
        loaded_data = mock_data_persistence.load_data('unicode_test')

        assert loaded_data == unicode_data
        assert loaded_data['name'] == 'Müller'

    @pytest.mark.unit
    def test_save_champions(self, mock_data_persistence):
        """Test saving champions data"""
        champions_data = {
            '2024-01': {'username': 'test_user', 'points': 500},
            '2024-02': {'username': 'admin_user', 'points': 750}
        }

        result = mock_data_persistence.save_champions(champions_data)

        assert result is True
        assert (mock_data_persistence.data_dir / 'champions.json').exists()

    @pytest.mark.unit
    def test_load_champions_returns_saved_data(self, mock_data_persistence):
        """Test loading champions returns previously saved data"""
        champions_data = {
            '2024-01': {'username': 'test_user', 'points': 500}
        }

        mock_data_persistence.save_champions(champions_data)
        loaded = mock_data_persistence.load_champions()

        assert loaded == champions_data

    @pytest.mark.unit
    def test_save_daily_user_stats(self, mock_data_persistence):
        """Test saving daily user stats"""
        stats_data = {
            '2024-01-15': {'test_user': {'bookings': 5, 'points': 25}}
        }

        result = mock_data_persistence.save_daily_user_stats(stats_data)

        assert result is True
        assert (mock_data_persistence.data_dir / 'daily_user_stats.json').exists()

    @pytest.mark.unit
    def test_load_daily_user_stats_returns_saved_data(self, mock_data_persistence):
        """Test loading daily user stats returns previously saved data"""
        stats_data = {
            '2024-01-15': {'test_user': {'bookings': 5, 'points': 25}}
        }

        mock_data_persistence.save_daily_user_stats(stats_data)
        loaded = mock_data_persistence.load_daily_user_stats()

        assert loaded == stats_data

    @pytest.mark.unit
    def test_fallback_to_static_directory(self, mock_data_persistence):
        """Test loading falls back to static directory when data_dir file missing"""
        # Save data only to static directory
        test_data = {'static_only': True}
        static_file = mock_data_persistence.static_dir / 'fallback_test.json'
        with open(static_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        # Load should find it in static directory
        loaded = mock_data_persistence.load_data('fallback_test')

        assert loaded == test_data

    @pytest.mark.unit
    def test_empty_data_handling(self, mock_data_persistence):
        """Test handling of empty data structures"""
        empty_data = {}

        result = mock_data_persistence.save_data('empty_test', empty_data)
        loaded = mock_data_persistence.load_data('empty_test')

        assert result is True
        assert loaded == {}

    @pytest.mark.unit
    def test_large_data_handling(self, mock_data_persistence):
        """Test handling of large data structures"""
        large_data = {f'user_{i}': {'points': i * 10, 'badges': [f'badge_{j}' for j in range(10)]}
                      for i in range(100)}

        result = mock_data_persistence.save_data('large_test', large_data)
        loaded = mock_data_persistence.load_data('large_test')

        assert result is True
        assert loaded == large_data
        assert len(loaded) == 100


class TestDataPersistenceEdgeCases:
    """Edge case tests for DataPersistence"""

    @pytest.mark.unit
    def test_concurrent_saves_dont_corrupt(self, mock_data_persistence):
        """Test that rapid successive saves don't corrupt data"""
        for i in range(10):
            mock_data_persistence.save_scores({f'user_{i}': i * 10})

        # Last save should be intact
        loaded = mock_data_persistence.load_scores()
        assert loaded == {'user_9': 90}

    @pytest.mark.unit
    def test_special_characters_in_data(self, mock_data_persistence):
        """Test handling of special characters in data"""
        special_data = {
            'quotes': "He said \"Hello\"",
            'newlines': "Line1\nLine2",
            'tabs': "Col1\tCol2",
            'unicode': "🎉🏆"
        }

        mock_data_persistence.save_data('special', special_data)
        loaded = mock_data_persistence.load_data('special')

        assert loaded == special_data

    @pytest.mark.unit
    def test_nested_data_structures(self, mock_data_persistence):
        """Test handling of deeply nested data structures"""
        nested_data = {
            'level1': {
                'level2': {
                    'level3': {
                        'level4': {
                            'value': 'deep'
                        }
                    }
                }
            }
        }

        mock_data_persistence.save_data('nested', nested_data)
        loaded = mock_data_persistence.load_data('nested')

        assert loaded == nested_data
        assert loaded['level1']['level2']['level3']['level4']['value'] == 'deep'
