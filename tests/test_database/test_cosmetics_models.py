# -*- coding: utf-8 -*-
"""
Database Tests - Cosmetics Models
Tests for UserCosmetic, CustomizationAchievement
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError


@pytest.mark.database
class TestUserCosmeticModel:
    """Tests for UserCosmetic model"""

    def test_create_user_cosmetic(self, db_session):
        """Test creating user cosmetic item"""
        from app.models.cosmetics import UserCosmetic

        cosmetic = UserCosmetic(
            username='test.user',
            item_id='theme_dark',
            item_type='theme',
            item_category='visual',
            name='Dark Theme',
            description='Sleek dark color scheme',
            rarity='common',
            is_owned=True,
            is_active=True,
            unlock_date=datetime.utcnow(),
            purchase_price=100,
            config={'primary': '#1a1a1a', 'accent': '#4a9eff'}
        )

        db_session.add(cosmetic)
        db_session.commit()

        result = db_session.query(UserCosmetic).filter_by(username='test.user').first()
        assert result is not None
        assert result.item_id == 'theme_dark'
        assert result.item_type == 'theme'
        assert result.is_owned is True
        assert result.config['primary'] == '#1a1a1a'

    def test_username_item_unique(self, db_session):
        """Test unique constraint on username+item_id"""
        from app.models.cosmetics import UserCosmetic

        cosmetic1 = UserCosmetic(
            username='test.user',
            item_id='theme_blue',
            item_type='theme',
            item_category='visual',
            name='Blue Theme',
            rarity='common'
        )
        db_session.add(cosmetic1)
        db_session.commit()

        # Try duplicate username+item_id
        cosmetic2 = UserCosmetic(
            username='test.user',
            item_id='theme_blue',
            item_type='theme',
            item_category='visual',
            name='Blue Theme',
            rarity='common'
        )
        db_session.add(cosmetic2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_query_cosmetics_by_type(self, db_session):
        """Test querying cosmetics by item type"""
        from app.models.cosmetics import UserCosmetic

        cosmetics_data = [
            ('theme_dark', 'theme'),
            ('effect_sparkle', 'effect'),
            ('avatar_cool', 'avatar'),
        ]

        for item_id, item_type in cosmetics_data:
            cosmetic = UserCosmetic(
                username='test.user',
                item_id=item_id,
                item_type=item_type,
                item_category='visual',
                name=f'Test {item_id}',
                rarity='common'
            )
            db_session.add(cosmetic)

        db_session.commit()

        themes = db_session.query(UserCosmetic).filter_by(item_type='theme').all()
        assert len(themes) == 1
        assert themes[0].item_id == 'theme_dark'

    def test_query_active_cosmetics(self, db_session):
        """Test querying active cosmetics"""
        from app.models.cosmetics import UserCosmetic

        cosmetics_data = [
            ('item1', True, True),   # Owned and active
            ('item2', True, False),  # Owned but not active
            ('item3', False, False), # Not owned
        ]

        for item_id, is_owned, is_active in cosmetics_data:
            cosmetic = UserCosmetic(
                username='test.user',
                item_id=item_id,
                item_type='theme',
                item_category='visual',
                name=f'Item {item_id}',
                rarity='common',
                is_owned=is_owned,
                is_active=is_active
            )
            db_session.add(cosmetic)

        db_session.commit()

        active = db_session.query(UserCosmetic).filter_by(is_active=True).all()
        assert len(active) == 1
        assert active[0].item_id == 'item1'

    def test_query_cosmetics_by_rarity(self, db_session):
        """Test querying cosmetics by rarity"""
        from app.models.cosmetics import UserCosmetic

        cosmetics_data = [
            ('common_item', 'common'),
            ('rare_item', 'rare'),
            ('legendary_item', 'legendary'),
        ]

        for item_id, rarity in cosmetics_data:
            cosmetic = UserCosmetic(
                username='test.user',
                item_id=item_id,
                item_type='avatar',
                item_category='visual',
                name=f'{rarity} avatar',
                rarity=rarity
            )
            db_session.add(cosmetic)

        db_session.commit()

        legendary = db_session.query(UserCosmetic).filter_by(rarity='legendary').all()
        assert len(legendary) == 1
        assert legendary[0].item_id == 'legendary_item'


@pytest.mark.database
class TestCustomizationAchievementModel:
    """Tests for CustomizationAchievement model"""

    def test_create_customization_achievement(self, db_session):
        """Test creating customization achievement"""
        from app.models.cosmetics import CustomizationAchievement

        achievement = CustomizationAchievement(
            username='test.user',
            achievement_id='collector_bronze',
            achievement_type='collector',
            title='Bronze Collector',
            description='Collect 10 cosmetic items',
            current_progress=5,
            target_progress=10,
            is_completed=False,
            reward_coins=100
        )

        db_session.add(achievement)
        db_session.commit()

        result = db_session.query(CustomizationAchievement).filter_by(username='test.user').first()
        assert result is not None
        assert result.achievement_id == 'collector_bronze'
        assert result.current_progress == 5
        assert result.target_progress == 10
        assert result.is_completed is False

    def test_username_achievement_unique(self, db_session):
        """Test unique constraint on username+achievement_id"""
        from app.models.cosmetics import CustomizationAchievement

        achievement1 = CustomizationAchievement(
            username='test.user',
            achievement_id='fashionista',
            achievement_type='fashionista',
            title='Fashionista',
            description='Use 5 different themes',
            target_progress=5,
            reward_coins=200
        )
        db_session.add(achievement1)
        db_session.commit()

        # Try duplicate
        achievement2 = CustomizationAchievement(
            username='test.user',
            achievement_id='fashionista',
            achievement_type='fashionista',
            title='Fashionista',
            description='Use 5 different themes',
            target_progress=5,
            reward_coins=200
        )
        db_session.add(achievement2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_achievement_completion_tracking(self, db_session):
        """Test achievement completion tracking"""
        from app.models.cosmetics import CustomizationAchievement

        now = datetime.utcnow()

        achievement = CustomizationAchievement(
            username='test.user',
            achievement_id='trendsetter',
            achievement_type='trendsetter',
            title='Trendsetter',
            description='Unlock all legendary items',
            current_progress=3,
            target_progress=3,
            is_completed=True,
            completed_at=now,
            reward_coins=500,
            reward_items={'exclusive_badge': 'trendsetter_badge'}
        )

        db_session.add(achievement)
        db_session.commit()

        result = db_session.query(CustomizationAchievement).filter_by(username='test.user').first()
        assert result.is_completed is True
        assert result.completed_at is not None
        assert result.reward_items['exclusive_badge'] == 'trendsetter_badge'

    def test_query_completed_achievements(self, db_session):
        """Test querying completed achievements"""
        from app.models.cosmetics import CustomizationAchievement

        achievements_data = [
            ('ach1', True),
            ('ach2', False),
            ('ach3', True),
        ]

        for ach_id, is_completed in achievements_data:
            achievement = CustomizationAchievement(
                username='test.user',
                achievement_id=ach_id,
                achievement_type='collector',
                title=f'Achievement {ach_id}',
                description='Test',
                target_progress=10,
                is_completed=is_completed,
                reward_coins=100
            )
            db_session.add(achievement)

        db_session.commit()

        completed = db_session.query(CustomizationAchievement).filter_by(is_completed=True).all()
        assert len(completed) == 2
