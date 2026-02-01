# CLAUDE.md

**Professionelle Anleitungen für Claude Code - Central Business Tool Hub**

---

## PFLICHT-CHECKLISTE VOR JEDER IMPLEMENTIERUNG

**STOPP! Diese Checkliste MUSS vor jeder Code-Änderung durchgegangen werden!**

### Bei UI-Änderungen MUSS Claude prüfen:

- [ ] **Base-Template identifiziert?**
  - Hub-Seiten: `templates/hub/base.html`
  - Slot-Booking: `templates/slots/base.html`
  - T2-Closer: `templates/t2/base.html`
  - Error-Pages: `templates/errors/base.html`

- [ ] **Template erbt von Base?**
  - Korrekt: `{% extends "hub/base.html" %}`
  - WARNUNG: `my_calendar.html`, `admin_dashboard.html`, `admin_tracking.html` sind Standalone - NICHT als Vorlage verwenden!

- [ ] **Farben aus Palette?**
  | Name | Hex | Tailwind-Klasse |
  |------|-----|-----------------|
  | Primary (Gold) | #d4af6a | `text-primary`, `bg-primary` |
  | Secondary (Teal) | #207487 | `text-secondary`, `bg-secondary` |
  | Accent (Dark Teal) | #294c5d | `text-accent`, `bg-accent` |
  | ZFA Gray | #77726d | `text-zfa-gray` |

- [ ] **DaisyUI-Komponenten verwendet?**
  - Buttons: `btn btn-primary`, `btn-ghost`, `btn-sm/md/lg`
  - Badges: `badge badge-success/warning/error/info`
  - Alerts: `alert alert-success/warning/error`
  - Cards: `.glass` + `rounded-2xl` + `p-6`
  - Modals: `modal`, `modal-box`, `modal-action`
  - Tables: `table table-zebra`
  - Tabs: `tabs tabs-boxed`

- [ ] **Glassmorphism korrekt?**
  ```html
  <div class="glass rounded-2xl p-6 shadow-xl">
    <!-- Inhalt -->
  </div>
  ```

- [ ] **Particles.js-Konfiguration?**
  ```javascript
  particles: { number: { value: 30 }, move: { speed: 0.5 } }
  interactivity: { events: { onhover: { enable: false } } }
  ```

### Bei Daten-Änderungen MUSS Claude prüfen:

- [ ] **Existiert bereits ein Service?** (Siehe Abschnitt "Datenmodell-Referenz")
- [ ] **Existiert bereits eine JSON-Datei oder DB-Tabelle?**
- [ ] **Dual-Write notwendig?** (PostgreSQL + JSON für kritische Daten)
- [ ] **Welcher Service greift bereits auf diese Daten zu?**

### Bei neuen Features MUSS Claude prüfen:

- [ ] **Gibt es ähnliche Features die erweitert werden können?**
- [ ] **Welche bestehenden Services können wiederverwendet werden?**
- [ ] **Müssen andere Bereiche benachrichtigt werden?**
  - Bei Buchungen: `tracking_system` + `achievement_system`
  - Bei Punkten: `data_persistence` + `level_system`
  - Bei User-Aktionen: `audit_service`

---

## DESIGN-SYSTEM REFERENZ

### Base-Template Entscheidung

| Bereich | Template | Wann verwenden |
|---------|----------|----------------|
| Hub-Seiten | `templates/hub/base.html` | Dashboard, Profile, Settings, Admin |
| Slot-Booking | `templates/slots/base.html` | Slot-Auswahl, Booking-Flow, Kalender |
| T2-Closer | `templates/t2/base.html` | T2-Dashboard, Würfeln, T2-Bookings |
| Error-Pages | `templates/errors/base.html` | 404, 500, Fehlerseiten |

### WARNUNG: Standalone-Templates

Diese Templates haben **KEINE Base-Vererbung** - NICHT als Vorlage kopieren:
- `my_calendar.html` - Kanban-Board (komplex, eigenständig)
- `admin_dashboard.html` - Admin-Übersicht (eigenständig)
- `admin_tracking.html` - Tracking-Analytics (eigenständig)

