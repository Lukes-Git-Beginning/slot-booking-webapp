import datetime
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request  # ✅ WICHTIG!

# ----------------- Konfiguration -----------------
CLIENT_SECRET_FILE = 'credentials.json'

OLD_CALENDAR_ID = '989b1f7cafbd2e77679dd48fff1f3d1317d6292a6ab97f01a84d2eb1659c595b@group.calendar.google.com'
NEW_CALENDAR_ID = 'zentralkalenderzfa@gmail.com'

SCOPES = ['https://www.googleapis.com/auth/calendar']
# -------------------------------------------------

ONLY_TWO_DIGITS_REGEX = re.compile(r"^\d{2}$")  # Überspringt alle Summaries wie "01", "12", etc.

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

def events_are_equal(e1, e2):
    return (
        e1.get("summary", "") == e2.get("summary", "") and
        e1.get("start", {}).get("dateTime", "") == e2.get("start", {}).get("dateTime", "")
    )

def main():
    service = authenticate_google()
    now = datetime.datetime.utcnow()
    time_min = now.isoformat() + "Z"

    print("Lese ALLE zukünftigen Termine aus dem alten Kalender aus...")
    old_events_result = service.events().list(
        calendarId=OLD_CALENDAR_ID,
        timeMin=time_min,
        singleEvents=True,
        orderBy='startTime',
        maxResults=2500
    ).execute()
    old_events = old_events_result.get('items', [])
    print(f"Gefundene Termine im alten Kalender: {len(old_events)}")

    print("Lese ALLE zukünftigen Termine aus dem neuen Kalender aus...")
    new_events_result = service.events().list(
        calendarId=NEW_CALENDAR_ID,
        timeMin=time_min,
        singleEvents=True,
        orderBy='startTime',
        maxResults=2500
    ).execute()
    new_events = new_events_result.get('items', [])
    print(f"Gefundene Termine im neuen Kalender: {len(new_events)}")

    migrated, skipped, filtered = 0, 0, 0

    for old_ev in old_events:
        summary = old_ev.get("summary", "").strip()
        # Filter: Nur echte Termine migrieren, keine Platzhalter mit nur zwei Ziffern
        if ONLY_TWO_DIGITS_REGEX.fullmatch(summary):
            filtered += 1
            print(f"Zwei-Ziffern-Platzhalter übersprungen: {summary}")
            continue

        duplicate = any(events_are_equal(old_ev, new_ev) for new_ev in new_events)
        if duplicate:
            skipped += 1
            continue

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
        print(f"Übertragen: {event_body['summary']} am {event_body['start'].get('dateTime', '')}")

    print("\n--- MIGRATION FERTIG ---")
    print(f"Übertragen: {migrated} Termine")
    print(f"Übersprungen (Duplikate): {skipped} Termine")
    print(f"Nicht migriert (nur 2-stellige Platzhalter): {filtered} Termine")

if __name__ == "__main__":
    main()
