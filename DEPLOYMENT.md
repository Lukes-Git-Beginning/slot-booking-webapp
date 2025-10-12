# Deployment-Anleitung: Phase 1 & 2 Features

Diese Anleitung beschreibt das Deployment der neu implementierten Features auf den Hetzner Production-Server.

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
- 🚀 Phase 4 Features aus CLAUDE.md bei Bedarf implementieren

Bei Fragen oder Problemen: Logs prüfen und ggf. Rollback durchführen.
