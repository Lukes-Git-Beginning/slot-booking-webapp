# CLAUDE.md

**Professionelle Anleitungen für Claude Code - Central Business Tool Hub**

---

## 📚 WICHTIG: Vollständige Dokumentation

**Vor dem Start IMMER die README.md lesen!**

Die README.md enthält:
- ✅ Projektübersicht & Architektur
- ✅ Installation & Setup
- ✅ Testing & Debugging
- ✅ Error Handling Details
- ✅ Feature-Dokumentation
- ✅ Version-Historie
- ✅ Troubleshooting

**Diese CLAUDE.md enthält NUR:**
- 🚀 Deployment-Workflow (KRITISCH!)
- 🔧 Server-Details & Quick-Reference
- 📝 Git-Richtlinien

---

## 📋 Projektübersicht

**Central Business Tool Hub** - Multi-Tool-Plattform mit Slot-Booking, T2-Closer-System und Analytics.

**Hauptkomponenten:**
- 🏠 Central Hub: Navigation, Authentifizierung, 2FA
- 🎯 Slot-Booking: Terminverwaltung, Google Calendar-Integration
- 📅 My Calendar: 7-Spalten Kanban mit Drag & Drop
- 👥 T2-Closer: T2-Termin-Management
- 📊 Analytics: Business Intelligence

**Technologie:**
- Backend: Flask 3.1.1, Python 3.11+, PostgreSQL
- Frontend: Tailwind CSS + DaisyUI (Hub/T2), Bootstrap 5.3.2 (Slots)
- Infrastruktur: Hetzner VPS, Nginx, Gunicorn (4 Workers)

---

## 🚀 Deployment Workflow (KRITISCH!)

**WORKFLOW:** Lokal → Server (Test) → GitHub

### 📍 Hetzner Production Server

- **Server:** `91.98.192.233`
- **SSH-Key:** `~/.ssh/server_key`
- **App-Pfad:** `/opt/business-hub/`
- **URL:** https://berater.zfa.gmbh/
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

---

## 🔧 Umgebungsvariablen

**Production:** `/opt/business-hub/.env`
**Development:** `.env` im Projektverzeichnis

```bash
# Core (ERFORDERLICH)
SECRET_KEY=<key>                              # Für Production generiert
USERLIST=user:pass,user2:pass2                # Komma-separierte User-Liste
ADMIN_USERS=admin1,admin2                     # Admin-Benutzer
PERSIST_BASE=/opt/business-hub/data           # VPS-Datenpfad (OHNE /persistent!)

# Google Calendar (ERFORDERLICH für Slots)
GOOGLE_CREDS_BASE64=<base64>                  # Service Account Credentials
CENTRAL_CALENDAR_ID=central-calendar@example.com
CONSULTANTS=Name1:consultant1@example.com,Name2:consultant2@example.com

# Sentry Error Tracking (Optional)
SENTRY_DSN=<your-sentry-dsn>                  # Get from https://sentry.io/settings/projects/
```

**WICHTIG:** Auf dem Hetzner-Server sind alle Placeholder durch echte Werte ersetzt.

---

## 📝 Git Commit-Richtlinien

- **NIEMALS** Claude Code-Attribution einschließen
- **NIEMALS** "🤖 Generated with Claude Code" oder "Co-Authored-By: Claude"
- Konventionelles Format: `feat:`, `fix:`, `docs:`, `refactor:`

---

## 🔔 Deployment Notifications

**Nach JEDEM `git push`:** Frage User ob Deployment-Notification erstellt werden soll!

**Methode (Flask App):**
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
        title='Feature XYZ ist live!',
        message='Beschreibung...',
        notification_type='success',
        show_popup=True,
        actions=[{'text': 'Jetzt testen', 'url': '/'}]
    )
    print('Notification erstellt!')
"
```

**Wann welche Rollen?**
- Neues Tool/Major-Feature: `all` (Pop-up: Ja)
- T2-System: `closer`, `coach`, `admin` (Pop-up: Ja)
- Slot-Booking: `opener`, `telefonist`, `admin` (Pop-up: Ja)
- Bugfixes: Betroffene Rollen (Pop-up: Nein)

---

## 👥 Rollen & Kalender (Kurzübersicht)

**System-Rollen (17 User):**
- **admin** (4): alexander.nehm, david.nehm, simon.mast, luke.hoppe
- **closer** (6): jose.torspecken, alexander.nehm, david.nehm, tim.kreisel, christian.mast, daniel.herbort
- **opener** (8): christian.mast, tim.kreisel, daniel.herbort, sonja.mast, simon.mast, dominik.mikic, ann-kathrin.welge, sara.mast
- **coach** (3): alexander.nehm, david.nehm, jose.torspecken
- **telefonist** (9): tim.kreisel, christian.mast, ladislav.heka, sonja.mast, simon.mast, alexandra.börner, yasmine.schumacher, ann-kathrin.welge, sara.mast
- **service** (3): alexandra.börner, vanessa.wagner, simon.mast

**T1 Slot-Booking (30min Slots):**
- **Standard (Vollzeit):** Ann-Kathrin, Sara, Dominik
- **Extended (Teilzeit/T2-Priorität):** Simon, Sonja, Tim, Christian, Daniel

**T2-System (2h Slots):**
- **Coaches (würfelbar):** David, Alexander, Jose
- **Berater (ausführend):** Christian, Daniel, Tim

---

## 📊 Aktuelle Version: v3.3.14 (LIVE)

**Letzte Änderungen (2025-12-11):**

- ✅ **T2 Feature Flag Rollback**: `T2_MODULAR_BLUEPRINTS: false` (zurück zu Legacy-System)
- ✅ **Bugfix: Bucket Config Import-Error**: 7 Import-Statements korrigiert
- ✅ **Bugfix: Draw History PostgreSQL Migration**: Analytics-Service migriert zu PostgreSQL-First
- ✅ **114 historische Draws** sichtbar (sara.mast: 30, ann-kathrin.welge: 26, dominik.mikic: 25)

**Deployment-Status:**
- 🟢 Production: LIVE auf http://91.98.192.233
- 🔄 Service: 4 Workers, 309MB RAM, stabil
- ⚡ PostgreSQL Query-Zeit: ~50ms

---

## 🚨 Error Handling (Kurzübersicht)

**Error-ID Format:** `<CATEGORY>-<YYYYMMDD>-<HHMMSS>-<4-CHAR-UUID>`

**Kategorien:**
- `BOOK-*` - Booking-Fehler
- `CAL-*` - Google Calendar API
- `TRK-*` - Tracking-Fehler
- `ERR-*` - Generisch

**Sentry Integration:** ✅ Konfiguriert (Deutsche Region)
- Dashboard: https://sentry.io
- Projekt: `business-hub`
- Tracking: 500+ Errors, Uncaught Exceptions, Performance

**Lokale Logs:** `data/persistent/logs/critical_errors.jsonl`

---

## 🔧 Quick Commands

```bash
# Lokale Entwicklung
python run.py                    # App starten
pytest tests/ -v                 # Tests ausführen

# Server-Diagnose
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub"
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"
curl -I https://berater.zfa.gmbh/health

# Git Status
git status && git log --oneline -10
```

---

**Für detaillierte Informationen siehe README.md!**
