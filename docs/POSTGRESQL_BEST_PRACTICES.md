# PostgreSQL Best Practices für Business-Hub

## 🎯 Performance-Optimierung

### 1. Index-Strategie

**Wann Indexes erstellen:**
- Spalten die häufig in WHERE-Clauses vorkommen
- Foreign Keys
- Spalten für JOIN-Operations
- Spalten für ORDER BY / GROUP BY

**Beispiele aus unserem Projekt:**
```sql
-- User-Lookups (sehr häufig)
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- Zeitbasierte Queries (My Calendar, Analytics)
CREATE INDEX idx_user_stats_date ON user_stats(stat_date);
CREATE INDEX idx_weekly_points_week ON weekly_points(week_id);

-- Composite Indexes für häufige Query-Kombinationen
CREATE INDEX idx_scores_username_month ON scores(username, month);
CREATE INDEX idx_user_badges_username_earned ON user_badges(username, earned_date DESC);
```

### 2. Query-Optimierung

**EXPLAIN ANALYZE verwenden:**
```sql
EXPLAIN ANALYZE
SELECT * FROM scores
WHERE username = 'luke.hoppe' AND month = '2025-11';

-- Zeigt:
-- - Execution Time
-- - Index Usage
-- - Sequential Scans (vermeiden!)
```

**N+1 Query-Problem vermeiden:**
```python
# ❌ SCHLECHT: N+1 Queries
users = session.query(User).all()
for user in users:
    badges = session.query(UserBadge).filter_by(username=user.username).all()

# ✅ GUT: Eager Loading
from sqlalchemy.orm import joinedload

users = session.query(User).options(
    joinedload(User.badges)
).all()
```

### 3. Connection Pooling

**Aktuelle Konfiguration (base.py):**
```python
engine = create_engine(
    database_url,
    pool_size=10,          # Max 10 simultane Connections
    max_overflow=20,        # Max 20 zusätzliche Connections
    pool_timeout=30,        # 30s Timeout
    pool_recycle=3600       # Connections nach 1h recyceln
)
```

**Monitoring:**
```sql
-- Aktive Connections anzeigen
SELECT count(*) FROM pg_stat_activity;

-- Details zu Connections
SELECT datname, usename, application_name, state, query
FROM pg_stat_activity
WHERE datname = 'business_hub';
```

### 4. Backup-Strategie

**Automatisches Backup (bereits eingerichtet):**
```bash
# Script: /opt/business-hub/scripts/backup_postgres.sh
pg_dump -U business_hub_user business_hub | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Retention: 7 Tage
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

**Manuelles Backup vor kritischen Änderungen:**
```bash
# Full Backup
pg_dump -U business_hub_user business_hub > backup_pre_migration.sql

# Nur Schema (für Testing)
pg_dump -U business_hub_user business_hub --schema-only > schema.sql

# Nur Daten
pg_dump -U business_hub_user business_hub --data-only > data.sql

# Restore
psql -U business_hub_user business_hub < backup.sql
```

### 5. Wartung

**VACUUM (Speicherplatz freigeben):**
```sql
-- Manuell für eine Tabelle
VACUUM ANALYZE scores;

-- Alle Tabellen
VACUUM ANALYZE;

-- Full Vacuum (mehr Zeit, aber bessere Komprimierung)
VACUUM FULL;
```

**Statistiken aktualisieren:**
```sql
-- Wichtig nach großen Data-Imports
ANALYZE;

-- Für spezifische Tabelle
ANALYZE user_badges;
```

**Auto-Vacuum Konfiguration prüfen:**
```sql
SHOW autovacuum;
SHOW autovacuum_naptime;
```

### 6. Monitoring & Alerts

**Wichtige Metriken:**
```sql
-- Database-Größe
SELECT pg_size_pretty(pg_database_size('business_hub'));

-- Table-Größen
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index-Größen
SELECT
    indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- Langsame Queries (pg_stat_statements Extension)
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### 7. Sicherheit

**User-Berechtigungen (bereits konfiguriert):**
```sql
-- Nur nötige Rechte vergeben
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO business_hub_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO business_hub_user;

-- Keine SUPERUSER-Rechte für App-User!
```

**Connection-Sicherheit:**
```bash
# pg_hba.conf: Nur lokale Connections
host    business_hub    business_hub_user    127.0.0.1/32    scram-sha-256

# SSL erzwingen (für Remote-Connections)
hostssl business_hub    business_hub_user    0.0.0.0/0       scram-sha-256
```

