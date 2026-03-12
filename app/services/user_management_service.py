# -*- coding: utf-8 -*-
"""
User Management Service
CRUD-Operationen und Datenanreicherung für die Admin-Benutzerverwaltung
"""

import os
import secrets
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pytz

from app.core.extensions import data_persistence
from app.config.base import Config, slot_config
from app.utils.helpers import get_userlist
from app.services.security_service import security_service
from app.services.activity_tracking import activity_tracking
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)
TZ = pytz.timezone(slot_config.TIMEZONE)

REGISTRY_FILE = 'user_registry'


class UserManagementService:
    """Service für User-CRUD und Datenanreicherung"""

    def _load_registry(self) -> dict:
        return data_persistence.load_data(REGISTRY_FILE, default={
            'added_users': {},
            'deleted_users': [],
            'admin_overrides': {}
        })

    def _save_registry(self, registry: dict):
        data_persistence.save_data(REGISTRY_FILE, registry)

    def _sync_runtime_userlist(self):
        """Synchronisiere os.environ USERLIST mit Registry-Änderungen"""
        registry = self._load_registry()
        userlist = get_userlist()

        # Add registry users to runtime
        for username, pw_hash in registry.get('added_users', {}).items():
            if username not in userlist:
                # Add placeholder to env USERLIST so get_userlist() sees it
                current = os.environ.get('USERLIST', '')
                # Use a dummy password - actual auth goes through custom_passwords
                os.environ['USERLIST'] = f"{current},{username}:__registry__" if current else f"{username}:__registry__"

        # Remove deleted users from runtime
        deleted = registry.get('deleted_users', [])
        if deleted:
            current = os.environ.get('USERLIST', '')
            if current:
                parts = []
                for part in current.split(','):
                    if ':' in part:
                        uname = part.split(':', 1)[0].strip()
                        if uname not in deleted:
                            parts.append(part)
                os.environ['USERLIST'] = ','.join(parts)

    def get_all_users(self) -> List[dict]:
        """Alle User mit angereicherten Daten laden"""
        self._sync_runtime_userlist()
        registry = self._load_registry()
        userlist = get_userlist()
        admin_users_list = Config.get_admin_users()
        admin_overrides = registry.get('admin_overrides', {})
        deleted = registry.get('deleted_users', [])

        # Filter deleted users
        active_usernames = [u for u in userlist.keys() if u not in deleted]

        # Load shared data once
        login_history = data_persistence.load_data('login_history', default={})
        scores = data_persistence.load_scores()
        online_users_list = activity_tracking.get_online_users(timeout_minutes=15)
        online_usernames = {u.get('username', '') if isinstance(u, dict) else u for u in online_users_list}

        # Current month key for scores
        now = datetime.now(TZ)
        current_month_key = now.strftime('%Y-%m')

        # Load level and badge data
        try:
            from app.services.level_system import level_system
        except ImportError:
            level_system = None

        try:
            from app.services.achievement_system import achievement_system
        except ImportError:
            achievement_system = None

        users = []
        for username in active_usernames:
            # Admin status: override > config
            if username in admin_overrides:
                is_admin = admin_overrides[username]
            else:
                is_admin = username in admin_users_list

            # Last login
            last_login_formatted = None
            user_logins = login_history.get(username, [])
            for entry in user_logins:
                if entry.get('success', True):
                    ts = entry.get('timestamp')
                    if ts:
                        try:
                            dt = datetime.fromisoformat(ts)
                            last_login_formatted = dt.strftime('%d.%m.%Y %H:%M')
                        except Exception:
                            last_login_formatted = ts
                    break

            # Current month points
            user_scores = scores.get(username, {})
            current_month_points = user_scores.get(current_month_key, 0)

            # Level info
            level = 0
            level_title = 'Neuling'
            if level_system:
                try:
                    level_info = level_system.calculate_user_level(username)
                    level = level_info.get('level', 0)
                    level_title = level_info.get('level_title', 'Neuling')
                except Exception:
                    pass

            # Badge count
            badge_count = 0
            if achievement_system:
                try:
                    badge_data = achievement_system.get_user_badges(username)
                    badge_count = badge_data.get('total_badges', 0)
                except Exception:
                    pass

            # Online status
            is_online = username in online_usernames

            users.append({
                'username': username,
                'is_admin': is_admin,
                'is_online': is_online,
                'last_login': last_login_formatted,
                'current_month_points': current_month_points,
                'level': level,
                'level_title': level_title,
                'badge_count': badge_count,
            })

        users.sort(key=lambda x: x['username'].lower())
        return users

    def get_user_detail(self, username: str) -> Optional[dict]:
        """Detaildaten für einen einzelnen User"""
        userlist = get_userlist()
        registry = self._load_registry()
        deleted = registry.get('deleted_users', [])

        if username not in userlist or username in deleted:
            return None

        # Login history (last 20)
        login_history = data_persistence.load_data('login_history', default={})
        user_logins = login_history.get(username, [])[:20]
        formatted_logins = []
        for entry in user_logins:
            ts = entry.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(ts)
                ts_formatted = dt.strftime('%d.%m.%Y %H:%M')
            except Exception:
                ts_formatted = ts
            formatted_logins.append({
                'timestamp': ts_formatted,
                'ip': entry.get('ip_address', '-'),
                'browser': entry.get('browser', '-'),
                'success': entry.get('success', True),
            })

        # Scores history (last 6 months)
        scores = data_persistence.load_scores()
        user_scores = scores.get(username, {})
        now = datetime.now(TZ)
        scores_history = []
        for i in range(5, -1, -1):
            month = now.month - i
            year = now.year
            while month <= 0:
                month += 12
                year -= 1
            key = f"{year}-{month:02d}"
            scores_history.append({
                'month': key,
                'points': user_scores.get(key, 0)
            })

        # Badges
        badges = []
        try:
            from app.services.achievement_system import achievement_system
            if achievement_system:
                badge_data = achievement_system.get_user_badges(username)
                badges = badge_data.get('badges', [])
        except Exception:
            pass

        # Level
        level_info = {'level': 0, 'level_title': 'Neuling', 'xp': 0, 'progress_to_next': 0}
        try:
            from app.services.level_system import level_system
            if level_system:
                level_info = level_system.calculate_user_level(username)
        except Exception:
            pass

        # 2FA status
        has_2fa = security_service.is_2fa_enabled(username)

        # Admin status
        admin_overrides = registry.get('admin_overrides', {})
        admin_users_list = Config.get_admin_users()
        if username in admin_overrides:
            is_admin = admin_overrides[username]
        else:
            is_admin = username in admin_users_list

        return {
            'username': username,
            'is_admin': is_admin,
            'has_2fa': has_2fa,
            'level': level_info.get('level', 0),
            'level_title': level_info.get('level_title', 'Neuling'),
            'xp': level_info.get('xp', 0),
            'progress_to_next': level_info.get('progress_to_next', 0),
            'login_history': formatted_logins,
            'scores_history': scores_history,
            'badges': [{'name': b.get('name', ''), 'emoji': b.get('emoji', ''), 'rarity': b.get('rarity', 'common')} for b in badges],
            'total_badges': len(badges),
        }

    def add_user(self, username: str, password: str, is_admin: bool, admin_username: str) -> Tuple[bool, str]:
        """Neuen User hinzufügen"""
        username = username.strip()

        if not username or not password:
            return False, "Benutzername und Passwort sind erforderlich"

        if len(username) < 2 or len(username) > 30:
            return False, "Benutzername muss 2-30 Zeichen lang sein"

        if len(password) < 6:
            return False, "Passwort muss mindestens 6 Zeichen lang sein"

        # Check for invalid characters
        if not username.replace('_', '').replace('-', '').isalnum():
            return False, "Benutzername darf nur Buchstaben, Zahlen, _ und - enthalten"

        # Check duplicates
        userlist = get_userlist()
        registry = self._load_registry()
        deleted = registry.get('deleted_users', [])

        if username in userlist and username not in deleted:
            return False, f"Benutzer '{username}' existiert bereits"

        # If user was previously deleted, remove from deleted list
        if username in deleted:
            registry['deleted_users'].remove(username)

        # Add to registry
        registry.setdefault('added_users', {})[username] = True

        # Set admin override if requested
        if is_admin:
            registry.setdefault('admin_overrides', {})[username] = True

        self._save_registry(registry)

        # Hash and store password via security_service
        hashed = security_service.hash_password(password)
        custom_passwords = data_persistence.load_data('user_passwords', {})
        custom_passwords[username] = hashed
        data_persistence.save_data('user_passwords', custom_passwords)

        # Update runtime USERLIST
        current = os.environ.get('USERLIST', '')
        os.environ['USERLIST'] = f"{current},{username}:__registry__" if current else f"{username}:__registry__"

        audit_service.log_user_created(username, admin_username)
        logger.info(f"User '{username}' created by {admin_username}")

        return True, f"Benutzer '{username}' erfolgreich erstellt"

    def delete_user(self, username: str, admin_username: str) -> Tuple[bool, str]:
        """User löschen (Soft-Delete)"""
        if username == admin_username:
            return False, "Du kannst dich nicht selbst löschen"

        userlist = get_userlist()
        if username not in userlist:
            return False, f"Benutzer '{username}' nicht gefunden"

        # Check if this is the last admin
        registry = self._load_registry()
        admin_overrides = registry.get('admin_overrides', {})
        admin_users_list = Config.get_admin_users()
        deleted = registry.get('deleted_users', [])

        active_admins = []
        for u in userlist:
            if u in deleted or u == username:
                continue
            if u in admin_overrides:
                if admin_overrides[u]:
                    active_admins.append(u)
            elif u in admin_users_list:
                active_admins.append(u)

        # Check if target user is admin
        is_target_admin = admin_overrides.get(username, username in admin_users_list)
        if is_target_admin and len(active_admins) == 0:
            return False, "Letzter Admin kann nicht gelöscht werden"

        # Soft delete
        registry.setdefault('deleted_users', [])
        if username not in registry['deleted_users']:
            registry['deleted_users'].append(username)
        self._save_registry(registry)

        # Sync runtime
        self._sync_runtime_userlist()

        audit_service.log_user_deleted(username, admin_username)
        logger.info(f"User '{username}' deleted by {admin_username}")

        return True, f"Benutzer '{username}' wurde gelöscht"

    def reset_password(self, username: str, admin_username: str) -> Tuple[bool, str, str]:
        """Passwort zurücksetzen, gibt (success, message, new_password) zurück"""
        userlist = get_userlist()
        if username not in userlist:
            return False, f"Benutzer '{username}' nicht gefunden", ""

        # Generate random password
        new_password = secrets.token_urlsafe(10)[:10]

        # Hash and store
        hashed = security_service.hash_password(new_password)
        custom_passwords = data_persistence.load_data('user_passwords', {})
        custom_passwords[username] = hashed
        data_persistence.save_data('user_passwords', custom_passwords)

        audit_service.log_admin_action('password_reset', {
            'target_user': username,
        }, admin_username)
        logger.info(f"Password reset for '{username}' by {admin_username}")

        return True, "Passwort wurde zurückgesetzt", new_password

    def toggle_admin(self, username: str, admin_username: str) -> Tuple[bool, str]:
        """Admin-Status umschalten"""
        if username == admin_username:
            return False, "Du kannst deine eigene Admin-Rolle nicht ändern"

        userlist = get_userlist()
        if username not in userlist:
            return False, f"Benutzer '{username}' nicht gefunden"

        registry = self._load_registry()
        admin_overrides = registry.get('admin_overrides', {})
        admin_users_list = Config.get_admin_users()

        # Determine current admin status
        if username in admin_overrides:
            currently_admin = admin_overrides[username]
        else:
            currently_admin = username in admin_users_list

        new_admin_status = not currently_admin

        # If removing admin, check we're not removing the last one
        if currently_admin and not new_admin_status:
            deleted = registry.get('deleted_users', [])
            active_admins = 0
            for u in userlist:
                if u in deleted or u == username:
                    continue
                if u in admin_overrides:
                    if admin_overrides[u]:
                        active_admins += 1
                elif u in admin_users_list:
                    active_admins += 1
            if active_admins == 0:
                return False, "Letzter Admin kann nicht entfernt werden"

        # Save override
        registry.setdefault('admin_overrides', {})[username] = new_admin_status
        self._save_registry(registry)

        status_text = "Admin" if new_admin_status else "Benutzer"
        audit_service.log_admin_action('admin_toggle', {
            'target_user': username,
            'new_status': status_text,
        }, admin_username)
        logger.info(f"Admin toggle for '{username}' -> {status_text} by {admin_username}")

        return True, f"'{username}' ist jetzt {status_text}"


# Global instance
user_management_service = UserManagementService()
