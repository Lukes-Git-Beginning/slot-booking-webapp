# -*- coding: utf-8 -*-
"""
Recovery-Script für fehlgeschlagene Tracking-Buchungen
Sucht Buchungsdaten in Google Calendar und trackt sie nach.

Usage:
    python3 scripts/recover_failed_tracking.py              # DRY-RUN
    python3 scripts/recover_failed_tracking.py --apply       # Wirklich schreiben
"""
import sys
import os
import re
import io
from datetime import datetime, time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pytz

TZ = pytz.timezone("Europe/Berlin")
DRY_RUN = "--apply" not in sys.argv

# Fehlgeschlagene Buchungen vom 2026-02-06
FAILED_BOOKINGS = [
    {"customer": "Offermanns, Matthias", "date": "2026-02-12", "time": "11:00"},
    {"customer": "Schneider, Alexander", "date": "2026-02-23", "time": "11:00"},
    {"customer": "Mosch, Sebastian",     "date": "2026-02-12", "time": "11:00"},
]


def main():
    print("=" * 70)
    print("FAILED TRACKING RECOVERY")
    print(f"Mode: {'DRY-RUN (keine Aenderungen)' if DRY_RUN else 'LIVE — Daten werden geschrieben!'}")
    print("=" * 70)
    print()

    # Initialize Flask app context for services
    os.environ.setdefault('FLASK_ENV', 'production')
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.core.extensions import tracking_system
        if not tracking_system:
            print("FEHLER: Tracking-System nicht verfuegbar!")
            return

        print(f"Tracking-System initialisiert")
        print(f"{len(FAILED_BOOKINGS)} Buchungen zu recovern")
        print()

        recovered = 0
        for idx, booking in enumerate(FAILED_BOOKINGS, 1):
            print(f"[{idx}/{len(FAILED_BOOKINGS)}] {booking['customer']} @ {booking['date']} {booking['time']}")

            # Suche im Google Calendar
            event_data = find_calendar_event(
                tracking_system.service,
                booking["customer"],
                booking["date"],
                booking["time"]
            )

            if not event_data:
                print(f"  WARNUNG: Kein Calendar-Event gefunden!")
                continue

            print(f"  Event gefunden: color_id={event_data['color_id']}, user={event_data['user']}")

            # Duplikat-Check
            booking_id = f"{booking['date']}_{booking['time']}_{booking['customer']}".replace(" ", "_")
            if is_already_tracked(tracking_system, booking_id):
                print(f"  SKIP: Bereits getrackt (Duplikat)")
                continue

            if DRY_RUN:
                print(f"  DRY-RUN: Wuerde track_booking() aufrufen")
                recovered += 1
                continue

            # Track booking
            result = tracking_system.track_booking(
                customer_name=booking["customer"],
                date=booking["date"],
                time_slot=booking["time"],
                user=event_data["user"],
                color_id=event_data["color_id"],
                description=""
            )

            if result:
                print(f"  OK: Tracking nachgeholt")
                recovered += 1
            else:
                print(f"  FEHLER: track_booking() returned None")

        print()
        print(f"Ergebnis: {recovered}/{len(FAILED_BOOKINGS)} Buchungen recovered")

        # Dismiss admin notifications
        if not DRY_RUN and recovered > 0:
            dismiss_tracking_notifications()

        print()
        if DRY_RUN:
            print("DRY-RUN abgeschlossen. Zum Ausfuehren: python3 scripts/recover_failed_tracking.py --apply")


def find_calendar_event(service, customer_name, date_str, time_str):
    """Suche ein Event im Google Calendar anhand von Kunde + Datum + Zeit"""
    from datetime import datetime, timedelta

    CENTRAL_CALENDAR_ID = os.getenv("CENTRAL_CALENDAR_ID", "zentralkalenderzfa@gmail.com")

    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    start_time = TZ.localize(datetime.combine(event_date, time.min))
    end_time = TZ.localize(datetime.combine(event_date, time.max))

    try:
        events_result = service.events().list(
            calendarId=CENTRAL_CALENDAR_ID,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=100
        ).execute()

        events = events_result.get('items', [])

        # Nachname aus "Nachname, Vorname" extrahieren
        last_name = customer_name.split(",")[0].strip().lower()

        for event in events:
            summary = event.get("summary", "").lower()
            if last_name in summary:
                # Prüfe Zeit
                event_start = event.get("start", {}).get("dateTime", "")
                if event_start:
                    event_time = datetime.fromisoformat(event_start).strftime("%H:%M")
                    if event_time == time_str:
                        # Gefunden — extrahiere User aus Description
                        description = event.get("description", "")
                        user = extract_booked_by(description)
                        color_id = event.get("colorId", "2")

                        return {
                            "user": user,
                            "color_id": color_id,
                            "event_id": event.get("id"),
                            "summary": event.get("summary")
                        }

    except Exception as e:
        print(f"  Calendar API Fehler: {e}")

    return None


def extract_booked_by(description):
    """Extrahiere '[Booked by: username]' aus Event-Description"""
    if not description:
        return "unknown"
    match = re.search(r'\[Booked by:\s*([^\]]+)\]', description)
    if match:
        return match.group(1).strip().lower()
    return "unknown"


def is_already_tracked(tracking_system, booking_id):
    """Prüfe ob Booking bereits in JSONL oder PostgreSQL existiert"""
    # Check JSONL
    if os.path.exists(tracking_system.bookings_file):
        try:
            with open(tracking_system.bookings_file, "r", encoding="utf-8") as f:
                for line in f:
                    if booking_id in line:
                        return True
        except Exception:
            pass

    # Check PostgreSQL
    try:
        from app.models import Booking, is_postgres_enabled
        if is_postgres_enabled():
            from app.utils.db_utils import db_session_scope
            with db_session_scope() as session:
                existing = session.query(Booking).filter_by(booking_id=booking_id).first()
                if existing:
                    return True
    except Exception:
        pass

    return False


def dismiss_tracking_notifications():
    """Dismiss alle 'Tracking Failed' Notifications für Admins"""
    try:
        from app.services.notification_service import notification_service
        notifications = notification_service._load_all_notifications()

        dismissed_count = 0
        admin_users = ['alexander.nehm', 'david.nehm', 'simon.mast', 'luke.hoppe']

        for username in admin_users:
            user_notifs = notifications.get(username, [])
            for notif in user_notifs:
                if (notif.get('title', '') == 'Tracking Failed - Action Required'
                        and not notif.get('dismissed', False)):
                    # Prüfe ob diese Notification eine der 3 Failed-Bookings betrifft
                    msg = notif.get('message', '')
                    for fb in FAILED_BOOKINGS:
                        last_name = fb['customer'].split(',')[0].strip()
                        if last_name in msg:
                            notif['dismissed'] = True
                            notif['dismissed_at'] = datetime.now(TZ).isoformat()
                            dismissed_count += 1
                            break

        notification_service._save_all_notifications(notifications)
        print(f"  {dismissed_count} Notifications dismissed")

    except Exception as e:
        print(f"  WARNUNG: Notifications konnten nicht dismissed werden: {e}")


if __name__ == "__main__":
    main()