**Passwort-Rotation:**
```sql
-- Passwort ändern
ALTER USER business_hub_user WITH PASSWORD 'new_secure_password';

-- Dann .env aktualisieren!
```

### 8. Data-Migrations Best Practices

**Vor der Migration:**
```bash
# 1. Backup erstellen
pg_dump business_hub > backup_pre_migration.sql

# 2. Dry-Run durchführen
python scripts/migrate_json_to_postgres.py --dry-run

# 3. Logs prüfen
tail -f migration.log
```

**Während der Migration:**
```python
# Batch-Processing für große Datasets
batch_size = 1000
for i in range(0, len(records), batch_size):
    batch = records[i:i+batch_size]
    session.bulk_insert_mappings(Model, batch)
    session.commit()  # Commit nach jedem Batch
```

**Nach der Migration:**
```sql
-- Statistiken aktualisieren
ANALYZE;

-- Foreign Keys prüfen
SELECT conname, conrelid::regclass
FROM pg_constraint
WHERE contype = 'f';

-- Data-Integrität prüfen
SELECT COUNT(*) FROM scores;  -- Mit JSON vergleichen
```

### 9. Common Pitfalls

**1. Zu viele Indexes:**
```sql
-- ❌ Overhead: Jeder Index verlangsamt INSERT/UPDATE
CREATE INDEX ON users(username);
CREATE INDEX ON users(email);
CREATE INDEX ON users(created_at);
CREATE INDEX ON users(updated_at);
CREATE INDEX ON users(last_login);
-- ... 20+ Indexes

-- ✅ Nur wirklich benötigte Indexes
CREATE INDEX ON users(username);  -- Hauptlookup
CREATE INDEX ON users(email);     -- Login
```

**2. String-Vergleiche ohne Index:**
```python
# ❌ SCHLECHT: LIKE ohne Index
session.query(User).filter(User.username.like('%hoppe%')).all()

# ✅ BESSER: Full-Text-Search oder präziser Query
session.query(User).filter(User.username == 'luke.hoppe').first()
```

**3. Große JSON-Felder:**
```python
# ❌ VERMEIDEN: Riesige JSON-Blobs in DB
user.profile_data = {huge_json_with_10MB}

# ✅ BESSER: Separate Tables oder Dateisystem
# Nur kleine Configs in JSON speichern
```

**4. Fehlende Transaktionen:**
```python
# ❌ SCHLECHT: Auto-Commit nach jeder Operation
user.points += 10
session.commit()
badge = UserBadge(...)
session.add(badge)
session.commit()  # Inkonsistent bei Fehler!

# ✅ GUT: Atomic Transaction
try:
    user.points += 10
    badge = UserBadge(...)
    session.add(badge)
    session.commit()  # Alles oder nichts
except:
    session.rollback()
    raise
```

### 10. Scaling-Überlegungen

**Wann auf externe DB umsteigen:**
- Mehr als 10.000 User
- Mehr als 1 Million Rows in einer Tabelle
- CPU/Memory-Limit des VPS erreicht
- Read-Replicas benötigt

**Alternativen:**
- **AWS RDS PostgreSQL**: Managed, Auto-Backups, Scaling
- **Heroku Postgres**: Einfach, aber teuer
- **DigitalOcean Managed DB**: Guter Mittelweg

**Aktuell (Hetzner VPS):**
- ✅ Perfekt für <1.000 User
- ✅ Kostengünstig (bereits bezahlt)
- ✅ Volle Kontrolle

---

## 📊 Checkliste für Production

- [ ] Backups laufen automatisch (7-Tage-Retention)
- [ ] Connection Pooling konfiguriert
- [ ] Wichtigste Indexes erstellt
- [ ] VACUUM & ANALYZE läuft regelmäßig
- [ ] Monitoring für DB-Größe & Performance
- [ ] Passwort ist sicher & rotiert
- [ ] Nur nötige User-Berechtigungen
- [ ] pg_stat_statements Extension aktiviert (optional)
- [ ] SSL für Remote-Connections (wenn nötig)
- [ ] Disaster-Recovery-Plan dokumentiert

---

**Weitere Infos:**
- PostgreSQL Docs: https://www.postgresql.org/docs/16/
- Performance-Tuning: https://wiki.postgresql.org/wiki/Performance_Optimization
