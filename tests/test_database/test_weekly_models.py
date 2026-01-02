# -*- coding: utf-8 -*-
"""
Database Tests - Weekly Models
Tests for WeeklyPointsParticipant, WeeklyPoints, WeeklyActivity, PrestigeData, MinigameData, PersistentData
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError


@pytest.mark.database
class TestWeeklyPointsParticipantModel:
    """Tests for WeeklyPointsParticipant model"""

    def test_create_participant(self, db_session):
        """Test creating weekly participant"""
        from app.models.weekly import WeeklyPointsParticipant

        participant = WeeklyPointsParticipant(
            participant_name='Test User',
            username='test.user',
            is_active=True,
            joined_date=datetime.utcnow(),
            total_weeks_participated=5,
            total_goal_points=250
        )

        db_session.add(participant)
        db_session.commit()

        result = db_session.query(WeeklyPointsParticipant).filter_by(participant_name='Test User').first()
        assert result is not None
        assert result.username == 'test.user'
        assert result.total_weeks_participated == 5
        assert result.is_active is True

    def test_participant_name_unique(self, db_session):
        """Test unique constraint on participant_name"""
        from app.models.weekly import WeeklyPointsParticipant

        participant1 = WeeklyPointsParticipant(
            participant_name='Duplicate User',
            username='user1'
        )
        db_session.add(participant1)
        db_session.commit()

        # Try duplicate participant_name
        participant2 = WeeklyPointsParticipant(
            participant_name='Duplicate User',
            username='user2'
        )
        db_session.add(participant2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_active_participants(self, db_session):
        """Test querying active participants"""
        from app.models.weekly import WeeklyPointsParticipant

        participants_data = [
            ('Active User 1', True),
            ('Inactive User', False),
            ('Active User 2', True),
        ]

        for name, is_active in participants_data:
            participant = WeeklyPointsParticipant(
                participant_name=name,
                is_active=is_active
            )
            db_session.add(participant)

        db_session.commit()

        active = db_session.query(WeeklyPointsParticipant).filter_by(is_active=True).all()
        assert len(active) == 2


@pytest.mark.database
class TestWeeklyPointsModel:
    """Tests for WeeklyPoints model"""

    def test_create_weekly_points(self, db_session):
        """Test creating weekly points entry"""
        from app.models.weekly import WeeklyPoints

        points = WeeklyPoints(
            week_id='2026-01',
            participant_name='Test User',
            goal_points=50,
            bonus_points=10,
            total_points=60,
            on_vacation=False,
            is_goal_set=True,
            activities=[
                {'type': 'booking', 'points': 10, 'date': '2026-01-05'},
                {'type': 'quest', 'points': 5, 'date': '2026-01-06'}
            ]
        )

        db_session.add(points)
        db_session.commit()

        result = db_session.query(WeeklyPoints).filter_by(week_id='2026-01').first()
        assert result is not None
        assert result.participant_name == 'Test User'
        assert result.total_points == 60
        assert len(result.activities) == 2

    def test_week_participant_unique(self, db_session):
        """Test unique constraint on week_id+participant_name"""
        from app.models.weekly import WeeklyPoints

        points1 = WeeklyPoints(
            week_id='2026-01',
            participant_name='Test User',
            goal_points=50
        )
        db_session.add(points1)
        db_session.commit()

        # Try duplicate week+participant
        points2 = WeeklyPoints(
            week_id='2026-01',
            participant_name='Test User',
            goal_points=100
        )
        db_session.add(points2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_points_by_week(self, db_session):
        """Test querying points by week"""
        from app.models.weekly import WeeklyPoints

        points_data = [
            ('2026-01', 'User 1', 50),
            ('2026-01', 'User 2', 75),
            ('2026-02', 'User 1', 60),
        ]

        for week_id, participant, points in points_data:
            entry = WeeklyPoints(
                week_id=week_id,
                participant_name=participant,
                goal_points=points
            )
            db_session.add(entry)

        db_session.commit()

        week1 = db_session.query(WeeklyPoints).filter_by(week_id='2026-01').all()
        assert len(week1) == 2


@pytest.mark.database
class TestWeeklyActivityModel:
    """Tests for WeeklyActivity model"""

    def test_create_weekly_activity(self, db_session):
        """Test creating weekly activity"""
        from app.models.weekly import WeeklyActivity

        activity = WeeklyActivity(
            week_id='2026-01',
            participant_name='Test User',
            activity_type='booking',
            activity_date=datetime.utcnow(),
            points_earned=10,
            is_pending=False,
            is_approved=True,
            approved_by='admin.user',
            approved_at=datetime.utcnow(),
            activity_data={'booking_id': 'BK123', 'customer': 'Test Customer'}
        )

        db_session.add(activity)
        db_session.commit()

        result = db_session.query(WeeklyActivity).filter_by(week_id='2026-01').first()
        assert result is not None
        assert result.activity_type == 'booking'
        assert result.points_earned == 10
        assert result.is_approved is True

    def test_query_pending_activities(self, db_session):
        """Test querying pending activities"""
        from app.models.weekly import WeeklyActivity

        now = datetime.utcnow()

        activities_data = [
            ('booking', 10, True),
            ('quest', 5, False),
            ('bonus', 15, True),
        ]

        for activity_type, points, is_pending in activities_data:
            activity = WeeklyActivity(
                week_id='2026-01',
                participant_name='Test User',
                activity_type=activity_type,
                activity_date=now,
                points_earned=points,
                is_pending=is_pending
            )
            db_session.add(activity)

        db_session.commit()

        pending = db_session.query(WeeklyActivity).filter_by(is_pending=True).all()
        assert len(pending) == 2

    def test_query_activities_by_participant(self, db_session):
        """Test querying activities by participant"""
        from app.models.weekly import WeeklyActivity

        now = datetime.utcnow()

        activities_data = [
            ('User 1', 10),
            ('User 2', 15),
            ('User 1', 20),
        ]

        for participant, points in activities_data:
            activity = WeeklyActivity(
                week_id='2026-01',
                participant_name=participant,
                activity_type='booking',
                activity_date=now,
                points_earned=points
            )
            db_session.add(activity)

        db_session.commit()

        user1_activities = db_session.query(WeeklyActivity).filter_by(
            participant_name='User 1'
        ).all()
        assert len(user1_activities) == 2


@pytest.mark.database
class TestPrestigeDataModel:
    """Tests for PrestigeData model"""

    def test_create_prestige_data(self, db_session):
        """Test creating prestige data"""
        from app.models.weekly import PrestigeData

        prestige = PrestigeData(
            username='test.user',
            prestige_level=2,
            prestige_points=150,
            pre_prestige_level=50,
            pre_prestige_points=5000,
            prestige_multiplier=1.2,
            unlocked_perks=['double_xp', 'faster_cooldowns'],
            last_prestige_date=datetime.utcnow(),
            lifetime_points=10000,
            lifetime_bookings=500
        )

        db_session.add(prestige)
        db_session.commit()

        result = db_session.query(PrestigeData).filter_by(username='test.user').first()
        assert result is not None
        assert result.prestige_level == 2
        assert result.prestige_multiplier == 1.2
        assert 'double_xp' in result.unlocked_perks
        assert result.lifetime_bookings == 500

    def test_username_unique_prestige(self, db_session):
        """Test unique constraint on username for prestige"""
        from app.models.weekly import PrestigeData

        prestige1 = PrestigeData(username='duplicate.user', prestige_level=1)
        db_session.add(prestige1)
        db_session.commit()

        # Try duplicate username
        prestige2 = PrestigeData(username='duplicate.user', prestige_level=2)
        db_session.add(prestige2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_prestige_history_tracking(self, db_session):
        """Test prestige history tracking"""
        from app.models.weekly import PrestigeData

        prestige = PrestigeData(
            username='test.user',
            prestige_level=3,
            prestige_history=[
                {'date': '2025-01-01', 'level': 1, 'points': 1000},
                {'date': '2025-06-01', 'level': 2, 'points': 2000},
                {'date': '2026-01-01', 'level': 3, 'points': 3000}
            ]
        )

        db_session.add(prestige)
        db_session.commit()

        result = db_session.query(PrestigeData).filter_by(username='test.user').first()
        assert len(result.prestige_history) == 3
        assert result.prestige_history[2]['level'] == 3


@pytest.mark.database
class TestMinigameDataModel:
    """Tests for MinigameData model"""

    def test_create_minigame_data(self, db_session):
        """Test creating minigame data"""
        from app.models.weekly import MinigameData

        minigame = MinigameData(
            username='test.user',
            minigame_id='tetris',
            minigame_name='Business Tetris',
            times_played=25,
            high_score=9500,
            average_score=6500.5,
            achievements_unlocked=['speed_demon', 'perfectionist'],
            last_played=datetime.utcnow(),
            total_coins_earned=500,
            total_xp_earned=1500
        )

        db_session.add(minigame)
        db_session.commit()

        result = db_session.query(MinigameData).filter_by(username='test.user').first()
        assert result is not None
        assert result.minigame_id == 'tetris'
        assert result.high_score == 9500
        assert 'speed_demon' in result.achievements_unlocked

    def test_username_minigame_unique(self, db_session):
        """Test unique constraint on username+minigame_id"""
        from app.models.weekly import MinigameData

        minigame1 = MinigameData(
            username='test.user',
            minigame_id='tetris',
            minigame_name='Tetris',
            high_score=1000
        )
        db_session.add(minigame1)
        db_session.commit()

        # Try duplicate
        minigame2 = MinigameData(
            username='test.user',
            minigame_id='tetris',
            minigame_name='Tetris',
            high_score=2000
        )
        db_session.add(minigame2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_minigames_by_high_score(self, db_session):
        """Test querying minigames by high score"""
        from app.models.weekly import MinigameData

        minigames_data = [
            ('user1', 'tetris', 5000),
            ('user2', 'tetris', 8000),
            ('user3', 'tetris', 3000),
        ]

        for username, minigame_id, high_score in minigames_data:
            minigame = MinigameData(
                username=username,
                minigame_id=minigame_id,
                minigame_name='Tetris',
                high_score=high_score
            )
            db_session.add(minigame)

        db_session.commit()

        top_scores = db_session.query(MinigameData).filter_by(
            minigame_id='tetris'
        ).order_by(MinigameData.high_score.desc()).all()

        assert len(top_scores) == 3
        assert top_scores[0].username == 'user2'  # Highest score
        assert top_scores[0].high_score == 8000


@pytest.mark.database
class TestPersistentDataModel:
    """Tests for PersistentData model (key-value store)"""

    def test_create_persistent_data(self, db_session):
        """Test creating persistent data"""
        from app.models.weekly import PersistentData

        data = PersistentData(
            data_key='app.settings.theme',
            data_value={'theme': 'dark', 'accent': 'blue'},
            data_type='config',
            description='Application theme settings'
        )

        db_session.add(data)
        db_session.commit()

        result = db_session.query(PersistentData).filter_by(data_key='app.settings.theme').first()
        assert result is not None
        assert result.data_type == 'config'
        assert result.data_value['theme'] == 'dark'

    def test_data_key_unique(self, db_session):
        """Test unique constraint on data_key"""
        from app.models.weekly import PersistentData

        data1 = PersistentData(
            data_key='duplicate.key',
            data_value={'value': 1},
            data_type='config'
        )
        db_session.add(data1)
        db_session.commit()

        # Try duplicate key
        data2 = PersistentData(
            data_key='duplicate.key',
            data_value={'value': 2},
            data_type='config'
        )
        db_session.add(data2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_persistent_data_with_expiry(self, db_session):
        """Test persistent data with expiry date"""
        from app.models.weekly import PersistentData

        expires_at = datetime.utcnow() + timedelta(hours=24)

        data = PersistentData(
            data_key='cache.temp_data',
            data_value={'cached': 'value'},
            data_type='cache',
            description='Temporary cached data',
            expires_at=expires_at
        )

        db_session.add(data)
        db_session.commit()

        result = db_session.query(PersistentData).filter_by(data_key='cache.temp_data').first()
        assert result is not None
        assert result.expires_at is not None
        assert result.data_type == 'cache'

    def test_query_data_by_type(self, db_session):
        """Test querying data by type"""
        from app.models.weekly import PersistentData

        data_entries = [
            ('config.1', 'config'),
            ('cache.1', 'cache'),
            ('system.1', 'system'),
        ]

        for key, data_type in data_entries:
            data = PersistentData(
                data_key=key,
                data_value={'test': 'value'},
                data_type=data_type
            )
            db_session.add(data)

        db_session.commit()

        configs = db_session.query(PersistentData).filter_by(data_type='config').all()
        assert len(configs) == 1
        assert configs[0].data_key == 'config.1'
