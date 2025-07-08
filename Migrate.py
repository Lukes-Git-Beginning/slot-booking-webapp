import datetime
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request  # Wichtig!

# ----------------- Konfiguration -----------------
CLIENT_SECRET_FILE = 'credentials.json'

OLD_CALENDAR_ID = '989b1f7cafbd2e77679dd48fff1f3d1317d6292a6ab97f01a84d2eb1659c595b@group.calendar.google.com'
NEW_CALENDAR_ID = 'zentralkalenderzfa@gmail.com'

SCOPES = ['https://www.googleapis.com/auth/calendar']
# -------------------------------------------------

ONLY_TWO_DIGITS_REGEX = re.compile(r"^\d{2}$")  # Überspringt Platzhalter wie "01", "12", etc.

def authenticate_google():
    creds = None
    try:
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    except Exception:
        pass

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def extract_name(summary):
    """
    Holt den Namen ohne Statusanhänge.
    Beispiel: 'Mustermann, Max – abgesagt' => 'Mustermann, Max'
    """
    return summary.split("–")[0].strip().lower()

def events_are_equal(e1, e2):
    """
    Vergleicht Name + Startzeit, ignoriert Statusanhänge.
    """
    name1 = extract_name(e1.get("summary", ""))
    name2 = extract_name(e2.get("summary", ""))
    time1 = e1.get("start", {}).get("dateTime", "")
    time2 = e2.get("start", {}).get("dateTime", "")
    return name1 == name2 and time1 == time2

def main():
    service = authenticate_google()
    now = datetime.datetime.utcnow()  # ⚠️ Deprecated, kannst du ersetzen mit datetime.datetime.now(datetime.UTC) falls gewünscht
    time_min = now.isoformat() + "Z"

    print("Lese ALLE zukünftigen Termine aus dem ALTEN Kalender aus...")
    old_events_result = service.events().list(
        calendarId=OLD_CALENDAR_ID,
        timeMin=time_min,
        singleEvents=True,
        orderBy='startTime',
        maxResults=2500
    ).execute()
    old_events = old_events_result.get('items', [])
    print(f"Gefundene Termine im ALTEN Kalender: {len(old_events)}")

    print("Lese ALLE zukünftigen Termine aus dem NEUEN Kalender aus...")
    new_events_result = service.events().list(
        calendarId=NEW_CALENDAR_ID,
        timeMin=time_min,
        singleEvents=True,
        orderBy='startTime',
        maxResults=2500
    ).execute()
    new_events = new_events_result.get('items', [])
    print(f"Gefundene Termine im NEUEN Kalender: {len(new_events)}")

    migrated, skipped, filtered, replaced = 0, 0, 0, 0

    for old_ev in old_events:
        summary = old_ev.get("summary", "").strip()

        if ONLY_TWO_DIGITS_REGEX.fullmatch(summary):
            filtered += 1
            print(f"Zwei-Ziffern-Platzhalter ➜ übersprungen: {summary}")
            continue

        # Finde eventuellen Match im neuen Kalender
        match = None
        for new_ev in new_events:
            if extract_name(summary) == extract_name(new_ev.get("summary", "")) and \
               old_ev.get("start", {}).get("dateTime", "") == new_ev.get("start", {}).get("dateTime", ""):
                match = new_ev
                break

        if match:
            if summary != match.get("summary", ""):
                # Status geändert ➜ Alt-Event löschen, Neu-Event ersetzen
                try:
                    service.events().delete(calendarId=NEW_CALENDAR_ID, eventId=match['id']).execute()
                    print(f"Status geändert ➜ Alt gelöscht: {summary}")
                except Exception as e:
                    print(f"⚠️  Konnte Alt nicht löschen: {summary} — Grund: {e}")
                try:
                    service.events().delete(calendarId=OLD_CALENDAR_ID, eventId=old_ev['id']).execute()
                    print(f"Status geändert ➜ ALT Kalender: Alt-Termin gelöscht: {summary}")
                except Exception as e:
                    print(f"⚠️  ALT Kalender: Alt-Termin konnte nicht gelöscht werden: {summary} — Grund: {e}")

                # Neu anlegen
                event_body = {
                    "summary": summary,
                    "start": old_ev.get("start"),
                    "end": old_ev.get("end"),
                    "description": old_ev.get("description", ""),
                    "location": old_ev.get("location", ""),
                    "colorId": old_ev.get("colorId", "9"),
                }
                if "attendees" in old_ev:
                    event_body["attendees"] = old_ev["attendees"]

                service.events().insert(calendarId=NEW_CALENDAR_ID, body=event_body).execute()
                replaced += 1
                print(f"Status geändert ➜ Neu angelegt: {summary}")
            else:
                skipped += 1
                print(f"Unverändert ➜ übersprungen: {summary}")
        else:
            # Neuer Termin ➜ übertragen
            event_body = {
                "summary": summary,
                "start": old_ev.get("start"),
                "end": old_ev.get("end"),
                "description": old_ev.get("description", ""),
                "location": old_ev.get("location", ""),
                "colorId": old_ev.get("colorId", "9"),
            }
            if "attendees" in old_ev:
                event_body["attendees"] = old_ev["attendees"]

            service.events().insert(calendarId=NEW_CALENDAR_ID, body=event_body).execute()
            migrated += 1
            print(f"Neu ➜ übertragen: {summary} am {event_body['start'].get('dateTime', '')}")

    print("\n--- MIGRATION FERTIG ---")
    print(f"Übertragen (neu): {migrated}")
    print(f"Übersprungen (unverändert): {skipped}")
    print(f"Status geändert & ersetzt: {replaced}")
    print(f"Nicht migriert (Platzhalter): {filtered}")

if __name__ == "__main__":
    main()