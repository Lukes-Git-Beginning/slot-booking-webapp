import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

CLIENT_SECRET_FILE = 'credentials.json'
CENTRAL_CALENDAR_ID = 'zentralkalenderzfa@gmail.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']

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

def main():
    service = authenticate_google()
    now = datetime.datetime.utcnow()
    time_min = now.isoformat() + \"Z\"

    print(\"🔍 Suche doppelte Einträge im Zentralkalender ...\")

    all_events = service.events().list(
        calendarId=CENTRAL_CALENDAR_ID,
        timeMin=time_min,
        singleEvents=True,
        orderBy='startTime',
        maxResults=2500
    ).execute().get('items', [])

    seen = {}
    duplicates = []

    for ev in all_events:
        key = (ev['summary'].strip(), ev['start']['dateTime'])
        if key in seen:
            duplicates.append(ev)
        else:
            seen[key] = ev

    print(f\"✅ Gefundene Duplikate: {len(duplicates)}\")

    for dup in duplicates:
        service.events().delete(calendarId=CENTRAL_CALENDAR_ID, eventId=dup['id']).execute()
        print(f\"❌ Gelöscht: {dup['summary']} am {dup['start']['dateTime']}\")
    
    print(\"✔️ Fertig!\")

if __name__ == \"__main__\":
    main()
