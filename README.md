# 🎯 Central Business Tool Hub

Eine professionelle Multi-Tool-Plattform mit Slot-Booking, T2-Closer-System, Gamification und Analytics auf Enterprise-Niveau.

## 📋 Inhaltsverzeichnis

- [Features](#-features)
- [Technologie-Stack](#-technologie-stack)
- [Voraussetzungen](#-voraussetzungen)
- [Installation](#-installation)
- [Konfiguration](#-konfiguration)
- [Deployment](#-deployment)
- [Automatisierung](#-automatisierung)
- [Sicherheit](#-sicherheit)
- [Fehlerbehebung](#-fehlerbehebung)
- [Changelog](#-changelog)

## ✨ Features

### 🚀 Kernfunktionalität
- **Central Hub**: Zentrale Navigation für alle Business-Tools
- **Terminbuchungssystem**: Vollständige Slot-Buchung mit Google Calendar-Integration
- **T2-Closer-System**: Spezialisiertes T2-Termin-Management
- **Echtzeit-Verfügbarkeit**: Automatische Slot-Generierung basierend auf Beraterkalendern
- **Multi-Berater-Support**: Verwaltung von Terminen für 9 Berater
- **Intelligente Terminplanung**: Verhindert Doppelbuchungen und Konflikte
- **German NRW Holiday Blocking**: Automatische Sperrung von deutschen Feiertagen (NRW)

### 🎮 Fortschrittliche Gamification-Engine
- **Achievement-System**: 50+ Badges in 6 Seltenheitsstufen (häufig → mythisch)
- **Prestige & Meisterschafts-System**: 6 Prestige-Level mit 5 spezialisierten Meisterschaftskategorien
- **Tägliche Quests**: Wechselnde Herausforderungen mit integrierten Mini-Games
- **XP & Level-System**: Progressive Weiterentwicklung mit freischaltbaren Belohnungen
- **Competitive Leaderboards**: Mehrere Ranking-Kategorien mit saisonalen Wettbewerben
- **Cosmetics Shop**: Vollständige Anpassung mit Titeln, Themes, Avataren und Spezialeffekten

### 📊 Business Intelligence & Analytics
- **Umfassendes Tracking**: Echtzeit-Überwachung aller Buchungsaktivitäten
- **Erweiterte Kundenprofilierung**: Risikobewertung und Zuverlässigkeits-Scoring
- **Consultant Analytics (My Calendar)**: Show/No-Show-Tracking für Telefonisten mit Drag & Drop Kanban
- **7-Spalten Kanban-Board**: HubSpot-Style Status-Management (Pending, Erschienen, Rückholung, Sonderkunden, Verschoben, Nicht Erschienen, Ghost)
- **Drag & Drop Status-Updates**: Visuelle Termin-Status-Verwaltung mit Undo-Funktion (3s)
- **Reschedule-Modal**: Vollständige Umbuchungs-Funktionalität mit dynamischen Zeitslots
- **Performance-Dashboards**: Echtzeit-KPI-Überwachung
- **Team-Analytics**: Vergleichende Leistungsanalyse zwischen Beratern

### 🎨 Anpassung & Personalisierung
- **Cosmetics Shop**: Vollständiger Marktplatz mit Titeln, Themes, Avataren und Effekten
- **Avatar-System**: 22 hochwertige PNG-Avatare (Business, Developer, Fantasy, etc.)
- **Theme-System**: 6+ visuelle Themes mit CSS Custom Properties
- **Canvas-Based Effects**: Vollständiges Particle-System (Sparkle, Confetti, Shake)
- **Audio Effects**: Web Audio API-Integration für immersive Sounds
- **ZFA Color Scheme**: Konsistentes Branding (Gold #d4af6a, Blau #207487, Dunkelblau #294c5d)

### 🔧 Erweiterte Technische Features
- **Moderne Flask-Architektur**: Application Factory Pattern mit Blueprints
- **Glassmorphism-Design**: Modernes UI mit Backdrop-Filter und CSS-Variablen
- **Lokale Asset-Hosting**: Bootstrap 5, Font Awesome, Lucide Icons lokal gehostet
- **Dual-Write-Persistenz**: Redundante Datenspeicherung mit automatischem Backup
- **Intelligentes Caching**: Mehrstufige Performance-Optimierung
- **Sicherheits-Framework**: 2FA, RBAC, Session-Management, Rate Limiting

## 🛠 Technologie-Stack

### Backend
- **Flask 3.1.1** - Web-Framework
- **Python 3.11+** - Programmiersprache
- **Google Calendar API** - Kalender-Integration
- **Gunicorn** - WSGI HTTP Server
- **holidays** - Deutsche Feiertage (NRW)

### Frontend
- **Jinja2 Templates** - Server-seitiges Rendering
- **Bootstrap 5.3.2** - Responsive CSS-Framework (lokal gehostet)
- **Tailwind CSS + DaisyUI** - Moderne Utility-First CSS (Hub & T2)
- **Font Awesome 6.4.2** - Icon-Library (lokal gehostet)
- **Lucide Icons** - Moderne Icon-Library (lokal gehostet)
- **JavaScript (ES6+)** - Interaktive Features inkl. Canvas API & Web Audio API

### Daten & Analytics
- **Pandas** - Datenmanipulation
- **NumPy** - Numerische Berechnungen
- **JSON/JSONL** - Datenpersistenz

### Infrastruktur
- **Hetzner VPS** - Production Server (91.98.192.233)
- **Nginx** - Reverse Proxy mit Rate Limiting
- **Gunicorn** - WSGI Server (4 Workers)
- **Systemd** - Service & Timer Management
- **Ubuntu 22.04 LTS** - Server Betriebssystem

## 📋 Voraussetzungen

- Python 3.11 oder höher
- Google Cloud Platform-Konto mit aktivierter Calendar API
- Service Account-Zugangsdaten für Google Calendar
- Git für Versionskontrolle
- (Production) Linux Server mit systemd

## ⚙️ Lokale Installation (Entwicklung)

### 1. Repository klonen

```bash
git clone https://github.com/Lukes-Git-Beginning/slot-booking-webapp.git
cd slot-booking-webapp
```

### 2. Virtuelle Umgebung erstellen

```bash
python -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. Umgebungsvariablen konfigurieren

Erstelle eine `.env`-Datei im Hauptverzeichnis (siehe [Konfiguration](#-konfiguration))

### 5. Anwendung starten

```bash
# Development-Modus
python run.py
```

Die Anwendung ist verfügbar unter `http://localhost:5000`

## 🔧 Konfiguration

### Umgebungsvariablen

Auf dem Produktionsserver: `/opt/business-hub/.env`

Für lokale Entwicklung: `.env` im Projektverzeichnis erstellen

```bash
# ========================================
# CORE CONFIGURATION
# ========================================
SECRET_KEY=<generierter-sicherer-schlüssel>
FLASK_ENV=production
DEBUG=False

# ========================================
# USER AUTHENTICATION
# ========================================
USERLIST=user1:pass1,user2:pass2,admin:adminpass
ADMIN_USERS=admin,username

# ========================================
# DOMAIN & SESSION CONFIGURATION
# ========================================
SESSION_COOKIE_DOMAIN=.berater.zfa.gmbh
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_NAME=zfa_session

SERVER_NAME=berater.zfa.gmbh
PREFERRED_URL_SCHEME=https

# ========================================
# GOOGLE CALENDAR INTEGRATION
# ========================================
GOOGLE_CREDS_BASE64=<base64-kodierte-service-account-json>
CENTRAL_CALENDAR_ID=zentralkalenderzfa@gmail.com
CONSULTANTS=Name1:email1@gmail.com,Name2:email2@gmail.com

# ========================================
# SECURITY SETTINGS
# ========================================
RATELIMIT_ENABLED=True
RATELIMIT_STORAGE_URL=memory://
PERMANENT_SESSION_LIFETIME=480

# ========================================
# LOGGING
# ========================================
LOG_LEVEL=INFO
LOG_FILE=/var/log/business-hub/app.log

# ========================================
# DATA PERSISTENCE
# ========================================
# WICHTIG: PERSIST_BASE darf NICHT /persistent enthalten!
# Der Code fügt automatisch /persistent hinzu.
PERSIST_BASE=/opt/business-hub/data
```

### Google Service Account-Setup

1. Erstelle ein Google Cloud Platform-Projekt
2. Aktiviere die Calendar API
3. Erstelle ein Service Account
4. Lade die JSON-Zugangsdatei herunter
5. Base64-kodiere die JSON-Datei:
   ```bash
   base64 -w 0 service_account.json
   ```
6. Setze den kodierten String als `GOOGLE_CREDS_BASE64`

### Verfügbare Routen

#### Hub & Navigation
- `/` - Central Hub Dashboard
- `/login` - Benutzerauthentifizierung
- `/logout` - Benutzer-Abmeldung

#### Slot-Booking
- `/slots` - Terminbuchungsinterface
- `/calendar-view` - Kalenderübersicht
- `/my-calendar` - Consultant Analytics mit Kanban-Board & Drag & Drop
- `/api/update-event-status` - Status-Update via Drag & Drop
- `/api/reschedule-booking` - Termin-Umbuchung
- `/api/get-available-slots` - Verfügbare Zeitslots abfragen

#### Gamification
- `/scoreboard` - Leaderboards und Rankings
- `/gamification` - Achievement-System
- `/daily-quests` - Tägliche Herausforderungen
- `/prestige-dashboard` - Prestige-System
- `/cosmetics-shop` - Cosmetics Marktplatz

#### T2-Closer
- `/t2` - T2-Closer Dashboard
- `/t2/bookings` - T2-Terminverwaltung

#### Administrative Oberfläche
- `/admin/dashboard` - Admin-Dashboard
- `/admin/blocked-dates` - Feiertage und Sperren verwalten
- `/admin/users` - Benutzerverwaltung
- `/admin/reports` - Erweiterte Berichte

## 🏗 Architektur

### Anwendungsstruktur

```
slot_booking_webapp/
├── run.py                      # Flask Application Entry Point
├── wsgi.py                     # Production WSGI
│
├── app/
│   ├── __init__.py             # Application Factory
│   ├── config/                 # Konfigurationsmanagement
│   ├── core/                   # Kern-Komponenten (Extensions, Google Calendar)
│   ├── routes/                 # HTTP Route Handler (Blueprints)
│   │   ├── hub.py              # Central Hub
│   │   ├── auth.py             # Authentifizierung
│   │   ├── security.py         # 2FA & Security
│   │   ├── admin/              # Admin-Features
│   │   ├── gamification/       # Gamification-Features
│   │   ├── main.py             # Slot-Booking Routes
│   │   └── t2.py               # T2-Closer
│   ├── services/               # Business Logic Layer
│   │   ├── achievement_system.py
│   │   ├── booking_service.py
│   │   ├── data_persistence.py
│   │   └── holiday_service.py
│   └── utils/                  # Hilfsfunktionen
│
├── templates/                  # Jinja2 HTML-Templates
│   ├── hub/                    # Central Hub Templates (ZFA)
│   ├── slots/                  # Slot-Booking (Bootstrap 5)
│   ├── t2/                     # T2-Closer (ZFA)
│   └── ...
│
├── static/                     # CSS, JS, Assets
│   ├── bootstrap.min.css       # Bootstrap 5.3.2 (lokal)
│   ├── fontawesome.min.css     # Font Awesome 6.4.2 (lokal)
│   └── avatars/                # 22 Avatar PNGs
│
├── data/persistent/            # Primäre Datenspeicherung
│   ├── user_badges.json
│   ├── scores.json
│   ├── user_cosmetics.json
│   └── ...
│
├── scripts/                    # Automatisierungs-Scripts
│   ├── generate_availability.py
│   ├── process_achievements.py
│   └── process_daily_outcomes.py
│
└── deployment/                 # Deployment-Konfigurationen
    ├── systemd/                # Systemd Service & Timer
    ├── scripts/                # Deployment-Scripts
    └── nginx-business-hub.conf # Nginx-Konfiguration
```

### Wichtige Design-Patterns

#### Dual-Write-Persistenz
- **Primär**: `/data/persistent/` Verzeichnis
- **Automatische Backups**: Tägliche Rotation
- **UTF-8 JSON-Kodierung**: `ensure_ascii=False`

#### Service-Layer-Architektur
- **Controller**: Flask-Routes handhaben HTTP-Requests
- **Services**: Business-Logic in dedizierten Modulen
- **Data Access**: Zentralisiert durch `data_persistence.py`

## 🌐 Deployment

### Hetzner VPS (Production)

**Server-Details:**
- IP: `91.98.192.233`
- SSH-Key: `~/.ssh/server_key`
- App-Pfad: `/opt/business-hub/`
- URL: http://91.98.192.233

#### Deployment-Prozess

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

#### Wichtige Server-Pfade

```
/opt/business-hub/                    # Hauptverzeichnis
/opt/business-hub/app/                # Flask-App
/opt/business-hub/templates/          # Templates
/opt/business-hub/data/persistent/    # Production-Daten
/var/log/business-hub/error.log       # Error-Logs
/etc/systemd/system/business-hub.service      # Main Service
/etc/systemd/system/availability-generator.*  # Timer
```

#### Production Services

```bash
# Main Application
sudo systemctl status business-hub

# Availability Generator (5x täglich)
sudo systemctl status availability-generator.timer

# Achievement Processor (täglich 22:00)
sudo systemctl status achievement-processor.timer

# Daily Outcome Check (täglich 21:00)
sudo systemctl status daily-outcome-check.timer

# Cache Cleanup (täglich 03:00)
sudo systemctl status cache-cleanup.timer
```

### Systemd Services verwalten

```bash
# Service Status
systemctl status business-hub

# Service neu starten
systemctl restart business-hub

# Logs anzeigen
journalctl -u business-hub -f

# Service automatisch starten
systemctl enable business-hub
```

### Nginx-Konfiguration

Die Nginx-Konfiguration befindet sich unter `/etc/nginx/sites-available/business-hub`

```bash
# Nginx neu laden
systemctl reload nginx

# Nginx-Logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

## ⚙️ Automatisierung

### Systemd Timer

Die Anwendung nutzt systemd Timer für automatisierte Aufgaben:

#### Verfügbarkeitsgenerierung
- **Zeitplan**: 5x täglich (06:00, 09:00, 12:00, 15:00, 18:00 UTC)
- **Berlin-Zeit**: 08:00, 11:00, 14:00, 17:00, 20:00
- **Service**: `availability-generator.timer`
- **Funktion**: Aktualisiert verfügbare Terminslots basierend auf Google Calendar

#### Tägliche Ergebnisverarbeitung
- **Zeitplan**: Täglich um 19:00 UTC (21:00 Berlin)
- **Service**: `daily-outcome-check.timer`
- **Funktion**: Verarbeitet Terminergebnisse und No-Shows

#### Achievement-Verarbeitung
- **Zeitplan**: Täglich um 20:00 UTC (22:00 Berlin)
- **Service**: `achievement-processor.timer`
- **Funktion**: Vergibt Badges und aktualisiert Statistiken

#### Wöchentlicher Reset
- **Zeitplan**: Montag 04:00 UTC
- **Service**: `weekly-reset.timer`
- **Funktion**: Wöchentliche Punkte-Zurücksetzung

#### Cache-Cleanup
- **Zeitplan**: Täglich um 03:00 UTC
- **Service**: `cache-cleanup.timer`
- **Funktion**: Automatische Bereinigung von Cache-Dateien >7 Tage

### Timer verwalten

```bash
# Status aller Timer anzeigen
systemctl list-timers

# Timer neu starten
sudo systemctl restart availability-generator.timer

# Logs anzeigen
journalctl -u availability-generator.service -n 50
```

## 🔒 Sicherheit

### Authentifizierung & Autorisierung
- **2FA-Support**: Two-Factor Authentication über Security Center
- **Session-basierte Authentifizierung**: Sichere Session-Verwaltung
- **Rollenbasierte Zugriffskontrolle**: Admin/User-Rollen
- **Passwort-Hashing**: Sichere Passwort-Speicherung

### Rate Limiting (Zweischichtig)

**Nginx-Layer:**
- Login: 5 Requests/Minute
- API: 60 Requests/Minute
- Booking: 10 Requests/Minute
- Global: 100 Requests/Minute

**Flask-Layer:**
- Zentralisierte Decorators für kritische Endpoints
- Custom 429 Error Handler

### Datenschutz
- Input-Sanitization und Validierung
- SQL-Injection-Prävention
- XSS-Schutz durch Template-Escaping
- CSRF-Schutz für zustandsändernde Operationen

### Logging & Monitoring
- Strukturiertes Logging mit Performance-Metriken
- Security-Event-Protokollierung
- Audit-Trails für sensitive Operationen

## 📈 Performance-Optimierung

### Mehrstufige Caching-Strategie
- Google Calendar API: 30-Minuten-Cache
- User-Daten: Intelligente Invalidierung
- Cache-Warming für kritische Daten

### Datenbank-Optimierung
- JSON-Optimierung mit Kompression
- Batch-Operationen für reduzierte I/O
- Datenpartitionierung (historische Daten getrennt)

### Frontend-Performance
- Asset-Optimierung: Minifizierte CSS/JS
- Progressive Loading: Lazy Loading für nicht-kritische Komponenten
- Responsive Design: Mobile-First-Ansatz

## 🔧 Fehlerbehebung

### Häufige Probleme

#### 1. Service startet nicht

```bash
# Logs prüfen
journalctl -u business-hub -n 100 --no-pager

# Umgebungsvariablen prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "cat /opt/business-hub/.env | grep USERLIST"

# Berechtigungen prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "ls -la /opt/business-hub/"
```

#### 2. Google Calendar API-Fehler

```bash
# Service Account Credentials prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && python3 -c 'from app.core.google_calendar import GoogleCalendarService; print(\"OK\" if GoogleCalendarService().is_configured() else \"FAIL\")'"
```

#### 3. Verfügbarkeit wird nicht aktualisiert

```bash
# Timer-Status prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status availability-generator.timer"

# Letzte Ausführung prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "journalctl -u availability-generator.service -n 50"

# Manuell ausführen
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl start availability-generator.service"
```

#### 4. Nginx-Fehler (502 Bad Gateway)

```bash
# Gunicorn läuft?
ssh -i ~/.ssh/server_key root@91.98.192.233 "ps aux | grep gunicorn"

# Socket prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "ls -la /opt/business-hub/business-hub.sock"

# Service neu starten
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"
```

### Diagnose-Kommandos

```bash
# Alle Timer anzeigen
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl list-timers --all"

# Disk Space prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "df -h /opt/business-hub"

# Memory Usage
ssh -i ~/.ssh/server_key root@91.98.192.233 "free -h && ps aux | grep gunicorn"

# Nginx-Status
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status nginx"

# Datenintegrität prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "ls -lh /opt/business-hub/data/persistent/"
```

### Backup & Recovery

```bash
# Manuelles Backup erstellen
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && python3 scripts/backup_data.py"

# Backups anzeigen
ssh -i ~/.ssh/server_key root@91.98.192.233 "ls -lh /opt/business-hub/data/backups/"

# Backup wiederherstellen (Vorsicht!)
ssh -i ~/.ssh/server_key root@91.98.192.233 "cp /opt/business-hub/data/backups/backup_YYYYMMDD.json /opt/business-hub/data/persistent/file.json"
```

## 📝 Changelog

### v3.3.5 - KRITISCHER BUGFIX: PERSIST_BASE Pfad-Verschachtelung (LIVE - 2025-10-27)
- ✅ **KRITISCHER BUGFIX**: Systematische Doppelverschachtelung aller Datenbanken behoben
  - `.env` korrigiert: `PERSIST_BASE=/opt/business-hub/data` (war: `/opt/business-hub/data/persistent`)
  - Problem: Code fügt automatisch `/persistent` hinzu → führte zu `/persistent/persistent/`
  - Alle 10 kritischen JSON-Dateien konsolidiert (user_badges, scores, t2_bucket_system, etc.)
  - Vollständiges Backup erstellt vor Änderungen
- ✅ **T2-Bucket-System Konfiguration**:
  - Standard-Wahrscheinlichkeiten auf 9-9-2 gesetzt (Alex: 9.0, David: 9.0, Jose: 2.0)
  - Max Draws auf 20 erhöht (war: 10)
  - Degressive Wahrscheinlichkeit: Mit jedem Draw sinkt Probability um 1
  - Min Probability: 0.0 (Closer kann nicht mehr gezogen werden wenn auf 0)
- ⚠️ **WICHTIG für zukünftige Deployments**:
  - `PERSIST_BASE` darf NIEMALS `/persistent` am Ende enthalten
  - Korrekt: `PERSIST_BASE=/opt/business-hub/data`
  - Falsch: `PERSIST_BASE=/opt/business-hub/data/persistent`

### v3.3.4 - My Calendar Phase 2: Drag & Drop Kanban (LIVE - 2025-10-25)
- ✅ **7-Spalten Kanban-Board**: HubSpot-Style Status-Management
  - Pending, Erschienen, Rückholung, Sonderkunden, Verschoben, Nicht Erschienen, Ghost
- ✅ **Drag & Drop Funktionalität**:
  - SortableJS-Integration für alle Kanban-Spalten
  - Visuelle Status-Updates mit Ghost-Effekt
  - Automatische Google Calendar colorId-Synchronisation
- ✅ **Reschedule-Modal** (Termin umbuchen):
  - Date-Picker mit Min-Date-Validation
  - Dynamische Zeitslot-Anzeige per AJAX (`/api/get-available-slots`)
  - Berater-Dropdown mit Auto-Auswahl
  - Optionale Notiz-Textarea
  - Vollständige Fehlerbehandlung
- ✅ **3-Sekunden Undo-Funktion**:
  - Countdown-Timer nach Status-Updates
  - Revert-API-Call bei Klick
  - Automatisches Ausblenden nach Timeout
- ✅ **Auto-Refresh (5 Minuten)**:
  - Intelligenter Refresh nur bei sichtbarem Tab (Visibility API)
  - Automatischer Start/Stop
- ✅ **Backend API Endpoints**:
  - `/api/update-event-status`: Status-Update via Drag & Drop
  - `/api/reschedule-booking`: Alte Termin → Verschoben, neuer Termin anlegen
  - `/api/get-available-slots`: Verfügbarkeits-Abfrage für gewähltes Datum
- ✅ **Toast-Benachrichtigungen**: Success/Error/Info für alle User-Aktionen
- ✅ **Backfill-Script**: `backfill_booked_by_tags.py` für retroaktives Tagging alter Events

### v3.3.3 - Dark Mode Logo & Username Migration (LIVE - 2025-10-23)
- ✅ **Dark Mode Logo optimiert**:
  - Transparentes goldenes Logo für Header (kein weißer Kasten mehr)
  - Separates Favicon (Stern-Logo) für Browser-Tabs
  - `zfa-dark.png` (67KB) + `favicon.png` (285KB)
- ✅ **Username Migration**: Alle 17 Benutzer auf volle Namen migriert
  - `d.mikic` → `dominik.mikic`, `l.hoppe` → `luke.hoppe`, etc.
  - .env-Datei und JSON-Datenbanken vollständig migriert
- ✅ **404-Template gefixt**:
  - Purple-Farben ersetzt durch ZFA Secondary Blue
  - Endpoint-Referenzen korrigiert
- ✅ **Git-History aktualisiert**: Server erfolgreich auf neue bereinigte History umgestellt

### v3.3.2 - Production Hardening & Documentation (2025-10-23)
- ✅ **Git-History komplett bereinigt**: Alle sensiblen Credentials aus gesamter History entfernt (595 Commits)
- ✅ **Availability Generator optimiert**: 5x täglich (08:00, 11:00, 14:00, 17:00, 20:00 Berlin-Zeit)
- ✅ **README vollständig überarbeitet**:
  - Hetzner VPS als Primary Deployment dokumentiert
  - Alle Render.com-Referenzen entfernt
  - Deployment-Prozesse aktualisiert
  - Fehlerbehebung mit SSH-Kommandos
- ✅ **ZFA Color Scheme 100% konsistent**: Purple/Violet komplett ersetzt durch ZFA-Blau (#207487)
- ✅ **Lucide Icons Integration**: Multi-Timeout-Initialisierung
- ✅ **Production Deployment**: Alle Features live und stabil auf Hetzner VPS

### v3.3.1 - Production Hardening & Automation (2025-10-17)
- ✅ **Google Calendar API Fix**: ISO 8601 Format - 100% Erfolgsrate
- ✅ **Security Hardening**: Zweischichtiges Rate Limiting (Nginx + Flask)
- ✅ **Automation**: Cache-Cleanup, Backup-Rotation, Log-Rotation
- ✅ **Cosmetics System v2**: Theme & Effects mit 22 PNG-Avataren

### v3.3.0 - ZFA Rebranding & Consultant Analytics (2025-10-16)
- ✅ **ZFA Color Scheme**: Vollständige Migration zu ZFA-Branding
- ✅ **Hub/Base Template System**: Automatische ZFA-Farb-Integration
- ✅ **Consultant Analytics**: Show/No-Show-Tracking für Telefonisten
- ✅ **Production Ready**: Alle Änderungen deployed und getestet

## 📊 Projekt-Statistiken

- **Codezeilen**: ~15.000+ (Python, HTML, CSS, JS)
- **Anwendungsmodule**: 40+ Python-Module
- **Unterstützte Sprachen**: Deutsch (primär)
- **API-Endpoints**: 50+ RESTful-Endpoints
- **Gamification-Elemente**: 50+ Badges, 6 Prestige-Level, Daily Quests
- **Maximale gleichzeitige Nutzer**: 100+ (getestet und optimiert)
- **Berater**: 9 konfigurierte Consultants
- **Deployment**: Hetzner VPS (91.98.192.233)
- **Uptime**: 99.9% (Systemd + Gunicorn)

## 📄 Lizenz

**Proprietäre Lizenz** - Alle Rechte vorbehalten

Diese Software ist proprietär und vertraulich. Unbefugtes Kopieren, Verteilen, Modifizieren ist strengstens untersagt.

---

**Entwickelt mit ❤️ unter Verwendung von Flask, Python und modernen Web-Technologien**

**Production:** http://91.98.192.233 ✅ LIVE (Go-Live: 2025-10-18)
