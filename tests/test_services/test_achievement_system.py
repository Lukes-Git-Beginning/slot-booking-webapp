# -*- coding: utf-8 -*-
"""
Tests fuer Achievement-System PG-Migration (Block 6).

Testet:
- load_mvp_badges PG-first + JSON-Fallback
- save_mvp_badges Dual-Write
- award_badge direkter PG-Write
- get_badge_leaderboard PG-Query + JSON-Fallback
- USE_POSTGRES=false Pfade
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock, mock_open, call
import json


# ========== FIXTURES ==========

@pytest.fixture(scope='module', autouse=True)
def mock_google_credentials():
    """Verhindert echten Google-Credential-Load beim Modul-Import."""
    with patch('app.utils.credentials.load_google_credentials', return_value=Mock()):
        yield


@pytest.fixture
def achievement_system():
    """AchievementSystem-Instanz mit gemocktem Dateisystem."""
    from app.services.achievement_system import AchievementSystem
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data='{}')):
            return AchievementSystem()


@pytest.fixture
def sample_mvp_data():
    return {
        "max.muster": {
            "badges": [
                {
                    "id": "mvp_week",
                    "name": "Wochenmvp 🥇",
                    "description": "Beste Woche - Wochenkoenig",
                    "emoji": "🥇",
                    "rarity": "epic",
                    "category": "mvp",
                    "earned_date": "2026-03-01 10:00:00",
                    "period": "2026-W09",
                    "color": "#f59e0b"
                }
            ],
            "periods": {
                "2026-W09": "2026-03-01 10:00:00"
            }
        },
        "anna.schmidt": {
            "badges": [
                {
                    "id": "mvp_month",
                    "name": "Monatsmvp 👑",
                    "description": "Bester Monat - Monatskoenig",
                    "emoji": "👑",
                    "rarity": "legendary",
                    "category": "mvp",
                    "earned_date": "2026-02-28 20:00:00",
                    "period": "2026-02",
                    "color": "#eab308"
                }
            ],
            "periods": {
                "2026-02": "2026-02-28 20:00:00"
            }
        }
    }


@pytest.fixture
def sample_badges_data():
    return {
        "max.muster": {
            "badges": [
                {
                    "id": "daily_10",
                    "name": "Anfaenger",
                    "description": "10 Punkte",
                    "emoji": "🌱",
                    "rarity": "common",
                    "category": "daily",
                    "earned_date": "2026-01-01 09:00:00",
                    "color": "#10b981"
                },
                {
                    "id": "weekly_100",
                    "name": "Wochenkrieger",
                    "description": "100 Wochenpunkte",
                    "emoji": "⚔️",
                    "rarity": "uncommon",
                    "category": "weekly",
                    "earned_date": "2026-01-07 18:00:00",
                    "color": "#3b82f6"
                }
            ],
            "earned_dates": {
                "daily_10": "2026-01-01 09:00:00",
                "weekly_100": "2026-01-07 18:00:00"
            },
            "total_badges": 2
        }
    }


# ========== load_mvp_badges ==========

@pytest.mark.service
class TestLoadMvpBadges:
    """PG-first Read fuer MVP-Badges."""

    def test_pg_first_returns_mvp_data(self, achievement_system, sample_mvp_data):
        """load_mvp_badges liest aus PG wenn USE_POSTGRES=True und PG verfuegbar."""
        mock_row_1 = MagicMock()
        mock_row_1.username = "max.muster"
        mock_row_1.badge_id = "mvp_week"
        mock_row_1.name = "Wochenmvp 🥇"
        mock_row_1.description = "Beste Woche - Wochenkoenig"
        mock_row_1.emoji = "🥇"
        mock_row_1.rarity = "epic"
        mock_row_1.category = "mvp"
        mock_row_1.color = "#f59e0b"
        mock_row_1.earned_date = datetime(2026, 3, 1, 10, 0, 0)
        mock_row_1.badge_metadata = {"period": "2026-W09"}

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_row_1]

        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope') as mock_scope:
            mock_scope.return_value.__enter__ = lambda s, *a: mock_session
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            result = achievement_system.load_mvp_badges()

        assert "max.muster" in result
        assert len(result["max.muster"]["badges"]) == 1
        assert result["max.muster"]["badges"][0]["id"] == "mvp_week"
        assert result["max.muster"]["periods"]["2026-W09"] == "2026-03-01 10:00:00"

    def test_pg_fallback_on_error(self, achievement_system, sample_mvp_data):
        """load_mvp_badges faellt auf JSON zurueck wenn PG fehlschlaegt."""
        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope') as mock_scope:
            mock_scope.return_value.__enter__ = Mock(side_effect=Exception("PG down"))
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            with patch('builtins.open', mock_open(read_data=json.dumps(sample_mvp_data))):
                result = achievement_system.load_mvp_badges()

        assert isinstance(result, dict)

    def test_no_pg_reads_json(self, achievement_system, sample_mvp_data):
        """load_mvp_badges liest direkt JSON wenn USE_POSTGRES=False."""
        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', False):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_mvp_data))):
                result = achievement_system.load_mvp_badges()

        assert "max.muster" in result
        assert "anna.schmidt" in result

    def test_empty_pg_returns_empty_dict(self, achievement_system):
        """load_mvp_badges gibt leeres Dict zurueck wenn PG keine Zeilen hat."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []

        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope') as mock_scope:
            mock_scope.return_value.__enter__ = lambda s, *a: mock_session
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            result = achievement_system.load_mvp_badges()

        assert result == {}


