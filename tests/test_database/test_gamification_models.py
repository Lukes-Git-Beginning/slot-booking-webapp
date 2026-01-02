# -*- coding: utf-8 -*-
"""
Database Tests - Gamification Models
Tests for Score, UserBadge, DailyQuest, QuestProgress, PersonalGoal, Champion, MasteryData
"""

import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError


@pytest.mark.database
class TestScoreModel:
    """Tests for Score model (monthly scores)"""

    def test_create_score_minimal(self, db_session):
        """Test creating score with minimal fields"""
        from app.models.gamification import Score

        score = Score(
            username='test.user',
            month='2025-12',
            points=150
        )

        db_session.add(score)
        db_session.commit()

        result = db_session.query(Score).filter_by(username='test.user').first()
        assert result is not None
        assert result.username == 'test.user'
        assert result.month == '2025-12'
        assert result.points == 150
        assert result.bookings_count == 0  # Default

    def test_score_username_month_unique(self, db_session):
        """Test unique constraint on username+month"""
        from app.models.gamification import Score

        score1 = Score(username='test.user', month='2025-12', points=100)
        db_session.add(score1)
        db_session.commit()

        # Try to create duplicate
        score2 = Score(username='test.user', month='2025-12', points=200)
        db_session.add(score2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_scores_by_month(self, db_session):
        """Test querying scores for a specific month"""
        from app.models.gamification import Score

        scores_data = [
            ('user1', '2025-12', 100),
            ('user2', '2025-12', 150),
            ('user3', '2026-01', 200),
        ]

        for username, month, points in scores_data:
            score = Score(username=username, month=month, points=points)
            db_session.add(score)

        db_session.commit()

        results = db_session.query(Score).filter_by(month='2025-12').order_by(Score.points.desc()).all()
        assert len(results) == 2
        assert results[0].username == 'user2'  # Highest points first
        assert results[0].points == 150


@pytest.mark.database
class TestUserBadgeModel:
    """Tests for UserBadge model"""

    def test_create_badge_minimal(self, db_session):
        """Test creating user badge"""
        from app.models.gamification import UserBadge

        badge = UserBadge(
            username='test.user',
            badge_id='first_booking',
            name='First Booking',
            description='Made your first booking',
            emoji='🎯',
            rarity='common',
            category='daily',
            earned_date=datetime.utcnow()
        )

        db_session.add(badge)
        db_session.commit()

        result = db_session.query(UserBadge).filter_by(username='test.user').first()
        assert result is not None
        assert result.badge_id == 'first_booking'
        assert result.rarity == 'common'

    def test_badge_username_badge_unique(self, db_session):
        """Test unique constraint - user can only earn badge once"""
        from app.models.gamification import UserBadge

        badge1 = UserBadge(
            username='test.user',
            badge_id='champion',
            name='Champion',
            description='Won the week',
            emoji='👑',
            rarity='legendary',
            category='weekly',
            earned_date=datetime.utcnow()
        )
        db_session.add(badge1)
        db_session.commit()

        # Try to earn same badge again
        badge2 = UserBadge(
            username='test.user',
            badge_id='champion',
            name='Champion',
            description='Won the week',
            emoji='👑',
            rarity='legendary',
            category='weekly',
            earned_date=datetime.utcnow()
        )
        db_session.add(badge2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_badges_by_rarity(self, db_session):
        """Test querying badges by rarity"""
        from app.models.gamification import UserBadge

        badges_data = [
            ('test.user', 'badge1', 'common'),
            ('test.user', 'badge2', 'rare'),
            ('test.user', 'badge3', 'legendary'),
        ]

        for username, badge_id, rarity in badges_data:
            badge = UserBadge(
                username=username,
                badge_id=badge_id,
                name=f'Badge {badge_id}',
                description='Test',
                emoji='🎯',
                rarity=rarity,
                category='daily',
                earned_date=datetime.utcnow()
            )
            db_session.add(badge)

        db_session.commit()

        legendary = db_session.query(UserBadge).filter_by(rarity='legendary').all()
        assert len(legendary) == 1
        assert legendary[0].badge_id == 'badge3'


@pytest.mark.database
class TestDailyQuestModel:
    """Tests for DailyQuest model"""

    def test_create_daily_quest(self, db_session):
        """Test creating daily quest"""
        from app.models.gamification import DailyQuest

        quest = DailyQuest(
            quest_id='quest_2026-01-15',
            quest_date=date(2026, 1, 15),
            title='Book 5 Customers',
            description='Book at least 5 customers today',
            category='booking',
            difficulty='medium',
            target_value=5,
            target_type='bookings',
            reward_points=100,
            reward_coins=50
        )

        db_session.add(quest)
        db_session.commit()

        result = db_session.query(DailyQuest).filter_by(quest_id='quest_2026-01-15').first()
        assert result is not None
        assert result.title == 'Book 5 Customers'
        assert result.target_value == 5
        assert result.is_active is True  # Default

    def test_quest_id_unique(self, db_session):
        """Test unique constraint on quest_id"""
        from app.models.gamification import DailyQuest

        quest1 = DailyQuest(
            quest_id='quest_123',
            quest_date=date(2026, 1, 15),
            title='Quest 1',
            description='Test',
            category='booking',
            difficulty='easy',
            target_value=3,
            target_type='bookings',
            reward_points=50
        )
        db_session.add(quest1)
        db_session.commit()

        # Try duplicate quest_id
        quest2 = DailyQuest(
            quest_id='quest_123',
            quest_date=date(2026, 1, 16),
            title='Quest 2',
            description='Test',
            category='booking',
            difficulty='easy',
            target_value=5,
            target_type='bookings',
            reward_points=100
        )
        db_session.add(quest2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_active_quests(self, db_session):
        """Test querying active quests"""
        from app.models.gamification import DailyQuest

        quests_data = [
            ('quest1', True),
            ('quest2', False),
            ('quest3', True),
        ]

        for quest_id, is_active in quests_data:
            quest = DailyQuest(
                quest_id=quest_id,
                quest_date=date(2026, 1, 15),
                title=f'Quest {quest_id}',
                description='Test',
                category='booking',
                difficulty='easy',
                target_value=5,
                target_type='bookings',
                reward_points=50,
                is_active=is_active
            )
            db_session.add(quest)

        db_session.commit()

        active = db_session.query(DailyQuest).filter_by(is_active=True).all()
        assert len(active) == 2


@pytest.mark.database
class TestQuestProgressModel:
    """Tests for QuestProgress model"""

    def test_create_quest_progress(self, db_session):
        """Test creating quest progress"""
        from app.models.gamification import QuestProgress

        progress = QuestProgress(
            username='test.user',
            quest_id='quest_123',
            current_value=3,
            target_value=5,
            progress_percent=60.0
        )

        db_session.add(progress)
        db_session.commit()

        result = db_session.query(QuestProgress).filter_by(username='test.user').first()
        assert result is not None
        assert result.current_value == 3
        assert result.target_value == 5
        assert result.is_completed is False

    def test_quest_progress_username_quest_unique(self, db_session):
        """Test unique constraint on username+quest_id"""
        from app.models.gamification import QuestProgress

        progress1 = QuestProgress(
            username='test.user',
            quest_id='quest_123',
            current_value=2,
            target_value=5,
            progress_percent=40.0
        )
        db_session.add(progress1)
        db_session.commit()

        # Try duplicate
        progress2 = QuestProgress(
            username='test.user',
            quest_id='quest_123',
            current_value=4,
            target_value=5,
            progress_percent=80.0
        )
        db_session.add(progress2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_quest_completion_tracking(self, db_session):
        """Test quest completion tracking"""
        from app.models.gamification import QuestProgress

        now = datetime.utcnow()

        progress = QuestProgress(
            username='test.user',
            quest_id='quest_123',
            current_value=5,
            target_value=5,
            progress_percent=100.0,
            is_completed=True,
            completed_at=now
        )

        db_session.add(progress)
        db_session.commit()

        result = db_session.query(QuestProgress).filter_by(username='test.user').first()
        assert result.is_completed is True
        assert result.completed_at is not None
        assert result.is_claimed is False  # Not yet claimed


@pytest.mark.database
class TestPersonalGoalModel:
    """Tests for PersonalGoal model"""

    def test_create_personal_goal(self, db_session):
        """Test creating personal goal"""
        from app.models.gamification import PersonalGoal

        goal = PersonalGoal(
            username='test.user',
            goal_id='goal_123',
            title='Book 100 Customers',
            description='Reach 100 bookings this quarter',
            category='performance',
            target_value=100.0,
            current_value=25.0,
            target_date=date(2026, 3, 31)
        )

        db_session.add(goal)
        db_session.commit()

        result = db_session.query(PersonalGoal).filter_by(username='test.user').first()
        assert result is not None
        assert result.title == 'Book 100 Customers'
        assert result.target_value == 100.0
        assert result.is_active is True

    def test_personal_goal_username_goal_unique(self, db_session):
        """Test unique constraint on username+goal_id"""
        from app.models.gamification import PersonalGoal

        goal1 = PersonalGoal(
            username='test.user',
            goal_id='goal_123',
            title='Goal 1',
            description='Test',
            category='performance',
            target_value=50.0
        )
        db_session.add(goal1)
        db_session.commit()

        # Try duplicate
        goal2 = PersonalGoal(
            username='test.user',
            goal_id='goal_123',
            title='Goal 2',
            description='Test',
            category='learning',
            target_value=100.0
        )
        db_session.add(goal2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_active_goals(self, db_session):
        """Test querying active goals"""
        from app.models.gamification import PersonalGoal

        goals_data = [
            ('goal1', True, False),
            ('goal2', False, False),
            ('goal3', True, True),
        ]

        for goal_id, is_active, is_completed in goals_data:
            goal = PersonalGoal(
                username='test.user',
                goal_id=goal_id,
                title=f'Goal {goal_id}',
                description='Test',
                category='performance',
                target_value=50.0,
                is_active=is_active,
                is_completed=is_completed
            )
            db_session.add(goal)

        db_session.commit()

        active = db_session.query(PersonalGoal).filter_by(is_active=True, is_completed=False).all()
        assert len(active) == 1
        assert active[0].goal_id == 'goal1'


@pytest.mark.database
class TestChampionModel:
    """Tests for Champion model"""

    def test_create_champion(self, db_session):
        """Test creating champion record"""
        from app.models.gamification import Champion

        champion = Champion(
            period='2025-W52',
            period_type='weekly',
            username='test.user',
            rank=1,
            total_points=500,
            total_bookings=25,
            show_rate=85.5,
            reward_coins=1000
        )

        db_session.add(champion)
        db_session.commit()

        result = db_session.query(Champion).filter_by(period='2025-W52').first()
        assert result is not None
        assert result.rank == 1
        assert result.username == 'test.user'
        assert result.total_points == 500

    def test_champion_period_rank_unique(self, db_session):
        """Test unique constraint on period+rank"""
        from app.models.gamification import Champion

        champ1 = Champion(
            period='2025-W52',
            period_type='weekly',
            username='user1',
            rank=1,
            total_points=500,
            total_bookings=25,
            show_rate=85.0
        )
        db_session.add(champ1)
        db_session.commit()

        # Try to create another champion with same period and rank
        champ2 = Champion(
            period='2025-W52',
            period_type='weekly',
            username='user2',
            rank=1,  # Same rank
            total_points=450,
            total_bookings=22,
            show_rate=80.0
        )
        db_session.add(champ2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_champions_by_period_type(self, db_session):
        """Test querying champions by period type"""
        from app.models.gamification import Champion

        champions_data = [
            ('2025-W52', 'weekly', 1),
            ('2025-12', 'monthly', 1),
            ('2026-W01', 'weekly', 1),
        ]

        for period, period_type, rank in champions_data:
            champion = Champion(
                period=period,
                period_type=period_type,
                username=f'user_{rank}',
                rank=rank,
                total_points=500,
                total_bookings=25,
                show_rate=85.0
            )
            db_session.add(champion)

        db_session.commit()

        weekly = db_session.query(Champion).filter_by(period_type='weekly').all()
        assert len(weekly) == 2


@pytest.mark.database
class TestMasteryDataModel:
    """Tests for MasteryData model"""

    def test_create_mastery_data(self, db_session):
        """Test creating mastery data"""
        from app.models.gamification import MasteryData

        mastery = MasteryData(
            username='test.user',
            skill_id='booking_speed',
            skill_name='Booking Speed',
            skill_category='booking',
            current_level=5,
            current_xp=350,
            xp_to_next_level=500,
            practice_count=50,
            success_rate=85.5,
            mastery_percent=70.0
        )

        db_session.add(mastery)
        db_session.commit()

        result = db_session.query(MasteryData).filter_by(username='test.user').first()
        assert result is not None
        assert result.skill_id == 'booking_speed'
        assert result.current_level == 5
        assert result.success_rate == 85.5

    def test_mastery_username_skill_unique(self, db_session):
        """Test unique constraint on username+skill_id"""
        from app.models.gamification import MasteryData

        mastery1 = MasteryData(
            username='test.user',
            skill_id='booking_speed',
            skill_name='Booking Speed',
            skill_category='booking',
            current_level=3,
            current_xp=150,
            xp_to_next_level=300
        )
        db_session.add(mastery1)
        db_session.commit()

        # Try duplicate
        mastery2 = MasteryData(
            username='test.user',
            skill_id='booking_speed',
            skill_name='Booking Speed',
            skill_category='booking',
            current_level=5,
            current_xp=350,
            xp_to_next_level=500
        )
        db_session.add(mastery2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_mastery_by_category(self, db_session):
        """Test querying mastery by skill category"""
        from app.models.gamification import MasteryData

        skills_data = [
            ('skill1', 'booking'),
            ('skill2', 'communication'),
            ('skill3', 'booking'),
        ]

        for skill_id, category in skills_data:
            mastery = MasteryData(
                username='test.user',
                skill_id=skill_id,
                skill_name=f'Skill {skill_id}',
                skill_category=category,
                current_level=3,
                current_xp=150,
                xp_to_next_level=300
            )
            db_session.add(mastery)

        db_session.commit()

        booking_skills = db_session.query(MasteryData).filter_by(skill_category='booking').all()
        assert len(booking_skills) == 2
