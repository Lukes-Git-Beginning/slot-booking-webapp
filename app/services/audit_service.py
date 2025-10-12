# -*- coding: utf-8 -*-
"""
Audit-Logging Service
Protokolliert Admin-Aktionen und Security-Events für Compliance & Sicherheit
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import request, session
from app.core.extensions import data_persistence

logger = logging.getLogger(__name__)


class AuditService:
    """Service für Audit-Logging von kritischen Aktionen"""

    def __init__(self):
        self.audit_file = 'audit_log'
        self.max_entries = 10000  # Maximal 10.000 Einträge (ca. 1 Jahr)

    def _load_audit_log(self) -> List[Dict]:
        """Lade Audit-Log"""
        return data_persistence.load_data(self.audit_file, [])

    def _save_audit_log(self, log_data: List[Dict]):
        """Speichere Audit-Log mit Auto-Rotation"""
        # Limitiere auf max_entries (älteste zuerst löschen)
        if len(log_data) > self.max_entries:
            log_data = log_data[-self.max_entries:]

        data_persistence.save_data(self.audit_file, log_data)

    def log_event(
        self,
        event_type: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = 'info',
        user: Optional[str] = None
    ) -> None:
        """
        Protokolliere Audit-Event

        Args:
            event_type: Kategorie (auth, admin, data, security)
            action: Beschreibung der Aktion
            details: Zusätzliche Details als Dict
            severity: info, warning, critical
            user: Benutzername (falls nicht in Session)
        """
        try:
            # User aus Session oder Parameter
            if not user:
                user = session.get('user', 'anonymous')

            # IP-Adresse erfassen
            ip_address = request.remote_addr if request else 'unknown'
            user_agent = request.headers.get('User-Agent', 'unknown') if request else 'unknown'

            # Event erstellen
            event = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'event_type': event_type,
                'action': action,
                'user': user,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'severity': severity,
                'details': details or {}
            }

            # Log laden, Event hinzufügen, speichern
            audit_log = self._load_audit_log()
            audit_log.append(event)
            self._save_audit_log(audit_log)

            # Auch ins normale Log schreiben
            log_level = {
                'info': logging.INFO,
                'warning': logging.WARNING,
                'critical': logging.CRITICAL
            }.get(severity, logging.INFO)

            logger.log(
                log_level,
                f"AUDIT [{event_type}]: {action} by {user}",
                extra={'details': details}
            )

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}", exc_info=True)

    # === Convenience Methods für häufige Events ===

    def log_login_success(self, username: str):
        """Erfolgreicher Login"""
        self.log_event(
            event_type='auth',
            action='login_success',
            user=username,
            severity='info'
        )

    def log_login_failure(self, username: str, reason: str = 'invalid_credentials'):
        """Fehlgeschlagener Login"""
        self.log_event(
            event_type='auth',
            action='login_failure',
            details={'username': username, 'reason': reason},
            severity='warning',
            user=username
        )

    def log_logout(self, username: str):
        """Logout"""
        self.log_event(
            event_type='auth',
            action='logout',
            user=username,
            severity='info'
        )

    def log_password_change(self, username: str):
        """Passwort-Änderung"""
        self.log_event(
            event_type='security',
            action='password_changed',
            user=username,
            severity='info'
        )

    def log_2fa_enabled(self, username: str):
        """2FA aktiviert"""
        self.log_event(
            event_type='security',
            action='2fa_enabled',
            user=username,
            severity='info'
        )

    def log_2fa_disabled(self, username: str):
        """2FA deaktiviert"""
        self.log_event(
            event_type='security',
            action='2fa_disabled',
            user=username,
            severity='warning'
        )

    def log_user_created(self, username: str, created_by: str):
        """User erstellt"""
        self.log_event(
            event_type='admin',
            action='user_created',
            details={'target_user': username},
            severity='info',
            user=created_by
        )

    def log_user_deleted(self, username: str, deleted_by: str):
        """User gelöscht"""
        self.log_event(
            event_type='admin',
            action='user_deleted',
            details={'target_user': username},
            severity='warning',
            user=deleted_by
        )

    def log_data_export(self, export_type: str, record_count: int, exported_by: str):
        """Daten-Export"""
        self.log_event(
            event_type='data',
            action='data_export',
            details={'export_type': export_type, 'record_count': record_count},
            severity='info',
            user=exported_by
        )

    def log_data_import(self, import_type: str, record_count: int, imported_by: str):
        """Daten-Import"""
        self.log_event(
            event_type='data',
            action='data_import',
            details={'import_type': import_type, 'record_count': record_count},
            severity='info',
            user=imported_by
        )

    def log_admin_action(self, action: str, details: Dict[str, Any], admin_user: str):
        """Generische Admin-Aktion"""
        self.log_event(
            event_type='admin',
            action=action,
            details=details,
            severity='info',
            user=admin_user
        )

    def log_security_alert(self, alert_type: str, details: Dict[str, Any]):
        """Security-Alert"""
        self.log_event(
            event_type='security',
            action=f'security_alert_{alert_type}',
            details=details,
            severity='critical'
        )

    # === Query Methods ===

    def get_recent_events(self, limit: int = 100, event_type: Optional[str] = None) -> List[Dict]:
        """Hole neueste Events (optional gefiltert nach Typ)"""
        audit_log = self._load_audit_log()

        if event_type:
            audit_log = [e for e in audit_log if e.get('event_type') == event_type]

        # Neueste zuerst
        audit_log.reverse()

        return audit_log[:limit]

    def get_user_events(self, username: str, limit: int = 50) -> List[Dict]:
        """Hole Events für spezifischen User"""
        audit_log = self._load_audit_log()
        user_events = [e for e in audit_log if e.get('user') == username]

        # Neueste zuerst
        user_events.reverse()

        return user_events[:limit]

    def get_failed_logins(self, hours: int = 24) -> List[Dict]:
        """Hole fehlgeschlagene Logins der letzten X Stunden"""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        audit_log = self._load_audit_log()

        failed_logins = [
            e for e in audit_log
            if e.get('action') == 'login_failure'
            and datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) > cutoff
        ]

        return failed_logins

    def get_critical_events(self, limit: int = 50) -> List[Dict]:
        """Hole kritische Security-Events"""
        audit_log = self._load_audit_log()
        critical = [e for e in audit_log if e.get('severity') == 'critical']

        # Neueste zuerst
        critical.reverse()

        return critical[:limit]

    def search_events(
        self,
        user: Optional[str] = None,
        event_type: Optional[str] = None,
        action: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Erweiterte Event-Suche"""
        audit_log = self._load_audit_log()

        # Filter anwenden
        if user:
            audit_log = [e for e in audit_log if e.get('user') == user]
        if event_type:
            audit_log = [e for e in audit_log if e.get('event_type') == event_type]
        if action:
            audit_log = [e for e in audit_log if e.get('action') == action]
        if severity:
            audit_log = [e for e in audit_log if e.get('severity') == severity]

        # Neueste zuerst
        audit_log.reverse()

        return audit_log[:limit]


# Global instance
audit_service = AuditService()
