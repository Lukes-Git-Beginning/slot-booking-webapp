# -*- coding: utf-8 -*-
"""
Database Tests - User Models
Tests for User, UserStats, UserPrediction, BehaviorPattern, PersonalInsight
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError


@pytest.mark.database
class TestUserModel:
    """Tests for User model (central user management)"""

    def test_create_user_minimal(self, db_session):
        """Test creating user with minimal fields"""
        from app.models.user import User

        user = User(
            username='test.user'
        )

        db_session.add(user)
        db_session.commit()

        result = db_session.query(User).filter_by(username='test.user').first()
        assert result is not None
        assert result.username == 'test.user'
        assert result.total_points == 0  # Default
        assert result.level == 1  # Default
        assert result.is_active is True  # Default

    def test_create_user_all_fields(self, db_session):
        """Test creating user with all fields"""
        from app.models.user import User

        user = User(
            username='test.user',
            email='test@example.com',
            full_name='Test User',
            password_hash='hashed_password',
            is_admin=True,
            consultant_name='Test Consultant',
            consultant_email='consultant@example.com',
            role='consultant',
            total_points=500,
            total_coins=250,
            level=5,
            experience=1500,
            prestige_level=1,
            prestige_points=100,
            last_login=datetime.utcnow(),
            on_vacation=False
        )

        db_session.add(user)
        db_session.commit()

        result = db_session.query(User).filter_by(username='test.user').first()
        assert result is not None
        assert result.email == 'test@example.com'
        assert result.is_admin is True
        assert result.level == 5
        assert result.total_coins == 250

    def test_username_unique(self, db_session):
        """Test unique constraint on username"""
        from app.models.user import User

        user1 = User(username='duplicate.user')
        db_session.add(user1)
        db_session.commit()

        # Try duplicate username
        user2 = User(username='duplicate.user')
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_email_unique(self, db_session):
        """Test unique constraint on email"""
        from app.models.user import User

        user1 = User(username='user1', email='duplicate@example.com')
        db_session.add(user1)
        db_session.commit()

        # Try duplicate email
        user2 = User(username='user2', email='duplicate@example.com')
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_users_by_role(self, db_session):
        """Test querying users by role"""
        from app.models.user import User

        users_data = [
            ('user1', 'consultant'),
            ('user2', 't2_closer'),
            ('user3', 'consultant'),
        ]

        for username, role in users_data:
            user = User(username=username, role=role)
            db_session.add(user)

        db_session.commit()

        consultants = db_session.query(User).filter_by(role='consultant').all()
        assert len(consultants) == 2


@pytest.mark.database
class TestUserStatsModel:
    """Tests for UserStats model"""

    def test_create_user_stats(self, db_session):
        """Test creating user stats"""
        from app.models.user import UserStats

        stats = UserStats(
            username='test.user',
            stat_date=datetime.utcnow(),
            stat_type='daily',
            bookings_count=10,
            bookings_erschienen=8,
            bookings_nicht_erschienen=2,
            show_rate=80.0,
            points_earned=150,
            coins_earned=50
        )

        db_session.add(stats)
        db_session.commit()

        result = db_session.query(UserStats).filter_by(username='test.user').first()
        assert result is not None
        assert result.bookings_count == 10
        assert result.show_rate == 80.0
        assert result.points_earned == 150

    def test_query_stats_by_type(self, db_session):
        """Test querying stats by type"""
        from app.models.user import UserStats

        now = datetime.utcnow()

        stats_data = [
            ('daily', 100),
            ('weekly', 500),
            ('monthly', 2000),
        ]

        for stat_type, points in stats_data:
            stats = UserStats(
                username='test.user',
                stat_date=now,
                stat_type=stat_type,
                points_earned=points
            )
            db_session.add(stats)

        db_session.commit()

        weekly_stats = db_session.query(UserStats).filter_by(stat_type='weekly').all()
        assert len(weekly_stats) == 1
        assert weekly_stats[0].points_earned == 500

    def test_query_stats_by_date_range(self, db_session):
        """Test querying stats by date range"""
        from app.models.user import UserStats

        base_date = datetime.utcnow()

        for i in range(5):
            stats = UserStats(
                username='test.user',
                stat_date=base_date + timedelta(days=i),
                stat_type='daily',
                points_earned=100 * (i + 1)
            )
            db_session.add(stats)

        db_session.commit()

        start_date = base_date + timedelta(days=1)
        end_date = base_date + timedelta(days=3)

        results = db_session.query(UserStats).filter(
            UserStats.username == 'test.user',
            UserStats.stat_date >= start_date,
            UserStats.stat_date <= end_date
        ).all()

        assert len(results) == 3


@pytest.mark.database
class TestUserPredictionModel:
    """Tests for UserPrediction model"""

    def test_create_user_prediction(self, db_session):
        """Test creating user prediction"""
        from app.models.user import UserPrediction

        prediction = UserPrediction(
            username='test.user',
            prediction_date=datetime.utcnow(),
            prediction_type='performance',
            predicted_value=85.5,
            confidence_score=0.92,
            model_version='v1.0',
            features_used={'bookings': 50, 'show_rate': 0.8}
        )

        db_session.add(prediction)
        db_session.commit()

        result = db_session.query(UserPrediction).filter_by(username='test.user').first()
        assert result is not None
        assert result.prediction_type == 'performance'
        assert result.predicted_value == 85.5
        assert result.confidence_score == 0.92

    def test_prediction_with_actual_value(self, db_session):
        """Test prediction with actual value (for accuracy tracking)"""
        from app.models.user import UserPrediction

        prediction = UserPrediction(
            username='test.user',
            prediction_date=datetime.utcnow(),
            prediction_type='churn',
            predicted_value=0.15,
            confidence_score=0.85,
            actual_value=0.12,  # Actual churn rate
            model_version='v1.0',
            features_used={'activity': 0.8}
        )

        db_session.add(prediction)
        db_session.commit()

        result = db_session.query(UserPrediction).filter_by(username='test.user').first()
        assert result.actual_value == 0.12

    def test_query_predictions_by_type(self, db_session):
        """Test querying predictions by type"""
        from app.models.user import UserPrediction

        now = datetime.utcnow()

        predictions_data = [
            ('performance', 80.0),
            ('churn', 0.1),
            ('growth', 1.5),
        ]

        for pred_type, value in predictions_data:
            prediction = UserPrediction(
                username='test.user',
                prediction_date=now,
                prediction_type=pred_type,
                predicted_value=value,
                confidence_score=0.9,
                model_version='v1.0',
                features_used={}
            )
            db_session.add(prediction)

        db_session.commit()

        performance_preds = db_session.query(UserPrediction).filter_by(
            prediction_type='performance'
        ).all()
        assert len(performance_preds) == 1
        assert performance_preds[0].predicted_value == 80.0


@pytest.mark.database
class TestBehaviorPatternModel:
    """Tests for BehaviorPattern model"""

    def test_create_behavior_pattern(self, db_session):
        """Test creating behavior pattern"""
        from app.models.user import BehaviorPattern

        pattern = BehaviorPattern(
            username='test.user',
            pattern_date=datetime.utcnow(),
            pattern_type='login',
            frequency=5.2,
            avg_duration=15.5,
            peak_hours={'9': 10, '14': 15, '18': 8},
            is_consistent=True,
            is_anomaly=False,
            raw_data={'logins': [9, 14, 18, 9, 14]}
        )

        db_session.add(pattern)
        db_session.commit()

        result = db_session.query(BehaviorPattern).filter_by(username='test.user').first()
        assert result is not None
        assert result.pattern_type == 'login'
        assert result.frequency == 5.2
        assert result.is_consistent is True

    def test_behavior_pattern_anomaly_detection(self, db_session):
        """Test behavior pattern with anomaly flag"""
        from app.models.user import BehaviorPattern

        pattern = BehaviorPattern(
            username='test.user',
            pattern_date=datetime.utcnow(),
            pattern_type='booking',
            frequency=0.5,  # Very low
            is_consistent=False,
            is_anomaly=True,  # Flagged as anomaly
            raw_data={'reason': 'low_activity'}
        )

        db_session.add(pattern)
        db_session.commit()

        result = db_session.query(BehaviorPattern).filter_by(username='test.user').first()
        assert result.is_anomaly is True
        assert result.is_consistent is False

    def test_query_patterns_by_type(self, db_session):
        """Test querying patterns by type"""
        from app.models.user import BehaviorPattern

        now = datetime.utcnow()

        patterns_data = [
            ('login', 5.0),
            ('booking', 3.5),
            ('activity', 4.2),
        ]

        for pattern_type, freq in patterns_data:
            pattern = BehaviorPattern(
                username='test.user',
                pattern_date=now,
                pattern_type=pattern_type,
                frequency=freq,
                raw_data={}
            )
            db_session.add(pattern)

        db_session.commit()

        login_patterns = db_session.query(BehaviorPattern).filter_by(
            pattern_type='login'
        ).all()
        assert len(login_patterns) == 1
        assert login_patterns[0].frequency == 5.0


@pytest.mark.database
class TestPersonalInsightModel:
    """Tests for PersonalInsight model"""

    def test_create_personal_insight(self, db_session):
        """Test creating personal insight"""
        from app.models.user import PersonalInsight

        insight = PersonalInsight(
            username='test.user',
            insight_date=datetime.utcnow(),
            insight_type='strength',
            insight_category='performance',
            title='Excellent Show Rate',
            description='Your show rate is 15% above team average',
            impact_score=8.5,
            is_read=False,
            is_dismissed=False
        )

        db_session.add(insight)
        db_session.commit()

        result = db_session.query(PersonalInsight).filter_by(username='test.user').first()
        assert result is not None
        assert result.title == 'Excellent Show Rate'
        assert result.insight_type == 'strength'
        assert result.impact_score == 8.5

    def test_insight_read_status(self, db_session):
        """Test insight read/dismissed status"""
        from app.models.user import PersonalInsight

        insight = PersonalInsight(
            username='test.user',
            insight_date=datetime.utcnow(),
            insight_type='improvement',
            insight_category='growth',
            title='Improve Booking Lead Time',
            description='Try booking further in advance',
            impact_score=6.0,
            is_read=True,
            is_dismissed=False
        )

        db_session.add(insight)
        db_session.commit()

        result = db_session.query(PersonalInsight).filter_by(username='test.user').first()
        assert result.is_read is True
        assert result.is_dismissed is False

    def test_query_insights_by_category(self, db_session):
        """Test querying insights by category"""
        from app.models.user import PersonalInsight

        now = datetime.utcnow()

        insights_data = [
            ('performance', 'strength'),
            ('growth', 'improvement'),
            ('social', 'achievement'),
        ]

        for category, insight_type in insights_data:
            insight = PersonalInsight(
                username='test.user',
                insight_date=now,
                insight_type=insight_type,
                insight_category=category,
                title=f'{category} insight',
                description='Test description',
                impact_score=5.0
            )
            db_session.add(insight)

        db_session.commit()

        performance_insights = db_session.query(PersonalInsight).filter_by(
            insight_category='performance'
        ).all()
        assert len(performance_insights) == 1
        assert performance_insights[0].insight_type == 'strength'
