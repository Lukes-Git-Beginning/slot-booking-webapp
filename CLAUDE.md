# CLAUDE.md

Diese Datei bietet Anleitungen für Claude Code (claude.ai/code) bei der Arbeit mit Code in diesem Repository.

## Projektübersicht

**Slot Booking Webapp** ist ein umfassendes Terminbuchungssystem auf Enterprise-Niveau mit fortschrittlicher Gamification, Analytics und Business Intelligence-Features. Dies ist nicht nur ein einfaches Buchungssystem - es ist eine voll ausgestattete Geschäftsanwendung mit ausgeklügeltem Nutzerengagement und Datenanalyse-Fähigkeiten.

### Hauptfunktionen
- 🎯 **Vollständige Terminverwaltung** - Multi-Berater-Buchung mit Google Calendar-Integration
- 🎮 **Fortschrittliche Gamification** - Achievement-Systeme, Badges, Level, Prestige, tägliche Quests, Cosmetics Shop
- 📊 **Business Intelligence** - Umfassende Analytics, Vorhersage-Einblicke, Kundenprofilerstellung
- 🔧 **Admin-Dashboard** - Vollständige administrative Kontrolle mit Reporting und Benutzerverwaltung
- 🎨 **Anpassungssystem** - Benutzer-Personalisierung mit Themes, Avataren und benutzerdefinierten Zielen
- 📱 **Moderne Architektur** - Produktionsreife Flask-Anwendung mit ordnungsgemäßer Trennung der Belange
- 🗓️ **Feiertags-Sperrung** - Automatische Sperrung deutscher Feiertage (NRW) mit Admin-Verwaltung

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

## Anwendungsarchitektur

### Moderne Flask-Struktur
Die Anwendung folgt einer professionellen Flask-Struktur mit:

```
app/
├── config/           # Umgebungsbasierte Konfiguration
│   ├── base.py      # Basis-Konfigurationsklassen
│   ├── development.py
│   └── production.py
├── core/            # Kern-Anwendungskomponenten
│   ├── extensions.py    # Flask-Extensions-Initialisierung
│   ├── google_calendar.py  # Google Calendar Service
│   └── middleware.py    # Request/Response-Middleware
├── routes/          # HTTP-Route-Handler (Blueprints)
│   ├── admin/       # Administrative Funktionen
│   │   ├── blocked_dates.py  # 🆕 Feiertags-/Sperrtermin-Verwaltung
│   │   ├── dashboard.py      # Admin-Dashboard
│   │   ├── reports.py        # Berichte
│   │   ├── users.py          # Benutzerverwaltung
│   │   └── telefonie.py      # Telefonie-Punkte
│   ├── gamification/ # Gamification-Features
│   ├── auth.py      # Authentifizierung
│   ├── booking.py   # Terminbuchung
│   ├── calendar.py  # Kalender-Ansichten
│   ├── main.py      # Haupt-Anwendungs-Routes
│   └── api.py       # JSON API-Endpoints
├── services/        # Business-Logic-Layer
│   ├── achievement_system.py  # Gamification-Engine
│   ├── booking_service.py     # Buchungs-Business-Logic
│   ├── data_persistence.py    # Datenspeicher-Abstraktion
│   ├── holiday_service.py     # 🆕 Feiertags-Service (NRW)
│   ├── level_system.py        # Benutzer-Progressions-System
│   ├── tracking_system.py     # Analytics und Tracking
│   └── weekly_points.py       # Punkte-Management
├── models/          # Datenmodelle (falls ORM verwendet)
└── utils/           # Hilfsfunktionen und Utilities
```

### Kern-Anwendungskomponenten
- **Flask Application Factory**: `app/__init__.py` - Modernes Flask App-Erstellungs-Pattern
- **Konfigurationsverwaltung**: `app/config/` - Umgebungsspezifische Einstellungen
- **Google Calendar-Integration**: `app/core/google_calendar.py` - Robuster Kalender-Service
- **Datenpersistenz-Layer**: `app/services/data_persistence.py` - Dual-Write-System
- **Gamification-Engine**: `app/services/achievement_system.py` - Vollständiges Engagement-System
- **Analytics-System**: `app/services/tracking_system.py` - Business Intelligence
- **Admin-Dashboard**: `app/routes/admin/` - Umfassende Verwaltungsschnittstelle
- **Feiertags-Service**: `app/services/holiday_service.py` - Deutsche NRW-Feiertage mit benutzerdefinierten Sperren

### Wichtige Architektur-Patterns

#### Datenspeicher-Strategie
Das App verwendet ein ausgeklügeltes Dual-Write-Persistenz-Pattern mit automatischer Provider-Erkennung:
- **VPS**: `/opt/business-hub/data/persistent/` (Hetzner, Strato, etc.)
- **Render.com**: `/opt/render/project/src/persist/persistent/`
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

