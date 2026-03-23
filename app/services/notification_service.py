# -*- coding: utf-8 -*-
"""
Notification Service
Zentrale Verwaltung für Benachrichtigungen mit Rollenbasierung

PostgreSQL Dual-Write: Neue Notifications werden in beide Systeme geschrieben.
Reads sind PG-first mit JSON-Fallback.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from app.core.extensions import data_persistence

logger = logging.getLogger(__name__)

# PostgreSQL dual-write support
USE_POSTGRES = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

try:
    from app.models.notification import Notification as NotificationModel
    from app.utils.db_utils import db_session_scope
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    USE_POSTGRES = False


class NotificationService:
    """Service für rollenbasierte Benachrichtigungen"""

    def __init__(self):
        self.notifications_file = 'user_notifications'

        # Rollen-Mapping: Welche User gehören zu welcher Rolle
        self.role_mapping = {
            'admin': ['alexander.nehm', 'david.nehm', 'simon.mast', 'luke.hoppe'],
            'closer': ['jose.torspecken', 'alexander.nehm', 'david.nehm', 'tim.kreisel', 'christian.mast', 'daniel.herbort'],
            'opener': ['christian.mast', 'tim.kreisel', 'daniel.herbort', 'sonja.mast', 'simon.mast', 'dominik.mikic', 'ann-kathrin.welge', 'sara.mast'],
            'coach': ['alexander.nehm', 'david.nehm', 'jose.torspecken'],
            'telefonist': ['tim.kreisel', 'christian.mast', 'sonja.mast', 'simon.mast', 'alexandra.börner', 'yasmine.schumacher', 'ann-kathrin.welge', 'sara.mast', 'benjamin.kerstan', 'yannis.maeusle'],
            'service': ['alexandra.börner', 'vanessa.wagner', 'simon.mast']
        }

    def _row_to_dict(self, row) -> Dict:
        """Konvertiert eine NotificationModel-Row zu einem Dict (JSON-kompatibel)"""
        # notification_id hat Format "{base_id}-{username}" — wir extrahieren die base_id
        notif_id = row.notification_id
        if '-' in notif_id:
            # Trenne am letzten Bindestrich-Segment, das den Username enthält
            # Format: {uuid8}-{username} — uuid8 selbst enthält keine Bindestriche
            # Verwende daher das erste Segment (8 Zeichen UUID)
            parts = notif_id.split('-', 1)
            base_id = parts[0]
        else:
            base_id = notif_id

        return {
            'id': base_id,
            'type': row.notification_type,
            'title': row.title,
            'message': row.message,
            'timestamp': row.created_at.isoformat() if row.created_at else '',
            'read': row.is_read,
            'dismissed': row.is_dismissed,
            'show_popup': row.show_popup,
            'roles': row.roles or [],
            'actions': row.actions or []
        }

    def _load_all_notifications(self) -> Dict[str, List[Dict]]:
        """
        Lade alle Benachrichtigungen.

        PG-first: Liest aus PostgreSQL (nur nicht-dismissed).
        JSON-Fallback bei PG-Fehler.
        """
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    rows = session.query(NotificationModel).filter(
                        NotificationModel.is_dismissed == False  # noqa: E712
                    ).order_by(NotificationModel.created_at.desc()).all()

                    result: Dict[str, List[Dict]] = {}
                    for row in rows:
                        if row.username not in result:
                            result[row.username] = []
                        result[row.username].append(self._row_to_dict(row))
                    return result
            except Exception as e:
                logger.warning(f"PG notification read failed, falling back to JSON: {e}")

        return data_persistence.load_data(self.notifications_file, {})

    def _save_all_notifications(self, notifications: Dict[str, List[Dict]]):
        """Speichere alle Benachrichtigungen (JSON-Fallback-Store)"""
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

        # Lade alle Notifications (JSON-Store für Dual-Write)
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

        # Füge Notification zu jedem Target-User hinzu (JSON-Store)
        created_count = {}
        for username in target_users:
            if username not in all_notifications:
                all_notifications[username] = []

            all_notifications[username].append(notification.copy())
            created_count[username] = 1

            logger.info(f"Created notification '{title}' for {username} (popup={show_popup})")

        # PostgreSQL Dual-Write: Jeder User bekommt seine eigene Row
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    for username in target_users:
                        notif_row = NotificationModel(
                            notification_id=f"{notification_id}-{username}",
                            username=username,
                            title=title,
                            message=message,
                            notification_type=notification_type,
                            is_read=False,
                            is_dismissed=False,
                            show_popup=show_popup,
                            roles=roles,
                            actions=actions
                        )
                        session.add(notif_row)
            except Exception as e:
                logger.error(f"PG notification create failed: {e}")

        # JSON write (immer)
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
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    query = session.query(NotificationModel).filter(
                        NotificationModel.username == username,
                        NotificationModel.is_dismissed == False  # noqa: E712
                    )
                    if show_popup_only:
                        query = query.filter(NotificationModel.show_popup == True)  # noqa: E712
                    if unread_only:
                        query = query.filter(NotificationModel.is_read == False)  # noqa: E712
                    query = query.order_by(NotificationModel.created_at.desc())
                    rows = query.all()
                    return [self._row_to_dict(row) for row in rows]
            except Exception as e:
                logger.warning(f"PG notification query failed for {username}: {e}")

        # JSON fallback
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
            notification_id: Notification ID (base_id ohne Username-Suffix)

        Returns:
            True wenn erfolgreich, False wenn nicht gefunden
        """
        # PostgreSQL Dual-Write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    # Prefix-Match: notification_id hat Format "{base_id}-{username}"
                    row = session.query(NotificationModel).filter(
                        NotificationModel.username == username,
                        NotificationModel.notification_id.like(f"{notification_id}%")
                    ).first()
                    if row:
                        row.is_read = True
                        row.read_at = datetime.now()
            except Exception as e:
                logger.error(f"PG mark_as_read failed for {username}/{notification_id}: {e}")

        # JSON write (bestehende Logik)
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
            notification_id: Notification ID (base_id ohne Username-Suffix)

        Returns:
            True wenn erfolgreich, False wenn nicht gefunden
        """
        # PostgreSQL Dual-Write
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    row = session.query(NotificationModel).filter(
                        NotificationModel.username == username,
                        NotificationModel.notification_id.like(f"{notification_id}%")
                    ).first()
                    if row:
                        row.is_dismissed = True
            except Exception as e:
                logger.error(f"PG dismiss_notification failed for {username}/{notification_id}: {e}")

        # JSON write (bestehende Logik)
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
        Anzahl ungelesener Benachrichtigungen — PG-first mit COUNT-Query

        Args:
            username: Username

        Returns:
            Anzahl ungelesener Notifications
        """
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    count = session.query(NotificationModel).filter(
                        NotificationModel.username == username,
                        NotificationModel.is_read == False,  # noqa: E712
                        NotificationModel.is_dismissed == False  # noqa: E712
                    ).count()
                    return count
            except Exception as e:
                logger.warning(f"PG unread count failed for {username}: {e}")

        # JSON fallback
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
        pg_count = 0

        # PostgreSQL Dual-Write (Bulk-Update)
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    pg_count = session.query(NotificationModel).filter(
                        NotificationModel.username == username,
                        NotificationModel.is_read == False,  # noqa: E712
                        NotificationModel.is_dismissed == False  # noqa: E712
                    ).update({'is_read': True, 'read_at': datetime.now()})
            except Exception as e:
                logger.error(f"PG mark_all_as_read failed for {username}: {e}")

        # JSON write (bestehende Logik)
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

        # Gib PG-Count zurück wenn verfügbar, sonst JSON-Count
        return pg_count if (USE_POSTGRES and POSTGRES_AVAILABLE and pg_count > 0) else count


# Singleton-Instanz
notification_service = NotificationService()
