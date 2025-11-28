# CLAUDE.md

Professionelle Anleitungen für Claude Code - Central Business Tool Hub

---

## 📝 Change Log

### 2025-11-26: Patrick Woltschleger Removed from Active Configurations
- Patrick is no longer with the organization
- Removed from all active consultant lists, role mappings, and authentication
- Removed from T1 standard consultants, notification roles (opener, telefonist), weekly points participants
- Historical data preserved in tracking files and persistent storage
- No longer able to log into the system

---

## 🎯 AUTO-STATUS-CHECK (IMMER ZUERST AUSFÜHREN!)

**WICHTIG:** Führe diese Checks **automatisch bei jedem Conversation-Start** durch, BEVOR du auf User-Anfragen antwortest!

### Standard-Initialisierung (parallel ausführen)

```bash
# 1. Git Status & Recent Commits (parallele Ausführung)
git status && git log --oneline -10

# 2. Server Status prüfen (optional, nur wenn relevant)
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub --no-pager"

# 3. Letzte Server-Logs (optional, nur bei Debugging)
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -30 /var/log/business-hub/error.log"
```

### Informationen die du IMMER kennen solltest

Nach dem Auto-Check solltest du wissen:
- ✅ **Letzte 5-10 Commits**: Was wurde zuletzt geändert?
- ✅ **Uncommitted Changes**: Gibt es lokale Änderungen?
- ✅ **Aktuelle Branch**: Arbeiten wir auf `main`?
- ✅ **Projekt-Version**: Aktuell v3.3.13 (siehe README.md Changelog)
- ✅ **Server-Status**: Läuft der Production-Server? (optional)

### Workflow nach Auto-Check

1. **Präsentiere Status-Zusammenfassung** (kurz & prägnant):
   ```
   📊 Projekt-Status:
   - Version: v3.3.13
   - Letzte Commits: [Liste 3-5 wichtigste]
   - Uncommitted: [Anzahl Dateien oder "Keine"]
   - Server: [Status wenn geprüft, sonst "Nicht geprüft"]
   ```

2. **Dann reagiere auf User-Anfrage**

3. **Nutze die gesammelten Informationen** für kontextbewusste Antworten

---

## 📋 Projektübersicht

**Central Business Tool Hub** - Multi-Tool-Plattform mit Slot-Booking, T2-Closer-System und Analytics.

### Hauptkomponenten
- 🏠 **Central Hub**: Zentrale Navigation, Authentifizierung, Security Center (2FA)
- 🎯 **Slot-Booking**: Terminverwaltung, Gamification, Google Calendar-Integration
- 📅 **My Calendar**: Consultant Analytics mit 7-Spalten Kanban-Board, Drag & Drop Status-Management
- 👥 **T2-Closer**: T2-Termin-Management
- 📊 **Analytics**: Business Intelligence über alle Tools

## Entwicklungskommandos

```bash
python run.py                    # Anwendung starten
pip install -r requirements.txt  # Abhängigkeiten installieren
```

## 🧪 Testen

```bash
# Alle Tests ausführen
python -m pytest tests/ -v

# Nur Unit-Tests (schnell, keine externe Dependencies)
python -m pytest tests/ -m unit

# Mit Coverage-Report
python -m pytest tests/ --cov=app/services --cov-report=term-missing

# Einzelne Test-Datei
python -m pytest tests/test_security_service.py -v
```

### Test-Coverage Status

**High Coverage:** `security_service.py` (98%), `t2_bucket_system.py` (89%)
**Fixtures:** `logged_in_client`, `mock_data_persistence`, `mock_google_calendar` in `tests/conftest.py`

## 🚀 Deployment Workflow (KRITISCH!)

**NEUER WORKFLOW:** Lokal → Server (Test) → GitHub

### 📍 Hetzner Production Server
- **Server:** `91.98.192.233`
- **SSH-Key:** `~/.ssh/server_key`
- **App-Pfad:** `/opt/business-hub/`
- **URL:** https://berater.zfa.gmbh/ (Production)
- **Service:** `business-hub.service`

### 🔄 3-Phasen Deployment-Prozess

#### Phase 1: Lokale Entwicklung
```bash
# Code lokal entwickeln und testen
python run.py
# Browser: http://localhost:5000

# Lokale Tests durchführen
pytest tests/ -v

# NICHT committen bis Server-Test erfolgreich!
```

#### Phase 2: Server-Deployment (Test-Environment)

