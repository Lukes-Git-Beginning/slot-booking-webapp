# -*- coding: utf-8 -*-
"""
Security Service
Passwort-Management und Zwei-Faktor-Authentifizierung
"""

import pyotp
import qrcode
import io
import base64
import secrets
import bcrypt
import logging
from typing import Dict, Optional, Tuple, List
from app.core.extensions import data_persistence
from app.utils.helpers import get_userlist

logger = logging.getLogger(__name__)


class SecurityService:
    """Service für Passwort-Änderung und 2FA"""

    def __init__(self):
        self.passwords_file = 'user_passwords'
        self.twofa_file = 'user_2fa'

    def _load_passwords(self) -> Dict[str, str]:
        """Lade überschriebene Passwörter (können Klartext oder Hashes sein)"""
        return data_persistence.load_data(self.passwords_file, {})

    def _save_passwords(self, passwords: Dict[str, str]):
        """Speichere überschriebene Passwörter"""
        data_persistence.save_data(self.passwords_file, passwords)

    def hash_password(self, password: str) -> str:
        """Hash Passwort mit bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_hashed_password(self, password: str, hashed: str) -> bool:
        """Verifiziere Passwort gegen bcrypt-Hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.debug(f"Hash verification failed: {e}")
            return False

    def is_hashed_password(self, password_str: str) -> bool:
        """Prüfe ob String ein bcrypt-Hash ist (beginnt mit $2b$)"""
        return password_str.startswith('$2b$') or password_str.startswith('$2a$')

    def _load_2fa_data(self) -> Dict[str, dict]:
        """Lade 2FA-Daten"""
        return data_persistence.load_data(self.twofa_file, {})

    def _save_2fa_data(self, data: Dict[str, dict]):
        """Speichere 2FA-Daten"""
        data_persistence.save_data(self.twofa_file, data)

    def migrate_userlist_passwords(self):
        """Pre-hash alle USERLIST-Passwoerter die noch nicht in custom_passwords sind"""
        userlist = get_userlist()
        if not userlist:
            return

        custom_passwords = self._load_passwords()
        migrated = 0

        for username, plaintext_pw in userlist.items():
            if username not in custom_passwords:
                custom_passwords[username] = self.hash_password(plaintext_pw)
                migrated += 1

        if migrated > 0:
            self._save_passwords(custom_passwords)
            logger.info(f"Pre-migrated {migrated} USERLIST passwords to bcrypt hashes")

    def verify_password(self, username: str, password: str) -> bool:
        """
        Verifiziere Passwort (nur bcrypt-Hash, kein Klartext-Fallback).
        migrate_userlist_passwords() laeuft beim Startup und stellt sicher,
        dass alle USERLIST-User einen bcrypt-Hash in custom_passwords haben.
        """
        custom_passwords = self._load_passwords()
        if username in custom_passwords:
            stored_pw = custom_passwords[username]
            if self.is_hashed_password(stored_pw):
                return self.verify_hashed_password(password, stored_pw)
            else:
                logger.warning(f"User {username} has unhashed password in custom_passwords — login blocked")
                return False

        # User existiert in USERLIST aber hat keinen Hash → Migration unvollstaendig
        userlist = get_userlist()
        if username in userlist:
            logger.error(f"User {username} in USERLIST but missing from custom_passwords — migration incomplete")
            return False

        return False

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Ändere Benutzerpasswort (neues Passwort wird IMMER gehasht)
        Returns: (success, message)
        """
        # Validierung
        if not new_password or len(new_password) < 6:
            return False, "Neues Passwort muss mindestens 6 Zeichen lang sein"

        if len(new_password) > 100:
            return False, "Passwort zu lang (max 100 Zeichen)"

        # Aktuelles Passwort verifizieren
        if not self.verify_password(username, old_password):
            return False, "Aktuelles Passwort ist falsch"

        # Neues Passwort HASHEN und speichern
        custom_passwords = self._load_passwords()
        hashed_password = self.hash_password(new_password)
        custom_passwords[username] = hashed_password
        self._save_passwords(custom_passwords)

        logger.info(f"Password changed for user {username} (now hashed)")
        return True, "Passwort erfolgreich geändert"

    def setup_2fa(self, username: str) -> Tuple[str, str, List[str]]:
        """
        Richte 2FA für Benutzer ein
        Returns: (secret, qr_code_base64, backup_codes)
        """
        # Generiere TOTP-Secret
        secret = pyotp.random_base32()

        # Erstelle TOTP-URL für QR-Code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=username,
            issuer_name="Business Tool Hub"
        )

        # Generiere QR-Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert zu Base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Generiere Backup-Codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

        # Speichere 2FA-Daten (noch nicht aktiviert)
        twofa_data = self._load_2fa_data()
        twofa_data[username] = {
            'secret': secret,
            'enabled': False,
            'backup_codes': backup_codes
        }
        self._save_2fa_data(twofa_data)

        return secret, qr_base64, backup_codes

    def enable_2fa(self, username: str, verification_code: str) -> Tuple[bool, str]:
        """
        Aktiviere 2FA nach Verifizierung
        Returns: (success, message)
        """
        twofa_data = self._load_2fa_data()

        if username not in twofa_data:
            return False, "2FA wurde noch nicht eingerichtet"

        user_2fa = twofa_data[username]
        totp = pyotp.TOTP(user_2fa['secret'])

        if totp.verify(verification_code):
            user_2fa['enabled'] = True
            self._save_2fa_data(twofa_data)
            return True, "2FA erfolgreich aktiviert"
        else:
            return False, "Ungültiger Verifizierungscode"

    def disable_2fa(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Deaktiviere 2FA
        Returns: (success, message)
        """
        # Passwort verifizieren
        if not self.verify_password(username, password):
            return False, "Passwort ist falsch"

        twofa_data = self._load_2fa_data()

        if username in twofa_data:
            del twofa_data[username]
            self._save_2fa_data(twofa_data)
            return True, "2FA wurde deaktiviert"

        return False, "2FA war nicht aktiviert"

    def verify_2fa(self, username: str, code: str) -> bool:
        """
        Verifiziere 2FA-Code oder Backup-Code
        """
        twofa_data = self._load_2fa_data()

        if username not in twofa_data:
            return True  # 2FA nicht aktiviert = immer OK

        user_2fa = twofa_data[username]

        if not user_2fa.get('enabled'):
            return True  # Nicht aktiviert = immer OK

        # TOTP-Code verifizieren
        totp = pyotp.TOTP(user_2fa['secret'])
        if totp.verify(code):
            return True

        # Backup-Code verifizieren
        backup_codes = user_2fa.get('backup_codes', [])
        if code.upper() in backup_codes:
            # Backup-Code entfernen (einmalig nutzbar)
            backup_codes.remove(code.upper())
            user_2fa['backup_codes'] = backup_codes
            self._save_2fa_data(twofa_data)
            return True

        return False

    def is_2fa_enabled(self, username: str) -> bool:
        """Prüfe ob 2FA für User aktiviert ist"""
        twofa_data = self._load_2fa_data()
        return twofa_data.get(username, {}).get('enabled', False)

    def get_backup_codes(self, username: str) -> List[str]:
        """Hole Backup-Codes für User"""
        twofa_data = self._load_2fa_data()
        return twofa_data.get(username, {}).get('backup_codes', [])


# Global instance
security_service = SecurityService()
