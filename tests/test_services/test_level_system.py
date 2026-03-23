# -*- coding: utf-8 -*-
"""
Service Layer Tests — Level System + Rank Tracking
Tests for:
- app/services/level_system.py  (LevelSystem)
- app/services/rank_tracking_service.py  (RankTrackingService)
"""

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open, call


# ========== FIXTURES ==========

@pytest.fixture(scope='module', autouse=True)
def mock_google_credentials():
    """Prevent Google credential loading during import."""
    with patch('app.utils.credentials.load_google_credentials', return_value=MagicMock()):
        yield


@pytest.fixture
def tmp_level_files(tmp_path):
    """Create temporary JSON files for level_system tests."""
    levels_file = tmp_path / "user_levels.json"
    history_file = tmp_path / "level_history.json"
    levels_file.write_text("{}", encoding="utf-8")
    history_file.write_text("{}", encoding="utf-8")
    return str(levels_file), str(history_file)


@pytest.fixture
def level_system_no_pg(tmp_level_files):
    """LevelSystem instance with PG disabled."""
    levels_file, history_file = tmp_level_files
    with patch.dict('os.environ', {'USE_POSTGRES': 'false', 'PERSIST_BASE': str(
            __import__('pathlib').Path(levels_file).parent.parent)}):
        with patch('app.services.level_system.USE_POSTGRES', False):
            with patch('app.services.level_system.POSTGRES_AVAILABLE', False):
                from app.services.level_system import LevelSystem
                system = LevelSystem()
                system.levels_file = levels_file
                system.level_history_file = history_file
                return system


@pytest.fixture
def rank_service_no_pg(tmp_path):
    """RankTrackingService instance with PG disabled."""
    history_file = tmp_path / "rank_history.json"
    history_file.write_text("{}", encoding="utf-8")
    with patch('app.services.rank_tracking_service.USE_POSTGRES', False):
        with patch('app.services.rank_tracking_service.POSTGRES_AVAILABLE', False):
            from app.services.rank_tracking_service import RankTrackingService
            svc = RankTrackingService.__new__(RankTrackingService)
            svc.history_file = str(history_file)
            return svc


# ========== LEVEL SYSTEM — UNIT TESTS ==========

class TestLevelCalculation:
    """Tests for pure calculation methods (no I/O)."""

    def test_calculate_level_from_xp_level1(self, level_system_no_pg):
        level, level_xp, next_xp = level_system_no_pg.calculate_level_from_xp(0)
        assert level == 1
        assert level_xp == 0
        assert next_xp == 100

    def test_calculate_level_from_xp_level1_boundary(self, level_system_no_pg):
        level, _, _ = level_system_no_pg.calculate_level_from_xp(99)
        assert level == 1

    def test_calculate_level_from_xp_level2(self, level_system_no_pg):
        level, _, _ = level_system_no_pg.calculate_level_from_xp(100)
        assert level == 2

    def test_calculate_level_from_xp_monotonic(self, level_system_no_pg):
        """Level must be non-decreasing as XP increases."""
        prev_level = 0
        for xp in range(0, 10000, 100):
            level, _, _ = level_system_no_pg.calculate_level_from_xp(xp)
            assert level >= prev_level
            prev_level = level

    def test_get_level_title_known(self, level_system_no_pg):
        assert level_system_no_pg.get_level_title(1) == "Anfänger"
        assert level_system_no_pg.get_level_title(5) == "Profi"
        assert level_system_no_pg.get_level_title(10) == "Mythos"

    def test_get_level_title_beyond_10(self, level_system_no_pg):
        title = level_system_no_pg.get_level_title(15)
        assert "15" in title

    def test_get_rarity_color_known(self, level_system_no_pg):
        assert level_system_no_pg.get_rarity_color("legendary") == "#eab308"
        assert level_system_no_pg.get_rarity_color("common") == "#10b981"

    def test_get_rarity_color_unknown(self, level_system_no_pg):
        # Should return default color, not raise
        color = level_system_no_pg.get_rarity_color("unknown_rarity")
        assert color.startswith("#")

    def test_calculate_total_xp_empty(self, level_system_no_pg):
        badges_data = {"badges": [], "total_badges": 0}
        with patch.object(level_system_no_pg, '_get_prestige_xp_offset', return_value=0):
            xp = level_system_no_pg.calculate_total_xp({}, badges_data)
        assert xp == 0

    def test_calculate_total_xp_points(self, level_system_no_pg):
        badges_data = {"badges": [], "total_badges": 0}
        xp = level_system_no_pg.calculate_total_xp({"2026-01": 10}, badges_data)
        assert xp == 100  # 10 points * 10 XP

    def test_calculate_total_xp_badges(self, level_system_no_pg):
        badges_data = {
            "badges": [{"rarity": "legendary"}, {"rarity": "common"}],
            "total_badges": 2
        }
        xp = level_system_no_pg.calculate_total_xp({}, badges_data)
        assert xp == 1000 + 50  # legendary + common


class TestCheckLevelUp:
    """Tests for check_level_up with JSON backend."""

    def test_first_entry_no_level_up(self, level_system_no_pg):
        result = level_system_no_pg.check_level_up("testuser", 1, 50)
        assert result is None

    def test_level_up_detected(self, level_system_no_pg, tmp_level_files):
        _, history_file = tmp_level_files
        # Seed history file with user at level 1
        history = {
            "testuser": {
                "current_level": 1,
                "current_xp": 50,
                "level_ups": [],
                "last_check": "2026-01-01 10:00:00"
            }
        }
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f)
        level_system_no_pg.level_history_file = history_file

        with patch('app.services.level_system.USE_POSTGRES', False):
            result = level_system_no_pg.check_level_up("testuser", 2, 120)

        assert result is not None
        assert result["old_level"] == 1
        assert result["new_level"] == 2

    def test_no_level_up_same_level(self, level_system_no_pg, tmp_level_files):
        _, history_file = tmp_level_files
        history = {
            "testuser": {
                "current_level": 2,
                "current_xp": 110,
                "level_ups": [],
                "last_check": "2026-01-01 10:00:00"
            }
        }
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f)
        level_system_no_pg.level_history_file = history_file

        with patch('app.services.level_system.USE_POSTGRES', False):
            result = level_system_no_pg.check_level_up("testuser", 2, 150)

        assert result is None


