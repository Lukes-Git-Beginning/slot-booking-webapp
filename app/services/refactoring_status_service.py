# -*- coding: utf-8 -*-
"""
Refactoring Status Service
Analyzes codebase and generates refactoring progress dashboard

Tracks:
- PostgreSQL migration status (JSON → PostgreSQL)
- Service layer refactoring (JSON vs PostgreSQL usage)
- TODO/FIXME comments
- Test coverage
- Roadmap progress
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RefactoringStatusService:
    """Tracks PostgreSQL migration and refactoring progress"""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.data_dir = self.project_root / 'data' / 'persistent'
        self.app_dir = self.project_root / 'app'

    def get_json_to_postgres_status(self) -> Dict:
        """Analyze JSON → PostgreSQL migration status"""

        # Define migration mapping (what exists vs what's migrated)
        migrations = {
            # COMPLETED
            'bookings.jsonl': {
                'model': 'Booking',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Slot bookings (364 records migrated)'
            },

            # IN PROGRESS (Dual-Write Phase)
            't2_bucket_system.json': {
                'model': 'T2BucketState',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'T2 Bucket drawing system (Dual-Write: PostgreSQL + JSON)'
            },

            # DONE (Dual-Write active)
            'scores.json': {
                'model': 'Score',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Gamification scores (Dual-Write: PostgreSQL + JSON)'
            },
            'user_badges.json': {
                'model': 'UserBadge',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Achievement badges (Dual-Write: PostgreSQL + JSON)'
            },
            'daily_quests.json': {
                'model': 'DailyQuest',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Daily quest system (Dual-Write: PostgreSQL + JSON)'
            },
            'quest_progress.json': {
                'model': 'QuestProgress',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Quest completion tracking (Dual-Write: PostgreSQL + JSON)'
            },
            'weekly_points.json': {
                'model': 'WeeklyPoints',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Weekly points system (Dual-Write: PostgreSQL + JSON)'
            },
            'prestige_data.json': {
                'model': 'PrestigeData',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Prestige level system (Dual-Write: PostgreSQL + JSON)'
            },
            'user_customizations.json': {
                'model': 'UserCosmetic',
                'status': 'pending',
                'migrated': False,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': False,
                'description': 'User cosmetics/themes'
            },
            'customization_achievements.json': {
                'model': 'CustomizationAchievement',
                'status': 'pending',
                'migrated': False,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': False,
                'description': 'Cosmetic unlocks'
            },
            'champions.json': {
                'model': 'Champion',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Weekly champions (Dual-Write: PostgreSQL + JSON)'
            },
            'mastery_data.json': {
                'model': 'MasteryData',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Skill mastery tracking (Dual-Write: PostgreSQL + JSON)'
            },
            'minigame_data.json': {
                'model': 'MinigameData',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Minigame progress (Dual-Write: PostgreSQL + JSON)'
            },
            'personal_goals.json': {
                'model': 'PersonalGoal',
                'status': 'pending',
                'migrated': False,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': False,
                'description': 'User personal goals'
            },

            # CONSOLIDATED into UserStats (daily_user_stats.json)
            'user_stats.json': {
                'model': 'UserStats',
                'status': 'consolidated',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'User statistics (consolidated into daily_user_stats/UserStats)'
            },
            'user_profiles.json': {
                'model': 'User',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'User authentication/profiles (Dual-Write: PostgreSQL + JSON)'
            },
            't2_bookings.json': {
                'model': 'T2Booking',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'T2 closer bookings (Dual-Write: PostgreSQL + JSON)'
            },
            'user_analytics.json': {
                'model': 'UserStats',
                'status': 'consolidated',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'User analytics data (consolidated into daily_user_stats/UserStats)'
            },
            'user_predictions.json': {
                'model': 'UserPrediction',
                'status': 'pending',
                'migrated': False,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': False,
                'description': 'AI predictions'
            },
            'behavior_patterns.json': {
                'model': 'BehaviorPattern',
                'status': 'pending',
                'migrated': False,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': False,
                'description': 'User behavior analysis'
            },
            'personal_insights.json': {
                'model': 'PersonalInsight',
                'status': 'pending',
                'migrated': False,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': False,
                'description': 'Personalized insights'
            },
            'user_coins.json': {
                'model': 'User.total_coins',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Virtual currency (Dual-Write: PostgreSQL + JSON)'
            },
            'daily_user_stats.json': {
                'model': 'UserStats',
                'status': 'complete',
                'migrated': True,
                'model_exists': True,
                'migration_exists': True,
                'service_refactored': True,
                'description': 'Daily user metrics (Dual-Write: PostgreSQL + JSON)'
            },
        }

        # Calculate statistics
        total = len(migrations)
        completed = sum(1 for m in migrations.values() if m['status'] == 'complete')
        in_progress = sum(1 for m in migrations.values() if m['status'] == 'in_progress')
        pending = sum(1 for m in migrations.values() if m['status'] == 'pending')

        return {
            'total_files': total,
            'completed': completed,
            'in_progress': in_progress,
            'pending': pending,
            'completion_percentage': round((completed / total) * 100, 1) if total > 0 else 0,
            'migrations': migrations
        }

    def get_service_refactoring_status(self) -> Dict:
        """Analyze service layer refactoring progress"""

        services_dir = self.app_dir / 'services'
        service_files = list(services_dir.glob('*.py'))

        status = {}
        for service_file in service_files:
            if service_file.name == '__init__.py':
                continue

            try:
                with open(service_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for PostgreSQL usage
                uses_postgres = bool(
                    re.search(r'from app\.models import.*get_db_session', content) or
                    re.search(r'session\.query\(', content) or
                    re.search(r'get_db_session\(\)', content)
                )

                # Check for JSON usage
                uses_json = bool(
                    re.search(r'data_persistence\.load_data', content) or
                    re.search(r'json\.load', content) or
                    re.search(r'\.json\(', content)
                )

                dual_write = uses_postgres and uses_json

                # Determine status
                if uses_postgres and not uses_json:
                    service_status = 'refactored'
                elif dual_write:
                    service_status = 'dual_write'
                elif uses_json:
                    service_status = 'legacy'
                else:
                    service_status = 'unknown'

                status[service_file.name] = {
                    'uses_postgres': uses_postgres,
                    'uses_json': uses_json,
                    'dual_write': dual_write,
                    'status': service_status
                }

            except Exception as e:
                logger.error(f"Error analyzing {service_file.name}: {e}")
                status[service_file.name] = {
                    'uses_postgres': False,
                    'uses_json': False,
                    'dual_write': False,
                    'status': 'error'
                }

        # Calculate statistics
        total = len(status)
        refactored = sum(1 for s in status.values() if s['status'] == 'refactored')
        dual_write = sum(1 for s in status.values() if s['status'] == 'dual_write')
        legacy = sum(1 for s in status.values() if s['status'] == 'legacy')

        return {
            'total_services': total,
            'refactored': refactored,
            'dual_write': dual_write,
            'legacy': legacy,
            'completion_percentage': round((refactored / total) * 100, 1) if total > 0 else 0,
            'services': status
        }

    def get_todo_fixme_count(self) -> Dict:
        """Count TODO and FIXME comments in codebase"""

        todos = []
        fixmes = []

        # Scan app/ directory
        for py_file in self.app_dir.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, start=1):
                    stripped = line.strip()
                    if 'TODO' in line:
                        todos.append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'line': line_num,
                            'text': stripped
                        })
                    if 'FIXME' in line:
                        fixmes.append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'line': line_num,
                            'text': stripped
                        })

            except Exception as e:
                logger.error(f"Error scanning {py_file}: {e}")

        return {
            'todo_count': len(todos),
            'fixme_count': len(fixmes),
            'total_count': len(todos) + len(fixmes),
            'todos': todos[:20],  # Limit to 20 for display
            'fixmes': fixmes[:20]
        }

    def get_test_coverage_status(self) -> Dict:
        """Get test coverage statistics from .coverage file or fallback to hardcoded values"""

        try:
            from coverage import Coverage

            coverage_file = self.project_root / '.coverage'
            if not coverage_file.exists():
                raise FileNotFoundError("No .coverage file found")

            cov = Coverage(data_file=str(coverage_file))
            cov.load()

            services = {}
            overall_lines = 0
            overall_covered = 0

            for filename in cov.get_data().measured_files():
                normalized = filename.replace('\\', '/')
                if '/app/services/' in normalized or '\\app\\services\\' in filename:
                    analysis = cov.analysis2(filename)
                    total = len(analysis[1]) + len(analysis[3])
                    covered = len(analysis[1])
                    if total > 0:
                        short_name = Path(filename).name
                        services[short_name] = round(covered / total * 100, 1)
                    overall_lines += total
                    overall_covered += covered

            overall_pct = round(overall_covered / overall_lines * 100, 1) if overall_lines > 0 else 0.0

            return {
                'overall_coverage': overall_pct,
                'target_coverage': 100.0,
                'services': dict(sorted(services.items(), key=lambda x: x[1], reverse=True)),
                'source': 'dynamic'
            }
        except Exception as e:
            logger.warning(f"Could not load coverage data: {e}. Run 'pytest --cov=app/services' to generate .coverage file.")
            return {
                'overall_coverage': 0.0,
                'target_coverage': 100.0,
                'services': {},
                'source': 'unavailable'
            }

    def get_roadmap_progress(self) -> Dict:
        """Calculate overall roadmap completion"""

        phases = {
            'Phase 1: PostgreSQL + Redis': {
                'total_hours': 17,
                'completed_hours': 17,
                'status': 'complete',
                'tasks': [
                    {'name': 'PostgreSQL Setup (24 tables, 121 indexes)', 'status': 'complete'},
                    {'name': 'Redis Integration (hybrid cache)', 'status': 'complete'},
                    {'name': 'Booking System Migration (364 records)', 'status': 'complete'},
                    {'name': 'Alembic Migrations Setup', 'status': 'complete'},
                ]
            },
            'Phase 2: Code Cleanup': {
                'total_hours': 10,
                'completed_hours': 10,
                'status': 'complete',
                'tasks': [
                    {'name': 'Routing Cleanup (1,275 lines removed)', 'status': 'complete'},
                    {'name': 'Template Unification (Bootstrap → Tailwind/DaisyUI)', 'status': 'complete'},
                    {'name': 'Code Hygiene (TODOs, Imports, Comments)', 'status': 'complete'},
                ]
            },
            'Phase 3: Feature Completion': {
                'total_hours': 14,
                'completed_hours': 14,
                'status': 'complete',
                'tasks': [
                    {'name': 'T2 Analytics Fix', 'status': 'complete'},
                    {'name': 'T2 Bucket PostgreSQL (Dual-Write)', 'status': 'complete'},
                    {'name': 'Gamification Services Migration (Scores, Badges, Quests, Prestige)', 'status': 'complete'},
                    {'name': 'Analytics Real Calculations', 'status': 'complete'},
                ]
            },
            'Phase 4: CI/CD & DevOps': {
                'total_hours': 8,
                'completed_hours': 0,
                'status': 'pending',
                'tasks': [
                    {'name': 'GitHub Actions Pipeline', 'status': 'pending'},
                    {'name': 'Monitoring & Alerts (Sentry)', 'status': 'pending'},
                    {'name': 'Automated Deployment', 'status': 'pending'},
                ]
            },
            'Phase 5: Quality & Bugfixes': {
                'total_hours': 8,
                'completed_hours': 8,
                'status': 'complete',
                'tasks': [
                    {'name': 'Test-Coverage Fix (37 Failures → 561 passed, 0 failed)', 'status': 'complete'},
                    {'name': 'Parsing-Bug Fix (F.4)', 'status': 'complete'},
                ]
            }
        }

        total_hours = sum(p['total_hours'] for p in phases.values())
        completed_hours = sum(p['completed_hours'] for p in phases.values())

        return {
            'total_hours': total_hours,
            'completed_hours': completed_hours,
            'remaining_hours': total_hours - completed_hours,
            'completion_percentage': round((completed_hours / total_hours) * 100, 1),
            'phases': phases
        }

    def get_full_status(self) -> Dict:
        """Get complete refactoring status"""

        return {
            'postgres_migration': self.get_json_to_postgres_status(),
            'service_refactoring': self.get_service_refactoring_status(),
            'todo_fixme': self.get_todo_fixme_count(),
            'test_coverage': self.get_test_coverage_status(),
            'roadmap': self.get_roadmap_progress(),
            'generated_at': datetime.now().isoformat()
        }


# Singleton
refactoring_status_service = RefactoringStatusService()
