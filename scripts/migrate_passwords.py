#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Password Migration Script
Migriert Klartext-Passwörter zu bcrypt-Hashes

USAGE:
    python scripts/migrate_passwords.py

WICHTIG:
    - Backup wird automatisch erstellt
    - USERLIST bleibt unverändert (env variable)
    - Nur user_passwords.json wird migriert
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.security_service import security_service
from app.services.data_persistence import data_persistence
from datetime import datetime


def migrate_passwords():
    """Migriere alle Klartext-Passwörter zu bcrypt-Hashes"""

    print("=" * 60)
    print("PASSWORD MIGRATION TOOL")
    print("Migriert Klartext-Passwörter zu bcrypt-Hashes")
    print("=" * 60)
    print()

    # Bestehende Passwörter laden
    custom_passwords = data_persistence.load_data('user_passwords', {})

    if not custom_passwords:
        print("ℹ️  Keine benutzerdefinierten Passwörter gefunden (user_passwords.json leer)")
        print("   Alle User nutzen USERLIST - keine Migration nötig!")
        return

    print(f"📁 Gefunden: {len(custom_passwords)} gespeicherte Passwörter")
    print()

    # Backup erstellen
    backup_name = f"user_passwords_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    data_persistence._create_backup('user_passwords', custom_passwords)
    print(f"✅ Backup erstellt: {backup_name}")
    print()

    # Passwörter analysieren
    plaintext_count = 0
    hashed_count = 0
    migrated = []

    for username, password in custom_passwords.items():
        if security_service.is_hashed_password(password):
            hashed_count += 1
            print(f"  ✅ {username}: Bereits gehasht")
        else:
            plaintext_count += 1
            print(f"  🔄 {username}: Klartext → wird migriert")
            migrated.append(username)

    print()
    print(f"📊 Status: {hashed_count} gehasht, {plaintext_count} Klartext")
    print()

    if plaintext_count == 0:
        print("✅ Alle Passwörter sind bereits sicher gehasht!")
        return

    # Bestätigung
    print(f"⚠️  ACHTUNG: {plaintext_count} Passwörter werden jetzt zu bcrypt migriert")
    response = input("Fortfahren? (yes/no): ").strip().lower()

    if response != 'yes':
        print("❌ Migration abgebrochen")
        return

    print()
    print("🔄 Migration läuft...")
    print()

    # Migration durchführen
    migrated_passwords = {}
    for username, password in custom_passwords.items():
        if security_service.is_hashed_password(password):
            # Bereits gehasht - übernehmen
            migrated_passwords[username] = password
        else:
            # Hashen
            hashed = security_service.hash_password(password)
            migrated_passwords[username] = hashed
            print(f"  ✅ {username}: Gehasht")

    # Speichern
    data_persistence.save_data('user_passwords', migrated_passwords)

    print()
    print("=" * 60)
    print("✅ MIGRATION ERFOLGREICH!")
    print(f"   {len(migrated)} Passwörter wurden sicher gehasht")
    print()
    print("📝 Nächste Schritte:")
    print("   1. User können sich normal einloggen")
    print("   2. Passwörter sind jetzt mit bcrypt gesichert")
    print("   3. Backup liegt in: data/backups/")
    print("=" * 60)


if __name__ == '__main__':
    try:
        migrate_passwords()
    except Exception as e:
        print(f"❌ FEHLER: {e}")
        sys.exit(1)
