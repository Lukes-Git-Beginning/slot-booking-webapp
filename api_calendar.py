# app/api_calendar.py  (oder: calendar_api.py)
import os, json, base64
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

bp = Blueprint("calendar_api", __name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
COLOR_MAP = {
    "1": "#7986cb", "2": "#33b679", "3": "#8e24aa", "4": "#e67c73", "5": "#f6c026",
    "6": "#f5511d", "7": "#039be5", "8": "#616161", "9": "#3f51b5", "10": "#0b8043", "11": "#d60000"
}

def load_credentials():
    # Variante A: Pfad in GOOGLE_APPLICATION_CREDENTIALS
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if path and os.path.exists(path):
        return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)

    # Variante B: Base64-JSON in GOOGLE_CALENDAR_CREDS_B64 (z.B. bei Render/GitHub Actions)
    b64 = os.getenv("GOOGLE_CALENDAR_CREDS_B64") or os.getenv("google_creds_json")
    if b64:
        data = json.loads(base64.b64decode(b64).decode("utf-8"))
        return service_account.Credentials.from_service_account_info(data, scopes=SCOPES)

    raise RuntimeError("Keine Google Credentials gefunden.")

def get_service():
    creds = load_credentials()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

@bp.route("/api/calendar/events")
def list_events():
    calendar_id = os.getenv("CENTRAL_CALENDAR_ID")
    if not calendar_id:
        return jsonify({"error": "CENTRAL_CALENDAR_ID not set"}), 500

    # FullCalendar schickt ?start=ISO&end=ISO (UTC). Fallback: ±30 Tage.
    start = request.args.get("start")
    end = request.args.get("end")
    try:
        if start and end:
            time_min = datetime.fromisoformat(start.replace("Z", "+00:00"))
            time_max = datetime.fromisoformat(end.replace("Z", "+00:00"))
        else:
            now = datetime.now(timezone.utc)
            time_min = now - timedelta(days=30)
            time_max = now + timedelta(days=30)
    except Exception:
        now = datetime.now(timezone.utc)
        time_min = now - timedelta(days=30)
        time_max = now + timedelta(days=30)

    svc = get_service()
    events = []
    page_token = None
    while True:
        resp = svc.events().list(
            calendarId=calendar_id,
            singleEvents=True,
            orderBy="startTime",
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=2500,
            pageToken=page_token
        ).execute()
        items = resp.get("items", [])
        for ev in items:
            # Start/End (ganztägig vs. zeitbasiert)
            start_dt = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
            end_dt   = ev.get("end", {}).get("dateTime")   or ev.get("end", {}).get("date")

            # Farbe (Google colorId → Hex)
            color = None
            color_id = ev.get("colorId")
            if color_id and color_id in COLOR_MAP:
                color = COLOR_MAP[color_id]

            # Titel
            title = ev.get("summary") or "(ohne Titel)"

            events.append({
                "id": ev.get("id"),
                "title": title,
                "start": start_dt,
                "end": end_dt,
                "color": color,
                "allDay": "date" in (ev.get("start") or {}),
                # Für spätere Nutzung im Frontend:
                "extendedProps": {
                    "organizer": (ev.get("organizer") or {}).get("email"),
                    "hangoutLink": ev.get("hangoutLink"),
                    "status": ev.get("status"),
                    "colorId": color_id
                }
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return jsonify(events)
