import os, json, base64
from google.oauth2 import service_account

def load_google_credentials(scopes):
    """
    Lädt Google Service Account Credentials aus Umgebungsvariablen.

    Unterstützt:
      - GOOGLE_CREDS_BASE64  (Base64-encodetes JSON)
      - GOOGLE_CREDS_B64     (Base64-encodetes JSON, alternative Schreibweise)
      - GOOGLE_CREDS_JSON    (plain JSON-String)
      - GOOGLE_APPLICATION_CREDENTIALS (Pfad zur JSON-Datei - Fallback)
    """
    # Beide Base64-Namen akzeptieren
    b64 = os.getenv("GOOGLE_CREDS_BASE64") or os.getenv("GOOGLE_CREDS_B64")
    if b64:
        info = json.loads(base64.b64decode(b64).decode("utf-8"))
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)

    raw = os.getenv("GOOGLE_CREDS_JSON")
    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)

    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if path and os.path.exists(path):
        return service_account.Credentials.from_service_account_file(path, scopes=scopes)

    raise RuntimeError(
        "Google credentials not found. Set GOOGLE_CREDS_BASE64 / GOOGLE_CREDS_B64 / GOOGLE_CREDS_JSON or GOOGLE_APPLICATION_CREDENTIALS."
    )