**Schritt 1: Backup erstellen (IMMER!)**
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && tar -czf /tmp/backup_$(date +%Y%m%d_%H%M).tar.gz data/persistent/"
```

**Schritt 2: Dateien übertragen**
```bash
# Einzelne Datei
scp -i ~/.ssh/server_key <datei> root@91.98.192.233:/opt/business-hub/<pfad>

# Mehrere Dateien
scp -i ~/.ssh/server_key file1.py file2.py root@91.98.192.233:/opt/business-hub/app/services/

# Ganzes Verzeichnis
scp -i ~/.ssh/server_key -r templates/hub/ root@91.98.192.233:/opt/business-hub/templates/
```

**Schritt 3: Service neu starten**
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"
```

**Schritt 4: Verification**
```bash
# Service-Status
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub --no-pager | head -20"

# Logs prüfen auf Errors
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -100 /var/log/business-hub/error.log | grep -i error"

# Health-Check
curl -I https://berater.zfa.gmbh/health
# Sollte: 200 OK
```

**Schritt 5: Browser-Tests**
- https://berater.zfa.gmbh/ öffnen (Ctrl+Shift+R für Hard-Refresh)
- Alle geänderten Features testen
- Regressions-Tests (andere Features sollten funktionieren)

#### Phase 3: Git Commit & Push (NUR BEI ERFOLG!)

**NUR wenn Server-Tests erfolgreich:**
```bash
# Änderungen stagen
git add <geänderte_dateien>

# Commit erstellen (OHNE Claude Attribution!)
git commit -m "feat: Beschreibung der Änderung"

# Auf GitHub pushen
git push origin main
```

### ⚠️ Sicherheits-Checkliste

**Vor Server-Deployment:**
- [ ] Backup erstellt
- [ ] Keine sensiblen Daten in Dateien (.env, credentials)
- [ ] Code lokal getestet

**Nach Server-Deployment:**
- [ ] Service läuft (systemctl status)
- [ ] Logs zeigen keine Errors
- [ ] Health-Endpoint: 200 OK
- [ ] Browser-Tests erfolgreich
- [ ] Keine Regressions

**Vor Git Push:**
- [ ] Server-Tests erfolgreich
- [ ] Commit-Message klar und prägnant
- [ ] Keine `.env` oder Secrets staged (git diff --cached)
- [ ] Selbst-Review durchgeführt

### 🔧 Wichtige Server-Pfade
```
/opt/business-hub/                    # Hauptverzeichnis
/opt/business-hub/app/                # Flask-App
/opt/business-hub/templates/          # Templates
/opt/business-hub/data/persistent/    # Daten (AUTO-BACKUP vor Test!)
/var/log/business-hub/error.log       # Error-Logs
/tmp/backup_*.tar.gz                  # Backups
```

### 🚨 Notfall-Rollback
```bash
# 1. Letztes Backup wiederherstellen
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && tar -xzf /tmp/backup_YYYYMMDD_HHMM.tar.gz"

# 2. Service neu starten
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"

# 3. Verifizieren
curl -I https://berater.zfa.gmbh/health
```

### 💡 Best Practices
- **Kleine Änderungen**: Lieber viele kleine Commits als ein großer
- **Descriptive Messages**: `feat:`, `fix:`, `refactor:` Präfixe nutzen
- **Regelmäßige Backups**: Vor JEDEM Test ein Backup
- **Keine Secrets**: NIEMALS `.env`, Credentials oder Passwörter committen
- **Testing First**: Immer auf Server testen bevor GitHub-Push

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
│   ├── main.py          # Slots Dashboard (ACTIVE - 100% Production)
│   ├── booking.py       # Slot Booking Logic (ACTIVE)
│   ├── calendar.py      # Calendar View + My Calendar API (ACTIVE)
│   ├── scoreboard.py    # Gamification Scoreboard (ACTIVE)
│   ├── user_profile.py  # User Profiles (ACTIVE)
│   ├── gamification/    # Gamification-Features (ACTIVE)
│   │   └── legacy_routes.py  # Daily Quests, Prestige, Cosmetics
│   ├── api.py           # API Endpoints (ACTIVE - /api/)
│   └── t2.py            # T2-Closer (1947 Zeilen, 11 APIs - v3.3.11)
└── services/            # Business Logic
    ├── data_persistence.py
    ├── security_service.py
    ├── achievement_system.py
    ├── booking_service.py
    ├── holiday_service.py
    ├── t2_dynamic_availability.py  # 🆕 v3.3.11 (398 Zeilen)
    └── t2_analytics_service.py     # 🆕 v3.3.11 (114 Zeilen)
