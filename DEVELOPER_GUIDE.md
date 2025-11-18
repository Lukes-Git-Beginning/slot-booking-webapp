# 👨‍💻 Developer Guide - Central Business Tool Hub

Vollständiger Entwickler-Leitfaden für Onboarding, Entwicklung und Troubleshooting.

---

## 📋 Inhaltsverzeichnis

- [Quick-Start](#-quick-start)
- [Architecture-Overview](#-architecture-overview)
- [Development-Workflow](#-development-workflow)
- [Code-Konventionen](#-code-konventionen)
- [Testing & Debugging](#-testing--debugging)
- [Troubleshooting](#-troubleshooting)
- [Performance-Optimierung](#-performance-optimierung)

---

## 🚀 Quick-Start

### 1. Repository klonen und Setup

```bash
# Repository klonen
git clone <repository-url>
cd slot_booking_webapp

# Virtual Environment erstellen
python -m venv venv

# Aktivieren (Windows)
venv\Scripts\activate

# Aktivieren (Linux/Mac)
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt
```

### 2. Umgebungsvariablen konfigurieren

Erstelle `.env` Datei im Root-Verzeichnis:

```bash
# Core Configuration
SECRET_KEY=<generiere-zufälligen-key>
USERLIST=user1:pass1,user2:pass2
ADMIN_USERS=admin1,admin2
PERSIST_BASE=data  # OHNE /persistent am Ende!

# Google Calendar API
GOOGLE_CREDS_BASE64=<base64-encoded-service-account-json>
CENTRAL_CALENDAR_ID=<calendar-email>
CONSULTANTS=berater1:email1,berater2:email2

# Optional: Sentry Error Tracking
# SENTRY_DSN=<your-sentry-dsn>
```

**WICHTIG**: Secret-Key generieren:
```python
import secrets
print(secrets.token_hex(32))
```

### 3. Anwendung starten

```bash
# Development-Server
python run.py

# App läuft auf http://localhost:5001
```

### 4. Erste Schritte

1. **Login**: Nutze Credentials aus `USERLIST`
2. **Admin-Zugang**: User aus `ADMIN_USERS` haben Admin-Rechte
3. **Google Calendar**: Service Account muss Zugriff auf Kalender haben
4. **Datenbank**: Wird automatisch in `data/persistent/` erstellt

---

## 🏗 Architecture-Overview

### Application Factory Pattern

```python
app/
├── __init__.py           # Flask App Factory
├── config/               # Konfiguration
│   ├── base.py          # Base Config
│   └── legacy_config.py # Logging Config
├── core/                 # Shared Infrastructure
│   ├── extensions.py    # Flask Extensions (Limiter, Cache, etc.)
│   └── google_calendar.py
├── routes/              # HTTP Blueprints
│   ├── hub.py           # Central Hub (/hub/...)
│   ├── auth.py          # Authentication (/login, /logout)
│   ├── admin/           # Admin Features (/admin/...)
│   ├── main.py          # Legacy Slots (/)
│   └── t2.py            # T2-Closer (/t2/...)
└── services/            # Business Logic
    ├── data_persistence.py
    ├── activity_tracking.py
    └── ...
```

### Blueprint-Registrierung (wichtig!)

Reihenfolge in `app/__init__.py`:
1. **Legacy Slots-Blueprints** (`main_bp`, `booking_bp`) - ZUERST registriert
2. **Neue Blueprints** (`slots_bp`, `hub_bp`) - DANACH registriert

⚠️ **Warum?** Legacy-Routes haben Priorität für Backward-Compatibility.

### Datenpersistenz-Layer

**JSON-basierte Persistenz** (production-ready):
```python
from app.services.data_persistence import data_persistence

# Daten laden
data = data_persistence.load_data('user_stats', default={})

# Daten speichern
data_persistence.save_data('user_stats', data)

# Backup erstellen
data_persistence.create_backup()
```

**Wichtige Datenbanken:**
- `user_stats.json` - User-Statistiken
- `scores.json` - Punkte & Termine
- `user_badges.json` - Achievement-System
- `login_history.json` - Login-Tracking
- `online_sessions.json` - Online-Status
- `t2_bucket_system.json` - T2-Würfelsystem

### Google Calendar Integration

```python
from app.core.google_calendar import GoogleCalendarService

cal_service = GoogleCalendarService()

# Events abrufen (mit Pagination)
events = cal_service.get_all_events_paginated(
    calendar_id='primary',
    max_results=2500
)

# Event erstellen
event = cal_service.create_event(
    calendar_id='primary',
    summary='Termin',
    start_time='2025-11-18T14:00:00',
    end_time='2025-11-18T15:00:00'
)
```

**Rate Limiting & Quota:**
- Google Calendar API: 1M Requests/Tag
- Aktuell: ~0.01% Nutzung
- Automatisches Rate Limiting in `GoogleCalendarService`

---

## 💻 Development-Workflow

### 1. Feature-Branch erstellen

```bash
git checkout -b feature/mein-feature
```

### 2. Code schreiben

**Services erstellen** (Business Logic):
```python
# app/services/my_service.py
class MyService:
    def __init__(self):
        self.data_file = 'my_data'

    def do_something(self, user):
        data = data_persistence.load_data(self.data_file, default={})
        # Business Logic hier
        data_persistence.save_data(self.data_file, data)
        return result

# Singleton instance
my_service = MyService()
```

**Routes erstellen** (HTTP-Handling):
```python
# app/routes/my_routes.py
from flask import Blueprint, render_template, jsonify
from app.services.my_service import my_service
from app.utils.decorators import require_login

my_bp = Blueprint('my_feature', __name__, url_prefix='/my')

@my_bp.route('/dashboard')
@require_login
def dashboard():
    user = session.get('user')
    data = my_service.do_something(user)
    return render_template('my_dashboard.html', data=data)
```

**Blueprint registrieren** in `app/__init__.py`:
```python
from app.routes.my_routes import my_bp
app.register_blueprint(my_bp)
```

### 3. Templates erstellen

```html
<!-- templates/my_dashboard.html -->
{% extends "hub/base.html" %}

{% block content %}
<div class="container">
    <h1>{{ data.title }}</h1>
    <!-- Content hier -->
</div>
{% endblock %}
```

### 4. Testen

```bash
# Lokaler Test
python run.py

# Integration Test (wenn vorhanden)
python test_integration.py
```

### 5. Commit & Push

```bash
git add .
git commit -m "feat: Add my feature

- Feature-Beschreibung
- Was wurde geändert
- Warum wurde es geändert"

git push origin feature/mein-feature
```

**Commit-Konventionen:**
- `feat:` - Neues Feature
- `fix:` - Bugfix
- `docs:` - Dokumentation
- `refactor:` - Code-Refactoring
- `test:` - Tests hinzufügen/ändern
- `chore:` - Build/Config-Änderungen

---

## 📐 Code-Konventionen

### Python Style

**PEP 8 Konventionen** befolgen:
```python
# UTF-8 Encoding
# -*- coding: utf-8 -*-

# Type Hints verwenden
def calculate_level(xp: int) -> dict:
    """
    Berechnet Level basierend auf XP

    Args:
        xp: User XP-Punkte

    Returns:
        Dict mit level, title, next_level_xp
    """
    pass

# Logging statt print()
import logging
logger = logging.getLogger(__name__)
logger.info(f"User {user} performed action")
```

### Flask Best Practices

**1. Blueprints für Modularität:**
```python
# Gut
from flask import Blueprint
my_bp = Blueprint('feature', __name__, url_prefix='/feature')

# Schlecht
@app.route('/feature/route')  # Direkt an App
```

**2. Services für Business Logic:**
```python
# Gut
from app.services.my_service import my_service
result = my_service.process_data(user)

# Schlecht
def route():
    # 200 Zeilen Business Logic in Route
```

**3. Templates erweitern:**
```html
<!-- Gut -->
{% extends "hub/base.html" %}

<!-- Schlecht -->
<!-- Komplettes HTML kopieren -->
```

### JavaScript Konventionen

```javascript
// ES6+ Syntax verwenden
const calculateTotal = (items) => {
    return items.reduce((sum, item) => sum + item.price, 0);
};

// Async/Await für AJAX
async function loadData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error loading data:', error);
    }
}
```

---

## 🧪 Testing & Debugging

### Logging aktivieren

```bash
# In .env
LOG_LEVEL=DEBUG  # INFO, WARNING, ERROR
```

### Flask Debug-Mode

```python
# run.py
if __name__ == "__main__":
    app.run(debug=True, port=5001)  # Auto-Reload bei Änderungen
```

### Health-Check nutzen

```bash
# Umfassender Health-Check
curl http://localhost:5001/health

# Response:
{
    "status": "healthy",
    "version": "3.3.8",
    "checks": {
        "data_persistence": {"status": "healthy"},
        "google_calendar": {"status": "healthy"},
        "system_resources": {"memory_usage": "45.2%"}
    }
}
```

### Browser DevTools

**Console-Debugging:**
```javascript
// In Templates
console.log('Data:', {{ data|tojson }});
```

**Network-Tab:**
- Alle AJAX-Requests überwachen
- Status-Codes prüfen (200, 400, 500)
- Response-Payloads inspizieren

---

## 🔧 Troubleshooting

### Problem: `ModuleNotFoundError`

**Ursache:** Import-Pfade falsch

**Lösung:**
```python
# ❌ Falsch
from services.data_persistence import data_persistence

# ✅ Richtig
from app.services.data_persistence import data_persistence
```

### Problem: Google Calendar API-Fehler

**Symptom:** `403 Forbidden` oder `401 Unauthorized`

**Lösung:**
1. Service Account hat Zugriff auf Kalender?
2. `GOOGLE_CREDS_BASE64` korrekt encodiert?
   ```bash
   base64 -w 0 service_account.json
   ```
3. Calendar API in Google Cloud aktiviert?

### Problem: Session-Loss nach Restart

**Ursache:** `SECRET_KEY` ändert sich

**Lösung:**
```bash
# .env - Festen Secret-Key verwenden
SECRET_KEY=<permanent-generated-key>
```

### Problem: `PERSIST_BASE` Doppelverschachtelung

**Symptom:** Daten in `/persistent/persistent/` gespeichert

**Lösung:**
```bash
# ❌ Falsch
PERSIST_BASE=/opt/business-hub/data/persistent

# ✅ Richtig
PERSIST_BASE=/opt/business-hub/data
```

⚠️ **Code fügt automatisch `/persistent` hinzu!**

### Problem: Rate Limiting blockiert Requests

**Symptom:** `429 Too Many Requests`

**Lösung:**
```python
# Rate Limits in config/base.py anpassen
RATELIMIT_DEFAULT = "200 per day, 50 per hour"
```

### Problem: Template nicht gefunden

**Symptom:** `TemplateNotFound: my_template.html`

**Lösung:**
1. Template in `templates/` Ordner?
2. Pfad korrekt: `templates/my_feature/my_template.html`
3. Blueprint-Template-Folder:
   ```python
   my_bp = Blueprint('my', __name__,
                     template_folder='templates/my_feature')
   ```

### Problem: JSON-Daten korrupt

**Symptom:** `JSONDecodeError`

**Lösung:**
```bash
# Backup wiederherstellen
cp data/backups/backup_YYYYMMDD.json data/persistent/file.json
```

**Prevention:** Nutze `data_persistence.create_backup()` vor großen Änderungen

### Problem: 500 Internal Server Error

**Debugging:**
1. **Logs checken:**
   ```bash
   # Production
   ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"

   # Development
   # Siehe Console-Output von run.py
   ```

2. **Flask Debug-Mode:**
   ```python
   app.run(debug=True)  # Zeigt Traceback im Browser
   ```

3. **Sentry aktivieren** (optional):
   ```bash
   SENTRY_DSN=<your-dsn>
   ```

---

## ⚡ Performance-Optimierung

### 1. Caching nutzen

```python
from app.core.extensions import cache_manager

# Cache-Entry erstellen
cache_manager.set('my_key', data, ttl=300)  # 5 Min

# Cache-Entry laden
cached_data = cache_manager.get('my_key')
if cached_data is None:
    # Daten neu berechnen
    pass
```

### 2. Google Calendar Pagination

```python
# ❌ Schlecht - Fixed Limit
events = cal_service.get_events(max_results=100)

# ✅ Gut - Pagination
events = cal_service.get_all_events_paginated(max_results=2500)
```

### 3. Database-Queries optimieren

```python
# ❌ Schlecht - Mehrfaches Laden
for user in users:
    data = data_persistence.load_data('scores')
    user_score = data.get(user)

# ✅ Gut - Einmal laden
all_scores = data_persistence.load_data('scores')
for user in users:
    user_score = all_scores.get(user)
```

### 4. Frontend-Optimierung

**Lazy-Loading für Bilder:**
```html
<img src="image.jpg" loading="lazy">
```

**AJAX statt Full-Page-Reload:**
```javascript
// ✅ Gut - AJAX
fetch('/api/data').then(r => r.json()).then(updateUI);

// ❌ Schlecht - Full Reload
window.location.href = '/page';
```

### 5. Asset-Optimierung

**Minification** (TODO - Phase 3):
- CSS/JS minifizieren
- Tree-Shaking für ungenutzte Styles
- Lazy-Loading für Third-Party-Scripts

---

## 🚀 Deployment

Siehe `CLAUDE.md` für vollständige Deployment-Anleitung.

**Quick-Deployment auf Hetzner:**
```bash
# 1. Datei übertragen
scp -i ~/.ssh/server_key <file> root@91.98.192.233:/opt/business-hub/<path>

# 2. Service neu starten
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"

# 3. Logs prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"
```

---

## 📚 Weitere Ressourcen

- **CLAUDE.md**: Vollständige Projekt-Dokumentation für AI-Assistenten
- **README.md**: User-facing Dokumentation
- **Flask Docs**: https://flask.palletsprojects.com/
- **Google Calendar API**: https://developers.google.com/calendar/api

---

## 🤝 Support

Bei Fragen oder Problemen:
1. **Logs checken** (lokal oder Production)
2. **Health-Check** ausführen (`/health`)
3. **CLAUDE.md** konsultieren
4. **Git-History** durchsuchen für ähnliche Fixes

---

**Happy Coding! 🚀**
