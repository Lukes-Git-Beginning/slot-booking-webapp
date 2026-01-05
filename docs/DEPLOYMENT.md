# Deployment Guide - Central Business Tool Hub

**Version:** 3.3.15
**Last Updated:** 2026-01-05

This guide describes deployment procedures for the Central Business Tool Hub on the Hetzner production server.

## Übersicht der neuen Features

### Phase 1: Quick Wins (Security & Performance)
✅ **1.1 Password-Hashing (bcrypt)**
- Sichere Passwort-Speicherung mit bcrypt
- Hybrid-Authentifizierung (Unterstützt Legacy + Hashed Passwords)
- Migrations-Script für bestehende Passwörter

✅ **1.2 Rate-Limiting**
- Login-Endpoint: 5 Anfragen/Minute
- Booking-Endpoint: 20 Anfragen/Minute
- DDoS & Brute-Force-Schutz

✅ **1.3 Audit-Logging**
- Umfassendes Event-Tracking (Login, Logout, Admin-Aktionen)
- Severity-Levels (info, warning, critical)
- Automatische Log-Rotation
- Query-API für Admin-Dashboard

✅ **1.4 Code-Cleanup**
- Alle `print()` Statements durch `app.logger` ersetzt
- Professionelles Logging in Production

### Phase 2: Analytics Dashboard
✅ **Analytics-Tool**
- Business Intelligence Dashboard (Admin-only)
- Executive KPIs (Bookings, Conversion Rate, Revenue Forecast)
- Team-Performance-Tracking
- Funnel-Analysen & Trend-Visualisierung
- Chart.js Integration für interaktive Diagramme

---

## 🛡️ Systemd Service Configuration

The Business Tool Hub runs as a systemd service with comprehensive security hardening.

### Service File Location

**Path:** `/etc/systemd/system/business-hub.service`

### Current Configuration (v3.3.15)

```ini
[Unit]
Description=Central Business Tool Hub - Multi-Tool Platform
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/business-hub
Environment="PATH=/opt/business-hub/venv/bin"
ExecStart=/opt/business-hub/venv/bin/gunicorn \
    --bind unix:/opt/business-hub/business-hub.sock \
    --workers 4 \
    --worker-class gthread \
    --threads 2 \
    --timeout 120 \
    --access-logfile /var/log/business-hub/access.log \
    --error-logfile /var/log/business-hub/error.log \
    --log-level info \
    'app:create_app()'

# Security Hardening
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/business-hub/data /opt/business-hub/logs /opt/business-hub/cache /var/log/business-hub /opt/business-hub/static
ReadOnlyPaths=/opt/business-hub/templates
NoNewPrivileges=true
PrivateDevices=true

# Resource Limits
LimitNOFILE=4096
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Security Hardening Explained

#### ProtectSystem=strict

- Makes entire filesystem read-only except specified paths
- Prevents accidental or malicious writes to system files
- Limits blast radius of potential code execution vulnerabilities

#### ProtectHome=true

- Blocks access to /home directories
- Prevents access to user data

#### ReadWritePaths

- `/opt/business-hub/data` - Application data (JSON databases, persistent storage)
- `/opt/business-hub/logs` - Application logs
- `/opt/business-hub/cache` - Cache files (availability, session data)
- `/var/log/business-hub` - Systemd service logs
- `/opt/business-hub/static` - **Added 2026-01-05** - Gamification dual-write architecture

#### ReadOnlyPaths

- `/opt/business-hub/templates` - Prevents template injection attacks

#### NoNewPrivileges=true

- Prevents privilege escalation
- Service cannot gain more privileges than it starts with

#### PrivateDevices=true

- Blocks access to physical devices
- Prevents device-based attacks

### File Ownership & Permissions

All application files must be owned by `www-data` user:

```bash
# Set ownership
chown -R www-data:www-data /opt/business-hub/

