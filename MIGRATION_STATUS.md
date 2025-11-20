# 🚀 PostgreSQL & Redis Migration - Status & Fortsetzung

**Datum**: 2025-11-20
**Phase**: Phase 1 - PostgreSQL & Redis Setup
**Status**: 🟡 IN PROGRESS (85% abgeschlossen)

---

## 📊 AKTUELLER STAND

### ✅ ERFOLGREICH ABGESCHLOSSEN

#### 1. Server-Setup (100%)
- ✅ PostgreSQL 16 installiert auf Hetzner VPS (91.98.192.233)
- ✅ Redis 7 installiert und läuft (Status: active/running)
- ✅ Database `business_hub` erstellt
- ✅ User `business_hub_user` erstellt
- ✅ Beide Services laufen stabil

#### 2. Code-Entwicklung (100%)
- ✅ **23 SQLAlchemy Models** erstellt für alle 20 JSON-Dateien:
  - `user.py`: User, UserStats, UserPrediction, BehaviorPattern, PersonalInsight
  - `gamification.py`: Score, UserBadge, DailyQuest, QuestProgress, PersonalGoal, Champion, MasteryData
  - `cosmetics.py`: UserCosmetic, CustomizationAchievement
  - `weekly.py`: WeeklyPointsParticipant, WeeklyPoints, WeeklyActivity, PrestigeData, MinigameData, PersistentData
  - `base.py`: Base Model, Database Engine, Session Management

- ✅ Alembic Setup komplett:
  - `alembic.ini` konfiguriert
  - `alembic/env.py` mit autogenerate Support
  - `alembic/README.md` mit Dokumentation

- ✅ Migration-Scripts erstellt:
  - `scripts/migrate_json_to_postgres.py` (Dry-Run + Execute Support)
  - `scripts/setup_postgresql.sh` (Automatisches PostgreSQL-Setup)
  - `scripts/setup_redis.sh` (Automatisches Redis-Setup)

#### 3. Dependencies (100%)
- ✅ Alle Packages installiert auf Server:
  - SQLAlchemy 2.0.36
  - psycopg2-binary 2.9.10
  - alembic 1.14.0
  - redis 5.1.1
  - Flask-Session 0.8.0
  - pytest-postgresql 6.1.1
  - pytest-redis 3.1.2

#### 4. Configuration (100%)
- ✅ `.env` auf Server erweitert mit:
  ```bash
  # PostgreSQL
  USE_POSTGRES=false  # Noch auf false, wird später auf true gesetzt
  DATABASE_URL=postgresql://business_hub_user:Cd3ma7OS+4MdAdyYshXVcKxvfoGnpYon@localhost/business_hub

  # Redis
  REDIS_URL=redis://localhost:6379/0
  SESSION_TYPE=redis
  SESSION_REDIS=redis://localhost:6379/0
  ```

#### 5. Git-Commits (100%)
- ✅ Commit 2055970: PostgreSQL & Redis migration - Phase 1
- ✅ Commit 97e06fe: Fix redis version to 5.1.1
- ✅ Commit 8505c6c: Remove invalid event listeners from base.py
- ✅ Commit 93433ee: Rename metadata to badge_metadata (SQLAlchemy reserved word)
- ✅ Alle Commits gepusht auf GitHub

---

## ⚠️ AKTUELLES PROBLEM

### Index-Namens-Konflikte in SQLAlchemy Models

**Problem**: Mehrere Tables nutzen denselben Index-Namen, was zu Konflikten führt:
- `idx_active` wird von 3 Tables verwendet (daily_quests, users, user_cosmetics)
- `idx_completed` wird von 2 Tables verwendet (quest_progress, customization_achievements)

**Fehlermeldung**:
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateTable) relation "idx_active" already exists
```

**Lösung (noch durchzuführen)**:
Index-Namen eindeutig machen durch Table-Präfix:
- `idx_active` → `idx_daily_quests_active`, `idx_users_active`, `idx_cosmetics_active`
- `idx_completed` → `idx_quest_progress_completed`, `idx_customization_completed`

**Betroffene Dateien**:
- `app/models/gamification.py` (quest_progress, customization_achievements, daily_quests)
- `app/models/user.py` (users)
- `app/models/cosmetics.py` (user_cosmetics)

---

## 🎯 NÄCHSTE SCHRITTE (verbleibend: ~15%)

### SOFORT (Kritisch):

#### Schritt 1: Index-Namen fixen (~30 Min)
```bash
# Lokale Änderungen in:
app/models/gamification.py
app/models/user.py
app/models/cosmetics.py
app/models/weekly.py