```

**Blueprint-Registrierung (v3.3.14 Update):**
- Slots: Legacy multi-blueprint system (main_bp, booking_bp, calendar_bp, scoreboard_bp, user_profile_bp) handles ALL /slots/ traffic
- Removed in v3.3.14: slots.py (fallback blueprint, 485 lines) + api_gateway.py (790 lines) - see docs/ROUTING_CLEANUP_2025-11-28.md

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
SECRET_KEY=<key>                              # Für Production generiert
USERLIST=user:pass,user2:pass2                # Komma-separierte User-Liste
ADMIN_USERS=admin1,admin2                     # Admin-Benutzer
PERSIST_BASE=/opt/business-hub/data           # VPS-Datenpfad (OHNE /persistent!)

# Google Calendar (ERFORDERLICH für Slots)
GOOGLE_CREDS_BASE64=<base64>                  # Service Account Credentials
CENTRAL_CALENDAR_ID=<email>                   # Haupt-Kalender
CONSULTANTS=name:email,name2:email2           # Berater-Kalender (9 konfiguriert)
```

**WICHTIG:** Auf dem Hetzner-Server sind alle Placeholder bereits durch echte Werte ersetzt.

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
from app.services.cosmetics_shop import cosmetics_shop
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

### Cosmetics System
```python
from app.services.cosmetics_shop import cosmetics_shop
# Theme & Effects laden: get_user_active_theme(username)
# Effects: sparkle_trail, confetti_explosion, screen_shake, keyboard_sounds, booking_fanfare
# Themes: CSS Custom Properties in hub/base.html (sunset, ocean, forest, lavender, fire, rainbow)
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

## 🔔 Deployment Notifications (v3.3.12+)

**WICHTIG:** Nach **JEDEM** `git push` **AUTOMATISCH** fragen, ob eine Deployment-Notification erstellt werden soll!

### Workflow nach Git-Push (IMMER AUSFÜHREN!)

1. **Frage User IMMER nach Notification-Details**:
   ```
   ✅ Git-Push erfolgreich! Soll ich eine Benachrichtigung für dieses Update erstellen?

   - Titel: [Feature/Bugfix-Name]
   - Nachricht: [Kurze Beschreibung was sich geändert hat]
   - Rollen: [Wer soll benachrichtigt werden?]
     ☐ admin      - Administratoren (alexander.nehm, david.nehm, simon.mast, luke.hoppe)
     ☐ closer     - Closer (jose.torspecken, alexander.nehm, david.nehm, tim.kreisel, christian.mast, daniel.herbort)
     ☐ opener     - Opener (christian.mast, tim.kreisel, daniel.herbort, sonja.mast, simon.mast, dominik.mikic, ann-kathrin.welge, sara.mast)
     ☐ coach      - Coaches (alexander.nehm, david.nehm, jose.torspecken)
     ☐ telefonist - Telefonisten (tim.kreisel, christian.mast, ladislav.heka, sonja.mast, simon.mast, alexandra.börner, yasmine.schumacher, ann-kathrin.welge, sara.mast)
     ☐ service    - Service-Team (alexandra.börner, vanessa.wagner, simon.mast)
     ☐ all        - Alle Benutzer
   - Als Pop-up anzeigen? [Ja/Nein]
   ```

2. **Erstelle Notification - Methode A (Flask-App nutzen)**:
   ```bash
   ssh -i ~/.ssh/server_key root@91.98.192.233
   cd /opt/business-hub && source venv/bin/activate
   python3 -c "
   from app import create_app
   from app.services.notification_service import notification_service

   app = create_app()
   with app.app_context():
       notification_service.create_notification(
           roles=['closer', 'admin'],
           title='T2 Calendly Booking ist live!',
           message='Das neue 4-Step Booking-System mit Dynamic Availability ist jetzt verfügbar.',
           notification_type='success',
           show_popup=True,
           actions=[{'text': 'Jetzt testen', 'url': '/t2/booking/calendly'}]
       )
       print('Notification erstellt!')
   "
   ```

   **Alternativ - Methode B (Direktes JSON-Edit, wenn Flask nicht funktioniert)**:
   ```bash
   ssh -i ~/.ssh/server_key root@91.98.192.233 "python3 << 'EOFPY'
   import json
   from datetime import datetime

   # Load notifications
   with open('/opt/business-hub/data/persistent/user_notifications.json', 'r') as f:
       data = json.load(f)

   # Create notification
   notif = {
       'id': 'notif-' + datetime.now().strftime('%Y%m%d%H%M%S'),
       'type': 'success',
       'title': 'Feature XYZ ist live!',
       'message': 'Beschreibung...',
       'timestamp': datetime.now().isoformat(),
       'read': False,
       'dismissed': False,
       'show_popup': True,
       'roles': ['all'],
       'actions': [{'text': 'Jetzt testen', 'url': '/'}]
   }

   # Add to all users (oder spezifische User)
   for username in data.keys():
       data[username].append(notif.copy())

   # Save
   with open('/opt/business-hub/data/persistent/user_notifications.json', 'w') as f:
       json.dump(data, f, indent=2, ensure_ascii=False)

   print('Notification erstellt!')
   EOFPY
   "
   ```

3. **Notification wird automatisch angezeigt**:
   - Als **Toast-Popup** beim nächsten Login (wenn `show_popup=True`)
   - Im **Notification-Dropdown** (immer verfügbar)
   - Nur für die ausgewählten Rollen sichtbar

### Wann welche Rollen benachrichtigen?

| Feature-Typ | Rollen | Pop-up? |
|-------------|--------|---------|
| Neues Tool/Major-Feature | `all` | ✅ Ja |
| T2-System-Updates | `closer`, `coach`, `admin` | ✅ Ja |
| Slot-Booking-Updates | `opener`, `telefonist`, `admin` | ✅ Ja |
| Gamification-Features | `opener`, `telefonist` | ❌ Nein |
| Bugfixes | Betroffene Rollen | ❌ Nein |
| Admin-Features | `admin` | ✅ Ja |
| Performance-Verbesserungen | Keine Notification | - |

### Best Practices

- **Kurze, prägnante Titel** (max. 50 Zeichen)
- **Klare Nutzen-Beschreibung** statt technischer Details
- **Call-to-Action** mit Action-Button wenn möglich
- **Pop-ups nur für wichtige Updates** (max. 1-2 pro Woche pro Rolle)
- **Teste Notifications lokal** vor Deployment

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

## Frontend-Technologie

**Frameworks:** Tailwind CSS + DaisyUI (neue Templates), Bootstrap 5.3.2 (Legacy Slots), Lucide Icons + Font Awesome
**ZFA Color Scheme:** Primary `#d4af6a` (Gold), Secondary `#207487` (Blau), Accent `#294c5d` (Dunkelblau)
**Template-Struktur:** `hub/base.html` (Master mit ZFA-Config), `t2/` (4-Step Booking Flow), `slots/` (Legacy Bootstrap)