### CSS-Framework-Zuweisung

| Bereich | Framework | Komponenten-Bibliothek |
|---------|-----------|------------------------|
| Hub | Tailwind CSS | DaisyUI |
| T2 | Tailwind CSS | DaisyUI |
| Slots | Bootstrap 5.3.2 | Bootstrap Components |
| Admin | Tailwind CSS | DaisyUI |

**WICHTIG:** Bootstrap und Tailwind NIEMALS mischen innerhalb eines Templates!

### Farb-Palette (Vollständig)

```css
/* Primäre Markenfarben */
--primary: #d4af6a;      /* Gold - Hauptaktionen, Buttons, Akzente */
--secondary: #207487;    /* Teal - Sekundäre Actions, Links */
--accent: #294c5d;       /* Dark Teal - Backgrounds, Karten */

/* Grautöne */
--zfa-gray: #77726d;     /* Text, Borders, Subtile Elemente */
--dark-bg: #1a1a2e;      /* Dunkler Hintergrund */
--card-bg: #16213e;      /* Karten-Hintergrund */

/* Status-Farben (DaisyUI) */
--success: #22c55e;      /* Erfolg, Bestätigt */
--warning: #f59e0b;      /* Warnung, Pending */
--error: #ef4444;        /* Fehler, Abgelehnt */
--info: #3b82f6;         /* Info, Hinweise */
```

### Standard-Komponenten (Copy-Paste-Ready)

**Glassmorphism Card:**
```html
<div class="glass rounded-2xl p-6 shadow-xl backdrop-blur-sm">
  <h3 class="text-xl font-bold text-primary mb-4">Titel</h3>
  <p class="text-gray-300">Inhalt</p>
</div>
```

**Primary Button:**
```html
<button class="btn btn-primary gap-2">
  <i class="fas fa-icon"></i>
  Button Text
</button>
```

**Status Badge:**
```html
<span class="badge badge-success">Aktiv</span>
<span class="badge badge-warning">Pending</span>
<span class="badge badge-error">Fehler</span>
```

**Modal Dialog:**
```html
<dialog id="my-modal" class="modal">
  <div class="modal-box glass">
    <h3 class="font-bold text-lg text-primary">Modal Titel</h3>
    <p class="py-4">Inhalt hier...</p>
    <div class="modal-action">
      <form method="dialog">
        <button class="btn btn-ghost">Abbrechen</button>
        <button class="btn btn-primary">Bestätigen</button>
      </form>
    </div>
  </div>
</dialog>
```

**Alert/Toast:**
```html
<div class="alert alert-success shadow-lg">
  <i class="fas fa-check-circle"></i>
  <span>Aktion erfolgreich!</span>
</div>
```

### Particles.js Standardkonfiguration

**IMMER diese Werte verwenden:**
```javascript
particlesJS('particles-js', {
  particles: {
    number: { value: 30 },           // NICHT mehr als 30!
    color: { value: '#d4af6a' },     // Primary Gold
    opacity: { value: 0.3 },
    size: { value: 2 },
    move: {
      enable: true,
      speed: 0.5                     // Langsam, nicht ablenkend
    }
  },
  interactivity: {
    events: {
      onhover: { enable: false },    // IMMER deaktiviert
      onclick: { enable: false }     // IMMER deaktiviert
    }
  }
});
```

---

## DATENMODELL-REFERENZ

### PostgreSQL Tabellen (Hauptdatenbank)

| Tabelle | Wichtige Felder | Zuständiger Service |
|---------|-----------------|---------------------|
| `users` | username, level, total_coins, xp | `app/models/user.py` |
| `scores` | username, month, points, bookings | `data_persistence` |
| `user_badges` | username, badge_id, earned_date | `achievement_system` |
| `bookings` | booking_id, customer, date, username, outcome | `tracking_system` |
| `booking_outcomes` | outcome_id, outcome, booking_id | `tracking_system` |
| `t2_bookings` | coach, berater, customer, date, status | `t2_bucket_system` |
| `daily_quests` | quest_date, target_type, target_value | `daily_quests` |
| `notifications` | id, roles, title, message, type | `notification_service` |
| `audit_log` | timestamp, username, action, details | `audit_service` |

