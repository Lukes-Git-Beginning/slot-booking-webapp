# CLAUDE.md

Diese Datei bietet Anleitungen für Claude Code (claude.ai/code) bei der Arbeit mit Code in diesem Repository.

## Projektübersicht

**Central Business Tool Hub** ist eine umfassende Multi-Tool-Plattform auf Enterprise-Niveau, die mehrere Business-Anwendungen unter einem einheitlichen Hub vereint. Was als Slot Booking Webapp begann, hat sich zu einem vollwertigen Business-Tool-Ökosystem entwickelt.

### Hauptkomponenten

#### 🏠 **Central Hub**
- Zentrale Landing-Page mit Tool-Navigation
- Einheitliche Authentifizierung über alle Tools hinweg
- Übergreifende Benutzer-Analytics und Dashboard
- Cross-Tool-Benachrichtigungen und Aktivitätstracking
- Security-Center (2FA, Passwort-Management)

#### 🎯 **Slot-Booking Tool** (Production-Ready)
- Multi-Berater-Terminverwaltung mit Google Calendar-Integration
- Fortschrittliche Gamification (Achievements, Badges, Prestige, Quests)
- Business Intelligence & Predictive Analytics
- Cosmetics Shop & Personalisierung
- Feiertags-Sperrung für deutsche NRW-Feiertage

#### 👥 **T2-Closer System** (Production-Ready)
- T2-Termin-Management und Follow-up-System
- Dedicated Dashboard für T2-Closer-Aktivitäten
- Integration mit Slot-Booking für nahtlose Workflows

#### 📊 **Analytics Tool** (Coming Soon)
- Business Intelligence über alle Tools hinweg
- Executive Reports & KPI-Dashboards
- Predictive Modeling & Forecasting

### Architektur-Highlights
- 🏗️ **Microservice-Architektur** - Jedes Tool als eigenständiges Modul mit gemeinsamer Infrastruktur
- 🔐 **Zentralisierte Sicherheit** - 2FA, Session-Management, RBAC über alle Tools
- 📱 **Moderne Flask-Struktur** - Blueprint-basiert, skalierbar, wartbar
- 🔄 **Shared Services** - Wiederverwendbare Services (Data Persistence, Caching, Logging)
- 🎨 **Konsistente UX** - Einheitliches Design-System über alle Tools

## Entwicklungskommandos

### Anwendung starten
```bash
python run.py                    # Anwendung starten (neue Struktur)
# ODER
python slot_booking_webapp.py    # Legacy-Startmethode
```

### Testen
```bash
python test_integration.py       # Umfassende Integrationstests ausführen
```

### Abhängigkeiten
```bash
pip install -r requirements.txt  # Alle Abhängigkeiten installieren
```

### Entwicklungstools
```bash
python -c "from app.core.extensions import data_persistence; data_persistence.create_backup()"  # Manuelles Backup
python -c "from app.services.achievement_system import achievement_system; achievement_system.process_daily_achievements()"  # Achievements verarbeiten
python -c "from app.services.holiday_service import holiday_service; print(holiday_service.get_upcoming_holidays(30))"  # Kommende Feiertage
```

## 🚀 Deployment-Workflow (WICHTIG!)

### Testserver & Live-Deployment

**WICHTIG:** Alle Änderungen werden NUR auf den Hetzner-Testserver deployed!

#### Hetzner-Testserver (Primär)
- **Server:** `91.98.192.233`
- **SSH-Key:** `~/.ssh/server_key`
- **App-Pfad:** `/opt/business-hub/`
- **Status:** Testserver (Go-Live in ~20 Tagen)
- **URL:** http://91.98.192.233

#### Deployment-Prozess für Änderungen

**IMMER direkt auf Hetzner-Server deployen:**

```bash
# 1. Einzelne Datei übertragen
scp -i ~/.ssh/server_key <lokale-datei> root@91.98.192.233:/opt/business-hub/<ziel-pfad>

# 2. Mehrere Dateien gleichzeitig
scp -i ~/.ssh/server_key file1.py file2.html root@91.98.192.233:/opt/business-hub/templates/

# 3. Service neu starten nach Änderungen
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"

# 4. Logs prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"

# 5. Status prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub --no-pager"
```

#### Wichtige Server-Pfade
```
/opt/business-hub/                          # Hauptverzeichnis
/opt/business-hub/app/routes/               # Flask-Routes
/opt/business-hub/templates/                # Jinja2-Templates
/opt/business-hub/static/                   # CSS/JS/Assets
/opt/business-hub/data/persistent/          # Persistente Daten
/opt/business-hub/backups/                  # Automatische Backups
/opt/business-hub/venv/                     # Python Virtual Environment
/var/log/business-hub/error.log             # Error-Logs
/var/log/business-hub/access.log            # Access-Logs
/var/log/business-hub/availability.log      # Availability-Generation-Logs
/var/log/business-hub/outcome-check.log     # Daily-Outcome-Check-Logs
/var/log/business-hub/achievement.log       # Achievement-Processing-Logs
/var/log/business-hub/backup.log            # Backup-Logs
/etc/systemd/system/business-hub.service    # Haupt-Service
/etc/systemd/system/*.timer                 # Geplante Task-Timer
/etc/nginx/sites-enabled/business-hub       # Nginx-Konfiguration
```

