# -*- coding: utf-8 -*-
"""
Notification Service
Zentrale Verwaltung für Benachrichtigungen mit Rollenbasierung
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from app.core.extensions import data_persistence

logger = logging.getLogger(__name__)


class NotificationService:
    """Service für rollenbasierte Benachrichtigungen"""

    def __init__(self):
        self.notifications_file = 'user_notifications'

        # Rollen-Mapping: Welche User gehören zu welcher Rolle
        self.role_mapping = {
            'admin': ['alexander.nehm', 'david.nehm', 'simon.mast'],
            'closer': ['jose.torspecken', 'alexander.nehm', 'david.nehm', 'tim.kreisel', 'christian.mast', 'daniel.herbort'],
            'opener': ['christian.mast', 'tim.kreisel', 'daniel.herbort', 'sonja.mast', 'simon.mast', 'patrick.woltschleger', 'dominik.mikic', 'ann-kathrin.welge'],
            'coach': ['alexander.nehm', 'david.nehm', 'jose.torspecken'],
            'telefonist': ['tim.kreisel', 'christian.mast', 'ladislav.heka', 'sonja.mast', 'simon.mast', 'alexandra.börner', 'patrick.woltschleger', 'yasmine.schumacher', 'ann-kathrin.welge'],
            'service': ['alexandra.börner', 'vanessa.wagner', 'simon.mast']
        }

    def _load_all_notifications(self) -> Dict[str, List[Dict]]:
        """Lade alle Benachrichtigungen"""
        return data_persistence.load_data(self.notifications_file, {})

    def _save_all_notifications(self, notifications: Dict[str, List[Dict]]):
        """Speichere alle Benachrichtigungen"""
        data_persistence.save_data(self.notifications_file, notifications)

    def _get_users_by_roles(self, roles: List[str]) -> List[str]:
        """
        Konvertiere Rollen zu User-Liste

        Args:
            roles: Liste von Rollen (z.B. ['admin', 'closer'])

        Returns:
            Liste von Usernamen die zu diesen Rollen gehören
        """
        if 'all' in roles:
            # Alle User aus allen Rollen (dedupliziert)
            all_users = set()
            for role_users in self.role_mapping.values():
                all_users.update(role_users)
            return list(all_users)

        users = set()
        for role in roles:
            if role in self.role_mapping:
                users.update(self.role_mapping[role])
            else:
                logger.warning(f"Unknown role: {role}")

        return list(users)

    def create_notification(
        self,
        roles: List[str],
        title: str,
        message: str,
        notification_type: str = 'info',
        show_popup: bool = False,
        actions: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, int]:
        """
        Erstelle neue Benachrichtigung für bestimmte Rollen

        Args:
            roles: Liste von Rollen (z.B. ['admin', 'closer', 'all'])
            title: Benachrichtigungs-Titel
            message: Benachrichtigungs-Nachricht
            notification_type: Typ (info, success, warning, error)
            show_popup: Soll als Toast-Popup angezeigt werden?
            actions: Optional Liste von Action-Buttons [{'text': 'Click me', 'url': '/path'}]

        Returns:
            Dict mit Anzahl erstellter Notifications pro User
        """
        if actions is None:
            actions = []

        # Hole User-Liste basierend auf Rollen
        target_users = self._get_users_by_roles(roles)

        if not target_users:
            logger.warning(f"No users found for roles: {roles}")
            return {}

        # Lade alle Notifications
        all_notifications = self._load_all_notifications()

        # Erstelle Notification-Objekt
        notification_id = str(uuid.uuid4())[:8]  # Kurze UUID
        timestamp = datetime.now().isoformat()

        notification = {
            'id': notification_id,
            'type': notification_type,
            'title': title,
            'message': message,
            'timestamp': timestamp,
            'read': False,
            'dismissed': False,
            'show_popup': show_popup,
            'roles': roles,
            'actions': actions
        }

        # Füge Notification zu jedem Target-User hinzu
        created_count = {}
        for username in target_users:
            if username not in all_notifications:
                all_notifications[username] = []

            all_notifications[username].append(notification.copy())
            created_count[username] = 1

            logger.info(f"Created notification '{title}' for {username} (popup={show_popup})")

        # Speichere alle Notifications
        self._save_all_notifications(all_notifications)

        return created_count

    def get_user_notifications(
        self,
        username: str,
        show_popup_only: bool = False,
        unread_only: bool = False
    ) -> List[Dict]:
        """
        Hole Benachrichtigungen für User

        Args:
            username: Username
            show_popup_only: Nur Notifications mit show_popup=True
            unread_only: Nur ungelesene Notifications

        Returns:
            Liste von Notifications
        """
        all_notifications = self._load_all_notifications()
        user_notifications = all_notifications.get(username, [])

        # Filter: Nicht dismissed
        user_notifications = [n for n in user_notifications if not n.get('dismissed', False)]

        # Filter: show_popup
        if show_popup_only:
            user_notifications = [n for n in user_notifications if n.get('show_popup', False)]

        # Filter: unread
        if unread_only:
            user_notifications = [n for n in user_notifications if not n.get('read', False)]

        # Sortiere nach Timestamp (neueste zuerst)
        user_notifications.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return user_notifications

    def mark_as_read(self, username: str, notification_id: str) -> bool:
        """
        Markiere Notification als gelesen

        Args:
            username: Username
            notification_id: Notification ID

        Returns:
            True wenn erfolgreich, False wenn nicht gefunden
        """
        all_notifications = self._load_all_notifications()
        user_notifications = all_notifications.get(username, [])

        for notification in user_notifications:
            if notification['id'] == notification_id:
                notification['read'] = True
                self._save_all_notifications(all_notifications)
                logger.info(f"Marked notification {notification_id} as read for {username}")
                return True

        logger.warning(f"Notification {notification_id} not found for {username}")
        return False

    def dismiss_notification(self, username: str, notification_id: str) -> bool:
        """
        Lösche Notification permanent (dismissed=True)

        Args:
            username: Username
            notification_id: Notification ID

        Returns:
            True wenn erfolgreich, False wenn nicht gefunden
        """
        all_notifications = self._load_all_notifications()
        user_notifications = all_notifications.get(username, [])

        for notification in user_notifications:
            if notification['id'] == notification_id:
                notification['dismissed'] = True
                self._save_all_notifications(all_notifications)
                logger.info(f"Dismissed notification {notification_id} for {username}")
                return True

        logger.warning(f"Notification {notification_id} not found for {username}")
        return False

    def get_unread_count(self, username: str) -> int:
        """
        Anzahl ungelesener Benachrichtigungen

        Args:
            username: Username

        Returns:
            Anzahl ungelesener Notifications
        """
        notifications = self.get_user_notifications(username, unread_only=True)
        return len(notifications)

    def mark_all_as_read(self, username: str) -> int:
        """
        Markiere alle Notifications als gelesen

        Args:
            username: Username

        Returns:
            Anzahl markierter Notifications
        """
        all_notifications = self._load_all_notifications()
        user_notifications = all_notifications.get(username, [])

        count = 0
        for notification in user_notifications:
            if not notification.get('read', False) and not notification.get('dismissed', False):
                notification['read'] = True
                count += 1

        if count > 0:
            self._save_all_notifications(all_notifications)
            logger.info(f"Marked {count} notifications as read for {username}")

        return count


# Singleton-Instanz
notification_service = NotificationService()
