# -*- coding: utf-8 -*-
"""
Audit-Logging Service
Protokolliert Admin-Aktionen und Security-Events für Compliance & Sicherheit
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from flask import request, session
from app.config.base import APIConfig
from app.core.extensions import data_persistence

logger = logging.getLogger(__name__)

# PostgreSQL dual-write support
USE_POSTGRES = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

try:
    from app.models.security import AuditLog as AuditLogModel
    from app.utils.db_utils import db_session_scope
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    USE_POSTGRES = False


def _row_to_dict(row: 'AuditLogModel') -> Dict:
    """Konvertiert AuditLog-Row zu Dict (JSON-kompatibles Format)"""
    return {
        'timestamp': row.timestamp.isoformat() + 'Z' if row.timestamp else '',
        'event_type': row.event_type,
        'action': row.action,
        'user': row.user,
        'ip_address': row.ip_address or 'unknown',
        'user_agent': row.user_agent or 'unknown',
        'severity': row.severity,
        'details': row.details or {}
    }


class AuditService:
    """Service für Audit-Logging von kritischen Aktionen"""

    def __init__(self):
        self.audit_file = 'audit_log'
        self.max_entries = APIConfig.MAX_AUDIT_ENTRIES

    def _load_audit_log(self) -> List[Dict]:
        """Lade Audit-Log — PG-first mit JSON-Fallback"""
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    rows = session.query(AuditLogModel).order_by(
                        AuditLogModel.timestamp.asc()
                    ).limit(self.max_entries).all()
                    return [_row_to_dict(row) for row in rows]
            except Exception as e:
                logger.warning(f"PG audit read failed, falling back to JSON: {e}")
        return data_persistence.load_data(self.audit_file, [])

    def _save_audit_log(self, log_data: List[Dict]):
        """Speichere Audit-Log mit Auto-Rotation (nur JSON — PG-Write erfolgt in log_event)"""
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
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'action': action,
                'user': user,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'severity': severity,
                'details': details or {}
            }

            # PostgreSQL write
            if USE_POSTGRES and POSTGRES_AVAILABLE:
                try:
                    with db_session_scope() as pg_session:
                        audit_row = AuditLogModel(
                            timestamp=datetime.fromisoformat(event['timestamp'].rstrip('Z')),
                            event_type=event_type,
                            action=action,
                            user=user,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            severity=severity,
                            details=details or {}
                        )
                        pg_session.add(audit_row)
                except Exception as e:
                    logger.error(f"PG audit log failed: {e}")

            # JSON write (always)
            audit_log = data_persistence.load_data(self.audit_file, [])
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
        """Hole neueste Events (optional gefiltert nach Typ) — PG-first"""
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    query = session.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc())
                    if event_type:
                        query = query.filter(AuditLogModel.event_type == event_type)
                    rows = query.limit(limit).all()
                    return [_row_to_dict(row) for row in rows]
            except Exception as e:
                logger.warning(f"PG audit get_recent_events failed, falling back to JSON: {e}")

        # JSON fallback
        audit_log = self._load_audit_log()
        if event_type:
            audit_log = [e for e in audit_log if e.get('event_type') == event_type]
        audit_log.reverse()
        return audit_log[:limit]

    def get_user_events(self, username: str, limit: int = 50) -> List[Dict]:
        """Hole Events für spezifischen User — PG-first"""
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    rows = session.query(AuditLogModel).filter(
                        AuditLogModel.user == username
                    ).order_by(AuditLogModel.timestamp.desc()).limit(limit).all()
                    return [_row_to_dict(row) for row in rows]
            except Exception as e:
                logger.warning(f"PG audit get_user_events failed, falling back to JSON: {e}")

        # JSON fallback
        audit_log = self._load_audit_log()
        user_events = [e for e in audit_log if e.get('user') == username]
        user_events.reverse()
        return user_events[:limit]

    def get_failed_logins(self, hours: int = 24) -> List[Dict]:
        """Hole fehlgeschlagene Logins der letzten X Stunden — PG-first"""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    rows = session.query(AuditLogModel).filter(
                        AuditLogModel.action == 'login_failure',
                        AuditLogModel.timestamp >= cutoff
                    ).order_by(AuditLogModel.timestamp.desc()).all()
                    return [_row_to_dict(row) for row in rows]
            except Exception as e:
                logger.warning(f"PG audit get_failed_logins failed, falling back to JSON: {e}")

        # JSON fallback
        audit_log = self._load_audit_log()
        failed_logins = []
        for e in audit_log:
            if e.get('action') != 'login_failure':
                continue
            try:
                ts_str = e['timestamp']
                # Normalisiere verschiedene UTC-Formate auf offset-aware datetime
                # Moegliche Formate: '...+00:00Z', '...+00:00', '...Z'
                ts_str = ts_str.rstrip('Z')
                if not ts_str.endswith('+00:00') and not ts_str.endswith('-00:00'):
                    ts_str += '+00:00'
                ts = datetime.fromisoformat(ts_str)
                if ts > cutoff:
                    failed_logins.append(e)
            except (ValueError, KeyError):
                continue
        return failed_logins

    def get_critical_events(self, limit: int = 50) -> List[Dict]:
        """Hole kritische Security-Events — PG-first"""
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    rows = session.query(AuditLogModel).filter(
                        AuditLogModel.severity == 'critical'
                    ).order_by(AuditLogModel.timestamp.desc()).limit(limit).all()
                    return [_row_to_dict(row) for row in rows]
            except Exception as e:
                logger.warning(f"PG audit get_critical_events failed, falling back to JSON: {e}")

        # JSON fallback
        audit_log = self._load_audit_log()
        critical = [e for e in audit_log if e.get('severity') == 'critical']
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
        """Erweiterte Event-Suche — PG-first"""
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    query = session.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc())
                    if user:
                        query = query.filter(AuditLogModel.user == user)
                    if event_type:
                        query = query.filter(AuditLogModel.event_type == event_type)
                    if action:
                        query = query.filter(AuditLogModel.action == action)
                    if severity:
                        query = query.filter(AuditLogModel.severity == severity)
                    rows = query.limit(limit).all()
                    return [_row_to_dict(row) for row in rows]
            except Exception as e:
                logger.warning(f"PG audit search_events failed, falling back to JSON: {e}")

        # JSON fallback
        audit_log = self._load_audit_log()
        if user:
            audit_log = [e for e in audit_log if e.get('user') == user]
        if event_type:
            audit_log = [e for e in audit_log if e.get('event_type') == event_type]
        if action:
            audit_log = [e for e in audit_log if e.get('action') == action]
        if severity:
            audit_log = [e for e in audit_log if e.get('severity') == severity]
        audit_log.reverse()
        return audit_log[:limit]


# Global instance
audit_service = AuditService()