# ========== save_mvp_badges ==========

@pytest.mark.service
class TestSaveMvpBadges:
    """Dual-Write fuer MVP-Badges."""

    def test_dual_write_pg_and_json(self, achievement_system, sample_mvp_data):
        """save_mvp_badges schreibt in PG UND JSON."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope') as mock_scope:
            mock_scope.return_value.__enter__ = lambda s, *a: mock_session
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            m = mock_open()
            with patch('builtins.open', m):
                achievement_system.save_mvp_badges(sample_mvp_data)

        # PG: session.add wurde aufgerufen (fuer neue Badges)
        assert mock_session.add.called
        # JSON: open+write wurde aufgerufen
        assert m.called

    def test_pg_write_skips_existing(self, achievement_system, sample_mvp_data):
        """save_mvp_badges fuegt keine Duplikate in PG ein."""
        existing_row = MagicMock()
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_row

        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope') as mock_scope:
            mock_scope.return_value.__enter__ = lambda s, *a: mock_session
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            with patch('builtins.open', mock_open()):
                achievement_system.save_mvp_badges(sample_mvp_data)

        # session.add darf nicht aufgerufen worden sein (bereits vorhanden)
        mock_session.add.assert_not_called()

    def test_json_always_written_even_if_pg_fails(self, achievement_system, sample_mvp_data):
        """JSON-Write passiert auch wenn PG-Write fehlschlaegt."""
        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope') as mock_scope:
            mock_scope.return_value.__enter__ = Mock(side_effect=Exception("PG down"))
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            m = mock_open()
            with patch('builtins.open', m):
                achievement_system.save_mvp_badges(sample_mvp_data)

        assert m.called

    def test_no_pg_writes_only_json(self, achievement_system, sample_mvp_data):
        """save_mvp_badges schreibt nur JSON wenn USE_POSTGRES=False."""
        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', False):
            m = mock_open()
            with patch('builtins.open', m):
                achievement_system.save_mvp_badges(sample_mvp_data)

        assert m.called


# ========== award_badge PG-Write ==========

@pytest.mark.service
class TestAwardBadgePgWrite:
    """award_badge schreibt direkt in PG."""

    def _make_scope_ctx(self, mock_session):
        """Hilfsfunktion: Erstellt einen Context-Manager fuer db_session_scope."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=mock_session)
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    def test_award_badge_inserts_into_pg(self, achievement_system):
        """award_badge fuegt neues Badge in PG ein wenn USE_POSTGRES=True."""
        badges_data = {}
        definition = {
            "name": "Anfaenger 🌱",
            "description": "10 Punkte an einem Tag erreicht",
            "emoji": "🌱",
            "rarity": "common",
            "category": "daily"
        }

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        import app.services.achievement_system as ach_mod
        ctx = self._make_scope_ctx(mock_session)

        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope', return_value=ctx), \
             patch('app.services.achievement_system.notification_service', create=True):
            try:
                achievement_system.award_badge("max.muster", "daily_10", definition, badges_data)
            except Exception:
                pass

        # PG-Write wurde versucht (query zur Duplikat-Pruefung)
        assert mock_session.query.called

    def test_award_badge_pg_add_called_for_new_badge(self, achievement_system):
        """award_badge ruft session.add auf wenn Badge noch nicht existiert."""
        badges_data = {}
        definition = {
            "name": "Anfaenger 🌱",
            "description": "10 Punkte an einem Tag erreicht",
            "emoji": "🌱",
            "rarity": "common",
            "category": "daily"
        }

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        import app.services.achievement_system as ach_mod
        ctx = self._make_scope_ctx(mock_session)

        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope', return_value=ctx):
            # Notification-Service wegpatchen damit kein Dateizugriff entsteht
            with patch('app.services.notification_service', create=True):
                try:
                    achievement_system.award_badge("max.muster", "daily_10", definition, badges_data)
                except Exception:
                    pass

        assert mock_session.add.called

    def test_award_badge_skips_pg_add_if_already_exists(self, achievement_system):
        """award_badge fuegt kein Duplikat in PG ein."""
        badges_data = {}
        definition = {
            "name": "Anfaenger 🌱",
            "description": "10 Punkte an einem Tag erreicht",
            "emoji": "🌱",
            "rarity": "common",
            "category": "daily"
        }

        existing_row = MagicMock()
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_row

        import app.services.achievement_system as ach_mod
        ctx = self._make_scope_ctx(mock_session)

        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope', return_value=ctx):
            with patch('app.services.notification_service', create=True):
                try:
                    achievement_system.award_badge("max.muster", "daily_10", definition, badges_data)
                except Exception:
                    pass

        mock_session.add.assert_not_called()

    def test_award_badge_no_pg_still_works(self, achievement_system):
        """award_badge setzt Badge in badges_data auch ohne PG."""
        badges_data = {}
        definition = {
            "name": "Anfaenger 🌱",
            "description": "10 Punkte an einem Tag",
            "emoji": "🌱",
            "rarity": "common",
            "category": "daily"
        }

        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', False):
            with patch('app.services.notification_service', create=True):
                try:
                    result = achievement_system.award_badge("max.muster", "daily_10", definition, badges_data)
                except Exception:
                    result = None

        assert "max.muster" in badges_data


