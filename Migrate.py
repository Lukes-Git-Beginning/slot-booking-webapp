import datetime
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request  # WICHTIG für Token-Refresh!

# ----------------- Konfiguration -----------------
CLIENT_SECRET_FILE = 'credentials.json'

OLD_CALENDAR_ID = '989b1f7cafbd2e77679dd48fff1f3d1317d6292a6ab97f01a84d2eb1659c595b@group.calendar.google.com'
NEW_CALENDAR_ID = 'zentralkalenderzfa@gmail.com'

SCOPES = ['https://www.googleapis.com/auth/calendar']
# -------------------------------------------------

ONLY_TWO_DIGITS_REGEX = re.compile(r"^\\d{2}$")  # Überspringt alle Platzhalter wie "01", "12", etc.

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
    Holt den Name-Teil ohne Status-Anhänge.
    Beispiel: 'T1 Patricia Seifert (erschienen)' => 'T1 Patricia Seifert'
    """
    return summary.split("–")[0].split("(")[0].strip().lower()

def events_are_equal(e1, e2):
    """
    Vergleicht Name + Startzeit und ignoriert Status-Anhänge.
    """
    name1 = extract_name(e1.get("summary", ""))
    name2 = extract_name(e2.get("summary", ""))
    time1 = e1.get("start", {}).get("dateTime", "")
    time2 = e2.get("start", {}).get("dateTime", "")
    return name1 == name2 and time1 == time2

def main():
    service = authenticate_google()
    now = datetime.datetime.utcnow()
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

    migrated, skipped, filtered, updated = 0, 0, 0, 0

    for new_ev in new_events:
        summary_new = new_ev.get("summary", "").strip()

        # Platzhalter überspringen
        if ONLY_TWO_DIGITS_REGEX.fullmatch(summary_new):
            filtered += 1
            print(f"Platzhalter übersprungen: {summary_new}")
            continue

        # Finde passendes Alt-Event (Name + Startzeit)
        matching_old = [o for o in old_events if events_are_equal(o, new_ev)]

        if matching_old:
            old_ev = matching_old[0]
            if old_ev['summary'] != new_ev['summary']:
                # Status hat sich geändert ➜ Alt löschen & neu anlegen
                service.events().delete(calendarId=OLD_CALENDAR_ID, eventId=old_ev['id']).execute()
                service.events().insert(calendarId=OLD_CALENDAR_ID, body=new_ev).execute()
                updated += 1
                print(f"Status geändert ➜ Alt gelöscht & neu angelegt: {new_ev['summary']}")
            else:
                skipped += 1
                print(f"Unverändert ➜ übersprungen: {summary_new}")
        else:
            # Alt fehlt ➜ neu anlegen
            service.events().insert(calendarId=OLD_CALENDAR_ID, body=new_ev).execute()
            migrated += 1
            print(f"Neu in ALT übertragen: {summary_new}")

    print("\\n--- MIGRATION FERTIG ---")
    print(f"Neu übertragen: {migrated} Termine")
    print(f"Status-Updates (ersetzt): {updated} Termine")
    print(f"Übersprungen (unverändert): {skipped} Termine")
    print(f"Gefiltert (Platzhalter): {filtered} Termine")

if __name__ == "__main__":
    main()
