# -*- coding: utf-8 -*-
"""
SQLAlchemy Data Models für PostgreSQL Migration

Architektur:
- base.py: Base Model, Database Engine, Session Management
- user.py: User, UserStats, UserPrediction, BehaviorPattern, PersonalInsight
- gamification.py: Score, UserBadge, DailyQuest, QuestProgress, PersonalGoal, Champion, MasteryData
- cosmetics.py: UserCosmetic, CustomizationAchievement
- weekly.py: WeeklyPointsParticipant, WeeklyPoints, WeeklyActivity, PrestigeData, MinigameData, PersistentData
- booking.py: Booking, BookingOutcome

JSON-Mapping (22 Dateien → 25 Models):
1. scores.json → Score
2. user_badges.json → UserBadge
3. user_profiles.json → User
4. user_stats.json, daily_user_stats.json, user_analytics.json → UserStats
5. user_predictions.json → UserPrediction
6. behavior_patterns.json → BehaviorPattern
7. personal_insights.json → PersonalInsight
8. user_customizations.json → UserCosmetic
9. customization_achievements.json → CustomizationAchievement
10. daily_quests.json, quest_progress.json → DailyQuest, QuestProgress
11. personal_goals.json → PersonalGoal
12. champions.json → Champion
13. mastery_data.json → MasteryData
14. weekly_points.json → WeeklyPointsParticipant, WeeklyPoints, WeeklyActivity
15. prestige_data.json → PrestigeData
16. minigame_data.json → MinigameData
17. persistent_data.json → PersistentData
18. user_coins.json → User.total_coins
19. bookings.jsonl → Booking
20. outcomes.jsonl → BookingOutcome
"""

# Base & Database
from app.models.base import (
    Base,
    init_db,
    get_db_session,
    get_database_url,
    is_postgres_enabled
)

# User Models
from app.models.user import (
    User,
    UserStats,
    UserPrediction,
    BehaviorPattern,
    PersonalInsight
)

# Gamification Models
from app.models.gamification import (
    Score,
    UserBadge,
    DailyQuest,
    QuestProgress,
    PersonalGoal,
    Champion,
    MasteryData
)

# Cosmetics Models
from app.models.cosmetics import (
    UserCosmetic,
    CustomizationAchievement
)

# Weekly & Complex Models
from app.models.weekly import (
    WeeklyPointsParticipant,
    WeeklyPoints,
    WeeklyActivity,
    PrestigeData,
    MinigameData,
    PersistentData
)

# Booking Models
from app.models.booking import (
    Booking,
    BookingOutcome
)

# T2 Bucket Models
from app.models.t2_bucket import (
    T2CloserConfig,
    T2BucketState,
    T2DrawHistory,
    T2UserLastDraw
)

__all__ = [
    # Base
    'Base',
    'init_db',
    'get_db_session',
    'get_database_url',
    'is_postgres_enabled',
    # User
    'User',
    'UserStats',
    'UserPrediction',
    'BehaviorPattern',
    'PersonalInsight',
    # Gamification
    'Score',
    'UserBadge',
    'DailyQuest',
    'QuestProgress',
    'PersonalGoal',
    'Champion',
    'MasteryData',
    # Cosmetics
    'UserCosmetic',
    'CustomizationAchievement',
    # Weekly
    'WeeklyPointsParticipant',
    'WeeklyPoints',
    'WeeklyActivity',
    'PrestigeData',
    'MinigameData',
    'PersistentData',
    # Booking
    'Booking',
    'BookingOutcome',
    # T2 Bucket
    'T2CloserConfig',
    'T2BucketState',
    'T2DrawHistory',
    'T2UserLastDraw',
]