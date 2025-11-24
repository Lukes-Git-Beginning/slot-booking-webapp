#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test-Script: Erstelle eine Demo-Notification für das neue Notification-System
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize Flask app context
from app import create_app
app = create_app()

def create_demo_notifications():
    """Erstelle Demo-Notifications für Testing"""
    from app.services.notification_service import notification_service

    print("[*] Erstelle Test-Notifications...")

    # 1. Toast-Popup für Admins (zeigt neues Notification-System)
    result1 = notification_service.create_notification(
        roles=['admin'],
        title='🎉 Neues Notification-System ist live!',
        message='Toast-Pop-ups mit Rollenbasierung, wegklickbar und mit klarem Design. Teste es jetzt!',
        notification_type='success',
        show_popup=True,
        actions=[{'text': 'Mehr erfahren', 'url': '/'}]
    )
    print(f"[+] Admin-Notification erstellt: {result1}")

    # 2. Info-Notification für alle (nur Dropdown, kein Popup)
    result2 = notification_service.create_notification(
        roles=['all'],
        title='System-Update verfugbar',
        message='Das Dashboard wurde optimiert fur bessere Performance und Benutzerfreundlichkeit.',
        notification_type='info',
        show_popup=False,
        actions=[]
    )
    print(f"[+] All-Notification erstellt: {result2}")

    # 3. T2-Closer Notification (Popup für Closer)
    result3 = notification_service.create_notification(
        roles=['closer', 'coach'],
        title='T2-System Verbesserungen',
        message='Neue Drag & Drop Features im T2-Booking-System verfugbar!',
        notification_type='info',
        show_popup=True,
        actions=[{'text': 'T2 offnen', 'url': '/t2/'}]
    )
    print(f"[+] T2-Notification erstellt: {result3}")

    # 4. Opener/Telefonist Notification
    result4 = notification_service.create_notification(
        roles=['opener', 'telefonist'],
        title='Slot-Booking Update',
        message='Das Booking-System wurde aktualisiert mit verbesserter Kalender-Synchronisation.',
        notification_type='success',
        show_popup=False,
        actions=[{'text': 'Slots anzeigen', 'url': '/slots/'}]
    )
    print(f"[+] Booking-Notification erstellt: {result4}")

    print("\n[*] Alle Test-Notifications erfolgreich erstellt!")
    print("[*] Starte die App mit 'python run.py' und logge dich ein, um sie zu sehen.")

if __name__ == '__main__':
    with app.app_context():
        create_demo_notifications()
