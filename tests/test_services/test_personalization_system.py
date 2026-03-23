# -*- coding: utf-8 -*-
"""
Service Tests - Personalization System (Block 5 PG-Migration)
Tests for app/services/personalization_system.py
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import json


# ========== FIXTURES ==========

@pytest.fixture(scope='module', autouse=True)
def mock_google_credentials():
    """Mock Google credentials to prevent loading during module import"""
    with patch('app.utils.credentials.load_google_credentials', return_value=MagicMock()):
        yield


@pytest.fixture
def mock_personalization_system():
    """PersonalizationSystem instance with mocked file I/O and no PostgreSQL"""
    # Import before patching open to avoid interfering with pytz timezone loading
    from app.services.personalization_system import PersonalizationSystem

    with patch('os.path.exists', return_value=True), \
         patch('os.makedirs'), \
         patch('builtins.open', mock_open(read_data='{}')), \
         patch('app.services.personalization_system.USE_POSTGRES', False), \
         patch('app.services.personalization_system.POSTGRES_AVAILABLE', False):
        system = PersonalizationSystem()
        return system


@pytest.fixture
def default_customization():
    return {
        "avatar": {
            "background": "gradient_blue",
            "border": "simple",
            "effect": "none",
            "title": "none"
        },
        "unlocked_items": ["gradient_blue", "simple", "none"]
    }


@pytest.fixture
def default_profile(default_customization):
    return {
        "user": "test.user",
        "display_name": "test.user",
        "bio": "",
        "favorite_quote": "",
        "privacy_settings": {
            "show_in_leaderboard": True,
            "show_statistics": True,
            "allow_friend_requests": True
        },
        "notification_preferences": {
            "achievement_notifications": True,
            "daily_quest_reminders": True,
            "streak_warnings": True,
            "level_up_celebrations": True
        },
        "customization": default_customization,
        "theme": "default"
    }


# ========== TESTS: load_user_profile (JSON-fallback) ==========

class TestLoadUserProfileJsonFallback:
    """Tests for load_user_profile() with USE_POSTGRES=false"""

    def test_load_profile_new_user_returns_defaults(self, mock_personalization_system):
        system = mock_personalization_system

        with patch.object(system, '_load_json', return_value={}), \
             patch.object(system, '_save_json'), \
             patch.object(system, 'get_user_customization', return_value={}):
            profile = system.load_user_profile("new.user")

        assert profile["user"] == "new.user"
        assert profile["display_name"] == "new.user"
        assert "privacy_settings" in profile
        assert "notification_preferences" in profile

    def test_load_profile_existing_user_returns_stored(self, mock_personalization_system, default_profile):
        system = mock_personalization_system
        stored = {"test.user": default_profile}

        with patch.object(system, '_load_json', return_value=stored), \
             patch.object(system, '_save_json'), \
             patch.object(system, 'get_user_customization', return_value={}):
            profile = system.load_user_profile("test.user")

        assert profile["user"] == "test.user"
        assert "last_active" in profile

    def test_load_profile_updates_last_active(self, mock_personalization_system):
        system = mock_personalization_system

        with patch.object(system, '_load_json', return_value={}), \
             patch.object(system, '_save_json'), \
             patch.object(system, 'get_user_customization', return_value={}):
            profile = system.load_user_profile("test.user")

        assert "last_active" in profile
        # last_active should be a valid ISO string
        from datetime import datetime
        datetime.fromisoformat(profile["last_active"])


# ========== TESTS: update_user_profile (JSON-fallback) ==========

class TestUpdateUserProfileJsonFallback:
    """Tests for update_user_profile() with USE_POSTGRES=false"""

    def test_update_display_name(self, mock_personalization_system):
        system = mock_personalization_system

        with patch.object(system, '_load_json', return_value={}), \
             patch.object(system, '_save_json') as mock_save, \
             patch.object(system, 'get_user_customization', return_value={}):
            profile = system.update_user_profile("test.user", {"display_name": "Test User"})

        assert profile["display_name"] == "Test User"
        mock_save.assert_called()

    def test_update_bio(self, mock_personalization_system):
        system = mock_personalization_system

        with patch.object(system, '_load_json', return_value={}), \
             patch.object(system, '_save_json'), \
             patch.object(system, 'get_user_customization', return_value={}):
            profile = system.update_user_profile("test.user", {"bio": "Meine Bio"})

        assert profile["bio"] == "Meine Bio"

    def test_update_theme(self, mock_personalization_system):
        system = mock_personalization_system

        with patch.object(system, '_load_json', return_value={}), \
             patch.object(system, '_save_json'), \
             patch.object(system, 'get_user_customization', return_value={}):
            profile = system.update_user_profile("test.user", {"theme": "midnight"})

        assert profile["theme"] == "midnight"

    def test_update_rejects_unknown_fields(self, mock_personalization_system):
        system = mock_personalization_system

        with patch.object(system, '_load_json', return_value={}), \
             patch.object(system, '_save_json'), \
             patch.object(system, 'get_user_customization', return_value={}):
            profile = system.update_user_profile("test.user", {"unknown_field": "hacked"})

        assert "unknown_field" not in profile

    def test_update_sets_last_updated(self, mock_personalization_system):
        system = mock_personalization_system

        with patch.object(system, '_load_json', return_value={}), \
             patch.object(system, '_save_json'), \
             patch.object(system, 'get_user_customization', return_value={}):
            profile = system.update_user_profile("test.user", {"bio": "Test"})

        assert "last_updated" in profile


# ========== TESTS: get_user_customization (JSON-fallback) ==========

class TestGetUserCustomizationJsonFallback:
    """Tests for get_user_customization() with USE_POSTGRES=false"""

    def test_returns_default_for_new_user(self, mock_personalization_system):
        system = mock_personalization_system

        with patch.object(system, '_load_json', return_value={}):
            result = system.get_user_customization("new.user")

        assert "avatar" in result
        assert result["avatar"]["background"] == "gradient_blue"
        assert "unlocked_items" in result

    def test_returns_stored_for_existing_user(self, mock_personalization_system, default_customization):
        system = mock_personalization_system
        stored = {"test.user": default_customization}

        with patch.object(system, '_load_json', return_value=stored):
            result = system.get_user_customization("test.user")

        assert result["avatar"]["background"] == "gradient_blue"

    def test_unlocked_items_present_by_default(self, mock_personalization_system):
        system = mock_personalization_system

        with patch.object(system, '_load_json', return_value={}):
            result = system.get_user_customization("any.user")

        assert isinstance(result["unlocked_items"], list)
        assert "gradient_blue" in result["unlocked_items"]


# ========== TESTS: PostgreSQL path (mocked session) ==========

class TestLoadUserProfileWithPostgres:
    """Tests for load_user_profile() when USE_POSTGRES=true"""

    def test_returns_pg_profile_when_user_exists(self):
        """PG-first: wenn User in DB gefunden wird, kommt Profil aus DB"""
        mock_db_user = MagicMock()
        mock_db_user.profile_data = {
            "user": "pg.user",
            "display_name": "PG User",
            "bio": "from db",
            "privacy_settings": {},
            "notification_preferences": {},
            "theme": "default"
        }

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_db_user

        with patch('app.services.personalization_system.USE_POSTGRES', True), \
             patch('app.services.personalization_system.POSTGRES_AVAILABLE', True), \
             patch('app.services.personalization_system.db_session_scope') as mock_scope, \
             patch('os.makedirs'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{}')):
            mock_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            from app.services.personalization_system import PersonalizationSystem
            system = PersonalizationSystem()

            with patch.object(system, 'get_user_customization', return_value={}):
                profile = system.load_user_profile("pg.user")

        assert profile["display_name"] == "PG User"
        assert profile["bio"] == "from db"

    def test_falls_back_to_json_when_pg_fails(self):
        """Falls PG fehlschlaegt, JSON-Fallback wird verwendet"""
        stored_profile = {
            "user": "json.user",
            "display_name": "JSON User",
            "bio": "from json",
            "privacy_settings": {},
            "notification_preferences": {},
            "theme": "default"
        }

        with patch('app.services.personalization_system.USE_POSTGRES', True), \
             patch('app.services.personalization_system.POSTGRES_AVAILABLE', True), \
             patch('app.services.personalization_system.db_session_scope') as mock_scope, \
             patch('os.makedirs'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{}')):
            # PG wirft Exception
            mock_scope.return_value.__enter__ = MagicMock(side_effect=Exception("DB down"))
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            from app.services.personalization_system import PersonalizationSystem
            system = PersonalizationSystem()

            with patch.object(system, '_load_json', return_value={"json.user": stored_profile}), \
                 patch.object(system, '_save_json'), \
                 patch.object(system, 'get_user_customization', return_value={}):
                profile = system.load_user_profile("json.user")

        assert profile["display_name"] == "JSON User"


class TestGetUserCustomizationWithPostgres:
    """Tests for get_user_customization() when USE_POSTGRES=true"""

    def test_returns_pg_config_when_row_exists(self):
        """PG-first: gibt config aus DB zurueck"""
        pg_config = {
            "avatar": {"background": "cosmic", "border": "fire", "effect": "sparkle", "title": "master"},
            "unlocked_items": ["cosmic", "fire", "sparkle", "master", "gradient_blue", "simple", "none"]
        }
        mock_row = MagicMock()
        mock_row.config = pg_config

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_row

        with patch('app.services.personalization_system.USE_POSTGRES', True), \
             patch('app.services.personalization_system.POSTGRES_AVAILABLE', True), \
             patch('app.services.personalization_system.db_session_scope_no_commit') as mock_scope, \
             patch('os.makedirs'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{}')):
            mock_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            from app.services.personalization_system import PersonalizationSystem
            system = PersonalizationSystem()
            result = system.get_user_customization("test.user")

        assert result["avatar"]["background"] == "cosmic"

    def test_falls_back_to_json_when_no_pg_row(self):
        """Wenn kein PG-Row vorhanden, JSON-Fallback"""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        with patch('app.services.personalization_system.USE_POSTGRES', True), \
             patch('app.services.personalization_system.POSTGRES_AVAILABLE', True), \
             patch('app.services.personalization_system.db_session_scope_no_commit') as mock_scope, \
             patch('os.makedirs'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{}')):
            mock_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            from app.services.personalization_system import PersonalizationSystem
            system = PersonalizationSystem()

            stored = {"test.user": {"avatar": {"background": "gradient_green"}, "unlocked_items": []}}
            with patch.object(system, '_load_json', return_value=stored):
                result = system.get_user_customization("test.user")

        assert result["avatar"]["background"] == "gradient_green"