#### Deployment-Checkliste für Änderungen
- [ ] Änderungen lokal testen (optional)
- [ ] Per SCP auf Hetzner-Server übertragen
- [ ] Service neu starten: `systemctl restart business-hub`
- [ ] Logs prüfen auf Fehler
- [ ] Funktionalität im Browser testen (http://91.98.192.233)
- [ ] **NICHT auf Git/Render deployen** - nur Hetzner!

#### Automatisierte Tasks auf dem Server

**Automatische Backups (Cronjob):**
```bash
# Tägliches Backup um 2:00 Uhr
0 2 * * * /usr/local/bin/business-hub-backup.sh

# Manuelles Backup erstellen
ssh -i ~/.ssh/server_key root@91.98.192.233 "/usr/local/bin/business-hub-backup.sh"

# Backups auflisten
ssh -i ~/.ssh/server_key root@91.98.192.233 "ls -lh /opt/business-hub/backups/"
```

**Systemd Timers für geplante Tasks:**
```bash
# Status aller Timer prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl list-timers"

# Verfügbarkeits-Generierung (stündlich 07-18 UTC)
systemctl status availability-generator.timer

# Tägliche Outcome-Checks (19:00 UTC / 21:00 Berlin)
systemctl status daily-outcome-check.timer

# Achievement-Verarbeitung (20:00 UTC / 22:00 Berlin)
systemctl status achievement-processor.timer

# Timer manuell ausführen
systemctl start availability-generator.service
systemctl start daily-outcome-check.service
systemctl start achievement-processor.service

# Logs der geplanten Tasks
tail -f /var/log/business-hub/availability.log
tail -f /var/log/business-hub/outcome-check.log
tail -f /var/log/business-hub/achievement.log
tail -f /var/log/business-hub/backup.log
```

**Server-Monitoring:**
```bash
# Service-Status
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub --no-pager"

# Ressourcen-Nutzung
ssh -i ~/.ssh/server_key root@91.98.192.233 "df -h /opt/business-hub && free -h"

# Letzte Errors
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log | grep ERROR"

# Health Check (psutil erforderlich)
curl http://91.98.192.233/health
```

#### Deployment-Status
- **Testserver:** http://91.98.192.233 (Aktiv - Alle Features verfügbar)
- **Production:** Go-Live in ~17 Tagen geplant
- **Legacy Render.com:** Nicht mehr aktiv (alle Dienste auf VPS migriert)

## Anwendungsarchitektur

### Moderne Flask-Struktur
Die Anwendung folgt einer professionellen Flask-Struktur mit:

```
app/
├── __init__.py           # Application Factory - Central Hub Setup
├── config/               # Umgebungsbasierte Konfiguration
│   ├── base.py          # Basis-Konfigurationsklassen
│   ├── development.py   # Development-Settings
│   ├── production.py    # Production-Settings
│   └── legacy_config.py # Legacy-Kompatibilität
├── core/                # Kern-Infrastruktur (Shared)
│   ├── extensions.py       # Flask-Extensions-Initialisierung
│   ├── google_calendar.py  # Google Calendar Service
│   ├── cache_manager.py    # Caching-System
│   └── middleware.py       # Request/Response-Middleware
├── routes/              # HTTP-Route-Handler (Tool-Blueprints)
│   ├── hub.py          # 🏠 Central Hub Dashboard
│   ├── auth.py         # 🔐 Authentifizierung (shared)
│   ├── security.py     # 🔐 2FA & Passwort-Management
│   ├── health.py       # 💓 Health-Check-Endpoints
│   ├── api_gateway.py  # 🌐 Central API Gateway
│   ├── error_handlers.py # ⚠️ Zentrale Error-Behandlung
│   │
│   ├── admin/          # 🔧 Administrative Funktionen (shared)
│   │   ├── dashboard.py      # Admin-Dashboard
│   │   ├── users.py          # Benutzerverwaltung
│   │   ├── reports.py        # System-Reports
│   │   ├── blocked_dates.py  # Feiertags-/Sperrtermin-Verwaltung
│   │   ├── telefonie.py      # Telefonie-Punkte
│   │   └── export.py         # Datenexport
│   │
│   ├── slots.py        # 🎯 Slot-Booking (Neuer Wrapper)
│   ├── main.py         # 🎯 Legacy Slots Main Routes
│   ├── booking.py      # 🎯 Slots Buchungs-Routes
│   ├── calendar.py     # 🎯 Slots Kalender-Routes
│   ├── scoreboard.py   # 🎯 Slots Scoreboard
│   ├── user_profile.py # 🎯 Slots Benutzerprofile
│   ├── gamification/   # 🎮 Gamification-Features
│   │   └── legacy_routes.py # Gamification-Routes
│   │
│   └── t2.py           # 👥 T2-Closer-System
│
├── services/            # Business-Logic-Layer (Shared)
│   ├── data_persistence.py    # Datenspeicher-Abstraktion
│   ├── security_service.py    # 2FA & Security
│   ├── achievement_system.py  # Gamification-Engine
│   ├── prestige_system.py     # Prestige & Mastery
│   ├── level_system.py        # XP & Level-System
│   ├── daily_quests.py        # Tägliche Quests
│   ├── cosmetics_shop.py      # Cosmetics & Shop
│   ├── personalization_system.py  # Anpassungen
│   ├── booking_service.py     # Buchungs-Business-Logic
│   ├── holiday_service.py     # Feiertags-Service (NRW)
│   ├── tracking_system.py     # Analytics und Tracking
│   ├── executive_reports.py   # Executive-Reports
│   └── weekly_points.py       # Telefonie-Punkte
│
├── models/              # Datenmodelle (falls ORM)
└── utils/               # Hilfsfunktionen und Utilities
```

### Kern-Anwendungskomponenten

#### Central Hub & Shared Infrastructure
- **Flask Application Factory**: `app/__init__.py` - Multi-Tool Hub mit Blueprint-Registrierung
- **Central Hub Dashboard**: `app/routes/hub.py` - Landing Page mit Tool-Navigation
- **Security Center**: `app/routes/security.py` + `app/services/security_service.py` - 2FA & Passwort-Management
- **Konfigurationsverwaltung**: `app/config/` - Umgebungsspezifische Einstellungen
- **API Gateway**: `app/routes/api_gateway.py` - Unified API über alle Tools
- **Error Handling**: `app/routes/error_handlers.py` - Zentrale Fehlerbehandlung
- **Health Monitoring**: `app/routes/health.py` - System-Health-Checks

#### Shared Services (Tool-übergreifend)
- **Datenpersistenz**: `app/services/data_persistence.py` - Dual-Write-System mit Auto-Backup
- **Cache-Management**: `app/core/cache_manager.py` - Multi-Level-Caching
- **Google Calendar**: `app/core/google_calendar.py` - Robuster Kalender-Service
- **Tracking & Analytics**: `app/services/tracking_system.py` - Business Intelligence
- **Executive Reports**: `app/services/executive_reports.py` - Cross-Tool-Reporting

#### Slot-Booking Tool (Unter /slots/)
- **Legacy-Routes**: Vollständige Render.com-App unter `/slots/` Präfix
- **Gamification Engine**: `app/services/achievement_system.py` - Badges, XP, Level, Prestige
- **Quest-System**: `app/services/daily_quests.py` - Tägliche Herausforderungen
- **Cosmetics Shop**: `app/services/cosmetics_shop.py` - Personalisierung & Anpassung
- **Booking Service**: `app/services/booking_service.py` - Termin-Business-Logic
- **Holiday Service**: `app/services/holiday_service.py` - Deutsche NRW-Feiertage

#### T2-Closer Tool (Unter /t2/)
- **T2-Dashboard**: `app/routes/t2.py` - T2-Termin-Management
- **Integration**: Nutzt shared Booking & Calendar Services

#### Admin-Tools (Unter /admin/)
- **Admin-Dashboard**: `app/routes/admin/dashboard.py` - Zentrale Verwaltung
- **Benutzerverwaltung**: `app/routes/admin/users.py` - User-Management
- **System-Reports**: `app/routes/admin/reports.py` - Analytics & Insights
- **Telefonie**: `app/routes/admin/telefonie.py` - Punkte-Management
- **Datenexport**: `app/routes/admin/export.py` - Bulk-Exports

### Wichtige Architektur-Patterns

#### Datenspeicher-Strategie
Das App verwendet ein ausgeklügeltes Dual-Write-Persistenz-Pattern:
- **VPS**: `/opt/business-hub/data/persistent/` (Production & Test)
- **Lokal**: `data/persistent/` (Entwicklung)
- **Fallback**: `static/` Verzeichnis für Legacy-Kompatibilität
- Die Pfad-Auswahl erfolgt automatisch basierend auf `PERSIST_BASE` Env-Variable oder System-Detection
- Alle JSON-Daten sind UTF-8-kodiert mit `ensure_ascii=False`
- Automatisches Backup-System mit Aufbewahrungsrichtlinien
- Datenintegritäts-Validierung und Migrations-Support

#### Google Calendar-Integration
- Zentraler Kalender: `zentralkalenderzfa@gmail.com`
- Service Account-Authentifizierung über `GOOGLE_CREDS_BASE64` Umgebungsvariable
- Robuste Fehlerbehandlung mit Retry-Logic in `safe_calendar_call()` Funktion
- Farbkodierte Events mappen zu Buchungsergebnissen (siehe `color_mapping.py`)
- Multi-Berater-Kalender-Support mit Verfügbarkeits-Scanning

#### Feiertags-/Sperrungssystem
- **Automatische deutsche Feiertage**: NRW-spezifische Feiertage mit `holidays` Package
- **Benutzerdefinierte Sperren**: Beliebige Termine mit Begründung sperren
- **Admin-Verwaltung**: Vollständiges Interface für Feiertags- und Sperrtermin-Management
- **Verfügbarkeits-Integration**: Automatische Filterung gesperrter Termine aus Buchungsoptionen
- **Fallback-Mechanismen**: Graceful Degradation bei fehlenden Dependencies

#### Fortschrittliche Gamification-System
- **Badge-System**: 6 Seltenheitsstufen (häufig → mythisch) mit 50+ einzigartigen Badges
- **Level-System**: XP-basierte Progression mit Belohnungen und Freischaltungen
- **Prestige-System**: 6 Prestige-Level mit 5 Meisterschafts-Kategorien
- **Tägliche Quests**: Rotierende Herausforderungen mit Mini-Games und Belohnungen
- **Cosmetics Shop**: Titel, Themes, Avatare und Spezialeffekte
- **Achievement-Engine**: Echtzeit-Fortschritts-Tracking und automatische Vergabe
- **Persönliche Ziele**: Benutzerdefinierte Herausforderungen mit individuellen Belohnungen

#### Business Intelligence & Analytics
- **Kundenprofilerstellung**: Risikobewertung und Zuverlässigkeits-Scoring
- **Verhaltensanalytics**: Mustererkennung und Einblicke
- **Predictive Modeling**: Erfolgsraten-Vorhersagen und Empfehlungen
- **Performance-Tracking**: Individuelle und Team-Metriken
- **Historische Analyse**: 269+ Tage integrierter Buchungsdaten
- **Export-Fähigkeiten**: JSON, CSV, PDF mit anpassbaren Filtern

#### Zeitfenster-Logic & Punkte-System
- Telefonie-Punkte haben Commit-Fenster (18-21h Europe/Berlin Zeitzone)
- Außerhalb des Commit-Fensters gehen Änderungen in Pending-Queues
- Urlaubs-Flags überschreiben Punkte-Berechnungen
- Wöchentliche Punkte-Verfolgung mit Übertrag und Bonus-Systemen
- Achievement-Meilensteine verknüpft mit Punkte-Akkumulation

### Erweiterte Datenflüsse

#### 1. Buchungs-Lebenszyklus
```
Benutzeranfrage → Validierung → Kalender-Check → Slot-Erstellung → Tracking → Gamification-Update → Benachrichtigung
```

#### 2. Echtzeit-Verarbeitung
```
Event-Trigger → Daten-Update → Cache-Invalidierung → Achievement-Check → UI-Update → Analytics-Log
```

#### 3. Geplante Operationen
- **Stündlich**: Verfügbarkeits-Generierung, Cache-Refresh
- **Täglich**: Ergebnis-Verarbeitung, Achievement-Vergabe, Analytics-Aggregation
- **Wöchentlich**: Punkte-Übertrag, Leaderboard-Updates, Backup-Erstellung
- **Monatlich**: Historische Analyse, Report-Generierung, Daten-Archivierung

#### 4. Gamification-Pipeline
```
Benutzeraktion → Fortschritts-Tracking → Quest-Update → Badge-Bewertung → Level-Check → Belohnungs-Verteilung
```

#### 5. Feiertags-/Sperrungsflow
```
Terminanfrage → Holiday Service → Sperrung prüfen → Verfügbarkeit anpassen → Antwort
```

## Vollständiger Feature-Katalog

### 🏠 Central Hub Features
- **Multi-Tool-Dashboard**: Zentrale Landing Page mit Übersicht aller Tools
- **Unified Authentication**: Single-Sign-On über alle Tools hinweg
- **Security Center**: 2FA-Verwaltung, Passwort-Änderung, Login-Historie
- **Cross-Tool-Navigation**: Nahtlose Navigation zwischen Tools mit Kontext-Erhalt
- **Activity-Feed**: Tool-übergreifende Aktivitätsverfolgung
- **Benachrichtigungssystem**: Zentrale Benachrichtigungen für alle Tools
- **User-Settings**: Globale Einstellungen & Präferenzen

### 🎯 Slot-Booking Tool Features
- **Multi-Berater-Terminplanung**: Support für unbegrenzte Berater mit individuellen Kalendern
- **Echtzeit-Verfügbarkeit**: Stündliche Kalender-Scanning und Slot-Generierung
- **Konflikt-Prävention**: Erweiterte Buchungs-Validierung und Doppelbuchungs-Prävention
- **Kundenverwaltung**: Vollständige Kundenprofile mit Historie und Präferenzen
- **Ergebnis-Tracking**: Automatische Erkennung von Terminen, No-Shows und Stornierungen
- **Feiertags-Sperrung**: Automatische Sperrung deutscher NRW-Feiertage mit Admin-Verwaltung

### 👥 T2-Closer Tool Features
- **T2-Dashboard**: Dedicated Interface für T2-Closer-Aktivitäten
- **Termin-Follow-up**: Systematisches Follow-up-Management
- **Integration**: Nahtlose Integration mit Slot-Booking-Daten

### 🎮 Gamification-Features (Fortgeschritten)
- **Achievement-System**: 50+ Badges in 6 Seltenheitsstufen
- **XP & Level-System**: Progressive Weiterentwicklung mit Belohnungen
- **Prestige-System**: 6 Prestige-Level mit spezialisierten Meisterschafts-Tracks
- **Tägliche Quests**: Rotierende Herausforderungen mit Mini-Games und Belohnungen
- **Leaderboards**: Multiple Ranking-Kategorien und kompetitive Elemente
- **Cosmetics Shop**: Vollständige Anpassung mit Titeln, Themes, Avataren, Effekten
- **Persönliche Ziele**: Benutzerdefinierte Herausforderungen mit individuellen Belohnungen
- **Verhaltens-Analytics**: Mustererkennung und Performance-Einblicke

### 📊 Analytics & Business Intelligence
- **Performance-Dashboards**: Echtzeit-Metriken und KPIs
- **Kundenprofilerstellung**: Risikobewertung und Zuverlässigkeits-Scoring
- **Predictive Analytics**: Erfolgsraten-Vorhersagen und Empfehlungen
- **Historische Analyse**: 269+ Tage Buchungsdaten
- **Export-Funktionen**: JSON, CSV, PDF mit erweiterten Filtern
- **Trend-Analyse**: Mustererkennung und Einblicks-Generierung
- **Team-Performance**: Vergleichende Analyse und Benchmarking

### 🔧 Administrative Features (Shared)
- **Benutzerverwaltung**: Vollständige Benutzer-Lebenszyklus-Verwaltung über alle Tools
- **Rollenbasierter Zugriff**: Admin/Benutzer-Berechtigungen mit granularen Kontrollen
- **Tool-übergreifende Reports**: Analytics & Insights über alle Tools
- **Feiertags-Verwaltung**: Deutsche NRW-Feiertage mit benutzerdefinierten Sperren
- **Telefonie-Punkte**: Telefonie-Punkte-Management mit Commit-Fenstern
- **Datenexport**: Umfassende Berichterstattung und Datenextraktion
- **System-Überwachung**: Performance-Metriken und Gesundheitschecks für alle Tools
- **Konfigurations-Management**: Dynamische Einstellungen und Feature-Toggles
- **Backup & Recovery**: Automatisierte Backups mit Aufbewahrungsrichtlinien

### 🔐 Security Features
- **2FA-Authentifizierung**: TOTP-basierte Zwei-Faktor-Authentifizierung mit QR-Code-Setup
- **Passwort-Management**: Sichere Passwort-Änderung mit Validierung
- **Session-Management**: Sichere Session-Handhabung über alle Tools
- **Login-Historie**: Tracking von Login-Aktivitäten und Security-Events
- **RBAC**: Rollenbasierte Zugriffskontrolle (Admin/User)

### 🎨 Anpassung & Personalisierung
- **Theme-System**: Multiple visuelle Themes und Farbschemata
- **Avatar-System**: Anpassbare Benutzerprofile mit freischaltbaren Komponenten
- **Dashboard-Anpassung**: Personalisierte Layouts und Widgets
- **Benachrichtigungs-Präferenzen**: Anpassbare Alerts und Updates
- **Persönliche Analytics**: Individuelle Einblicke und Fortschritts-Tracking

### Umgebungsvariablen & Konfiguration

#### Core Configuration
- `FLASK_ENV`: Umgebungseinstellung (development/production)
- `SECRET_KEY`: Flask Session-Verschlüsselungs-Schlüssel (WICHTIG!)
- `PERSIST_BASE`: Override für Persistenz-Verzeichnis (optional)

#### Authentication & Users
- `USERLIST`: Benutzer-Zugangsdaten (`user1:pass1,user2:pass2`)
- `ADMIN_USERS`: Komma-getrennte Liste von Admin-Benutzernamen

#### Google Calendar Integration (Slots-Tool)
- `GOOGLE_CREDS_BASE64`: Base64-kodierte Service Account JSON
- `CENTRAL_CALENDAR_ID`: Haupt-Kalender-ID
- `CONSULTANTS`: Berater-Mapping (name:email Paare)

#### Gamification Configuration (Slots-Tool)
- `EXCLUDED_CHAMPION_USERS`: Benutzer ausgeschlossen von Leaderboards

#### Tool-Specific Settings
- Weitere tool-spezifische Env-Variablen in jeweiligen Tool-Dokumentationen

### Kritische Dateien & Verzeichnisse

#### Application Structure
- `run.py`: Haupt-Einstiegspunkt für die Anwendung
- `app/__init__.py`: Application Factory mit Blueprint-Registrierung
- `app/config/`: Umgebungsspezifische Konfigurationsdateien
- `requirements.txt`: Python-Dependencies (inkl. psutil, pyotp, qrcode)

#### Templates & Static Assets
- `templates/`: Jinja2 HTML-Templates für alle Tools
  - `templates/hub/`: Central Hub Templates
  - `templates/slots/`: Slot-Booking Templates (Legacy unter Root)
  - `templates/t2/`: T2-Closer Templates
  - `templates/errors/`: Error-Page Templates
- `static/`: CSS, JavaScript und statische Assets (shared)

#### Data & Persistence
- `data/persistent/`: Primäre Datenspeicherung mit vollständigem Anwendungszustand
- `data/backups/`: Automatisiertes Backup-Verzeichnis mit Aufbewahrung
- `static/availability.json`: Generierte Slot-Verfügbarkeit (Legacy-Fallback)

#### Security & Credentials
- `service_account.json`: Google Service Account-Zugangsdaten (niemals committen!)
- `.env`: Umgebungsvariablen (niemals committen!)
- `.env.example`: Template für .env-Datei

#### Deployment
- `deployment/`: VPS-Deployment-Scripts & Dokumentation
  - `vps_setup.sh`: Automatisches Server-Setup
  - `business-hub.service`: Systemd Service
  - `nginx.conf`: Nginx Reverse-Proxy Config

## Entwicklungsworkflow & Best Practices

### Code-Qualitäts-Standards
- **Flask Best Practices befolgen**: Blueprints, Application Factory Pattern verwenden
- **Separation of Concerns beibehalten**: Services für Business Logic, Routes für HTTP-Handling
- **Type Hints empfohlen**: Python Type Hints für bessere Code-Klarheit verwenden
- **Fehlerbehandlung**: Immer ordnungsgemäße Fehlerbehandlung mit Logging implementieren
- **Testen**: Tests für neue Features und kritische Funktionalität schreiben

### Datenbank & Datenmanagement
- **JSON-first Ansatz**: Alle Daten in optimiertem JSON-Format gespeichert
- **Dual-Write-Pattern**: Immer in sowohl persistente als auch statische Verzeichnisse schreiben
- **Backup-Strategie**: Automatisierte Backups mit manuellen Backup-Fähigkeiten
- **Datenintegrität**: Daten bei Lese-/Schreiboperationen validieren
- **UTF-8-Kodierung**: Immer `ensure_ascii=False` für JSON-Dateien verwenden

### API-Entwicklung
- **RESTful Prinzipien**: REST-Konventionen für API-Endpoints befolgen
- **JSON-Antworten**: Konsistente JSON-Struktur für alle API-Antworten
- **Fehlercodes**: Angemessene HTTP-Statuscodes verwenden
- **Rate Limiting**: Rate Limiting für API-Endpoints implementieren
- **Dokumentation**: Alle API-Endpoints mit Beispielen dokumentieren

### Fehlerbehebung & Debugging

#### Häufige Probleme
1. **Google Calendar API-Fehler**
   ```bash
   # Zugangsdaten prüfen
   python -c "from app.core.google_calendar import GoogleCalendarService; print('OK' if GoogleCalendarService().is_configured() else 'FAIL')"
   ```

2. **Datenpersistenz-Probleme**
   ```bash
   # Datenintegrität verifizieren
   python -c "from app.services.data_persistence import data_persistence; data_persistence.verify_integrity()"
   ```

3. **Gamification-System-Probleme**
   ```bash
   # Benutzer-Achievements zurücksetzen (nur Admin)
   python -c "from app.services.achievement_system import achievement_system; achievement_system.reset_user_progress('username')"
   ```

4. **Performance-Probleme**
   ```bash
   # Alle Caches leeren
   python -c "from app.core.extensions import cache_manager; cache_manager.clear_all()"
   ```

5. **Feiertags-System-Probleme**
   ```bash
   # Holiday Service prüfen
   python -c "from app.services.holiday_service import holiday_service; print('OK' if holiday_service.is_holiday(date(2024,12,25)) else 'FAIL')"
   ```

### Test-Strategie
- **Integrationstests**: `test_integration.py` deckt End-to-End-Workflows ab
- **Unit-Tests**: Individuelle Komponententests
- **Performance-Tests**: Load-Testing für kritische Pfade
- **Daten-Tests**: Datenintegrität und Migration validieren

### Deployment-Checkliste
- [ ] Umgebungsvariablen konfiguriert
- [ ] Google Calendar-Zugangsdaten gültig
- [ ] Datenbank/Persistenz-Layer initialisiert
- [ ] Statische Assets ordnungsgemäß bereitgestellt
- [ ] Geplante Aufgaben konfiguriert (Systemd Timer auf VPS)
- [ ] Überwachung und Logging aktiviert
- [ ] Backup-System operational

## Git Commit-Richtlinien
- **NIEMALS** Claude Code-Attribution in Commit-Nachrichten einschließen
- **NIEMALS** "🤖 Generated with [Claude Code]" oder "Co-Authored-By: Claude" hinzufügen
- Commit-Nachrichten sauber und professionell ohne AI-Tool-Referenzen halten
- Konventionelles Commit-Format verwenden: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
- Issue-Nummern referenzieren wenn anwendbar

## Projektstatus & Aktuelle Updates

### Aktuelle Version: v4.0+ (Multi-Tool Hub mit Security Center)
Die Anwendung hat sich von einer Slot-Booking-App zu einem **vollwertigen Business Tool Hub** entwickelt:

#### ✅ Abgeschlossene Major-Features (v4.0)
- ✅ **Central Hub Architecture**: Multi-Tool-Plattform mit einheitlicher Navigation
- ✅ **Security Center**: 2FA-Authentifizierung (TOTP) + Passwort-Management
- ✅ **T2-Closer Tool**: Dedicated T2-Management-System
- ✅ **API Gateway**: Unified API über alle Tools
- ✅ **Shared Services**: Tool-übergreifende Services (Persistence, Caching, Analytics)
- ✅ **Health Monitoring**: System-Health-Checks für alle Tools
- ✅ **Error Handling**: Zentrale Fehlerbehandlung mit Custom Error-Pages
- ✅ **VPS Deployment**: Production-ready Deployment auf Hetzner (Testserver aktiv)

#### ✅ Slots-Tool Features (Migriert von Render)
- ✅ **Vollständiges Gamification-System**: Badges, XP, Prestige, Quests, Shop
- ✅ **Business Intelligence**: Analytics, Tracking, Predictive Insights
- ✅ **Feiertags-Sperrung**: Deutsche NRW-Feiertage mit Admin-Verwaltung
- ✅ **Performance-Optimierung**: Multi-Level-Caching, Deduplizierung

#### 🔄 In Arbeit
- 🔄 **Analytics Tool**: Dedicated Analytics-Dashboard über alle Tools (Modul vorbereitet)
- 🔄 **Tool #4-6**: Weitere Business-Tools in Planung
- 🔄 **Mobile PWA**: Progressive Web App-Fähigkeiten
- 🔄 **Notification System**: Push-Benachrichtigungen über alle Tools

#### 🚀 Deployment-Status
- **Hetzner Testserver**: ✅ LIVE (http://91.98.192.233)
- **Production Go-Live**: In ~17 Tagen geplant
- **Legacy Render.com**: Nicht mehr aktiv (alle Dienste auf VPS migriert)

### Letzte Git-Commits
```
d714373 fix: Prestige display, scoreboard avatars, and cosmetics shop
02f1ff9 fix: Badge progress bar width and prestige mastery display
93cf182 fix: Correct gamification display issues and API endpoints
1c254b0 fix: Correct admin.dashboard endpoint in index.html
2d2f0a9 feat: Implement Password Change & 2FA Authentication
```

## Technische Implementierungs-Anleitung

### Arbeiten mit der Codebase

#### Wichtige Service-Klassen

```python
# Central Hub & Shared Services
from app.services.data_persistence import data_persistence
from app.services.security_service import security_service  # 🆕 2FA & Security
from app.services.tracking_system import tracking_system
from app.services.executive_reports import executive_reports
from app.core.extensions import cache_manager
from app.core.google_calendar import GoogleCalendarService

# Slot-Booking Tool Services
from app.services.achievement_system import achievement_system
from app.services.prestige_system import prestige_system
from app.services.level_system import level_system
from app.services.daily_quests import daily_quests
from app.services.cosmetics_shop import cosmetics_shop
from app.services.personalization_system import personalization_system
from app.services.booking_service import BookingService
from app.services.holiday_service import holiday_service
from app.services.weekly_points import weekly_points

# T2-Closer Tool Services
# (Nutzt shared services wie BookingService, GoogleCalendarService)
```

#### Datenpersistenz-Patterns
```python
# Immer die Datenpersistenz-Layer für Datenoperationen verwenden
data_persistence.save_data('user_badges', badge_data)
user_data = data_persistence.load_data('user_stats', {})
data_persistence.create_backup()  # Manuelle Backup-Erstellung
```

#### Feiertags-Integration
```python
# Feiertags-Service für Sperrungen verwenden
from app.services.holiday_service import holiday_service

def check_booking_availability(date_str):
    # Datum parsen
    check_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    # Prüfen ob gesperrt
    if holiday_service.is_blocked_date(check_date):
        reason = holiday_service.get_blocked_reason(check_date)
        return False, f"Datum gesperrt: {reason}"

    return True, "Verfügbar"
```

#### Neue Features hinzufügen

**Für ein bestehendes Tool:**
1. **Service-Klasse erstellen/erweitern** in `app/services/` für Business Logic
2. **Route-Handler hinzufügen** in entsprechendem `app/routes/` Blueprint
3. **Template erstellen** in `templates/<tool-name>/` falls UI nötig
4. **Tests hinzufügen** zu `tests/` (optional)
5. **Dokumentation aktualisieren** in CLAUDE.md

**Für ein neues Tool:**
1. **Blueprint erstellen** in `app/routes/<tool-name>.py`
2. **Blueprint registrieren** in `app/__init__.py` (register_blueprints)
3. **Templates erstellen** in `templates/<tool-name>/`
4. **Tool zur Navigation hinzufügen** in `get_available_tools()` (app/__init__.py)
5. **Service-Klassen erstellen** in `app/services/` (oder shared services nutzen)
6. **Dokumentation hinzufügen** zu CLAUDE.md und README.md

#### Gamification-Integration
```python
# Achievements für neue Features vergeben
from app.services.achievement_system import achievement_system

def handle_new_feature_action(user, action_data):
    # Deine Feature-Logic hier
    result = perform_action(action_data)

    # Mit Gamification integrieren
    achievement_system.update_quest_progress(user, 'new_feature_quest', 1)
    achievement_system.check_and_award_badges(user)

    return result
```

#### Fehlerbehandlungs-Best-Practices
```python
import logging
from app.utils.logging import get_logger

logger = get_logger(__name__)

def safe_operation():
    try:
        # Deine Operation hier
        result = risky_operation()
        logger.info("Operation erfolgreich abgeschlossen")
        return result
    except Exception as e:
        logger.error(f"Operation fehlgeschlagen: {str(e)}", extra={'operation': 'safe_operation'})
        return None
```

### Datenbank-Schema (JSON-Collections)

#### Kern-Datenstruktur
```
data/persistent/
├── 🔐 Security & Auth
│   ├── user_2fa.json           # 🆕 2FA-Secrets & Backup-Codes
│   └── login_history.json      # 🆕 Login-Aktivitäten (geplant)
│
├── 🎯 Slot-Booking Tool
│   ├── blocked_dates.json      # Gesperrte Termine (Feiertage + Custom)
│   ├── user_badges.json        # Badge-Vergaben und Zeitstempel
│   ├── user_levels.json        # XP und Level-Progression
│   ├── daily_user_stats.json   # Tägliche Performance-Metriken
│   ├── prestige_data.json      # Prestige-System-Daten
│   ├── cosmetic_purchases.json # Shop-Käufe und ausgerüstete Items
│   ├── daily_quests.json       # Quest-Fortschritt und Abschlüsse
│   ├── behavior_patterns.json  # Benutzer-Verhaltens-Analytics
│   ├── weekly_points.json      # Telefonie-Punkte-System
│   ├── champions.json          # Leaderboard-Daten
│   ├── scores.json             # Gesamt-Scoring-System
│   └── booking_data.json       # Buchungsdaten (wenn vorhanden)
│
├── 👥 T2-Closer Tool
│   └── t2_data.json            # T2-spezifische Daten (wenn vorhanden)
│
└── 📊 Analytics & Reporting
    └── cross_tool_analytics.json  # Tool-übergreifende Analytics (geplant)
```

#### Datenbeziehungen
- **Benutzer** werden durch Benutzername-Strings identifiziert
- **Badges** verknüpfen zu Benutzern über Benutzername-Keys
- **Quests** verfolgen Fortschritt pro Benutzer pro Tag
- **Analytics** aggregieren Daten über mehrere Zeitrahmen
- **Punkte** folgen wöchentlichen Zyklen mit Übertrag-Logic
- **Gesperrte Termine** kombinieren automatische Feiertage mit benutzerdefinierten Sperren

### API-Entwicklungs-Richtlinien

#### Neue Endpoints erstellen
```python
# In app/routes/api.py
@api_bp.route("/feature/<parameter>")
@require_login
def api_new_feature(parameter):
    """API-Endpoint für neues Feature"""
    try:
        user = session.get("user")
        result = feature_service.process(user, parameter)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

#### Antwortformat-Standards
```python
# Erfolg-Antwort
{
    "success": true,
    "data": {...},
    "message": "Operation abgeschlossen"
}

# Fehler-Antwort
{
    "success": false,
    "error": "Fehlerbeschreibung",
    "code": "ERROR_CODE"
}
```

### Test-Richtlinien

#### Integrationstest-Struktur
```python
# Zu test_integration.py hinzufügen
def test_new_feature():
    """Neue Feature-Funktionalität testen"""
    # Setup
    test_user = "test_user"
    test_data = {"param": "value"}

    # Ausführen
    result = new_feature_function(test_user, test_data)

    # Verifizieren
    assert result is not None
    assert result["success"] == True

    # Aufräumen falls nötig
    cleanup_test_data()

def test_holiday_blocking():
    """Feiertags-Sperrung testen"""
    from app.services.holiday_service import holiday_service
    from datetime import date

    # Weihnachten sollte gesperrt sein
    christmas = date(2024, 12, 25)
    assert holiday_service.is_holiday(christmas)
    assert holiday_service.is_blocked_date(christmas)

    # Normaler Tag sollte nicht gesperrt sein
    normal_day = date(2024, 6, 15)
    assert not holiday_service.is_holiday(normal_day)
```

### Performance-Überlegungen

#### Caching-Richtlinien
- **Häufig aufgerufene Daten cachen** (Benutzer-Stats, Verfügbarkeit)
- **Angemessene Timeouts verwenden** (5min für dynamisch, 1h für semi-statisch)
- **Cache-Invalidierung implementieren** bei Daten-Updates
- **Cache-Hit-Raten überwachen** für Optimierung

#### Datenbank-Optimierung
- **Batch-Schreiboperationen** wenn möglich
- **data_persistence.save_multiple() verwenden** für Bulk-Updates
- **Datenarchivierung implementieren** für historische Datensätze
- **Dateigrößen überwachen** und Kompression implementieren falls nötig

### Deployment-Überlegungen

#### Umgebungskonfiguration
```bash
# Core Configuration (ERFORDERLICH)
SECRET_KEY=<starker-secret-key>               # Flask Session-Verschlüsselung
USERLIST=<user:pass,user2:pass2>              # Benutzer-Credentials
ADMIN_USERS=<admin1,admin2>                   # Admin-Benutzer

# Google Calendar (ERFORDERLICH für Slots-Tool)
GOOGLE_CREDS_BASE64=<base64-kodierte-zugangsdaten>
CENTRAL_CALENDAR_ID=<kalender-email>
CONSULTANTS=<name:email,name2:email2>         # Berater-Mapping

# Optionale Konfiguration
PERSIST_BASE=<custom-persistenz-pfad>         # Override für Datenpfad
FLASK_ENV=<development|production>            # Umgebung
EXCLUDED_CHAMPION_USERS=<user1,user2>         # Von Leaderboards ausschließen
```

#### Gesundheitschecks
```python
# Health-Check ist bereits implementiert in app/routes/health.py
# Endpoint: /health

# Beispiel Health-Check Response:
{
    "status": "healthy",
    "timestamp": "2024-10-06T12:00:00",
    "version": "4.0.0",
    "tools": {
        "slots": "healthy",
        "t2": "healthy",
        "analytics": "not_ready"
    },
    "services": {
        "database": "healthy",
        "cache": "healthy",
        "calendar": "healthy"
    },
    "memory": {
        "percent": 45.2,
        "available_mb": 2048
    }
}
```

## Wichtige Notizen für Entwicklung

### Code-Qualitäts-Anforderungen
- **Immer Type Hints verwenden** für Funktionsparameter und Returns
- **PEP 8 befolgen** für Code-Formatierung und Stil
- **Docstrings hinzufügen** für komplexe Funktionen und Klassen
- **Bedeutungsvolle Variablennamen verwenden** die ihren Zweck beschreiben
- **Ordnungsgemäße Fehlerbehandlung implementieren** mit Logging
- **Shared Services nutzen** - Keine Duplikation von Core-Funktionalität

### Sicherheits-Anforderungen
- **Niemals Zugangsdaten committen** oder sensible Daten (.env, service_account.json)
- **Immer Benutzereingaben validieren** vor Verarbeitung
- **Session-Security beachten** - Keine sensiblen Daten in Sessions
- **2FA-Secrets sicher speichern** - Nur verschlüsselt in user_2fa.json
- **Rate Limiting implementieren** für sensitive Endpoints (Login, 2FA)
- **Sicherheitsrelevante Ereignisse protokollieren** für Audit-Trails

### Performance-Anforderungen
- **Kritische Code-Pfade profilieren** für Engpässe
- **Multi-Level-Caching nutzen** (Cache-Manager verwenden)
- **Background-Tasks verwenden** für schwere Verarbeitung (systemd timers auf VPS)
- **Speicherverbrauch überwachen** und Datenstrukturen optimieren
- **Unter Last testen** um Skalierbarkeit zu gewährleisten

### Blueprint & Tool-Entwicklung Best Practices
- **URL-Präfixe konsistent halten**: `/slots/`, `/t2/`, `/admin/`, etc.
- **Shared Templates nutzen**: `templates/hub/base.html` als Basis
- **Tool-Isolation beachten**: Jedes Tool kann eigenständig funktionieren
- **Legacy-Kompatibilität**: Root-Level-Redirects für Rückwärtskompatibilität
- **Cross-Tool-Features**: Security, Analytics, Reports über alle Tools verfügbar

### Deployment-Best-Practices
- **Immer auf Hetzner-Testserver deployen** (derzeit primäres Deployment-Ziel)
- **Service nach Code-Änderungen neu starten**: `systemctl restart business-hub`
- **Logs überwachen**: `/var/log/business-hub/*.log`
- **Backups vor größeren Änderungen**: `/usr/local/bin/business-hub-backup.sh`
- **Health-Check nach Deployment**: `curl http://91.98.192.233/health`

---

## 🎉 Zusammenfassung

Der **Central Business Tool Hub** ist eine umfassende Multi-Tool-Plattform, die von einer einzelnen Slot-Booking-App zu einem vollwertigen Business-Ökosystem gewachsen ist. Mit shared Services, zentraler Sicherheit, und modularer Architektur bietet sie eine solide Grundlage für unbegrenzte Tool-Erweiterungen.

**Aktuelle Production-Umgebung:**
- Hetzner VPS Testserver (http://91.98.192.233)
- Production Go-Live in ~17 Tagen
- 3 aktive Tools: Slots, T2-Closer, Admin
- Security Center mit 2FA
- Vollständige VPS-Automatisierung mit systemd

Diese Enterprise-Grade-Plattform ist bereit für Skalierung und weitere Business-Tool-Integration. 🚀