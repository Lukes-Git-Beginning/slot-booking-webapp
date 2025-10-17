# 📋 Post-Reset Tasks - Nach Session-Reset durchführen

**Datum**: 2025-10-17
**Session-Budget**: ~94% verbraucht (Reset erforderlich)
**Zeitpunkt**: Nach erfolgreichem Reset weiterarbeiten

---

## 🎯 Priorität A - Optional aber empfohlen (Heute Nachmittag)

### 1. **Sentry Error Tracking Setup** (30 Minuten)
**Warum**: Automatische Fehlerbenachrichtigung vor Go-Live am Montag

**Tasks**:
- [ ] Sentry Account erstellen / bestehendes Projekt verwenden
- [ ] `sentry-sdk` in `requirements.txt` hinzufügen
- [ ] Sentry in `app/__init__.py` initialisieren
- [ ] DSN als `SENTRY_DSN` in `.env` konfigurieren
- [ ] Test-Error auslösen und verifizieren
- [ ] Auf Server deployen

**Code-Snippet**:
```python
# In app/__init__.py nach create_app()
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

if app.config.get('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=app.config['SENTRY_DSN'],
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,
        environment='production'
    )
```

---

### 2. **Performance Testing** (45-60 Minuten)
**Warum**: Sicherstellen dass System unter Last stabil läuft

**Tasks**:
- [ ] Load-Test für Booking-Endpoint (50 gleichzeitige Requests)
- [ ] Google Calendar API Quota-Test (prüfen ob 180 req/min ausreichen)
- [ ] Memory-Leak-Test (Service 1 Stunde laufen lassen, RAM beobachten)
- [ ] Rate Limiting testen (verifizieren dass 429 korrekt zurückgegeben wird)
- [ ] Response-Time-Messung für kritische Endpoints

**Tools**:
```bash
# Load Testing mit Apache Bench
ab -n 100 -c 10 http://91.98.192.233/slots/

# Rate Limit Test
for i in {1..20}; do curl -s -w "%{http_code}\n" -o /dev/null http://91.98.192.233/login; done

# Memory-Check
ssh -i ~/.ssh/server_key root@91.98.192.233 "while true; do systemctl status business-hub --no-pager | grep Memory; sleep 300; done"
```

---

## 🎯 Priorität B - Nice-to-Have (Sonntag)

### 3. **Extended Health Checks** (20 Minuten)
**Warum**: Bessere Uptime-Robot Integration und Debugging

**Tasks**:
- [ ] Health-Endpoint erweitern mit detaillierten Checks
  - Google Calendar API Connectivity
  - Data Persistence Layer Status
  - Cache Manager Status
  - Disk Space Check
- [ ] JSON-Response mit Status-Codes (200 = healthy, 503 = degraded)
- [ ] Uptimerobot auf erweiterten Endpoint umstellen

---

### 4. **Documentation für Team** (30 Minuten)
**Warum**: Team-Mitglieder müssen System verstehen

**Tasks**:
- [ ] Kurzes Admin-Handbuch erstellen (`ADMIN_GUIDE.md`)
  - Wie man gesperrte Termine verwaltet
  - Wie man Logs einsieht
  - Wie man Backups manuell erstellt
  - Notfall-Kontakte und Prozeduren
- [ ] User-Guide für Consultant Analytics
- [ ] Troubleshooting-Guide für häufige Probleme

---

## 🎯 Priorität C - Nach Go-Live (kommende Woche)

### 5. **Database Migration zu PostgreSQL** (2-3 Stunden)
**Warum**: Skalierbarkeit und Performance für Production

**Tasks**:
- [ ] PostgreSQL auf Hetzner installieren
- [ ] `psycopg2` hinzufügen
- [ ] SQLAlchemy-Models für alle JSON-Datenstrukturen erstellen
- [ ] Migration-Script für bestehende JSON-Daten
- [ ] Data-Persistence-Layer auf PostgreSQL umstellen
- [ ] Backup-Strategie anpassen (pg_dump)

---

### 6. **Redis für Caching & Sessions** (1-2 Stunden)
**Warum**: In-Memory-Cache besser als Pickle-Files

**Tasks**:
- [ ] Redis auf Hetzner installieren
- [ ] `redis-py` und `Flask-Session` hinzufügen
- [ ] Cache-Manager auf Redis umstellen
- [ ] Session-Storage auf Redis umstellen
- [ ] Rate-Limiting auf Redis umstellen (statt Memory)

---

## 📊 System-Status Checkliste (vor Go-Live Montag)

**Freitag Abend / Samstag Morgen**:
- [ ] Alle Logs durchsehen auf Errors/Warnings
- [ ] Uptimerobot Status überprüfen (sollte 100% Uptime zeigen)
- [ ] Google Calendar API Quota überprüfen
- [ ] Test-Buchung durchführen (kompletter Flow)
- [ ] Admin-Interface testen (gesperrte Termine, User-Management)
- [ ] 2FA testen
- [ ] Rate Limiting verifizieren
- [ ] Cache-Cleanup Timer überprüfen (`systemctl list-timers`)
- [ ] Backup-Rotation überprüfen (Cron-Log)

**Sonntag Abend** (Go/No-Go Decision):
- [ ] Finale Systemprüfung
- [ ] Backup erstellen (Full System)
- [ ] Team benachrichtigen
- [ ] Rollback-Plan dokumentieren

---

## 🚨 Notfall-Kontakte & Rollback

### Rollback-Prozedur
```bash
# 1. Service stoppen
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl stop business-hub"

# 2. Zu letztem funktionierenden Commit zurück
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && git reset --hard <commit-hash>"

# 3. Service starten
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl start business-hub"

# 4. Logs prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"
```

### Monitoring
- **Uptimerobot**: https://uptimerobot.com (Monitor-IDs notieren)
- **Server**: http://91.98.192.233
- **Logs**: `/var/log/business-hub/error.log`
- **Service**: `systemctl status business-hub`

---

## ✅ Abgeschlossen heute (2025-10-17)

- ✅ Google Calendar API Fix (ISO 8601)
- ✅ Security Hardening (Nginx + Flask Rate Limiting)
- ✅ Cache-Cleanup Automation (Systemd Timer)
- ✅ Backup Rotation (Cron)
- ✅ Log Rotation (verifiziert)
- ✅ System Health Check
- ✅ README.md update
- ✅ CLAUDE.md update

**Zeit investiert**: ~2 Stunden
**System Status**: ✅ Production-Ready für Go-Live Montag
