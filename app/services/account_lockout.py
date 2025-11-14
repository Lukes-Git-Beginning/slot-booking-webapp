# -*- coding: utf-8 -*-
"""
Account Lockout Service
Verhindert Brute-Force-Angriffe durch temporäre Konto-Sperrung
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from app.core.extensions import data_persistence

logger = logging.getLogger(__name__)


class AccountLockoutService:
    """
    Verwaltet fehlgeschlagene Login-Versuche und Account-Lockouts

    Sicherheitsrichtlinie:
    - Nach 5 fehlgeschlagenen Versuchen: 15 Minuten Sperre
    - Nach 10 fehlgeschlagenen Versuchen: 1 Stunde Sperre
    - Nach 15 fehlgeschlagenen Versuchen: 24 Stunden Sperre
    """

    def __init__(self):
        self.lockout_file = 'account_lockouts'
        self.max_attempts_tier1 = 5
        self.max_attempts_tier2 = 10
        self.max_attempts_tier3 = 15
        self.lockout_duration_tier1 = 15  # Minuten
        self.lockout_duration_tier2 = 60  # Minuten
        self.lockout_duration_tier3 = 1440  # Minuten (24 Stunden)

    def _load_lockout_data(self) -> Dict:
        """Lade Lockout-Daten"""
        return data_persistence.load_data(self.lockout_file, {})

    def _save_lockout_data(self, data: Dict):
        """Speichere Lockout-Daten"""
        data_persistence.save_data(self.lockout_file, data)

    def is_locked_out(self, username: str) -> Tuple[bool, Optional[int]]:
        """
        Prüfe ob Account gesperrt ist

        Returns:
            (is_locked, minutes_remaining)
        """
        lockout_data = self._load_lockout_data()

        if username not in lockout_data:
            return False, None

        user_data = lockout_data[username]
        locked_until = datetime.fromisoformat(user_data.get('locked_until', ''))

        if datetime.now() < locked_until:
            # Noch gesperrt
            remaining = (locked_until - datetime.now()).total_seconds() / 60
            return True, int(remaining)

        # Sperre abgelaufen - Zähler zurücksetzen
        del lockout_data[username]
        self._save_lockout_data(lockout_data)
        return False, None

    def record_failed_attempt(self, username: str) -> Tuple[bool, Optional[int]]:
        """
        Registriere fehlgeschlagenen Login-Versuch

        Returns:
            (is_now_locked, lockout_minutes)
        """
        lockout_data = self._load_lockout_data()

        if username not in lockout_data:
            lockout_data[username] = {
                'failed_attempts': 0,
                'first_attempt': datetime.now().isoformat(),
                'last_attempt': None,
                'locked_until': None
            }

        user_data = lockout_data[username]
        user_data['failed_attempts'] += 1
        user_data['last_attempt'] = datetime.now().isoformat()

        failed_attempts = user_data['failed_attempts']
        lockout_duration = 0

        # Bestimme Lockout-Tier
        if failed_attempts >= self.max_attempts_tier3:
            lockout_duration = self.lockout_duration_tier3
            logger.warning(f"Account {username} locked for {lockout_duration} minutes (Tier 3: {failed_attempts} attempts)")
        elif failed_attempts >= self.max_attempts_tier2:
            lockout_duration = self.lockout_duration_tier2
            logger.warning(f"Account {username} locked for {lockout_duration} minutes (Tier 2: {failed_attempts} attempts)")
        elif failed_attempts >= self.max_attempts_tier1:
            lockout_duration = self.lockout_duration_tier1
            logger.warning(f"Account {username} locked for {lockout_duration} minutes (Tier 1: {failed_attempts} attempts)")

        if lockout_duration > 0:
            locked_until = datetime.now() + timedelta(minutes=lockout_duration)
            user_data['locked_until'] = locked_until.isoformat()
            self._save_lockout_data(lockout_data)
            return True, lockout_duration

        # Noch nicht gesperrt
        self._save_lockout_data(lockout_data)
        return False, None

    def record_successful_login(self, username: str):
        """Lösche fehlgeschlagene Versuche nach erfolgreichem Login"""
        lockout_data = self._load_lockout_data()

        if username in lockout_data:
            del lockout_data[username]
            self._save_lockout_data(lockout_data)
            logger.info(f"Failed login attempts cleared for {username}")

    def admin_unlock(self, username: str) -> bool:
        """Admin-Funktion: Account manuell entsperren"""
        lockout_data = self._load_lockout_data()

        if username in lockout_data:
            del lockout_data[username]
            self._save_lockout_data(lockout_data)
            logger.info(f"Account {username} manually unlocked by admin")
            return True

        return False

    def get_lockout_info(self, username: str) -> Optional[Dict]:
        """Hole Lockout-Informationen für Admin-Dashboard"""
        lockout_data = self._load_lockout_data()

        if username not in lockout_data:
            return None

        user_data = lockout_data[username]
        locked_until = datetime.fromisoformat(user_data.get('locked_until', '')) if user_data.get('locked_until') else None

        return {
            'username': username,
            'failed_attempts': user_data.get('failed_attempts', 0),
            'first_attempt': user_data.get('first_attempt'),
            'last_attempt': user_data.get('last_attempt'),
            'locked_until': user_data.get('locked_until'),
            'is_locked': locked_until and datetime.now() < locked_until if locked_until else False,
            'minutes_remaining': int((locked_until - datetime.now()).total_seconds() / 60) if locked_until and datetime.now() < locked_until else 0
        }

    def get_all_locked_accounts(self) -> list:
        """Hole alle aktuell gesperrten Accounts"""
        lockout_data = self._load_lockout_data()
        locked_accounts = []

        for username, user_data in lockout_data.items():
            locked_until = datetime.fromisoformat(user_data.get('locked_until', '')) if user_data.get('locked_until') else None

            if locked_until and datetime.now() < locked_until:
                locked_accounts.append({
                    'username': username,
                    'failed_attempts': user_data.get('failed_attempts', 0),
                    'locked_until': user_data.get('locked_until'),
                    'minutes_remaining': int((locked_until - datetime.now()).total_seconds() / 60)
                })

        return locked_accounts


# Global instance
account_lockout = AccountLockoutService()