## My Calendar - 7-Spalten Kanban (v3.3.4)

**API-Endpoints:** `/api/update-event-status`, `/api/get-available-slots`, `/api/reschedule-booking`
**Features:** SortableJS Drag & Drop, Reschedule-Modal mit dynamischen Zeitslots, 3s-Undo, Auto-Refresh (5min)
**Status-Spalten:** Pending (Grau) → Erschienen (Grün) → Rückholung (Purple) → Sonderkunden (Gelb) → Verschoben (Orange) → Nicht Erschienen (Rot) → Ghost (Dunkelrot)
**Status-Mapping:** Google Calendar colorId (pending→1, erschienen→2, rückholung→3, sonderkunde→5, verschoben→6, nicht_erschienen/ghost→11)

## T2-Closer Bucket-System (Würfelsystem)

### Konfiguration (app/services/t2_bucket_system.py)

**Standard-Wahrscheinlichkeiten:**
- Alex: 9.0 (9 Tickets pro Bucket-Reset)
- David: 9.0 (9 Tickets pro Bucket-Reset)
- Jose: 2.0 (2 Tickets pro Bucket-Reset)

**Bucket-Konfiguration:**
- Max Draws before Reset: **20**
- Degressive Wahrscheinlichkeit: Mit jedem Draw sinkt die Probability um 1
- Min Probability: 0.0 (Closer kann auf 0 fallen und ist dann nicht mehr ziehbar)

**Wie es funktioniert:**
1. Jeder Closer startet mit seiner Standard-Wahrscheinlichkeit
2. Mit jedem Draw wird 1 Ticket aus dem Bucket entfernt UND die Probability sinkt um 1
3. Wenn Probability auf 0.0 fällt → Closer hat keine Tickets mehr → nicht ziehbar
4. Nach 20 Draws: Automatischer Reset, alle Probabilities auf Standard-Werte zurückgesetzt