class TestGetLevelStatistics:
    """Tests for get_level_statistics with JSON fallback."""

    def test_statistics_unknown_user_returns_defaults(self, level_system_no_pg, tmp_level_files):
        _, history_file = tmp_level_files
        # history_file is empty {} — unknown user should return default structure
        with patch('app.services.level_system.USE_POSTGRES', False):
            stats = level_system_no_pg.get_level_statistics("unknown_user")
        assert stats.get("current_level") == 1
        assert stats.get("total_level_ups") == 0
        assert stats.get("recent_level_ups") == []

    def test_statistics_unreadable_file_returns_empty(self, level_system_no_pg, tmp_path):
        # Point to a non-existent file so JSON load fails -> returns {}
        level_system_no_pg.level_history_file = str(tmp_path / "does_not_exist.json")
        with patch('app.services.level_system.USE_POSTGRES', False):
            stats = level_system_no_pg.get_level_statistics("ghost_user")
        assert stats == {}

    def test_statistics_user_present(self, level_system_no_pg, tmp_level_files):
        _, history_file = tmp_level_files
        history = {
            "alice": {
                "current_level": 3,
                "current_xp": 400,
                "level_ups": [
                    {"old_level": 1, "new_level": 2, "xp_gained": 100, "timestamp": "2026-01-01 10:00:00"},
                    {"old_level": 2, "new_level": 3, "xp_gained": 300, "timestamp": "2026-02-01 10:00:00"},
                ],
                "last_check": "2026-02-01 10:00:00"
            }
        }
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f)
        level_system_no_pg.level_history_file = history_file

        with patch('app.services.level_system.USE_POSTGRES', False):
            stats = level_system_no_pg.get_level_statistics("alice")

        assert stats["current_level"] == 3
        assert stats["total_level_ups"] == 2
        assert stats["average_xp_per_level"] == 200


# ========== RANK TRACKING SERVICE — UNIT TESTS ==========

class TestRankTrackingServiceNoPg:
    """RankTrackingService tests with PG disabled (pure JSON)."""

    def test_record_and_load_history(self, rank_service_no_pg):
        scores = [("alice", 100), ("bob", 80), ("carol", 60)]
        with patch('app.services.rank_tracking_service.USE_POSTGRES', False):
            rank_service_no_pg.record_daily_ranks(scores)
            history = rank_service_no_pg._load_history()

        assert len(history) == 1
        date_key = list(history.keys())[0]
        assert history[date_key]["alice"] == 1
        assert history[date_key]["bob"] == 2
        assert history[date_key]["carol"] == 3

    def test_get_rank_change_no_history(self, rank_service_no_pg):
        change = rank_service_no_pg.get_rank_change("newuser", 1)
        assert change == 0

    def test_get_rank_changes_batch(self, rank_service_no_pg, tmp_path):
        import json as _json
        from datetime import date, timedelta

        # Seed a yesterday snapshot
        yesterday = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        history = {yesterday: {"alice": 2, "bob": 1}}
        history_file = tmp_path / "rank_history.json"
        history_file.write_text(_json.dumps(history), encoding="utf-8")
        rank_service_no_pg.history_file = str(history_file)

        with patch('app.services.rank_tracking_service.USE_POSTGRES', False):
            changes = rank_service_no_pg.get_rank_changes([("alice", 100), ("bob", 80)])

        # alice was 2, now 1 => +1
        assert changes["alice"] == 1
        # bob was 1, now 2 => -1
        assert changes["bob"] == -1

    def test_get_rank_history_json_fallback(self, rank_service_no_pg, tmp_path):
        import json as _json
        from datetime import date, timedelta

        today = datetime.now().date()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
        history = {d: {"alice": i + 1} for i, d in enumerate(dates)}
        history_file = tmp_path / "rh.json"
        history_file.write_text(_json.dumps(history), encoding="utf-8")
        rank_service_no_pg.history_file = str(history_file)

        with patch('app.services.rank_tracking_service.USE_POSTGRES', False):
            result = rank_service_no_pg.get_rank_history("alice", days=10)

        assert len(result) == 5
        assert all("date" in r and "rank" in r for r in result)


# ========== MODELS — SANITY CHECKS ==========

class TestGamificationModels:
    """Ensure new models can be instantiated without DB."""

    def test_user_level_repr(self):
        from app.models.gamification import UserLevel
        ul = UserLevel(username="test", level=3, xp=350, level_title="Aktiver")
        assert "test" in repr(ul)
        assert "3" in repr(ul)

    def test_level_history_repr(self):
        from app.models.gamification import LevelHistory
        lh = LevelHistory(
            username="test", old_level=2, new_level=3,
            old_xp=200, new_xp=350, xp_gained=150,
            leveled_up_at=datetime(2026, 1, 15, 12, 0, 0)
        )
        assert "2->3" in repr(lh)

    def test_rank_history_repr(self):
        from app.models.gamification import RankHistory
        rh = RankHistory(date="2026-01-15", username="alice", rank_position=1)
        assert "alice" in repr(rh)
        assert "1" in repr(rh)