### JSON-Dateien (data/persistent/)

| Datei | Inhalt | Zuständiger Service |
|-------|--------|---------------------|
| `scores.json` | Monatliche Punkte pro User | `data_persistence` |
| `user_badges.json` | Verdiente Badges | `data_persistence` |
| `user_coins.json` | Coin-Guthaben | `data_persistence` |
| `t2_bucket_system.json` | T2-Würfel-System, Buchungen | `t2_bucket_system` |
| `daily_quests.json` | Aktive Tagesquests | `daily_quests` |
| `quest_progress.json` | Quest-Fortschritt pro User | `daily_quests` |
| `user_customizations.json` | Gekaufte Cosmetics | `cosmetics_shop` |
| `prestige_data.json` | Prestige-Level | `prestige_system` |
| `weekly_points.json` | Wöchentliche Punkte | `weekly_points` |
| `champions.json` | Wöchentliche Champions | `weekly_points` |
| `user_profiles.json` | Profilbilder, Bio | `personalization_system` |
| `audit_log.json` | Audit-Events (Backup) | `audit_service` |
| `user_passwords.json` | Passwort-Hashes | `security_service` |
| `user_2fa.json` | 2FA-Secrets | `security_service` |
| `account_lockouts.json` | Gesperrte Accounts | `account_lockout` |
| `persistent_data.json` | Allgemeine persistente Daten | `data_persistence` |
| `user_stats.json` | User-Statistiken | `data_persistence` |
| `daily_user_stats.json` | Tägliche User-Statistiken | `activity_tracking` |
| `user_analytics.json` | User-Analytics-Daten | `analytics_service` |
| `user_predictions.json` | User-Vorhersagen | `analytics_service` |
| `behavior_patterns.json` | Verhaltensmuster | `analytics_service` |
| `personal_insights.json` | Persönliche Insights | `personalization_system` |
| `personal_goals.json` | Persönliche Ziele | `personalization_system` |
| `mastery_data.json` | Mastery-Fortschritt | `achievement_system` |
| `minigame_data.json` | Minigame-Daten | `daily_reward_system` |
| `customization_achievements.json` | Customization-Achievements | `cosmetics_shop` |

### Service-Zuordnung (Welcher Service für was?)