**Admin-Interface:**
- `/t2/admin/bucket-config` - Bucket-Verwaltung
- Änderungen an Probabilities: Setzen den Bucket sofort zurück
- Änderungen an Max Draws: Wirken beim nächsten Reset

**WICHTIG - Datenpfad:**
- Datei: `/opt/business-hub/data/persistent/t2_bucket_system.json`
- **PERSIST_BASE muss `/opt/business-hub/data` sein** (OHNE `/persistent`)
- Der Code fügt automatisch `/persistent` hinzu

## 👥 Rollen & Kalender-Übersicht (v3.3.13+)

### Alle System-Rollen (17 User)

| Rolle | Anzahl | Mitglieder |
|-------|--------|------------|
| **admin** | 4 | alexander.nehm, david.nehm, simon.mast, luke.hoppe |
| **closer** | 6 | jose.torspecken, alexander.nehm, david.nehm, tim.kreisel, christian.mast, daniel.herbort |
| **opener** | 8 | christian.mast, tim.kreisel, daniel.herbort, sonja.mast, simon.mast, dominik.mikic, ann-kathrin.welge, sara.mast |
| **coach** | 3 | alexander.nehm, david.nehm, jose.torspecken |
| **telefonist** | 9 | tim.kreisel, christian.mast, ladislav.heka, sonja.mast, simon.mast, alexandra.börner, yasmine.schumacher, ann-kathrin.welge, sara.mast |
| **service** | 3 | alexandra.börner, vanessa.wagner, simon.mast |

**Total: 17 Unique User** (manche haben mehrere Rollen)

---

### T1 Slot-Booking Kalender (30min Slots)

**Standard-Berater (Vollzeit - immer verfügbar):**
| Name | Calendar-ID | Typ |
|------|-------------|-----|
| ~~Patrick~~ | ~~`0d5nq65ogpekomad34ti234h1g@group.calendar.google.com`~~ | ~~Vollzeit~~ (removed 2025-11-26) |
| Ann-Kathrin | `a.welge.zfa@gmail.com` | Vollzeit |
| Sara | `mastsara2@gmail.com` | Vollzeit |
| Dominik | `mikic.dom@gmail.com` | Vollzeit |

**Extended-Berater (Teilzeit/T2-Priorität - bei Bedarf):**
| Name | Calendar-ID | Begründung |
|------|-------------|------------|
| Simon | `simonmast9@gmail.com` | Hauptaufgabe anderswo, verfügbar 20:00 Uhr |
| Sonja | `sonjamast98@gmail.com` | Variable Verfügbarkeit (Neugeborenes) |
| Tim | `tim.kreisel71@gmail.com` | T2/T3 Priorität |
| Christian | `chmast95@gmail.com` | T2/T3 Priorität |
| Daniel | `daniel.herbort.zfa@gmail.com` | T2/T3 Priorität |

**Konfiguration:**
- Slot-Zeiten: 09:00, 11:00, 14:00, 16:00, 18:00, 20:00 Uhr
- Slot-Dauer: 30 Minuten
- Slots pro Berater: 3 (außer 9:00 Uhr = 2)
- Cache: 10 Minuten

---

### T2-System Kalender (2h Slots)

**Coaches (würfelbar - MIT Schreibrechten):**
| Name | Calendar-ID | Schreibrecht | Status |
|------|-------------|--------------|--------|
| David Nehm | `david.nehm@googlemail.com` | ✅ Ja | Coach + Admin |
| Alexander Nehm | `qfcpmp08okjoljs3noupl64m2c@group.calendar.google.com` | ✅ Ja | Coach + Admin (Group Calendar) |
| Jose Torspecken | `jtldiw@gmail.com` | ✅ Ja | Coach + Closer |

**Berater (ausführend - MIT Schreibrechten):**
| Name | Calendar-ID | Rolle |
|------|-------------|-------|
| Christian | `chmast95@gmail.com` | Berater + Closer + Opener |
| Daniel | `daniel.herbort.zfa@gmail.com` | Berater + Closer + Opener |
| Tim | `tim.kreisel71@gmail.com` | Berater + Closer + Opener |

