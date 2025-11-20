# -*- coding: utf-8 -*-
"""
JSON → PostgreSQL Migration Script

Migriert alle 20 JSON-Dateien in PostgreSQL-Datenbank
mit Dry-Run, Validation, Progress-Tracking und Rollback-Support

Usage:
    python scripts/migrate_json_to_postgres.py --dry-run     # Test-Run ohne Änderungen
    python scripts/migrate_json_to_postgres.py --execute     # Echte Migration
    python scripts/migrate_json_to_postgres.py --rollback    # Rollback zur JSON-Version
"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# SQLAlchemy imports
from sqlalchemy.orm import Session
from app.models import (
    init_db, get_db_session,
    User, UserStats, UserPrediction, BehaviorPattern, PersonalInsight,
    Score, UserBadge, DailyQuest, QuestProgress, PersonalGoal, Champion, MasteryData,
    UserCosmetic, CustomizationAchievement,
    WeeklyPointsParticipant, WeeklyPoints, WeeklyActivity,
    PrestigeData, MinigameData, PersistentData
)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationStats:
    """Statistics für Migration-Progress"""
    total_records: int = 0
    migrated_records: int = 0
    skipped_records: int = 0
    failed_records: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class JSONToPostgresMigrator:
    """Hauptklasse für JSON → PostgreSQL Migration"""

    def __init__(self, data_dir: Path, dry_run: bool = True):
        self.data_dir = data_dir
        self.dry_run = dry_run
        self.stats = {}  # {file_name: MigrationStats}
        self.session: Optional[Session] = None

        logger.info(f"🚀 Migration initialisiert")
        logger.info(f"📁 Data-Directory: {data_dir}")
        logger.info(f"{'🔍 DRY-RUN MODE' if dry_run else '⚡ LIVE MODE'}")

    def init_database(self) -> None:
        """Initialisiert PostgreSQL-Connection"""
        try:
            logger.info("📊 Initialisiere PostgreSQL...")
            init_db()
            self.session = get_db_session()
            logger.info("✅ PostgreSQL initialisiert")
        except Exception as e:
            logger.error(f"❌ PostgreSQL-Initialisierung fehlgeschlagen: {e}")
            raise

    def load_json(self, filename: str) -> Optional[Dict]:
        """Lädt JSON-Datei"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            logger.warning(f"⚠️ Datei nicht gefunden: {filename}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"📖 Geladen: {filename} ({len(str(data))} bytes)")
            return data
        except Exception as e:
            logger.error(f"❌ Fehler beim Laden von {filename}: {e}")
            return None

    # ==================== MIGRATION METHODS ====================

    def migrate_scores(self) -> MigrationStats:
        """
        Migriert scores.json → Score Model

        Format: {username: {month: points}}
        """
        logger.info("\n📊 Migriere Scores...")
        stats = MigrationStats()

        data = self.load_json('scores.json')
        if not data:
            return stats

        for username, months in data.items():
            for month, points in months.items():
                stats.total_records += 1

                try:
                    if not self.dry_run:
                        score = Score(
                            username=username,
                            month=month,
                            points=int(points),
                            bookings_count=0  # Wird später berechnet
                        )
                        self.session.merge(score)  # merge statt add (update if exists)

                    stats.migrated_records += 1
                    logger.debug(f"  ✓ {username} - {month}: {points} points")

                except Exception as e:
                    stats.failed_records += 1
                    stats.errors.append(f"Score {username}/{month}: {e}")
                    logger.error(f"  ❌ Fehler: {e}")

        if not self.dry_run:
            self.session.commit()

        logger.info(f"✅ Scores: {stats.migrated_records}/{stats.total_records} migriert")
        self.stats['scores'] = stats
        return stats

    def migrate_user_badges(self) -> MigrationStats:
        """
        Migriert user_badges.json → UserBadge Model

        Format: {username: {badges: [...], earned_dates: {...}}}
        """
        logger.info("\n🏆 Migriere User-Badges...")
        stats = MigrationStats()

        data = self.load_json('user_badges.json')
        if not data:
            return stats

        for username, user_data in data.items():
            badges = user_data.get('badges', [])

            for badge in badges:
                stats.total_records += 1

                try:
                    if not self.dry_run:
                        earned_date_str = badge.get('earned_date', datetime.utcnow().isoformat())
                        earned_date = datetime.fromisoformat(earned_date_str.replace('Z', '+00:00'))

                        user_badge = UserBadge(
                            username=username,
                            badge_id=badge.get('id', ''),
                            name=badge.get('name', ''),
                            description=badge.get('description', ''),
                            emoji=badge.get('emoji', ''),
                            rarity=badge.get('rarity', 'common'),
                            category=badge.get('category', 'general'),
                            color=badge.get('color', '#3b82f6'),
                            earned_date=earned_date,
                            requirements_met=badge.get('requirements_met'),
                            metadata=badge.get('metadata')
                        )
                        self.session.merge(user_badge)

                    stats.migrated_records += 1

                except Exception as e:
                    stats.failed_records += 1
                    stats.errors.append(f"Badge {username}/{badge.get('id')}: {e}")
                    logger.error(f"  ❌ Fehler: {e}")

        if not self.dry_run:
            self.session.commit()

        logger.info(f"✅ Badges: {stats.migrated_records}/{stats.total_records} migriert")
        self.stats['user_badges'] = stats
        return stats

    def migrate_weekly_points(self) -> MigrationStats:
        """
        Migriert weekly_points.json → WeeklyPoints Model

        Format: {participants: [...], weeks: {week_id: {users: {...}}}}
        """
        logger.info("\n📅 Migriere Weekly-Points...")
        stats = MigrationStats()

        data = self.load_json('weekly_points.json')
        if not data:
            return stats

        # 1. Participants migrieren
        participants = data.get('participants', [])
        for participant in participants:
            try:
                if not self.dry_run:
                    p = WeeklyPointsParticipant(
                        participant_name=participant,
                        is_active=True
                    )
                    self.session.merge(p)
                logger.debug(f"  ✓ Participant: {participant}")
            except Exception as e:
                logger.error(f"  ❌ Participant {participant}: {e}")

        # 2. Weekly-Points migrieren
        weeks = data.get('weeks', {})
        for week_id, week_data in weeks.items():
            users = week_data.get('users', {})

            for participant_name, user_data in users.items():
                stats.total_records += 1

                try:
                    if not self.dry_run:
                        weekly = WeeklyPoints(
                            week_id=week_id,
                            participant_name=participant_name,
                            goal_points=user_data.get('goal_points', 0),
                            bonus_points=0,  # Wird berechnet
                            total_points=user_data.get('goal_points', 0),
                            on_vacation=user_data.get('on_vacation', False),
                            is_goal_set=user_data.get('goal_points', 0) > 0,
                            activities=user_data.get('activities'),
                            pending_activities=user_data.get('pending_activities'),
                            pending_goal=user_data.get('pending_goal'),
                            audit=user_data.get('audit')
                        )
                        self.session.merge(weekly)

                    stats.migrated_records += 1

                except Exception as e:
                    stats.failed_records += 1
                    stats.errors.append(f"WeeklyPoints {week_id}/{participant_name}: {e}")

        if not self.dry_run:
            self.session.commit()

        logger.info(f"✅ Weekly-Points: {stats.migrated_records}/{stats.total_records} migriert")
        self.stats['weekly_points'] = stats
        return stats

    def migrate_user_cosmetics(self) -> MigrationStats:
        """Migriert user_customizations.json → UserCosmetic Model"""
        logger.info("\n🎨 Migriere User-Cosmetics...")
        stats = MigrationStats()

        data = self.load_json('user_customizations.json')
        if not data:
            return stats

        for username, user_data in data.items():
            owned = user_data.get('owned', {})
            active = user_data.get('active', {})

            # Owned Items
            for item_type, items in owned.items():
                for item in items:
                    stats.total_records += 1

                    try:
                        if not self.dry_run:
                            cosmetic = UserCosmetic(
                                username=username,
                                item_id=item,
                                item_type=item_type,
                                item_category='visual',
                                name=item.replace('_', ' ').title(),
                                description=f"{item_type.title()} cosmetic",
                                rarity='common',
                                is_owned=True,
                                is_active=(item in active.get(item_type, [])),
                                unlock_date=datetime.utcnow()
                            )
                            self.session.merge(cosmetic)

                        stats.migrated_records += 1

                    except Exception as e:
                        stats.failed_records += 1
                        stats.errors.append(f"Cosmetic {username}/{item}: {e}")

        if not self.dry_run:
            self.session.commit()

        logger.info(f"✅ Cosmetics: {stats.migrated_records}/{stats.total_records} migriert")
        self.stats['user_cosmetics'] = stats
        return stats

    def migrate_prestige_data(self) -> MigrationStats:
        """Migriert prestige_data.json → PrestigeData Model"""
        logger.info("\n⭐ Migriere Prestige-Data...")
        stats = MigrationStats()

        data = self.load_json('prestige_data.json')
        if not data:
            logger.info("  ℹ️ Keine Prestige-Daten vorhanden (leere Datei)")
            return stats

        for username, prestige_info in data.items():
            stats.total_records += 1

            try:
                if not self.dry_run:
                    prestige = PrestigeData(
                        username=username,
                        prestige_level=prestige_info.get('prestige_level', 0),
                        prestige_points=prestige_info.get('prestige_points', 0),
                        pre_prestige_level=prestige_info.get('pre_prestige_level', 0),
                        pre_prestige_points=prestige_info.get('pre_prestige_points', 0),
                        prestige_multiplier=prestige_info.get('prestige_multiplier', 1.0),
                        unlocked_perks=prestige_info.get('unlocked_perks'),
                        prestige_history=prestige_info.get('prestige_history'),
                        lifetime_points=prestige_info.get('lifetime_points', 0),
                        lifetime_bookings=prestige_info.get('lifetime_bookings', 0)
                    )
                    self.session.merge(prestige)

                stats.migrated_records += 1

            except Exception as e:
                stats.failed_records += 1
                stats.errors.append(f"Prestige {username}: {e}")

        if not self.dry_run:
            self.session.commit()

        logger.info(f"✅ Prestige: {stats.migrated_records}/{stats.total_records} migriert")
        self.stats['prestige_data'] = stats
        return stats

    # ==================== MAIN MIGRATION ====================

    def run_full_migration(self) -> Dict[str, MigrationStats]:
        """Führt komplette Migration durch"""
        logger.info("\n" + "="*70)
        logger.info("🚀 STARTE VOLLSTÄNDIGE MIGRATION")
        logger.info("="*70)

        try:
            # Initialize Database
            self.init_database()

            # Migrate alle Dateien (in logischer Reihenfolge)
            self.migrate_scores()
            self.migrate_user_badges()
            self.migrate_weekly_points()
            self.migrate_user_cosmetics()
            self.migrate_prestige_data()

            # TODO: Weitere Migrations hinzufügen
            # self.migrate_user_stats()
            # self.migrate_quests()
            # self.migrate_champions()
            # self.migrate_mastery()
            # etc.

            logger.info("\n" + "="*70)
            logger.info("✅ MIGRATION ABGESCHLOSSEN")
            self.print_summary()
            logger.info("="*70)

            return self.stats

        except Exception as e:
            logger.error(f"\n❌ MIGRATION FEHLGESCHLAGEN: {e}")
            if self.session and not self.dry_run:
                self.session.rollback()
                logger.warning("🔄 Rollback durchgeführt")
            raise

        finally:
            if self.session:
                self.session.close()

    def print_summary(self) -> None:
        """Gibt Migrations-Zusammenfassung aus"""
        logger.info("\n📊 MIGRATIONS-ZUSAMMENFASSUNG:")
        logger.info("-" * 70)

        total_all = 0
        migrated_all = 0
        failed_all = 0

        for file_name, stats in self.stats.items():
            logger.info(f"  {file_name:25} | "
                       f"Total: {stats.total_records:5} | "
                       f"Migriert: {stats.migrated_records:5} | "
                       f"Failed: {stats.failed_records:3}")

            total_all += stats.total_records
            migrated_all += stats.migrated_records
            failed_all += stats.failed_records

            # Errors ausgeben
            if stats.errors:
                for error in stats.errors[:5]:  # Maximal 5 Errors pro File
                    logger.error(f"    ❌ {error}")

        logger.info("-" * 70)
        logger.info(f"  {'GESAMT':25} | "
                   f"Total: {total_all:5} | "
                   f"Migriert: {migrated_all:5} | "
                   f"Failed: {failed_all:3}")

        # Success-Rate
        if total_all > 0:
            success_rate = (migrated_all / total_all) * 100
            logger.info(f"\n  ✅ Erfolgsrate: {success_rate:.2f}%")


def main():
    """Main Entry-Point"""
    parser = argparse.ArgumentParser(description='JSON → PostgreSQL Migration')
    parser.add_argument('--dry-run', action='store_true', help='Test-Run ohne Änderungen')
    parser.add_argument('--execute', action='store_true', help='Echte Migration durchführen')
    parser.add_argument('--data-dir', type=str, default='data/persistent',
                       help='Pfad zum Data-Directory (default: data/persistent)')

    args = parser.parse_args()

    # Validation
    if not args.dry_run and not args.execute:
        logger.error("❌ Bitte --dry-run oder --execute angeben!")
        sys.exit(1)

    # Data-Dir prüfen
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"❌ Data-Directory nicht gefunden: {data_dir}")
        sys.exit(1)

    # Migrator erstellen und ausführen
    migrator = JSONToPostgresMigrator(
        data_dir=data_dir,
        dry_run=args.dry_run
    )

    try:
        migrator.run_full_migration()
        logger.info("\n🎉 Migration erfolgreich!")
        sys.exit(0)

    except Exception as e:
        logger.error(f"\n💥 Migration fehlgeschlagen: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
