# 🎯 Slot Booking Webapp

Eine moderne Webanwendung für die Terminbuchung mit integriertem Achievement-System, Tracking und Analytics.

## ✨ Features

### 🏆 Achievement System
- **Badge-System**: Sammle Badges für verschiedene Leistungen
- **Tägliche Challenges**: Erreiche tägliche Punkteziele
- **Wöchentliche/Monatliche MVPs**: Werde zum besten Telefonisten
- **Streak-System**: Bleibe konstant aktiv
- **Spezial-Badges**: Für besondere Leistungen (Nachteule, etc.)

### 📊 Tracking & Analytics
- **Automatische No-Show Erkennung**: Erkennt nicht erschienene Kunden
- **Kundenprofile**: Verfolgt Zuverlässigkeit und Risiko-Level
- **Performance-Dashboard**: Detaillierte Statistiken für Admins
- **Wöchentliche Berichte**: Automatische Auswertungen
- **ML-Vorbereitung**: Datenexport für Machine Learning

### 🎨 Gamification
- **Punkte-System**: Verdiene Punkte für Buchungen
- **Champion-System**: Monatliche Bestenlisten
- **Badge-Übersicht**: Zeige deine Erfolge
- **Leaderboards**: Vergleiche dich mit Kollegen

### 🔧 Technische Features
- **Google Calendar Integration**: Vollständige Kalender-Synchronisation
- **Automatische Verfügbarkeit**: Generiert Slots basierend auf Berater-Kalendern
- **Color-Coding**: Intelligente Farbzuordnung für Outcomes
- **Caching-System**: Performance-Optimierung durch intelligentes Caching
- **Real-time Updates**: Server-Sent Events für Live-Updates
- **Export-Funktionen**: JSON, CSV, PDF Export für alle Daten
- **Admin-Dashboard**: Erweiterte Funktionen für Administratoren

## 🚀 Installation

### Voraussetzungen
- Python 3.11+
- Google Calendar API Zugriff
- Service Account Credentials

### Setup
1. **Repository klonen**
   ```bash
   git clone <repository-url>
   cd slot_booking_webapp
   ```

2. **Dependencies installieren**
   ```bash
   pip install -r requirements.txt
   ```

3. **Umgebungsvariablen setzen**
   ```bash
   # Google Calendar Credentials
   export GOOGLE_CREDS_BASE64="<base64-encoded-service-account-json>"
   export CENTRAL_CALENDAR_ID="zentralkalenderzfa@gmail.com"
   
   # User Management
   export USERLIST="user1:pass1,user2:pass2"
   
   # Flask Secret
   export SECRET_KEY="your-secret-key"
   ```

4. **Anwendung starten**
   ```bash
   python slot_booking_webapp.py
   ```

## 📋 Cron Jobs

Die Anwendung verwendet GitHub Actions für automatische Tasks:

### 🕐 Availability Generation
- **Zeit**: Mo-Fr, 5-14 Uhr UTC (stündlich)
- **Datei**: `.github/workflows/availability-cron.yml`
- **Funktion**: Generiert verfügbare Slots basierend auf Berater-Kalendern

### 📊 Daily Outcome Check
- **Zeit**: Täglich 19:00 UTC (21:00 Berlin)
- **Datei**: `.github/workflows/daily-outcome-check.yml`
- **Funktion**: Erkennt No-Shows und aktualisiert Kundenprofile

### 🏆 Achievement Check
- **Zeit**: Täglich 20:00 UTC (22:00 Berlin)
- **Datei**: `.github/workflows/achievement-check.yml`
- **Funktion**: Vergibt MVP-Badges und aktualisiert Statistiken

## 🎨 Color Mapping

Das System verwendet ein einheitliches Color-Mapping:

| Color ID | Name | Outcome | Verfügbarkeit |
|----------|------|---------|---------------|
| 2 | Grün | Completed | Blockiert |
| 7 | Blau | Completed | Blockiert |
| 5 | Gelb | Completed | Blockiert |
| 3 | Weintraube | Completed | Blockiert |
| 9 | Graphit | Completed | Blockiert |
| 10 | Flamingo | Completed | Blockiert |
| **11** | **Tomate** | **No-Show** | **Blockiert NICHT** |
| **6** | **Mandarine** | **Cancelled** | **Blockiert NICHT** |

## 📁 Projektstruktur