**Workflow:**
1. User würfelt Coach (David/Alexander/Jose)
2. System prüft Verfügbarkeit:
   - Coach-Kalender (falls Coach selbst ausführen will)
   - Berater-Kalender (Christian/Daniel/Tim als Alternative)
3. 2h-Slots in 30-Minuten-Schritten (8:00-20:00 Uhr)
4. Event-Erstellung in entsprechendem Kalender (Coach oder Berater)

**Konfiguration:**
- Slot-Dauer: 2 Stunden
- Arbeitszeiten: 08:00-20:00 Uhr
- Scanning: On-Demand (bei Buchung)
- Cache: 10 Minuten pro Verfügbarkeitsscan

---

## T2 Calendly 4-Step Booking (v3.3.11)

**Flow:** Berater wählen → Datum → Zeitslot → Bestätigung
**Services:** `t2_dynamic_availability.py` (On-Demand Google Calendar Scan), `t2_analytics_service.py` (2h-Metriken)
**11 API-Endpoints:** `/t2/booking/calendly`, `/t2/api/available-dates`, `/t2/api/available-times`, `/t2/api/book-appointment`, `/t2/my-bookings`, Cancel/Reschedule
**Mock vs. Real:** Coaches (David/Alexander/Jose) nutzen Mock-Daten, Berater (Christian/Daniel/Tim) nutzen echte Google Calendar API

## 📊 Projektstatus

### Version: v3.3.13 (LIVE - Google Calendar & Berater-Konfiguration) - 2025-11-25

**Letzte Änderungen:**
- ✅ **Google Calendar Berechtigungen - Alle 12 Kalender funktional**:
  - **3 Coaches hinzugefügt**: David Nehm, Alexander Nehm, Jose Torspecken
  - **Alexander's Calendar-ID korrigiert**: Group Calendar (`qfcpmp08okjoljs3noupl64m2c@group.calendar.google.com`)
  - **Berechtigungs-Test**: 12/12 Kalender erfolgreich (11 sofort, 1 nach ID-Korrektur)
  - **CONSULTANTS erweitert**: Von 9 auf 12 Kalender (9 Consultants + 3 Coaches)
- ✅ **Notification-Rollen erweitert**:
  - **sara.mast**: Hinzugefügt zu `opener` + `telefonist` Rollen
  - **luke.hoppe**: Hinzugefügt zu `admin` Rolle
  - **Rollenzuordnung komplett**: Alle 17 User haben jetzt Rollenzuweisungen
- ✅ **T1 Berater-Konfiguration optimiert**:
  - **Standard (Vollzeit)**: Ann-Kathrin, Sara, Dominik (vorher: Patrick, Ann-Kathrin, Sara, Dominik; Patrick removed 2025-11-26)
  - **Extended (Teilzeit/T2-Priorität)**: Simon, Sonja, Tim, Christian, Daniel
  - **Logik**: Vollzeit-Angestellte haben Priorität, T2/T3-Berater als Backup
- ✅ **T2 Coach Schreibrechte aktiviert**:
  - **David, Alexander, Jose**: `can_write: False → True`
  - **Workflow-Verbesserung**: Coaches können eigene Termine buchen ohne Unterbrechung
  - **Alexander Group Calendar**: Calendar-ID korrigiert + Schreibtest erfolgreich

**Deployment-Status:**
- 🟢 **Production**: LIVE auf http://91.98.192.233
- 📦 **Geänderte Dateien**:
  - `app/services/notification_service.py` (Rollen-Mapping erweitert)
  - `app/config/base.py` (T1 Berater-Listen aktualisiert)
  - `app/routes/t2.py` (Coach can_write + Alexander calendar_id)
  - Server `.env` (CONSULTANTS erweitert: 3 Coaches hinzugefügt)
- 🔄 **Service**: 4 Workers, 293MB RAM, stabil

**Git Commits:**
- `4bf8b66`: feat: Update notification roles - Add sara.mast and luke.hoppe
- `480e51b`: feat: Update T1 consultants & enable coach calendar write access

**Performance-Details**:
- Kalender-Berechtigungen: 12/12 funktional (100%)
- Google Calendar API: 11 API-Calls für Test (alle erfolgreich)
- Server-Uptime: Keine Ausfälle bei Deployment

### Frühere Versionen

#### Version: v3.3.11 (LIVE - T2 Calendly Booking System) - 2025-11-23