# Pattern: idx_{table_name}_{column_name}
# Beispiel: Index('idx_daily_quests_active', 'is_active')
```

**Betroffene Index-Namen**:
1. `idx_active` → Präfix mit Table-Name hinzufügen
2. `idx_completed` → Präfix mit Table-Name hinzufügen
3. `idx_username_*` → Prüfen ob unique über alle Tables
4. Alle anderen doppelten Index-Namen

#### Schritt 2: Database neu aufsetzen (~5 Min)
```bash
# Auf Server
ssh -i ~/.ssh/server_key root@91.98.192.233

# Database droppen und neu erstellen
sudo -u postgres psql -c 'DROP DATABASE IF EXISTS business_hub;'
sudo -u postgres psql -c 'CREATE DATABASE business_hub;'
sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON DATABASE business_hub TO business_hub_user;'
sudo -u postgres psql -d business_hub -c 'GRANT ALL ON SCHEMA public TO business_hub_user;'
```

#### Schritt 3: Alembic Migration neu generieren (~5 Min)
```bash
# Code pushen
git add app/models/*.py
git commit -m "fix: Make all index names unique across tables"
git push origin main

# Auf Server
cd /opt/business-hub
git pull origin main
source venv/bin/activate

# Migration generieren
export DATABASE_URL=postgresql://business_hub_user:Cd3ma7OS+4MdAdyYshXVcKxvfoGnpYon@localhost/business_hub
alembic revision --autogenerate -m "Initial migration - all 23 models"

# Migration anwenden
alembic upgrade head

# Tables prüfen
export PGPASSWORD=Cd3ma7OS+4MdAdyYshXVcKxvfoGnpYon
psql -U business_hub_user -d business_hub -h localhost -c "\dt"
# Sollte 23-24 Tables zeigen!
```

#### Schritt 4: JSON → PostgreSQL Migration (~30 Min)
```bash
# Auf Server
cd /opt/business-hub
source venv/bin/activate

# 1. Dry-Run (Test ohne Änderungen)
export DATABASE_URL=postgresql://business_hub_user:Cd3ma7OS+4MdAdyYshXVcKxvfoGnpYon@localhost/business_hub
python scripts/migrate_json_to_postgres.py --dry-run --data-dir /opt/business-hub/data/persistent

# Logs prüfen
tail -50 migration.log

# 2. Wenn Dry-Run OK: Echte Migration
python scripts/migrate_json_to_postgres.py --execute --data-dir /opt/business-hub/data/persistent

# 3. Erfolg prüfen
psql -U business_hub_user -d business_hub -h localhost -c "SELECT COUNT(*) FROM scores;"
psql -U business_hub_user -d business_hub -h localhost -c "SELECT COUNT(*) FROM user_badges;"
```

#### Schritt 5: .env auf PostgreSQL umstellen (~2 Min)
```bash
# Auf Server
nano /opt/business-hub/.env

# Ändern:
USE_POSTGRES=false  →  USE_POSTGRES=true

# Speichern: Ctrl+O, Enter, Ctrl+X
```

---

### DANACH (Nice-to-Have):

#### Schritt 6: Redis Integration Code-Änderungen (~2h)

**1. cache_manager.py auf Redis umstellen**
```python
# Datei: app/core/cache_manager.py
# Ändern von In-Memory Dictionary zu Redis
import redis

class CacheManager:
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

    def get(self, key):
        value = self.redis_client.get(key)
        return json.loads(value) if value else None

    def set(self, key, value, ttl=300):
        self.redis_client.setex(key, ttl, json.dumps(value))
```

**2. Session-Storage auf Redis umstellen**
```python
# Datei: app/__init__.py
from flask_session import Session

def create_app(config_class=None):
    # ...

    # Session Configuration
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = redis.from_url(os.getenv('REDIS_URL'))
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'business_hub:'

    Session(app)
```

#### Schritt 7: Service neu starten & testen (~10 Min)
```bash
# Auf Server
systemctl restart business-hub

# Logs überwachen
tail -f /var/log/business-hub/error.log

# Health-Check
curl http://localhost:5000/health/detailed

# Funktionalität testen
curl http://91.98.192.233/
```

---

## 🔐 WICHTIGE SERVER-CREDENTIALS

### PostgreSQL
```
Host: localhost
Port: 5432
Database: business_hub
User: business_hub_user
Password: Cd3ma7OS+4MdAdyYshXVcKxvfoGnpYon
```

### Redis
```
Host: localhost
Port: 6379
URL: redis://localhost:6379/0
Status: Läuft (redis-cli ping → PONG)
```

### SSH
```
Server: 91.98.192.233
User: root
Key: ~/.ssh/server_key
Command: ssh -i ~/.ssh/server_key root@91.98.192.233
```

---

## 🐛 PROBLEME & LÖSUNGEN (Dokumentiert)

### Problem 1: redis==5.2.2 existiert nicht
**Error**: `ERROR: No matching distribution found for redis==5.2.2`
**Lösung**: Version auf 5.1.1 geändert (Commit 97e06fe)

### Problem 2: Invalid event listeners in base.py
**Error**: `TypeError: <lambda>() takes 0 positional arguments but 1 was given`
**Lösung**: Event-Listeners entfernt (Commit 8505c6c)

### Problem 3: SQLAlchemy reserved word 'metadata'
**Error**: `Attribute name 'metadata' is reserved when using the Declarative API`
**Lösung**: Renamed zu `badge_metadata` (Commit 93433ee)

### Problem 4: Redis Config-Syntax-Fehler
**Error**: `Invalid save parameters` (Kommentare in redis.conf)
**Lösung**: Kommentare aus `save`-Zeilen entfernt, Redis läuft jetzt

### Problem 5: Index-Namens-Konflikte (AKTUELL)
**Error**: `relation "idx_active" already exists`
**Status**: ⚠️ OFFEN - Muss noch gefixt werden (siehe "Nächste Schritte")
**Lösung**: Index-Namen eindeutig machen mit Table-Präfix

---

## 📁 WICHTIGE DATEIEN & PFADE

### Lokale Entwicklung
```
app/models/
├── base.py              # Base Model, DB Engine
├── user.py              # 5 User-Models
├── gamification.py      # 7 Gamification-Models
├── cosmetics.py         # 2 Cosmetics-Models
├── weekly.py            # 6 Weekly/Complex-Models
└── __init__.py          # Exports

scripts/
├── migrate_json_to_postgres.py   # Migration-Script
├── setup_postgresql.sh           # PostgreSQL-Setup
└── setup_redis.sh                # Redis-Setup

alembic/
├── env.py               # Alembic Environment
├── README.md            # Alembic Dokumentation
└── versions/            # Migration-Scripts
    └── 20251120_1259_*.py  # Aktuelle Migration (mit Bugs)
```

### Server-Pfade
```
/opt/business-hub/                      # App-Root
/opt/business-hub/data/persistent/      # JSON-Datenbanken (20 Dateien)
/opt/business-hub/alembic/              # Alembic Migrations
/opt/business-hub/.env                  # Environment Variables
/var/log/business-hub/error.log         # Error-Logs
/etc/redis/redis.conf                   # Redis Config
```

---

## 🔧 NÜTZLICHE COMMANDS

### PostgreSQL
```bash
# Connection testen
export PGPASSWORD=Cd3ma7OS+4MdAdyYshXVcKxvfoGnpYon
psql -U business_hub_user -d business_hub -h localhost

# Tables listen
psql -U business_hub_user -d business_hub -h localhost -c "\dt"

# Database neu aufsetzen
sudo -u postgres psql -c 'DROP DATABASE business_hub;'
sudo -u postgres psql -c 'CREATE DATABASE business_hub;'
sudo -u postgres psql -c 'GRANT ALL PRIVILEGES ON DATABASE business_hub TO business_hub_user;'

# Backup erstellen
pg_dump -U business_hub_user business_hub > backup.sql
```

### Redis
```bash
# Status prüfen
systemctl status redis-server

# Verbindung testen
redis-cli ping  # → PONG

# Stats anzeigen
redis-cli INFO server
redis-cli INFO memory

# Monitoring
redis-cli MONITOR

# Keys auflisten
redis-cli KEYS '*'
```

### Alembic
```bash
# Migration generieren
alembic revision --autogenerate -m "Description"

# Migration anwenden
alembic upgrade head

# Eine Migration zurück
alembic downgrade -1

# Aktuelle Revision
alembic current

# History
alembic history
```

### Service Management
```bash
# Service neu starten
systemctl restart business-hub

# Status prüfen
systemctl status business-hub --no-pager

# Logs
tail -f /var/log/business-hub/error.log
journalctl -u business-hub -f
```

---

## 📈 FORTSCHRITT VISUALISIERT

```
Phase 1: PostgreSQL & Redis Migration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 85%

✅ PostgreSQL Setup        ████████████ 100%
✅ Redis Setup             ████████████ 100%
✅ Dependencies            ████████████ 100%
✅ SQLAlchemy Models       ████████████ 100%
✅ Alembic Setup           ████████████ 100%
✅ Migration-Scripts       ████████████ 100%
✅ .env Configuration      ████████████ 100%
⚠️  Index-Namen Fix        ░░░░░░░░░░░░   0%  ← NEXT
⬜ Tables erstellen        ░░░░░░░░░░░░   0%
⬜ JSON Migration          ░░░░░░░░░░░░   0%
⬜ Redis Integration       ░░░░░░░░░░░░   0%
⬜ Testing & Verifikation  ░░░░░░░░░░░░   0%

Geschätzter verbleibender Aufwand: ~2-3 Stunden
```

---

## 🎯 ERFOLGSKRITERIEN

### Wann ist Phase 1 abgeschlossen?

- [ ] Alle 23 Tables erfolgreich in PostgreSQL erstellt
- [ ] JSON-Migration durchgeführt (5 Files: scores, badges, weekly_points, cosmetics, prestige)
- [ ] `USE_POSTGRES=true` in `.env` gesetzt
- [ ] Redis läuft und wird von Flask-Session genutzt
- [ ] Cache-Manager nutzt Redis
- [ ] Service läuft stabil nach Neustart
- [ ] Health-Check zeigt PostgreSQL & Redis als "OK"
- [ ] Keine Fehler in `/var/log/business-hub/error.log`
- [ ] App funktioniert normal (Login, Buchungen, Gamification)

---

## 🚨 ROLLBACK-PLAN (Falls etwas schief geht)

### Sofortiger Rollback zu JSON
```bash
# 1. .env ändern
nano /opt/business-hub/.env
# USE_POSTGRES=true → USE_POSTGRES=false

# 2. Service neu starten
systemctl restart business-hub

# 3. Prüfen dass alles läuft
curl http://91.98.192.233/
```

### Vollständiger Rollback
```bash
# 1. Code auf alten Stand zurücksetzen
cd /opt/business-hub
git checkout <commit-vor-migration>

# 2. Service neu starten
systemctl restart business-hub

# 3. PostgreSQL optional deinstallieren
systemctl stop postgresql
apt remove postgresql postgresql-contrib
```

**JSON-Backups liegen in**: `/opt/business-hub/data/persistent/` (Original-Daten bleiben erhalten!)

---

## 📝 NOTES FÜR FORTSETZUNG

1. **Index-Namen-Fix ist der kritische Schritt** - Alles andere wartet darauf
2. **JSON-Daten bleiben erhalten** während der gesamten Migration (Parallel-Betrieb)
3. **Erst nach erfolgreichen Tests** `USE_POSTGRES=true` setzen
4. **Server läuft stabil** - keine Downtime während der Entwicklung
5. **Alle Credentials sind dokumentiert** oben in diesem File

---

## 🔗 RELATED DOCS

- `README.md` - Projekt-Übersicht & Features
- `ROADMAP.md` - Komplette Roadmap (Phase 1-4)
- `CLAUDE.md` - Claude Code Anleitungen
- `alembic/README.md` - Alembic-spezifische Doku
- `deployment/` - Deployment-Dokumentation

---

**Zuletzt aktualisiert**: 2025-11-20 13:05 UTC
**Nächster Schritt**: Index-Namen in Models fixen
**Erwartete Zeit bis Phase 1 Complete**: 2-3 Stunden

---

## 🎉 QUICK START (Fortsetzung nach Auto-Compact)

```bash
# 1. Status checken
ssh -i ~/.ssh/server_key root@91.98.192.233
systemctl status postgresql redis-server business-hub

# 2. Lokal: Index-Namen fixen
cd C:\Users\Luke\Documents\Slots\slot_booking_webapp
# Models bearbeiten (siehe "Nächste Schritte")

# 3. Deploy & Test
git add app/models/*.py
git commit -m "fix: Make all index names unique"
git push origin main

# 4. Auf Server fortsetzen
cd /opt/business-hub
git pull origin main
# ... (siehe "Nächste Schritte" Schritt 3-7)
```

**Du bist hier**: 85% durch Phase 1, hauptsächlich Index-Fix fehlt noch! 🚀