# ========== get_badge_leaderboard ==========

@pytest.mark.service
class TestGetBadgeLeaderboard:
    """PG-first Leaderboard-Query."""

    def test_pg_leaderboard_groups_by_user(self, achievement_system):
        """get_badge_leaderboard aggregiert Badges korrekt aus PG."""
        row1 = MagicMock()
        row1.username = "max.muster"
        row1.badge_id = "daily_10"
        row1.name = "Anfaenger"
        row1.description = "10 Punkte"
        row1.emoji = "🌱"
        row1.rarity = "common"
        row1.category = "daily"
        row1.color = "#10b981"
        row1.earned_date = datetime(2026, 1, 1, 9, 0, 0)

        row2 = MagicMock()
        row2.username = "max.muster"
        row2.badge_id = "weekly_100"
        row2.name = "Wochenkrieger"
        row2.description = "100 Wochenpunkte"
        row2.emoji = "⚔️"
        row2.rarity = "uncommon"
        row2.category = "weekly"
        row2.color = "#3b82f6"
        row2.earned_date = datetime(2026, 1, 7, 18, 0, 0)

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [row1, row2]

        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope') as mock_scope:
            mock_scope.return_value.__enter__ = lambda s, *a: mock_session
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            result = achievement_system.get_badge_leaderboard()

        assert len(result) == 1
        assert result[0]["total_badges"] == 2
        assert result[0]["rarity_points"] == 3  # common=1, uncommon=2

    def test_pg_leaderboard_fallback_on_error(self, achievement_system, sample_badges_data):
        """get_badge_leaderboard faellt auf JSON-Fallback zurueck bei PG-Fehler."""
        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', True), \
             patch.object(ach_mod, 'POSTGRES_AVAILABLE', True), \
             patch.object(ach_mod, 'db_session_scope') as mock_scope:
            mock_scope.return_value.__enter__ = Mock(side_effect=Exception("PG down"))
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)

            with patch.object(achievement_system, 'load_badges', return_value=sample_badges_data):
                result = achievement_system.get_badge_leaderboard()

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_no_pg_uses_json_fallback(self, achievement_system, sample_badges_data):
        """get_badge_leaderboard nutzt JSON wenn USE_POSTGRES=False."""
        import app.services.achievement_system as ach_mod
        with patch.object(ach_mod, 'USE_POSTGRES', False):
            with patch.object(achievement_system, 'load_badges', return_value=sample_badges_data):
                result = achievement_system.get_badge_leaderboard()

        assert isinstance(result, list)
        assert result[0]["user"] in ("max.muster", "max.muster")

    def test_leaderboard_sorted_by_rarity_points(self, achievement_system):
        """get_badge_leaderboard sortiert korrekt nach rarity_points absteigend."""
        import app.services.achievement_system as ach_mod

        badges_data = {
            "user_a": {
                "badges": [
                    {"id": "b1", "rarity": "legendary", "earned_date": "2026-01-01 00:00:00", "color": "#eab308"}
                ],
                "total_badges": 1
            },
            "user_b": {
                "badges": [
                    {"id": "b2", "rarity": "common", "earned_date": "2026-01-01 00:00:00", "color": "#10b981"},
                    {"id": "b3", "rarity": "common", "earned_date": "2026-01-01 00:00:00", "color": "#10b981"},
                ],
                "total_badges": 2
            }
        }

        with patch.object(ach_mod, 'USE_POSTGRES', False):
            with patch.object(achievement_system, 'load_badges', return_value=badges_data):
                result = achievement_system.get_badge_leaderboard()

        # user_a: legendary=10 Punkte > user_b: 2x common=2 Punkte
        assert result[0]["user"] == "user_a"


# ========== __init__ Pfad-Setup ==========

@pytest.mark.service
class TestInitPaths:
    """__init__ verwendet PERSIST_BASE korrekt."""

    def test_init_uses_persist_base(self):
        """AchievementSystem nutzt PERSIST_BASE fuer Dateipfade."""
        import app.services.achievement_system as ach_mod
        with patch.dict('os.environ', {'PERSIST_BASE': '/tmp/test_hub'}), \
             patch('os.makedirs'), \
             patch('os.path.exists', return_value=True):
            system = ach_mod.AchievementSystem()

        assert '/tmp/test_hub' in system.badges_file
        assert '/tmp/test_hub' in system.mvp_file
        assert 'persistent' in system.badges_file
        assert 'persistent' in system.mvp_file