### 🎯 Kern-Buchungsfeatures
- **Multi-Berater-Terminplanung**: Support für unbegrenzte Berater mit individuellen Kalendern
- **Echtzeit-Verfügbarkeit**: Stündliche Kalender-Scanning und Slot-Generierung
- **Konflikt-Prävention**: Erweiterte Buchungs-Validierung und Doppelbuchungs-Prävention
- **Kundenverwaltung**: Vollständige Kundenprofile mit Historie und Präferenzen
- **Ergebnis-Tracking**: Automatische Erkennung von Terminen, No-Shows und Stornierungen
- **Feiertags-Sperrung**: Automatische Sperrung deutscher NRW-Feiertage mit Admin-Verwaltung

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

### 🔧 Administrative Features
- **Benutzerverwaltung**: Vollständige Benutzer-Lebenszyklus-Verwaltung
- **Rollenbasierter Zugriff**: Admin/Benutzer-Berechtigungen mit granularen Kontrollen
- **Feiertags-Verwaltung**: Deutsche NRW-Feiertage mit benutzerdefinierten Sperren
- **Datenexport**: Umfassende Berichterstattung und Datenextraktion
- **System-Überwachung**: Performance-Metriken und Gesundheitschecks
- **Konfigurations-Management**: Dynamische Einstellungen und Feature-Toggles
- **Backup & Recovery**: Automatisierte Backups mit Aufbewahrungsrichtlinien

### 🎨 Anpassung & Personalisierung
- **Theme-System**: Multiple visuelle Themes und Farbschemata
- **Avatar-System**: Anpassbare Benutzerprofile mit freischaltbaren Komponenten
- **Dashboard-Anpassung**: Personalisierte Layouts und Widgets
- **Benachrichtigungs-Präferenzen**: Anpassbare Alerts und Updates
- **Persönliche Analytics**: Individuelle Einblicke und Fortschritts-Tracking

### Umgebungsvariablen & Konfiguration
- `GOOGLE_CREDS_BASE64`: Base64-kodierte Service Account JSON
- `CENTRAL_CALENDAR_ID`: Haupt-Kalender-ID
- `USERLIST`: Benutzer-Zugangsdaten (`user1:pass1,user2:pass2`)
- `SECRET_KEY`: Flask Session-Verschlüsselungs-Schlüssel
- `PERSIST_BASE`: Override für Persistenz-Verzeichnis
- `FLASK_ENV`: Umgebungseinstellung (development/production)
- `ADMIN_USERS`: Komma-getrennte Liste von Admin-Benutzernamen
- `CONSULTANTS`: Berater-Mapping (name:email Paare)
- `EXCLUDED_CHAMPION_USERS`: Benutzer ausgeschlossen von Leaderboards

### Kritische Dateien & Verzeichnisse
- `service_account.json`: Google Service Account-Zugangsdaten (niemals committen)
- `data/persistent/`: Primäre Datenspeicherung mit vollständigem Anwendungszustand
- `data/backups/`: Automatisiertes Backup-Verzeichnis mit Aufbewahrung
- `static/availability.json`: Generierte Slot-Verfügbarkeit (Legacy-Fallback)
- `app/config/`: Umgebungsspezifische Konfigurationsdateien
- `templates/`: Jinja2 HTML-Templates für alle Seiten
- `static/`: CSS, JavaScript und statische Assets

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
- [ ] Geplante Aufgaben konfiguriert (GitHub Actions)
- [ ] Überwachung und Logging aktiviert
- [ ] Backup-System operational

## Git Commit-Richtlinien
- **NIEMALS** Claude Code-Attribution in Commit-Nachrichten einschließen
- **NIEMALS** "🤖 Generated with [Claude Code]" oder "Co-Authored-By: Claude" hinzufügen
- Commit-Nachrichten sauber und professionell ohne AI-Tool-Referenzen halten
- Konventionelles Commit-Format verwenden: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
- Issue-Nummern referenzieren wenn anwendbar

## Projektstatus & Aktuelle Updates

### Aktuelle Version: v3.2+ (Enterprise-Grade mit Feiertags-System)
Die Anwendung hat sich zu einer ausgeklügelten Geschäftsplattform entwickelt mit:
- ✅ **Vollständiges Gamification-System**: Fortgeschrittene Engagement-Features
- ✅ **Business Intelligence**: Umfassende Analytics und Berichterstattung
- ✅ **Moderne Architektur**: Produktionsreife Flask-Anwendung
- ✅ **Administrative Dashboard**: Vollständige Verwaltungsfähigkeiten
- ✅ **Anpassungsplattform**: Benutzer-Personalisierungs-Features
- ✅ **Performance-Optimierung**: Caching, Deduplizierung, Fehlerbehandlung
- ✅ **Feiertags-Sperrung**: Deutsche NRW-Feiertage mit Admin-Verwaltung