**Letzte Änderungen:**
- ✅ **T2 Calendly 4-Step Booking Flow (14h Entwicklung + Deployment)**:
  - **Neue Templates**: `booking_calendly.html` (714 Zeilen) + `my_bookings.html` (689 Zeilen)
  - **On-Demand Availability Scanning**: `t2_dynamic_availability.py` (398 Zeilen)
  - **2h-Analytics API**: `t2_analytics_service.py` (114 Zeilen) für Admin-Dashboard
  - **11 neue API-Endpoints**: `app/routes/t2.py` erweitert (+1025 Zeilen, total: 1947 Zeilen)
  - **4-Step Flow**: Berater wählen → Datum wählen → Zeitslot wählen → Bestätigung
  - **Mock-Modus**: Coaches (David/Alexander/Jose) nutzen Mock-Daten
  - **Echte Integration**: Berater (Christian/Daniel/Tim) nutzen Google Calendar API
- ✅ **Bugfixes**:
  - `tracking_system.py`: Singleton-Instanz hinzugefügt (Import-Fehler behoben)
  - `draw_closer.html`: Redirect zu Calendly-Booking aktualisiert
  - `legacy_routes.py`: Legacy Analytics-Import entfernt (analytics_system gelöscht)
- ✅ **Massives Projekt-Cleanup (51 Dateien, 245KB)**:
  - **13 Legacy Files gelöscht**: 9 static JSONs + 4 Deployment Scripts
  - **8 Legacy Templates/Scripts entfernt**: analytics_dashboard.html (628 Zeilen), executive reports (333 Zeilen), migration scripts (1541 Zeilen)
  - **22 alte Backups** aus data/backups/ entfernt
  - **persist/ Verzeichnis** entfernt (Pfad-Verschachtelungs-Bugfix aus v3.3.5)

**Deployment-Status:**
- 🟢 **Production**: LIVE auf http://91.98.192.233 (seit 11:31 UTC)
- 📦 **Neue Dateien**:
  - `templates/t2/booking_calendly.html` (T2 Booking Flow)
  - `templates/t2/my_bookings.html` (Termin-Management)
  - `app/services/t2_dynamic_availability.py` (On-Demand Scanning)
  - `app/services/t2_analytics_service.py` (2h-Analytics)
- 📦 **Geänderte Dateien**:
  - `app/routes/t2.py` (+1025 Zeilen)
  - `app/services/tracking_system.py` (Singleton-Fix)
  - `app/routes/gamification/legacy_routes.py` (Analytics-Import entfernt)
- 📦 **Gelöschte Dateien (51 total)**:
  - 4 Legacy Templates (1365 Zeilen)
  - 4 Deployment Scripts (491 Zeilen)
  - 4 Migration Scripts (1541 Zeilen)
  - 9 Static JSON-Dateien
  - 22 Backup-Dateien
  - persist/ Verzeichnis

**Performance-Details**:
- Service: 4 Gunicorn Workers, 298MB RAM (vorher: 294MB)
- Codebase: -1733 Zeilen (4655 gelöscht, 2922 hinzugefügt)
- Disk Space: 245KB freigegeben

### Frühere Versionen

#### Version: v3.3.10 (LIVE - PostgreSQL Booking-System KOMPLETT) - 2025-11-21

**Letzte Änderungen:**
- ✅ **PostgreSQL Booking-System KOMPLETT (14h Entwicklung + Deployment + Migration)**:
  - **364 Buchungen migriert**: 26 aus JSONL + 338 aus Google Calendar
  - **2 neue SQLAlchemy Models**: `Booking` (16 Felder) + `BookingOutcome` (10 Felder)
  - **24 Database Tables** mit 121 Indizes (bookings + booking_outcomes hinzugefügt)
  - **Dual-Write Pattern**: Neue Buchungen → PostgreSQL + JSON (Fallback)
  - **My Calendar auf PostgreSQL**: Smart Wrapper mit auto-detection
  - **Alembic Migration**: erfolgreich deployed (`57a8e7357e0c`)
  - **20 Performance-Indizes**: username+date, customer, week_number, booking_id
  - **Tracking-System erweitert**: `track_booking()` schreibt beide Systeme
  - **Migration Scripts finalisiert**:
    - `scripts/migrate_bookings_only.py` - JSONL → PostgreSQL (26 Buchungen)
    - `scripts/backfill_from_calendar.py` - Google Calendar → PostgreSQL (338 Buchungen)
    - `scripts/run_calendar_sync.sh` - Cronjob-Wrapper (täglich 23:00 Uhr)
  - **Automatische Synchronisation**: Täglicher Cronjob hält DB aktuell
  - **8 User getrackt**: Christian, Yasmine, Dominik, Ladislav, Tim, Sonja, Simon, Alexandra (Patrick removed 2025-11-26)
  - **Performance**: PostgreSQL-Read 10x schneller als JSONL