```
slot_booking_webapp/
├── slot_booking_webapp.py      # Hauptanwendung
├── tracking_system.py          # Tracking & Analytics
├── achievement_system.py       # Badge & Gamification
├── generate_availability.py    # Slot-Generierung
├── color_mapping.py           # Zentrale Color-Definition
├── creds_loader.py            # Google Credentials
├── test_integration.py        # Integration Tests
├── requirements.txt           # Python Dependencies
├── render.yaml               # Deployment Config
├── .github/workflows/        # GitHub Actions
│   ├── availability-cron.yml
│   ├── daily-outcome-check.yml
│   └── achievement-check.yml
├── static/                   # Statische Dateien
│   ├── availability.json     # Verfügbare Slots
│   ├── scores.json          # User-Punkte
│   ├── champions.json       # Monatliche Champions
│   ├── user_badges.json     # User-Badges
│   └── daily_user_stats.json # Tägliche Statistiken
├── data/tracking/           # Tracking-Daten
│   ├── bookings.jsonl       # Buchungen
│   ├── outcomes.jsonl       # Outcomes
│   ├── daily_metrics.json   # Tagesmetriken
│   └── customer_profiles.json # Kundenprofile
└── templates/               # HTML Templates
    ├── index.html           # Hauptseite
    ├── badges.html          # Badge-Übersicht
    ├── scoreboard.html      # Punkte-Rangliste
    ├── admin_dashboard.html # Admin-Dashboard
    └── ...
```

## 🔧 Konfiguration

### Berater-Kalender
In `generate_availability.py`:
```python
consultants = {
    "Daniel": "daniel.herbort.zfa@gmail.com",
    "Simon": "simonmast9@gmail.com",
    # ... weitere Berater
}
```

### Verfügbare Zeiten
```python
slots = {
    "Mo": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    "Di": ["11:00", "14:00", "16:00", "18:00", "20:00"],
    # ... weitere Tage
}
```

### Admin-User
In `slot_booking_webapp.py`:
```python
admin_users = ["admin", "administrator", "Jose", "Simon"]
```

## 🧪 Testing

Führe die Integration-Tests aus:
```bash
python test_integration.py
```

## 🛠 Deployment & Persistenz (Render)

- Persistent Disk: 1 GB
- Mount Path: `/opt/render/project/src/persist`
- `render.yaml` legt Symlinks `static/` und `data/` → Volume und ruft `initialize_persistence.py` auf

### Wichtige ENV Variablen
- `SECRET_KEY`: Flask Session Secret
- `ADMIN_USERS`: Komma-separierte Adminliste, z. B. `admin,Jose,Simon`
- `CRON_TOKEN`: Secret für `/admin/maintenance/run`
- `CENTRAL_CALENDAR_ID`: Google Calendar Account
- Render Secrets: `GOOGLE_CREDS_BASE64` (Service Account, Base64)

## 🕒 Tägliche Maintenance

### Option A – Render Scheduler
- HTTP-Call: `GET /admin/maintenance/run` mit Header `X-CRON-TOKEN: $CRON_TOKEN`

### Option B – GitHub Actions (empfohlen)
- Workflow: `.github/workflows/daily-maintenance.yml`
- Secrets: `MAINTENANCE_URL`, `CRON_TOKEN`

## 🔐 Sicherheit
- Security-Header (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- Session-Cookies: `HttpOnly`, `Secure`, `SameSite=Lax`
- Request-Body-Limit: 2 MB

## 📊 Monitoring

### Logs
- Application Logs: `logs/` Verzeichnis
- GitHub Actions: Repository Actions Tab
- Render Logs: Render Dashboard

### Metriken
- No-Show Rate: Automatische Erkennung
- Performance Dashboard: Admin-Bereich
- Weekly Reports: Automatische Generierung

## 🤝 Contributing

1. Fork das Repository
2. Erstelle einen Feature Branch
3. Führe Tests aus: `python test_integration.py`
4. Committe deine Änderungen
5. Erstelle einen Pull Request

## 📝 Changelog

### v2.1.0 - Performance & Analytics Enhancement
- ✅ Caching-System implementiert
- ✅ Real-time Updates mit Server-Sent Events
- ✅ Erweiterte Export-Funktionen (JSON, CSV, PDF)
- ✅ Analytics-Funktionen vollständig implementiert
- ✅ Verbessertes Error Handling
- ✅ Zentrale Datums-Formatierung
- ✅ Performance-Optimierungen

### v2.0.0 - Achievement System Integration
- ✅ Achievement System vollständig integriert
- ✅ Badge-System mit UI
- ✅ Automatische MVP-Vergabe
- ✅ Zentrale Color-Definition
- ✅ Bereinigte Dependencies
- ✅ Integration Tests
- ✅ Neue GitHub Actions Workflows

### v1.0.0 - Initial Release
- ✅ Grundlegende Buchungsfunktionalität
- ✅ Google Calendar Integration
- ✅ Tracking System
- ✅ Admin Dashboard

## 📞 Support

Bei Fragen oder Problemen:
1. Prüfe die GitHub Issues
2. Schaue in die Logs
3. Führe die Integration Tests aus
4. Erstelle ein Issue mit detaillierter Beschreibung

## 📄 Lizenz

Proprietär - Alle Rechte vorbehalten 