# Set permissions
chmod 755 /opt/business-hub/  # Directories
chmod 644 /opt/business-hub/app/*.py  # Python files
chmod 600 /opt/business-hub/.env  # Secrets (owner read only)

# Writable directories
chmod 755 /opt/business-hub/data/persistent/
chmod 755 /opt/business-hub/static/
chmod 755 /opt/business-hub/logs/
chmod 755 /var/log/business-hub/
```

### Managing the Service

**Basic Commands:**

```bash
# Start service
systemctl start business-hub

# Stop service
systemctl stop business-hub

# Restart service
systemctl restart business-hub

# Reload systemd after config changes
systemctl daemon-reload

# View service status
systemctl status business-hub

# Enable auto-start on boot
systemctl enable business-hub

# Disable auto-start
systemctl disable business-hub
```

**Viewing Logs:**

```bash
# Real-time logs
journalctl -u business-hub -f

# Last 100 lines
journalctl -u business-hub -n 100

# Today's logs only
journalctl -u business-hub --since today

# Logs from specific date
journalctl -u business-hub --since "2026-01-05"

# Application error log
tail -f /var/log/business-hub/error.log

# Application access log
tail -f /var/log/business-hub/access.log
```

### Troubleshooting Systemd Issues

**Service Won't Start:**

```bash
# 1. Check syntax errors
journalctl -u business-hub -n 50

# 2. Check Python syntax
cd /opt/business-hub
source venv/bin/activate
python -m py_compile app/__init__.py

# 3. Test manual start
cd /opt/business-hub
source venv/bin/activate
gunicorn 'app:create_app()' --bind 127.0.0.1:8000 --workers 1
# If this works, issue is in systemd config
```

**Permission Errors:**

```bash
# Error: "Permission denied" when writing to files
# Solution: Check file ownership
ls -la /opt/business-hub/data/persistent/
ls -la /opt/business-hub/static/

# Fix ownership if needed
chown -R www-data:www-data /opt/business-hub/data/
chown -R www-data:www-data /opt/business-hub/static/
systemctl restart business-hub
```

**Read-only Filesystem Errors:**

```bash
# Error: "[Errno 30] Read-only file system"
# Cause: ProtectSystem=strict blocks writes to non-specified paths

# Solution 1: Add path to ReadWritePaths
nano /etc/systemd/system/business-hub.service
# Add path to ReadWritePaths line
systemctl daemon-reload
systemctl restart business-hub

# Solution 2: Verify path is in allowed list
grep ReadWritePaths /etc/systemd/system/business-hub.service
```

**Service Crashes Repeatedly:**

```bash
# 1. Check crash logs
journalctl -u business-hub --since "5 minutes ago"

# 2. Check application errors
tail -100 /var/log/business-hub/error.log

# 3. Disable auto-restart temporarily for debugging
systemctl stop business-hub
# Run manually to see full error output
cd /opt/business-hub && source venv/bin/activate
gunicorn 'app:create_app()' --bind unix:/opt/business-hub/business-hub.sock --workers 1 --log-level debug
```

### Performance Tuning

**Worker Configuration:**

- **Workers:** 4 (matches CPU cores on VPS)
- **Worker Class:** gthread (hybrid process/thread model)
- **Threads per Worker:** 2
- **Total Capacity:** 4 workers × 2 threads = 8 concurrent requests

**Recommended Settings by Traffic:**

**Low Traffic (<50 req/min):**
```bash
--workers 2 --threads 2  # 4 concurrent requests
```

**Medium Traffic (50-200 req/min):**
```bash
--workers 4 --threads 2  # 8 concurrent requests (current)
```

**High Traffic (>200 req/min):**
```bash
--workers 8 --threads 4  # 32 concurrent requests
# Note: Requires more RAM (estimate 150MB per worker)
```

**To Change Worker Settings:**
```bash
# 1. Edit service file
nano /etc/systemd/system/business-hub.service

# 2. Update ExecStart line
ExecStart=/opt/business-hub/venv/bin/gunicorn \
    --bind unix:/opt/business-hub/business-hub.sock \
    --workers 8 \
    --worker-class gthread \
    --threads 4 \
    ...

# 3. Reload and restart
systemctl daemon-reload
systemctl restart business-hub

# 4. Monitor resource usage
htop  # Watch memory usage
```

### Security Hardening Changelog

| Date       | Change                                                 | Reason                                               |
|------------|--------------------------------------------------------|------------------------------------------------------|
| 2026-01-03 | Initial hardening deployment                           | Security best practices                              |
| 2026-01-05 | Added `/opt/business-hub/static` to ReadWritePaths     | Gamification data writes failing (6-day outage)      |
| 2026-01-05 | Removed `/opt/business-hub/static` from ReadOnlyPaths  | Conflicting permissions                              |

---

## 🚀 Deployment-Schritte

### Voraussetzungen

```bash
# 1. SSH-Zugang zum Server
ssh -i ~/.ssh/server_key root@91.98.192.233

# 2. Backup erstellen (WICHTIG!)
/usr/local/bin/business-hub-backup.sh

# 3. Backup verifizieren
ls -lh /opt/business-hub/backups/
```

---

## Teil 1: Dateien auf Server übertragen

### 1. Backend-Dateien (Python)

```bash
# Von lokalem Windows-Rechner aus:
cd C:\Users\Luke\Documents\Slots\slot_booking_webapp

# 1. Security Service (Password Hashing + 2FA)
scp -i ~/.ssh/server_key app/services/security_service.py root@91.98.192.233:/opt/business-hub/app/services/

# 2. Audit Service (Logging)
scp -i ~/.ssh/server_key app/services/audit_service.py root@91.98.192.233:/opt/business-hub/app/services/

# 3. Analytics Service (Business Intelligence)
scp -i ~/.ssh/server_key app/services/analytics_service.py root@91.98.192.233:/opt/business-hub/app/services/

# 4. Auth Routes (Rate Limiting + Audit Integration)
scp -i ~/.ssh/server_key app/routes/auth.py root@91.98.192.233:/opt/business-hub/app/routes/

# 5. Booking Routes (Rate Limiting)
scp -i ~/.ssh/server_key app/routes/booking.py root@91.98.192.233:/opt/business-hub/app/routes/

# 6. Analytics Blueprint
scp -i ~/.ssh/server_key app/routes/analytics.py root@91.98.192.233:/opt/business-hub/app/routes/

# 7. Application Factory (Blueprint-Registrierung + Code-Cleanup)
scp -i ~/.ssh/server_key app/__init__.py root@91.98.192.233:/opt/business-hub/app/

# 8. Requirements (bcrypt hinzugefügt)
scp -i ~/.ssh/server_key requirements.txt root@91.98.192.233:/opt/business-hub/
```

### 2. Templates (HTML)

```bash
# Analytics Dashboard Template
scp -i ~/.ssh/server_key templates/analytics/dashboard.html root@91.98.192.233:/opt/business-hub/templates/analytics/

# Falls analytics/-Verzeichnis nicht existiert:
ssh -i ~/.ssh/server_key root@91.98.192.233 "mkdir -p /opt/business-hub/templates/analytics"
# Dann erneut SCP ausführen
```

### 3. Scripts & Tools

```bash
# Password-Migrations-Script (optional, für manuelle Passwort-Migration)
scp -i ~/.ssh/server_key scripts/migrate_passwords.py root@91.98.192.233:/opt/business-hub/scripts/

# Falls scripts/-Verzeichnis nicht existiert:
ssh -i ~/.ssh/server_key root@91.98.192.233 "mkdir -p /opt/business-hub/scripts"
```

---

## Teil 2: Server-Konfiguration

### 1. Python-Dependencies installieren

```bash
# SSH auf Server
ssh -i ~/.ssh/server_key root@91.98.192.233

# In Virtual Environment wechseln
cd /opt/business-hub
source venv/bin/activate

# bcrypt installieren (wichtigste neue Dependency)
pip install bcrypt==4.2.1

# Oder alle Requirements neu installieren
pip install -r requirements.txt

# Installation verifizieren
python -c "import bcrypt; print('bcrypt installed:', bcrypt.__version__)"
```

### 2. Persistenz-Verzeichnisse erstellen

```bash
# Auf dem Server (als root):
cd /opt/business-hub

# Audit-Log-Verzeichnis (falls noch nicht vorhanden)
mkdir -p data/persistent/audit_logs

# Berechtigungen setzen
chown -R www-data:www-data data/persistent/
chmod -R 755 data/persistent/
```

### 3. Umgebungsvariablen prüfen

```bash
# .env-Datei auf Server prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "cat /opt/business-hub/.env | grep -E 'SECRET_KEY|USERLIST|ADMIN_USERS'"

# Wichtig: Diese Variablen müssen gesetzt sein:
# SECRET_KEY=<starker-key>
# USERLIST=<user:pass,user2:pass2>  # Kann jetzt auch bcrypt-Hashes enthalten
# ADMIN_USERS=<admin1,admin2,admin3>
```

---

## Teil 3: Service neu starten

### 1. Syntax-Check

```bash
# Auf dem Server:
cd /opt/business-hub
source venv/bin/activate

# Python-Syntax prüfen
python -m py_compile app/__init__.py
python -m py_compile app/services/security_service.py
python -m py_compile app/services/audit_service.py
python -m py_compile app/services/analytics_service.py
python -m py_compile app/routes/analytics.py

# Flask-App laden (sollte keine Fehler geben)
python -c "from app import create_app; app = create_app(); print('✅ App loaded successfully')"
```

### 2. Service neu starten

```bash
# Systemd-Service neu starten
systemctl restart business-hub

# Status prüfen (sollte "active (running)" zeigen)
systemctl status business-hub --no-pager

# Logs in Echtzeit verfolgen
tail -f /var/log/business-hub/error.log
```

### 3. Health-Check

```bash
# Von lokalem Rechner oder auf Server:
curl http://91.98.192.233/health

# Erwartete Antwort:
# {
#   "status": "healthy",
#   "timestamp": "2025-...",
#   "version": "1.0.0",
#   "tools": {
#     "slots": "healthy",
#     "t2": "healthy",
#     "analytics": "healthy"
#   },
#   "database": "healthy",
#   "memory": "ok"
# }
```

---

## Teil 4: Funktionalitäts-Tests

### 1. Password-Hashing testen

```bash
# Auf dem Server:
python3 << 'EOF'
from app.services.security_service import security_service

# Test 1: Plaintext-Passwort (Legacy)
print("Test 1 - Legacy Plaintext:")
result = security_service.verify_password("testuser", "plaintext_password")
print(f"Result: {result}")

# Test 2: Bcrypt-Hash
print("\nTest 2 - Bcrypt Hash:")
hashed = security_service.hash_password("secure_password_123")
print(f"Hashed: {hashed[:30]}...")
result = security_service.verify_hashed_password("secure_password_123", hashed)
print(f"Verification: {result}")

print("\n✅ Password hashing functional")
EOF
```

### 2. Rate-Limiting testen

```bash
# Von lokalem Rechner (schnelle Login-Versuche):
for i in {1..6}; do
  echo "Request $i:"
  curl -X POST http://91.98.192.233/login \
    -d "username=test&password=test" \
    -w "\nStatus: %{http_code}\n\n" \
    -s -o /dev/null
  sleep 1
done

# Erwartung: Erste 5 Requests → 200/302, 6. Request → 429 (Rate Limit Exceeded)
```

### 3. Audit-Logging testen

```bash
# Auf dem Server:
python3 << 'EOF'
from app.services.audit_service import audit_service

# Event loggen
audit_service.log_event(
    event_type='test',
    action='deployment_test',
    details={'message': 'Testing audit logging after deployment'},
    severity='info',
    user='deployment_script'
)

print("✅ Audit event logged")

# Events abrufen
recent = audit_service.get_recent_events(limit=5)
print(f"\nRecent events: {len(recent)}")
for event in recent:
    print(f"  - {event['timestamp']}: {event['action']}")
EOF
```

### 4. Analytics-Dashboard testen

```bash
# Browser öffnen (von lokalem Rechner):
# 1. Login als Admin:
#    http://91.98.192.233/login

# 2. Analytics-Dashboard aufrufen:
#    http://91.98.192.233/analytics/

# Erwartung:
# - Dashboard lädt ohne Fehler
# - Quick Stats werden angezeigt (Total Bookings, Active Users, etc.)
# - Charts laden (Funnel-Chart, Trend-Chart)
# - Recent Activity Tabelle zeigt Ereignisse
# - Nur für Admins zugänglich (Nicht-Admins → 403 Forbidden)

# 3. API-Endpoints testen:
curl http://91.98.192.233/analytics/api/funnel
curl http://91.98.192.233/analytics/api/trends/month
curl http://91.98.192.233/analytics/api/berater-stats
```

---

## Teil 5: Passwort-Migration (Optional)

Falls Sie alle bestehenden Plaintext-Passwörter zu bcrypt-Hashes migrieren möchten:

### Option A: Automatische Migration (Empfohlen)

```bash
# Auf dem Server:
cd /opt/business-hub
source venv/bin/activate

# Migrations-Script ausführen
python scripts/migrate_passwords.py

# Das Script wird:
# 1. Backup erstellen
# 2. Alle Plaintext-Passwörter zu bcrypt-Hashes konvertieren
# 3. user_passwords.json aktualisieren
# 4. Bestätigung anzeigen
```

### Option B: Manuelle Migration pro Benutzer

```bash
# Auf dem Server - Python-Shell:
python3 << 'EOF'
from app.services.security_service import security_service
from app.core.extensions import data_persistence

# Bestehende Passwörter laden
passwords = data_persistence.load_data('user_passwords', {})

# Beispiel: Passwort für "Jose" ändern
username = "Jose"
new_password = "secure_password_123"  # Neues Passwort

# Passwort hashen und speichern
hashed = security_service.hash_password(new_password)
passwords[username] = hashed
data_persistence.save_data('user_passwords', passwords)

print(f"✅ Password for {username} updated")
EOF
```

**WICHTIG:** Nach Migration müssen Benutzer ihre neuen Passwörter verwenden (falls geändert).

---

## Teil 6: Monitoring & Logs

### 1. Log-Dateien überwachen

```bash
# Error-Log (wichtigste Log-Datei)
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"

# Audit-Log (neue Security-Events)
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/audit.log"

# Access-Log (HTTP-Requests)
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/access.log"

# Live-Monitoring (Echtzeit)
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -f /var/log/business-hub/error.log"
```

### 2. Systemd-Service-Status

```bash
# Service-Status prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub --no-pager"

# Service-Logs ansehen
ssh -i ~/.ssh/server_key root@91.98.192.233 "journalctl -u business-hub -n 50 --no-pager"

# Bei Problemen: Service neu starten
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"
```

### 3. Performance-Monitoring

```bash
# Speicher-Nutzung
ssh -i ~/.ssh/server_key root@91.98.192.233 "free -h"

# Disk-Space
ssh -i ~/.ssh/server_key root@91.98.192.233 "df -h /opt/business-hub"

# Python-Prozess-Ressourcen
ssh -i ~/.ssh/server_key root@91.98.192.233 "ps aux | grep python"

# Nginx-Status
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status nginx --no-pager"
```

---

## 🛡️ Rollback-Plan (Bei Problemen)

Falls nach dem Deployment Probleme auftreten:

### 1. Schneller Rollback (Dateien wiederherstellen)

```bash
# Auf dem Server:
cd /opt/business-hub

# Neuestes Backup finden
ls -lt backups/ | head -5

# Backup wiederherstellen (Beispiel)
BACKUP_FILE="backups/backup_2025XXXX_XXXXXX.tar.gz"
tar -xzf $BACKUP_FILE -C /opt/business-hub/

# Service neu starten
systemctl restart business-hub
```

### 2. Selektiver Rollback (einzelne Dateien)

```bash
# Einzelne Datei aus Backup wiederherstellen
cd /opt/business-hub
tar -xzf backups/backup_latest.tar.gz --strip-components=2 data/persistent/user_passwords.json

# Service neu starten
systemctl restart business-hub
```

### 3. Dependencies-Rollback

```bash
# Falls bcrypt Probleme verursacht:
pip uninstall bcrypt

# Alte requirements.txt wiederherstellen und installieren
pip install -r requirements.txt.backup
```

---

## ✅ Deployment-Checkliste

Nach erfolgreichem Deployment sollten folgende Punkte erfüllt sein:

### Backend
- [ ] Alle Python-Dateien auf Server übertragen
- [ ] bcrypt installiert und funktionsfähig
- [ ] Service erfolgreich neu gestartet
- [ ] Keine Fehler in `/var/log/business-hub/error.log`

### Funktionalität
- [ ] Login funktioniert (mit Plaintext und gehashten Passwörtern)
- [ ] Rate-Limiting aktiv (6. Login-Versuch wird geblockt)
- [ ] Audit-Logging funktioniert (Events in `data/persistent/audit_logs/`)
- [ ] Analytics-Dashboard lädt (nur für Admins)
- [ ] Charts werden korrekt angezeigt (Funnel, Trends)

### Security
- [ ] Admin-Only-Access für Analytics funktioniert (403 für Nicht-Admins)
- [ ] 2FA funktioniert weiterhin (falls bereits aktiviert)
- [ ] Audit-Logs erfassen Login-Aktivitäten

### Performance
- [ ] Dashboard lädt in <2 Sekunden
- [ ] Keine Memory-Leaks (Server-Speicher stabil)
- [ ] Health-Check gibt "healthy" zurück

---

## 📞 Support & Troubleshooting

### Häufige Probleme

#### Problem 1: "Module 'bcrypt' not found"
```bash
# Lösung:
cd /opt/business-hub
source venv/bin/activate
pip install bcrypt==4.2.1
systemctl restart business-hub
```

#### Problem 2: "Permission denied" beim Audit-Logging
```bash
# Lösung:
chown -R www-data:www-data /opt/business-hub/data/persistent/
chmod -R 755 /opt/business-hub/data/persistent/
systemctl restart business-hub
```

#### Problem 3: Analytics-Dashboard zeigt 404
```bash
# Prüfen ob Blueprint registriert:
python3 -c "from app import create_app; app = create_app(); print([r.rule for r in app.url_map.iter_rules() if 'analytics' in r.rule])"

# Falls leer: app/__init__.py nochmal übertragen
scp -i ~/.ssh/server_key app/__init__.py root@91.98.192.233:/opt/business-hub/app/
systemctl restart business-hub
```

#### Problem 4: Rate-Limiting funktioniert nicht
```bash
# Prüfen ob Flask-Limiter installiert:
python3 -c "from flask_limiter import Limiter; print('Flask-Limiter OK')"

# Falls fehlt:
pip install Flask-Limiter
systemctl restart business-hub
```

### Debug-Modus aktivieren (Nur für Troubleshooting!)

```bash
# NICHT in Production empfohlen!
# Nur temporär zum Debuggen:

ssh -i ~/.ssh/server_key root@91.98.192.233
cd /opt/business-hub

# Flask Debug-Modus (gibt detaillierte Fehlermeldungen)
export FLASK_DEBUG=1
python run.py

# Danach: Service normal neu starten
systemctl restart business-hub
```

---

## 📊 Erfolgsmessung

Nach 24 Stunden Betrieb prüfen:

```bash
# 1. Audit-Log-Statistik
python3 << 'EOF'
from app.services.audit_service import audit_service
stats = audit_service.get_statistics()
print(f"Total Events: {stats['total_events']}")
print(f"Login Success: {stats['login_success']}")
print(f"Login Failures: {stats['login_failures']}")
EOF

# 2. Rate-Limiting-Wirksamkeit
grep "Rate limit exceeded" /var/log/business-hub/error.log | wc -l

# 3. Analytics-Dashboard-Zugriffe
grep "GET /analytics" /var/log/business-hub/access.log | wc -l
```

---

## 🎉 Deployment abgeschlossen!

Wenn alle Checks ✅ sind, ist das Deployment erfolgreich abgeschlossen.

**Nächste Schritte:**
- 📈 Analytics-Dashboard regelmäßig nutzen für Business-Insights
- 🔐 Passwort-Migration planen (falls noch nicht durchgeführt)
- 📊 Audit-Logs monatlich reviewen
- 🚀 Phase 4 Features aus docs/CLAUDE.md bei Bedarf implementieren

---

## 📚 Detaillierte Deployment-Konfigurationen

Für technische Deep-Dives und spezifische Setup-Anleitungen siehe:

**Server-Setup:**
- [DNS Setup Guide](../deployment/DNS_SETUP.md) - Domain & DNS-Konfiguration
- [SSH Key Setup](../deployment/SSH_KEY_SETUP.md) - Sichere SSH-Authentifizierung
- [Git Token Setup](../deployment/GIT_TOKEN_SETUP.md) - GitHub-Integration für Deployment

**System-Konfiguration:**
- [Systemd Services](../deployment/README.md) - Service-Management & Background Jobs
- [Backup Setup](../deployment/BACKUP_SETUP.md) - Automatische Backups & Rotation
- [VPS Migration Guide](../deployment/VPS_MIGRATION_GUIDE.md) - Server-Migration

**T2-System:**
- [T2 Deployment](../deployment/T2_DEPLOYMENT.md) - T2-Closer-System Setup
- [T2 Bucket System](../deployment/T2_BUCKET_SYSTEM_DEPLOYMENT.md) - Würfelsystem-Konfiguration

**Weitere Ressourcen:**
- [Documentation Index](INDEX.md) - Vollständige Dokumentationsübersicht
- [Developer Guide](DEVELOPER_GUIDE.md) - Lokale Entwicklungsumgebung
- [Security Guidelines](SECURITY.md) - Sicherheitsrichtlinien

Bei Fragen oder Problemen: Logs prüfen und ggf. Rollback durchführen.