### Neueste Feature-Ergänzungen
- ✅ **German NRW Holiday Blocking**: Automatische Sperrung deutscher Feiertage
- ✅ **Admin Feiertags-Interface**: Vollständige Verwaltung gesperrter Termine
- ✅ **Benutzerdefinierte Sperren**: Beliebige Termine mit Begründung sperren
- ✅ **Deutsche Lokalisierung**: Vollständige deutsche Übersetzung
- ✅ **Fallback-Mechanismen**: Robuste Fehlerbehandlung für fehlende Dependencies
- ✅ **Moderne Flask-Struktur**: Ordnungsgemäße Anwendungsorganisation

### Nächste Entwicklungsprioritäten
- 🔄 **API-Verbesserung**: Umfassende REST API für mobile/externe Apps
- 🔄 **Echtzeit-Features**: WebSocket-Integration für Live-Updates
- 🔄 **Machine Learning**: Predictive Analytics und Empfehlungs-Engine
- 🔄 **Mobile PWA**: Progressive Web App-Fähigkeiten
- 🔄 **Erweiterte Sicherheit**: Verbesserte Authentifizierung und Autorisierung

## Technische Implementierungs-Anleitung

### Arbeiten mit der Codebase

#### Wichtige Service-Klassen
```python
# Kern-Services - immer für größere Operationen importieren
from app.services.data_persistence import data_persistence
from app.services.achievement_system import achievement_system
from app.services.booking_service import BookingService
from app.services.tracking_system import tracking_system
from app.services.holiday_service import holiday_service  # 🆕 Feiertags-Service
from app.core.extensions import cache_manager, level_system
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
1. **Service-Klasse erstellen** in `app/services/` für Business Logic
2. **Route-Handler hinzufügen** in entsprechendem `app/routes/` Blueprint
3. **Konfiguration aktualisieren** in `app/config/base.py` falls nötig
4. **Tests hinzufügen** zu `test_integration.py`
5. **Dokumentation aktualisieren** sowohl in CLAUDE.md als auch README.md

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
├── blocked_dates.json         # 🆕 Gesperrte Termine (Feiertage + Custom)
├── user_badges.json          # Badge-Vergaben und Zeitstempel
├── user_levels.json          # XP und Level-Progression
├── daily_user_stats.json     # Tägliche Performance-Metriken
├── prestige_data.json        # Prestige-System-Daten
├── cosmetic_purchases.json   # Shop-Käufe und ausgerüstete Items
├── daily_quests.json         # Quest-Fortschritt und Abschlüsse
├── behavior_patterns.json    # Benutzer-Verhaltens-Analytics
├── weekly_points.json        # Telefonie-Punkte-System
├── champions.json            # Leaderboard-Daten
└── scores.json               # Gesamt-Scoring-System
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
# Erforderliche Umgebungsvariablen
GOOGLE_CREDS_BASE64=<base64-kodierte-zugangsdaten>
CENTRAL_CALENDAR_ID=<kalender-email>
SECRET_KEY=<starker-secret-key>
USERLIST=<user:pass,user2:pass2>

# Optionale Konfiguration
PERSIST_BASE=<custom-persistenz-pfad>
FLASK_ENV=<development|production>
ADMIN_USERS=<admin1,admin2>
```

#### Gesundheitschecks
```python
# Gesundheitscheck-Endpoints hinzufügen
@app.route('/health')
def health_check():
    """System-Gesundheits-Verifizierung"""
    checks = {
        'database': data_persistence.verify_integrity(),
        'calendar': google_calendar_service.test_connection(),
        'cache': cache_manager.is_healthy(),
        'holidays': holiday_service.is_holiday(date(2024,12,25))  # 🆕 Holiday Service Check
    }

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return jsonify({
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks
    }), status_code
```

## Wichtige Notizen für Entwicklung

### Code-Qualitäts-Anforderungen
- **Immer Type Hints verwenden** für Funktionsparameter und Returns
- **PEP 8 befolgen** für Code-Formatierung und Stil
- **Docstrings hinzufügen** für komplexe Funktionen und Klassen
- **Bedeutungsvolle Variablennamen verwenden** die ihren Zweck beschreiben
- **Ordnungsgemäße Fehlerbehandlung implementieren** mit Logging

### Sicherheits-Anforderungen
- **Niemals Zugangsdaten committen** oder sensible Daten
- **Immer Benutzereingaben validieren** vor Verarbeitung
- **Parametrisierte Queries verwenden** um Injection-Angriffe zu verhindern
- **Rate Limiting implementieren** für API-Endpoints
- **Sicherheitsrelevante Ereignisse protokollieren** für Audit-Trails

### Performance-Anforderungen
- **Kritische Code-Pfade profilieren** für Engpässe
- **Caching implementieren** für teure Operationen
- **Background-Tasks verwenden** für schwere Verarbeitung
- **Speicherverbrauch überwachen** und Datenstrukturen optimieren
- **Unter Last testen** um Skalierbarkeit zu gewährleisten

Diese umfassende Slot-Booking-Anwendung repräsentiert eine ausgeklügelte Geschäftsplattform, die als Grundlage für umfangreiche Enterprise-Anwendungen und Multi-Programm-Ökosysteme dienen kann.