| Aufgabe | Service | Import |
|---------|---------|--------|
| Punkte laden/speichern | `data_persistence` | `from app.core.extensions import data_persistence` |
| Badges vergeben | `achievement_system` | `from app.services.achievement_system import check_achievements` |
| Level berechnen | `level_system` | `from app.services.level_system import LevelSystem` |
| Buchungen tracken | `tracking_system` | `from app.services.tracking_system import TrackingSystem` |
| T2-Buchungen | `t2_bucket_system` | `from app.services.t2_bucket_system import T2BucketSystem` |
| Tagesquests | `daily_quests` | `from app.services.daily_quests import DailyQuestSystem` |
| Notifications | `notification_service` | `from app.services.notification_service import notification_service` |
| Audit-Logging | `audit_service` | `from app.services.audit_service import AuditService` |
| Coins verwalten | `data_persistence` | `data_persistence.add_coins(username, amount)` |
| Google Calendar | `google_calendar` | `from app.core.google_calendar import get_google_calendar_service` |
| Analytics/BI | `analytics_service` | `from app.services.analytics_service import AnalyticsService` |
| Executive Reports | `executive_reports` | `from app.services.executive_reports import ExecutiveReportService` |
| Prestige-System | `prestige_system` | `from app.services.prestige_system import PrestigeSystem` |
| Wöchentliche Punkte | `weekly_points` | `from app.services.weekly_points import WeeklyPointsSystem` |
| Consultant Ranking | `consultant_ranking` | `from app.services.consultant_ranking import ConsultantRanking` |
| Personalisierung | `personalization_system` | `from app.services.personalization_system import PersonalizationSystem` |
| Tägliche Belohnungen | `daily_reward_system` | `from app.services.daily_reward_system import DailyRewardSystem` |
| Discord Webhooks | `discord_webhook_service` | `from app.services.discord_webhook_service import DiscordWebhookService` |
| Activity Tracking | `activity_tracking` | `from app.services.activity_tracking import ActivityTracking` |
| Security/2FA | `security_service` | `from app.services.security_service import SecurityService` |
| Account Lockout | `account_lockout` | `from app.services.account_lockout import AccountLockout` |
| T2 Analytics | `t2_analytics_service` | `from app.services.t2_analytics_service import T2AnalyticsService` |
| T2 Verfügbarkeit | `t2_availability_service` | `from app.services.t2_availability_service import T2AvailabilityService` |
| T2 Kalender-Parser | `t2_calendar_parser` | `from app.services.t2_calendar_parser import T2CalendarParser` |
| T2 Dynamische Slots | `t2_dynamic_availability` | `from app.services.t2_dynamic_availability import T2DynamicAvailability` |
| Feiertage | `holiday_service` | `from app.services.holiday_service import HolidayService` |
| Cosmetics Shop | `cosmetics_shop` | `from app.services.cosmetics_shop import CosmeticsShop` |

### Daten-Zugriff Patterns

**RICHTIG - Via Service (IMMER bevorzugen!):**
```python
from app.core.extensions import data_persistence

# Punkte laden
scores = data_persistence.load_scores()

# Punkte für User
user_score = data_persistence.get_user_score(username, month)

# Coins hinzufügen
data_persistence.add_coins(username, 50)
```

**RICHTIG - Via PostgreSQL (für komplexe Queries):**
```python
from app.models import Booking, get_db_session

with get_db_session() as session:
    bookings = session.query(Booking).filter(
        Booking.username == username,
        Booking.date >= start_date
    ).all()
```

**FALSCH - Direkte JSON-Manipulation:**
```python
# NIEMALS SO!
import json
with open('data/persistent/scores.json', 'r') as f:
    scores = json.load(f)  # NEIN! Verwende data_persistence!
```

---

## INTEGRATION-REGELN

### Bestehende System-Verknüpfungen

```
T1-Booking Flow:
  booking_service → tracking_system → achievement_system → data_persistence
                                                        ↓
                                                   audit_service

T2-Booking Flow:
  t2_bucket_system → PostgreSQL (t2_bookings) → notification_service

Gamification Flow:
  Punkte → level_system → achievement_system → cosmetics_shop (Coins)
                                ↓
                         notification_service
```

### MUSS-Regeln für neue Features

1. **NIEMALS neue Datenquellen erstellen** wenn ähnliche existieren
   - Vor JSON-Datei-Erstellung: Prüfe ob data_persistence erweitert werden kann
   - Vor neuer DB-Tabelle: Prüfe ob bestehende Tabelle erweitert werden kann

2. **IMMER bestehende Services wiederverwenden**
   - Punkte? → `data_persistence`
   - Badges? → `achievement_system`
   - Logging? → `audit_service`
   - Benachrichtigungen? → `notification_service`

3. **Bei Buchungen IMMER aufrufen:**
   ```python
   # Nach erfolgreicher Buchung:
   tracking_system.record_booking(booking_data)
   achievement_system.check_achievements(username, 'booking', context)
   audit_service.log('booking_created', username, details)
   ```

4. **Bei Admin-Features IMMER:**
   - Template erbt von `hub/base.html`
   - Audit-Logging für alle Admin-Aktionen
   - Role-Check via `@admin_required` Decorator

5. **Bei User-sichtbaren Änderungen:**
   - Notification erstellen wenn sinnvoll
   - Toast/Feedback im Frontend

### Feature-Erweiterung statt Neuentwicklung

