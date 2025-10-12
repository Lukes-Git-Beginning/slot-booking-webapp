# CLAUDE.md

Anleitungen für Claude Code bei der Arbeit mit diesem Repository.

## Projektübersicht

**Central Business Tool Hub** - Multi-Tool-Plattform mit Slot-Booking, T2-Closer-System und Analytics.

### Hauptkomponenten
- 🏠 **Central Hub**: Zentrale Navigation, Authentifizierung, Security Center (2FA)
- 🎯 **Slot-Booking**: Terminverwaltung, Gamification, Google Calendar-Integration
- 👥 **T2-Closer**: T2-Termin-Management
- 📊 **Analytics**: Business Intelligence über alle Tools

## Entwicklungskommandos

```bash
python run.py                    # Anwendung starten
python test_integration.py       # Tests ausführen
pip install -r requirements.txt  # Abhängigkeiten installieren
```

## 🚀 Deployment (WICHTIG!)

**Alle Änderungen NUR auf Hetzner-Testserver deployen!**

### Hetzner-Testserver
- **Server:** `91.98.192.233`
- **SSH-Key:** `~/.ssh/server_key`
- **App-Pfad:** `/opt/business-hub/`
- **URL:** http://91.98.192.233

### Deployment-Prozess

```bash
# 1. Datei übertragen
scp -i ~/.ssh/server_key <datei> root@91.98.192.233:/opt/business-hub/<pfad>

# 2. Service neu starten
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"

# 3. Logs prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"

# 4. Status prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub --no-pager"
```

### Wichtige Server-Pfade
```
/opt/business-hub/                    # Hauptverzeichnis
/opt/business-hub/app/                # Flask-App
/opt/business-hub/templates/          # Templates
/opt/business-hub/data/persistent/    # Daten
/var/log/business-hub/error.log       # Error-Logs
```

## Anwendungsarchitektur

```
app/
├── __init__.py           # Application Factory
├── config/               # Konfiguration
├── core/                 # Shared Infrastructure
│   ├── extensions.py
│   ├── google_calendar.py
│   └── cache_manager.py
├── routes/              # HTTP-Routes (Blueprints)
│   ├── hub.py           # Central Hub
│   ├── auth.py          # Authentifizierung
│   ├── security.py      # 2FA & Security
│   ├── admin/           # Admin-Features
│   ├── slots.py         # Slot-Booking
│   └── t2.py            # T2-Closer
└── services/            # Business Logic
    ├── data_persistence.py
    ├── security_service.py
    ├── achievement_system.py
    ├── booking_service.py
    └── holiday_service.py
```

### Wichtige Architektur-Patterns

**Datenspeicher:**
- **VPS:** `/opt/business-hub/data/persistent/` (Production)
- **Lokal:** `data/persistent/` (Development)
- Automatisches Backup-System
- UTF-8 JSON-Kodierung (`ensure_ascii=False`)

**Google Calendar:**
- Service Account-Auth via `GOOGLE_CREDS_BASE64`
- Robuste Fehlerbehandlung mit Retry-Logic
- Multi-Berater-Kalender-Support

**Feiertags-System:**
- Automatische NRW-Feiertage (`holidays` Package)
- Benutzerdefinierte Sperren via Admin-Interface

## Umgebungsvariablen

```bash
# Core (ERFORDERLICH)
SECRET_KEY=<key>
USERLIST=user:pass,user2:pass2
ADMIN_USERS=admin1,admin2

# Google Calendar (ERFORDERLICH für Slots)
GOOGLE_CREDS_BASE64=<base64>
CENTRAL_CALENDAR_ID=<email>
CONSULTANTS=name:email,name2:email2
```

## Wichtige Service-Klassen

```python
# Shared Services
from app.services.data_persistence import data_persistence
from app.services.security_service import security_service
from app.core.google_calendar import GoogleCalendarService
from app.core.extensions import cache_manager

# Slot-Booking Services
from app.services.achievement_system import achievement_system
from app.services.booking_service import BookingService
from app.services.holiday_service import holiday_service
```

## Best Practices

### Code-Qualität
- Flask Best Practices befolgen (Blueprints, Application Factory)
- Services für Business Logic, Routes für HTTP-Handling
- Type Hints verwenden
- Ordnungsgemäße Fehlerbehandlung mit Logging

### Datenpersistenz
```python
# Immer data_persistence verwenden
data_persistence.save_data('user_badges', badge_data)
user_data = data_persistence.load_data('user_stats', {})
data_persistence.create_backup()
```

### Feiertags-Integration
```python
from app.services.holiday_service import holiday_service

if holiday_service.is_blocked_date(check_date):
    reason = holiday_service.get_blocked_reason(check_date)
    return False, f"Datum gesperrt: {reason}"
```

### Neue Features hinzufügen

**Für bestehendes Tool:**
1. Service-Klasse in `app/services/` erstellen/erweitern
2. Route-Handler in `app/routes/` hinzufügen
3. Template in `templates/<tool>/` erstellen
4. Dokumentation aktualisieren

**Für neues Tool:**
1. Blueprint in `app/routes/<tool>.py` erstellen
2. Blueprint in `app/__init__.py` registrieren
3. Templates in `templates/<tool>/` erstellen
4. Tool zu Navigation hinzufügen (`get_available_tools()`)

## Debugging

```bash
# Google Calendar prüfen
python -c "from app.core.google_calendar import GoogleCalendarService; print('OK' if GoogleCalendarService().is_configured() else 'FAIL')"

# Datenintegrität prüfen
python -c "from app.services.data_persistence import data_persistence; data_persistence.verify_integrity()"

# Cache leeren
python -c "from app.core.extensions import cache_manager; cache_manager.clear_all()"
```

## Git Commit-Richtlinien
- **NIEMALS** Claude Code-Attribution einschließen
- **NIEMALS** "🤖 Generated with Claude Code" oder "Co-Authored-By: Claude"
- Konventionelles Format: `feat:`, `fix:`, `docs:`, `refactor:`

## Deployment-Checkliste
- [ ] Per SCP auf Hetzner-Server übertragen
- [ ] Service neu starten: `systemctl restart business-hub`
- [ ] Logs prüfen auf Fehler
- [ ] Funktionalität testen (http://91.98.192.233)
- [ ] Health-Check: `curl http://91.98.192.233/health`

## Sicherheit
- Niemals Zugangsdaten committen (`.env`, `service_account.json`)
- Benutzereingaben validieren
- 2FA-Secrets verschlüsselt speichern
- Rate Limiting für sensitive Endpoints
- Security-Events protokollieren

## Projektstatus

### Version: v4.0+ (Multi-Tool Hub)
- ✅ Central Hub Architecture
- ✅ Security Center (2FA + Password Management)
- ✅ T2-Closer Tool
- ✅ Vollständiges Gamification-System
- ✅ Analytics Dashboard
- ✅ VPS Deployment auf Hetzner

### Deployment-Status
- **Testserver:** http://91.98.192.233 ✅ LIVE
- **Production:** Go-Live in ~17 Tagen
