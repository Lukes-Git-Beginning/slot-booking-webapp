#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passwort-Migrations-Script - Konvertiert Klartext-Passwörter zu bcrypt-Hashes

KRITISCHE SICHERHEITSVERBESSERUNG:
Dieses Script liest alle Benutzer aus USERLIST (.env), hasht die Passwörter mit bcrypt
und speichert sie in user_passwords.json. Danach können die Klartext-Passwörter aus
USERLIST entfernt werden.

Usage:
    python scripts/migrate_passwords_to_bcrypt.py

Requirements:
    - .env muss existieren mit USERLIST
    - bcrypt muss installiert sein
    - data/persistent/ Verzeichnis muss existieren
"""

import os
import sys
import json
import bcrypt
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / '.env'
if not env_path.exists():
    print("❌ ERROR: .env file not found!")
    print(f"   Expected at: {env_path}")
    sys.exit(1)

load_dotenv(env_path)


class PasswordMigrator:
    """Migriert Klartext-Passwörter zu bcrypt-Hashes"""

    def __init__(self):
        self.userlist_str = os.getenv('USERLIST', '')
        self.persist_base = os.getenv('PERSIST_BASE', 'data')
        self.passwords_file = Path(self.persist_base) / 'persistent' / 'user_passwords.json'

    def parse_userlist(self) -> dict:
        """Parse USERLIST in username:password Dictionary"""
        if not self.userlist_str:
            print("❌ ERROR: USERLIST not found in .env!")
            return {}

        users = {}
        for user_pass in self.userlist_str.split(","):
            if ":" in user_pass:
                username, password = user_pass.split(":", 1)
                users[username.strip()] = password.strip()

        return users

    def hash_password(self, password: str) -> str:
        """Hash Passwort mit bcrypt (12 Rounds)"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def load_existing_passwords(self) -> dict:
        """Lade existierende Passwörter (falls vorhanden)"""
        if self.passwords_file.exists():
            with open(self.passwords_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_passwords(self, passwords: dict):
        """Speichere Passwörter in JSON"""
        # Ensure directory exists
        self.passwords_file.parent.mkdir(parents=True, exist_ok=True)

        # Create backup if file exists
        if self.passwords_file.exists():
            backup_path = self.passwords_file.with_suffix(
                f'.json.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            )
            self.passwords_file.rename(backup_path)
            print(f"✓ Backup erstellt: {backup_path.name}")

        # Save new passwords
        with open(self.passwords_file, 'w', encoding='utf-8') as f:
            json.dump(passwords, f, indent=2, ensure_ascii=False)

    def migrate(self, dry_run=False):
        """Führe Migration durch"""
        print("=" * 70)
        print("PASSWORT-MIGRATION: Klartext → bcrypt")
        print("=" * 70)
        print()

        # Parse USERLIST
        users = self.parse_userlist()
        if not users:
            print("❌ Keine Benutzer in USERLIST gefunden!")
            return False

        print(f"✓ {len(users)} Benutzer in USERLIST gefunden:")
        for username in users.keys():
            print(f"  - {username}")
        print()

        # Load existing passwords
        existing_passwords = self.load_existing_passwords()
        if existing_passwords:
            print(f"⚠️  {len(existing_passwords)} existierende Passwörter gefunden in {self.passwords_file.name}")
            print("   Diese werden überschrieben falls User in USERLIST ist.")
            print()

        # Migrate passwords
        migrated_passwords = {}
        skipped = []
        updated = []

        for username, plaintext_password in users.items():
            # Check if already hashed (bcrypt hashes start with $2b$ or $2a$)
            if plaintext_password.startswith('$2b$') or plaintext_password.startswith('$2a$'):
                print(f"⏭️  {username}: Already hashed, skipping")
                skipped.append(username)
                migrated_passwords[username] = plaintext_password
                continue

            # Hash password
            print(f"🔐 {username}: Hashing password...", end='')
            hashed = self.hash_password(plaintext_password)
            migrated_passwords[username] = hashed
            updated.append(username)
            print(" ✓")

        print()
        print("-" * 70)
        print(f"ZUSAMMENFASSUNG:")
        print(f"  • Neu gehasht: {len(updated)}")
        print(f"  • Übersprungen (bereits gehasht): {len(skipped)}")
        print(f"  • Gesamt: {len(migrated_passwords)}")
        print("-" * 70)
        print()

        if dry_run:
            print("🚧 DRY RUN: Keine Änderungen gespeichert")
            print()
            print("Beispiel-Hash (erster User):")
            if updated:
                first_user = updated[0]
                print(f"  {first_user}: {migrated_passwords[first_user][:60]}...")
            return True

        # Save passwords
        print(f"💾 Speichere Passwörter in {self.passwords_file}...")
        self.save_passwords(migrated_passwords)
        print(f"✓ Migration abgeschlossen!")
        print()

        # Reminder
        print("=" * 70)
        print("⚠️  NÄCHSTE SCHRITTE:")
        print("=" * 70)
        print()
        print("1. Teste Login für alle migrierten Benutzer")
        print("2. Wenn alle Logins funktionieren:")
        print("   - Entferne Passwörter aus USERLIST in .env")
        print("   - Oder ersetze durch 'MIGRATED' als Marker")
        print("   - Beispiel: USERLIST=user1:MIGRATED,user2:MIGRATED")
        print()
        print("3. Backup von .env erstellen:")
        print(f"   cp .env .env.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print()
        print("=" * 70)

        return True


def main():
    """Main Entry Point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migriere Klartext-Passwörter zu bcrypt-Hashes"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Nur Test-Lauf ohne Änderungen zu speichern'
    )
    args = parser.parse_args()

    migrator = PasswordMigrator()
    success = migrator.migrate(dry_run=args.dry_run)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