| Wenn du brauchst... | Erweitere... | Statt neu zu bauen |
|---------------------|--------------|-------------------|
| Neue Statistiken | `analytics_service` | Neuen Analytics-Service |
| Neues Achievement | `achievement_system` (ACHIEVEMENTS dict) | Neues Badge-System |
| Neue Quest-Art | `daily_quests` (QUEST_TYPES) | Neues Quest-System |
| Neue Admin-Ansicht | Bestehende Admin-Routes | Neues Admin-Modul |
| Neues Report | `executive_reports` | Neuen Report-Service |

---

## DEPLOYMENT WORKFLOW

**WORKFLOW:** Lokal entwickeln → Server testen → GitHub pushen

### Server-Details

| Detail | Wert |
|--------|------|
| Server | `91.98.192.233` |
| SSH-Key | `~/.ssh/server_key` |
| App-Pfad | `/opt/business-hub/` |
| URL | https://berater.zfa.gmbh/ |
| Service | `business-hub.service` |

### Deployment-Schritte

```bash
# 1. BACKUP (IMMER!)
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && tar -czf /tmp/backup_$(date +%Y%m%d_%H%M).tar.gz data/persistent/"

# 2. Dateien übertragen
scp -i ~/.ssh/server_key <datei> root@91.98.192.233:/opt/business-hub/<pfad>

# 3. Service neu starten
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"

# 4. Verifizieren
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub --no-pager | head -20"
curl -I https://berater.zfa.gmbh/health  # Sollte 200 OK sein
```

### Deployment-Checkliste

**Vor Deployment:**
- [ ] Code lokal getestet (`python run.py`)
- [ ] Keine Secrets in Dateien
- [ ] Backup erstellt

**Nach Deployment:**
- [ ] Service läuft (systemctl status)
- [ ] Health-Check: 200 OK
- [ ] Browser-Test (Ctrl+Shift+R)
- [ ] Keine Errors in Logs

**Nach erfolgreichem Test - Git:**
```bash
git add <geänderte_dateien>
git commit -m "feat: Beschreibung"  # OHNE Claude Attribution!
git push origin main
```

### Wichtige Server-Pfade

```
/opt/business-hub/                    # Hauptverzeichnis
/opt/business-hub/app/                # Flask-App
/opt/business-hub/templates/          # Templates
/opt/business-hub/data/persistent/    # Persistente Daten
/var/log/business-hub/error.log       # Error-Logs
```

### Notfall-Rollback

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && tar -xzf /tmp/backup_YYYYMMDD_HHMM.tar.gz"
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"
```

---

## QUICK REFERENCE

### Umgebungsvariablen (.env)

```bash
SECRET_KEY=<key>
USERLIST=user:pass,user2:pass2
ADMIN_USERS=admin1,admin2
PERSIST_BASE=/opt/business-hub/data
GOOGLE_CREDS_BASE64=<base64>
CENTRAL_CALENDAR_ID=calendar@example.com
CONSULTANTS=Name1:email1,Name2:email2
SENTRY_DSN=<dsn>  # Optional
```

### Git Commit-Richtlinien

- **NIEMALS** Claude Code-Attribution (`Co-Authored-By`, etc.)
- Format: `feat:`, `fix:`, `docs:`, `refactor:`

### Rollen-Übersicht

| Rolle | Zugriff |
|-------|---------|
| admin | Alles |
| closer | T2-System |
| opener | T1 Slot-Booking |
| coach | T2-Coaches |
| telefonist | Telefon-Tracking |
| service | Service-Features |

### Deployment Notifications

Nach `git push` fragen ob Notification erstellt werden soll:
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
        show_popup=True
    )
"
```

---

## VERSION & STATUS

**Version:** 3.3.16 | **Status:** Production | **URL:** https://berater.zfa.gmbh/

**Technologie:** Flask 3.1.1, Python 3.11+, PostgreSQL, Tailwind/DaisyUI, Hetzner VPS

**Für detaillierte Informationen siehe README.md!**
