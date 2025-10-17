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
│   ├── main.py          # Legacy Slots (Hauptroute)
│   ├── booking.py       # Legacy Booking-Logik
│   ├── calendar.py      # Legacy Kalender-Ansicht
│   ├── scoreboard.py    # Legacy Gamification
│   ├── user_profile.py  # Legacy Profile
│   ├── slots.py         # Neue Slots (Fallback)
│   └── t2.py            # T2-Closer
└── services/            # Business Logic
    ├── data_persistence.py
    ├── security_service.py
    ├── achievement_system.py
    ├── booking_service.py
    └── holiday_service.py
```

**Blueprint-Registrierung:** Legacy Slots-Blueprints (`main_bp`, `booking_bp`, etc.) werden ZUERST registriert und haben Priorität über neue `slots_bp`.

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
PERSIST_BASE=/opt/business-hub/data/persistent # VPS-Datenpfad

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

### Cosmetics System (Themes & Effects)
```python
# Themes & Effects werden automatisch geladen wenn user/base.html erweitert wird
# Backend-Integration:
from app.services.cosmetics_shop import cosmetics_shop

# User-Theme laden (in hub.py get_dashboard_data)
user_theme = get_user_active_theme(username)  # Returns theme dict or None

# Aktive Effects API (automatisch von JavaScript geladen)
@hub_bp.route('/api/cosmetics/active-effects')
def api_active_effects():
    user_cosmetics = cosmetics_shop.get_user_cosmetics(session['user'])
    active_effects = user_cosmetics.get('active', {}).get('effects', [])
    return jsonify({'success': True, 'effects': active_effects})

# Custom Events für Effect-Trigger (im Frontend JavaScript)
document.dispatchEvent(new CustomEvent('achievement-unlocked'));
document.dispatchEvent(new CustomEvent('booking-success'));
```

**Verfügbare Effects:**
- `sparkle_trail` - 8 goldene Sparkles bei jedem Klick
- `confetti_explosion` - 50 Konfetti-Partikel bei Achievements/Bookings
- `screen_shake` - 500ms Kamera-Shake bei Achievement-Unlock
- `keyboard_sounds` - Tastatur-Sound-Framework (Web Audio API)
- `booking_fanfare` - C5-Note mit Decay bei erfolgreicher Buchung

**Theme-System:**
- CSS Custom Properties: `--theme-primary`, `--theme-secondary`, `--theme-accent`
- Automatische Injection in `hub/base.html` wenn user_theme gesetzt
- Überschreibt `.glass`, `.btn-primary`, `.gradient-bg` Klassen
- 6+ vordefinierte Themes (sunset, ocean, forest, lavender, fire, rainbow)

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

## Frontend-Technologie

### UI-Framework & Design - ZFA Branding (v3.3.0)
- **Tailwind CSS + DaisyUI**: Lokal gehostet in `static/` (alle neuen Templates)
- **Lucide Icons**: Lokal gehostet für moderne Icon-Library
- **Bootstrap 5.3.2**: Lokal gehostet für Legacy Slot-Booking (228KB)
- **Font Awesome 6.4.2**: Lokal gehostet für Legacy Templates (100KB)
- **Glassmorphism-Design**: CSS Custom Properties mit Backdrop-Filter
- **ZFA Color Scheme**: Konsistentes Branding über alle Tools

### ZFA Color Scheme (Zentrum für Finanzielle Aufklärung)
```javascript
// Tailwind Config (in templates/hub/base.html und T2)
tailwind.config = {
  theme: {
    extend: {
      colors: {
        'primary': '#d4af6a',        // ZFA Gold
        'primary-dark': '#c2ae7f',   // ZFA Gold Dark
        'secondary': '#207487',      // ZFA Blau
        'accent': '#294c5d',         // ZFA Dunkelblau
      },
    },
  },
}
```

### Template-Architektur
```
templates/
├── hub/                    # Central Hub Templates (ZFA)
│   ├── base.html          # 🎨 Master Template mit ZFA Tailwind Config
│   └── dashboard.html     # Hub Dashboard
├── t2/                     # T2-Closer Templates (ZFA)
│   ├── base.html          # T2 Base mit ZFA Farben
│   └── ...
├── slots/                  # Legacy Slot-Booking (Bootstrap 5)
│   ├── base.html          # Bootstrap 5 + FontAwesome
│   └── dashboard.html     # Legacy Layout mit Glassmorphism
├── login.html             # 🆕 ZFA Branding (Gold/Blau)
├── calendar_view.html     # 🆕 ZFA Navigation
├── my_calendar.html       # 🆕 Consultant Analytics mit ZFA
├── scoreboard.html        # Erweitert hub/base.html (automatisch ZFA)
├── gamification.html      # Erweitert hub/base.html (automatisch ZFA)
├── daily_quests.html      # Erweitert hub/base.html (automatisch ZFA)
├── prestige_dashboard.html # Erweitert hub/base.html (automatisch ZFA)
└── cosmetics_shop.html    # Erweitert hub/base.html (automatisch ZFA)
```

**Wichtig:**
- Alle Templates die `hub/base.html` erweitern, erben automatisch ZFA-Farben
- Slot-Booking Templates nutzen Bootstrap 5 und behalten Legacy-Struktur
- T2-Templates haben eigene base.html mit ZFA-Tailwind-Config

## Projektstatus

### Version: v3.3.1 (Production Hardening & Automation)
- ✅ Central Hub Architecture
- ✅ Security Center (2FA + Password Management)
- ✅ T2-Closer Tool
- ✅ Vollständiges Gamification-System
- ✅ Analytics Dashboard
- ✅ ZFA Color Scheme vollständig integriert
- ✅ Consultant Analytics mit Show/No-Show Tracking
- ✅ Glassmorphism-Design mit Bootstrap 5
- ✅ Lokale Asset-Hosting (Bootstrap + FontAwesome)
- ✅ VPS Deployment auf Hetzner
- ✅ **Zweischichtige Rate Limiting** (Nginx + Flask)
- ✅ **Automatische Cache-Cleanup** (Systemd Timer)
- ✅ **Backup Rotation** (Cron Daily)

### Deployment-Status
- **Testserver:** http://91.98.192.233 ✅ LIVE & PRODUCTION-READY
- **Production:** Go-Live am Montag (2025-10-21)

### Letzte Updates (2025-10-17)
- ✅ **KRITISCH** Google Calendar API Fix (ISO 8601 Format) - 100% Erfolgsrate
- ✅ **Security Hardening**: Nginx + Flask Rate Limiting deployed und getestet
- ✅ **Automation**: Cache-Cleanup (Systemd), Backup-Rotation (Cron)
- ✅ **Log Rotation**: Verifiziert funktioniert (Daily, 14 Tage, komprimiert)
- ✅ **System Status**: Service stabil, 216MB RAM, 4 Gunicorn Workers
- ✅ **Monitoring**: Systemd Timer (Cache), Cron (Backups), Logrotate (Logs)
- ✅ **Cosmetics System v2**: Vollständige Theme & Effects Funktionalität deployed
  - Canvas-basiertes Particle System (sparkle_trail, confetti_explosion, screen_shake)
  - CSS Theme Injection mit Custom Properties (6+ Themes verfügbar)
  - Event-driven Architecture für Achievement/Booking-Trigger
  - Web Audio API Integration für Sounds (booking_fanfare, keyboard_sounds)
  - 22 Avatar PNGs aus C:\Users\Luke\Pictures\Avatare integriert