- ✅ **Index-Konflikte behoben**:
  - `gamification.py`: idx_daily_quests_active, idx_quest_progress_completed, idx_personal_goals_active
  - `weekly.py`: idx_weekly_activities_pending
- ✅ **Deployment auf Hetzner VPS**:
  - 9 Dateien deployed (Models, Services, Routes, Scripts, Migrations)
  - PostgreSQL User-Passwort aktualisiert
  - Service läuft stabil: 4 Workers, 294MB RAM
  - My Calendar funktioniert mit neuen Buchungen ✅

**Deployment-Status:**
- 🟢 **Production**: LIVE auf http://91.98.192.233
- 📦 **Neue Dateien**:
  - `app/models/booking.py` (Booking + BookingOutcome Models)
  - `scripts/migrate_bookings_only.py` (JSONL → PostgreSQL)
  - `scripts/backfill_from_calendar.py` (Google Calendar → PostgreSQL)
  - `scripts/run_calendar_sync.sh` (Cronjob-Wrapper)
  - `alembic/versions/20251120_1740_57a8e7357e0c_*.py` (Migration)
- 📦 **Geänderte Dateien**:
  - `app/models/__init__.py` (Booking imports)
  - `app/models/gamification.py` (Index-Namen gefixt)
  - `app/models/weekly.py` (Index-Namen gefixt)
  - `app/services/tracking_system.py` (PostgreSQL Dual-Write)
  - `app/routes/calendar.py` (PostgreSQL read mit Fallback)
  - `scripts/migrate_json_to_postgres.py` (Booking-Migration)

**Migration-Details (2025-11-21)**:
- ✅ **Phase 1 - JSONL Migration**:
  - 26 historische Buchungen aus `bookings.jsonl` → PostgreSQL
  - Script: `migrate_bookings_only.py`
  - Zeitraum: 24.11.2025 - 13.01.2026

- ✅ **Phase 2 - Calendar Backfill**:
  - 338 Buchungen aus Google Calendar extrahiert
  - Pattern: `[Booked by: username]` Tag in Event-Descriptions
  - Script: `backfill_from_calendar.py`
  - Zeitraum: 24.10.2025 - 21.11.2025

- ✅ **Cronjob Setup**:
  - Location: `/opt/business-hub/scripts/run_calendar_sync.sh`
  - Schedule: Täglich 23:00 Uhr (01:00 Berlin-Zeit)
  - Crontab: `0 23 * * * /opt/business-hub/scripts/run_calendar_sync.sh >> /var/log/business-hub/calendar-sync.log 2>&1`
  - Funktion: Synchronisiert manuelle Google Calendar Buchungen nach PostgreSQL

**Wichtige Hinweise:**
- **My Calendar zeigt ALLE Buchungen**: PostgreSQL-Integration komplett ✅
- **364 Historische Buchungen migriert**: JSONL (26) + Google Calendar (338) ✅
- **Dual-Write aktiv**: Alle neuen Buchungen gehen in PostgreSQL + JSON
- **Automatische Sync**: Täglicher Cronjob synchronisiert Google Calendar → PostgreSQL
- **Fallback vorhanden**: Bei PostgreSQL-Fehler nutzt System JSON-Files

### Wichtige Frühere Versionen (v3.3.3 - v3.3.7)

**v3.3.7** (2025-11-12): PDF Reports mit ZFA-Branding, ApexCharts T2-Analytics
**v3.3.6** (2025-11-05): Pagination-System (4,800+ Events), booking.py 500er Bugfix, Advanced Blocked Dates (3 Typen)
**v3.3.5** (2025-10-27): PERSIST_BASE Doppelverschachtelungs-Fix, T2-Bucket 9-9-2 Wahrscheinlichkeiten
**v3.3.4** (2025-10-25): My Calendar 7-Spalten Kanban + Drag & Drop, Reschedule-Modal, 3s-Undo
**v3.3.3** (2025-10-23): Dark Mode Logo Fix, Username Migration (17 User), ZFA Color Scheme 100%, Lucide Icons

**Go-Live:** 2025-10-18 auf http://91.98.192.233 ✅ LIVE