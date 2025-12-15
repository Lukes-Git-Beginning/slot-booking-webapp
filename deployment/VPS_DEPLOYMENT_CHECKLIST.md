# VPS Deployment Checklist
## Business Tool Hub - Vollständige Setup-Checkliste

---

## 📋 Pre-Deployment (Vorbereitung)

### Server-Beschaffung
- [ ] VPS bestellt (Hetzner CX22 empfohlen, siehe SERVER_COMPARISON.md)
- [ ] Server-IP-Adresse notiert: `____________`
- [ ] Root-Passwort oder SSH-Key erhalten
- [ ] Server läuft und ist erreichbar

### Domain & DNS (Optional, aber empfohlen)
- [ ] Domain registriert oder vorhanden
- [ ] DNS-Provider Zugangsdaten bereit
- [ ] A-Records vorbereitet (noch nicht aktiviert)

### Credentials & Konfiguration
- [ ] Google Service Account JSON vorhanden
- [ ] GOOGLE_CREDS_BASE64 generiert: `echo -n "$(cat service_account.json)" | base64 -w 0`
- [ ] USERLIST vorbereitet (username:password,...)
- [ ] Alle Kalender-IDs dokumentiert
- [ ] Admin-Benutzer definiert

---

## 🚀 Phase 1: Server-Basis-Setup

### Erste Verbindung
- [ ] SSH-Verbindung erfolgreich: `ssh root@<server-ip>`
- [ ] Root-Passwort geändert (falls nötig)
- [ ] SSH-Key hinzugefügt zu `~/.ssh/authorized_keys`

### System-Updates
```bash
apt-get update && apt-get upgrade -y
```
- [ ] System aktualisiert
- [ ] Reboot (falls Kernel-Update): `reboot`

### Basis-Konfiguration
```bash
hostnamectl set-hostname business-hub
timedatectl set-timezone Europe/Berlin
```
- [ ] Hostname gesetzt
- [ ] Timezone auf Europe/Berlin gesetzt
- [ ] Locale geprüft: `locale`

### VPS Setup-Script
```bash
wget https://raw.githubusercontent.com/.../deployment/vps_setup.sh
chmod +x vps_setup.sh
./vps_setup.sh
```
- [ ] vps_setup.sh heruntergeladen
- [ ] Script ausgeführt (ohne Fehler)
- [ ] Log-Datei gespeichert: `/tmp/business-hub-setup.log`

**Script erstellt:**
- [ ] Python 3.11 installiert
- [ ] Nginx installiert und läuft
- [ ] UFW Firewall konfiguriert (Port 22, 80, 443)
- [ ] Application-User `business-hub` erstellt
- [ ] Verzeichnisse `/opt/business-hub/*` erstellt
- [ ] Certbot für SSL installiert
- [ ] Log-Rotation konfiguriert

---

## 📦 Phase 2: Application Deployment

### Repository klonen
```bash
cd /opt/business-hub
sudo -u business-hub git clone <repo-url> .
```
- [ ] Repository geklont
- [ ] Branch `main` aktiv
- [ ] Dateien vorhanden: `ls -la`

### Python Virtual Environment
```bash
sudo -u business-hub python3 -m venv venv
sudo -u business-hub venv/bin/pip install --upgrade pip
sudo -u business-hub venv/bin/pip install -r requirements.txt
```
- [ ] Virtual Environment erstellt
- [ ] Pip aktualisiert
- [ ] Dependencies installiert (keine Fehler)
- [ ] Verifiziert: `venv/bin/pip list`

### Umgebungsvariablen (.env)
```bash
sudo -u business-hub cp .env.example .env
sudo -u business-hub nano .env
```
- [ ] .env Datei erstellt
- [ ] SECRET_KEY generiert (NEU, nicht von Render!)
- [ ] GOOGLE_CREDS_BASE64 eingetragen
- [ ] CENTRAL_CALENDAR_ID eingetragen
- [ ] CONSULTANTS konfiguriert
- [ ] T2_CLOSERS konfiguriert
- [ ] USERLIST konfiguriert
- [ ] ADMIN_USERS definiert
- [ ] PERSIST_BASE=/opt/business-hub/data gesetzt
- [ ] FLASK_ENV=production gesetzt

**Alle wichtigen .env Variablen:**
```
SECRET_KEY=<neu-generiert>
FLASK_ENV=production
GOOGLE_CREDS_BASE64=<base64-encoded>
CENTRAL_CALENDAR_ID=central-calendar@example.com
CONSULTANTS=Name1:consultant1@example.com,Name2:consultant2@example.com
T2_CLOSERS=Name1:closer1@example.com,Name2:closer2@example.com
USERLIST=user1:pass1,user2:pass2
ADMIN_USERS=admin,user1
PERSIST_BASE=/opt/business-hub/data
```

### Service Account (optional)
```bash
sudo -u business-hub nano /opt/business-hub/service_account.json
chmod 600 /opt/business-hub/service_account.json
```
- [ ] service_account.json erstellt (falls benötigt)
- [ ] Permissions korrekt (600)

---

## 📊 Phase 3: Daten-Migration

### Daten von Render holen
**Methode A: Via Git (empfohlen)**
```bash
# Bereits im Repository:
ls -la /opt/business-hub/data/persistent/
ls -la /opt/business-hub/static/
```
- [ ] Daten im Repository gefunden
- [ ] scores.json vorhanden
- [ ] champions.json vorhanden
- [ ] user_badges.json vorhanden
- [ ] weekly_points.json vorhanden

**Methode B: Manueller Upload (falls nötig)**
```bash
# Von lokalem PC:
scp ~/render-backup/*.json root@<server-ip>:/tmp/
# Auf Server:
sudo -u business-hub cp /tmp/*.json /opt/business-hub/data/persistent/
```
- [ ] Daten hochgeladen
- [ ] In `/opt/business-hub/data/persistent/` kopiert
- [ ] Permissions gesetzt: `chown business-hub:www-data *.json`

### Datenintegrität prüfen
```bash
sudo -u business-hub bash -c 'cd /opt/business-hub && source venv/bin/activate && python3 -c "
from app.services.data_persistence import data_persistence
ok, issues = data_persistence.validate_data_integrity()
print(\"OK\" if ok else f\"FEHLER: {issues}\")
"'
```
- [ ] Datenintegritäts-Check erfolgreich
- [ ] Keine Fehler gefunden

---

## ⚙️ Phase 4: Systemd Service

### Service-Datei einrichten
```bash
cp /opt/business-hub/deployment/business-hub.service /etc/systemd/system/
nano /etc/systemd/system/business-hub.service
```
- [ ] Service-Datei kopiert
- [ ] Pfade in Service-Datei geprüft (sollten passen)
- [ ] User: `business-hub`
- [ ] WorkingDirectory: `/opt/business-hub`
- [ ] EnvironmentFile: `/opt/business-hub/.env`

### Service aktivieren & starten
```bash
systemctl daemon-reload
systemctl enable business-hub
systemctl start business-hub
systemctl status business-hub
```
- [ ] daemon-reload ausgeführt
- [ ] Service enabled (Auto-Start)
- [ ] Service gestartet
- [ ] Status = `active (running)`

### Service-Logs prüfen
```bash
journalctl -u business-hub -n 50 --no-pager
journalctl -u business-hub -f
```
- [ ] Keine Fehler in Logs
- [ ] Gunicorn läuft
- [ ] Workers gestartet (2-4)
- [ ] Application ready

### Port-Check
```bash
netstat -tlnp | grep 5000
curl http://127.0.0.1:5000/health
```
- [ ] Port 5000 hört auf localhost
- [ ] Health-Check antwortet: `{"status": "healthy"}`

---

## 🌐 Phase 5: Nginx Reverse Proxy

### Nginx-Konfiguration
```bash
cp /opt/business-hub/deployment/nginx.conf /etc/nginx/sites-available/business-hub
nano /etc/nginx/sites-available/business-hub
```
- [ ] Nginx-Config kopiert
- [ ] Domain in Config angepasst (oder IP für IP-basiertes Setup)

**Domain-Setup:**
```nginx
server_name deine-domain.de www.deine-domain.de;
```

**IP-basiertes Setup (ohne Domain):**
```nginx
server_name _;  # Akzeptiert alle Anfragen
```

### Nginx aktivieren
```bash
ln -s /etc/nginx/sites-available/business-hub /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```
- [ ] Symlink erstellt
- [ ] Default-Site entfernt (optional)
- [ ] Nginx-Syntax-Test OK: `nginx -t`
- [ ] Nginx neu geladen

### Nginx-Test
```bash
curl -I http://<server-ip>/
curl http://<server-ip>/health
```
- [ ] HTTP-Anfrage erfolgreich (200 OK)
- [ ] Health-Check über Nginx funktioniert
- [ ] Nginx-Logs zeigen Anfragen: `tail -f /var/log/nginx/business-hub-access.log`

---

## 🔒 Phase 6: SSL & DNS

### DNS-Einträge setzen (falls Domain vorhanden)
Bei deinem DNS-Provider:
```
A-Record:
  Name: @
  Type: A
  Value: <server-ip>
  TTL: 3600

A-Record:
  Name: www
  Type: A
  Value: <server-ip>
  TTL: 3600
```
- [ ] A-Records erstellt
- [ ] DNS-Propagation gewartet (5-60 Min)
- [ ] DNS-Check: `nslookup deine-domain.de`
- [ ] Domain zeigt auf Server-IP

### SSL-Zertifikat (Let's Encrypt)
```bash
certbot --nginx -d deine-domain.de -d www.deine-domain.de
```
- [ ] Certbot ausgeführt
- [ ] Email angegeben
- [ ] Terms akzeptiert
- [ ] HTTPS-Redirect aktiviert (empfohlen: Ja)
- [ ] Zertifikat erfolgreich installiert
- [ ] Auto-Renewal-Test: `certbot renew --dry-run`

### HTTPS-Test
```bash
curl -I https://deine-domain.de/
curl https://deine-domain.de/health
```
- [ ] HTTPS funktioniert
- [ ] HTTP → HTTPS Redirect aktiv
- [ ] Browser-Test: Grünes Schloss-Symbol

---

## ✅ Phase 7: Funktionstests

### Basis-Funktionen
Via Browser auf https://deine-domain.de testen:

- [ ] **Startseite:** Root `/` lädt (Login oder Redirect)
- [ ] **Login:** `/login` funktioniert
- [ ] **Dashboard:** Nach Login erreichbar
- [ ] **Hub:** `/hub` zeigt Tool-Übersicht
- [ ] **Slots-Tool:** `/slots/` lädt komplett
- [ ] **T2-Tool:** `/t2/` lädt komplett
- [ ] **Health-Check:** `/health` zeigt Status

### Erweiterte Features
- [ ] **Terminbuchung:** Buchung funktioniert
- [ ] **Google Calendar:** Integration aktiv (Termine erscheinen)
- [ ] **Kalender-Ansicht:** `/slots/calendar` zeigt Termine
- [ ] **Gamification:** Badges/Levels laden
- [ ] **Scoreboard:** `/slots/scoreboard` zeigt Rangliste
- [ ] **Admin-Bereich:** `/admin/` für Admin-User erreichbar
- [ ] **Feiertags-Sperrung:** Blockierte Termine erkannt

### Performance-Tests
```bash
# Response-Time
time curl -I https://deine-domain.de/

# Load-Test (optional)
ab -n 100 -c 10 https://deine-domain.de/
```
- [ ] Response-Time < 500ms
- [ ] Load-Test erfolgreich (falls durchgeführt)

---

## 📈 Phase 8: Monitoring & Backup

### Log-Dateien einrichten
```bash
ls -la /var/log/business-hub/
tail -f /var/log/business-hub/access.log
tail -f /var/log/business-hub/error.log
```
- [ ] Log-Verzeichnis vorhanden
- [ ] Logs werden geschrieben
- [ ] Log-Rotation aktiv: `/etc/logrotate.d/business-hub`

### Backup-Script
```bash
cp /opt/business-hub/deployment/vps_backup.sh /usr/local/bin/
chmod +x /usr/local/bin/vps_backup.sh
```
- [ ] Backup-Script kopiert
- [ ] Ausführbar gemacht
- [ ] Manueller Test: `/usr/local/bin/vps_backup.sh`

### Cron-Job für automatische Backups
```bash
crontab -e
# Add:
0 2 * * * /usr/local/bin/vps_backup.sh >> /var/log/business-hub/backup.log 2>&1
```
- [ ] Cron-Job erstellt
- [ ] Backup-Zeit: Täglich 2:00 Uhr
- [ ] Test-Backup erfolgreich

### Monitoring
```bash
htop  # Ressourcen-Überwachung
systemctl status business-hub  # Service-Status
journalctl -u business-hub -f  # Live-Logs
```
- [ ] Monitoring-Tools installiert (htop, iotop)
- [ ] Service läuft stabil
- [ ] RAM-Nutzung akzeptabel (<50% auf CX22)
- [ ] CPU-Load niedrig (<1.0)

---

## 🔧 Phase 9: Optimierung & Security

### Security-Hardening
```bash
# SSH-Port ändern (optional)
nano /etc/ssh/sshd_config
# Port 22 → 2222
systemctl restart sshd

# SSH Password-Auth deaktivieren (nach SSH-Key-Setup!)
nano /etc/ssh/sshd_config
# PasswordAuthentication no
```
- [ ] SSH-Port geändert (optional)
- [ ] SSH-Key-Only aktiv (empfohlen)
- [ ] Root-Login via SSH deaktiviert (optional)

### Fail2Ban (optional)
```bash
apt-get install fail2ban -y
systemctl enable fail2ban
systemctl start fail2ban
```
- [ ] Fail2Ban installiert (optional)
- [ ] Gegen Brute-Force geschützt

### Performance-Tuning
```bash
# In /etc/systemd/system/business-hub.service:
# Workers erhöhen falls genug RAM (2 → 4)
nano /etc/systemd/system/business-hub.service
systemctl daemon-reload
systemctl restart business-hub
```
- [ ] Gunicorn Workers optimiert (falls nötig)
- [ ] Nginx-Caching aktiviert (bereits in Config)

---

## 🎉 Phase 10: Go-Live

### Pre-Launch-Checks
- [ ] Alle Funktionstests erfolgreich
- [ ] SSL aktiv und valide
- [ ] Backups eingerichtet
- [ ] Monitoring aktiv
- [ ] 24h Testbetrieb erfolgreich
- [ ] Team informiert

### Render.com deaktivieren (nach Testphase)
- [ ] 1 Woche parallel-Betrieb erfolgreich
- [ ] GitHub Actions auf VPS umgestellt (optional)
- [ ] Final-Backup von Render erstellt
- [ ] Render Service pausiert/gestoppt

### Post-Launch
- [ ] DNS TTL zurückgesetzt (von 300 auf 3600)
- [ ] Performance-Monitoring erste Woche
- [ ] Backup-Restore-Test durchgeführt
- [ ] Team-Feedback gesammelt

---

## 📊 System-Metriken (Benchmark)

### Erwartete Performance (Hetzner CX22):

```
RAM Usage:      ~1.5-2.0 GB / 4 GB (38-50%)
CPU Load:       0.2-0.8 (idle-normal)
Disk I/O:       Low (JSON-basiert)
Response Time:  100-300ms (avg)
Uptime:         99.9%+
```

### Monitoring-Kommandos:
```bash
# Ressourcen
htop
df -h
free -h

# Service
systemctl status business-hub
journalctl -u business-hub --since "1 hour ago"

# Nginx
tail -f /var/log/nginx/business-hub-access.log
nginx -t && echo "Config OK"

# Network
netstat -tlnp
ufw status
```

---

## 🆘 Troubleshooting-Quick-Reference

### Application startet nicht
```bash
journalctl -u business-hub -n 100 --no-pager
# Check .env, permissions, dependencies
```

### Nginx 502 Bad Gateway
```bash
systemctl status business-hub
netstat -tlnp | grep 5000
# Gunicorn läuft nicht → Service-Logs prüfen
```

### Google Calendar fehlt
```bash
sudo -u business-hub bash -c 'cd /opt/business-hub && source venv/bin/activate && python3 -c "
from app.core.google_calendar import GoogleCalendarService
print(GoogleCalendarService().is_configured())
"'
```

### Daten fehlen
```bash
ls -la /opt/business-hub/data/persistent/
# Bootstrap from static:
sudo -u business-hub bash -c 'cd /opt/business-hub && source venv/bin/activate && python3 -c "
from app.services.data_persistence import data_persistence
data_persistence.bootstrap_from_static_if_missing()
"'
```

---

## ✅ Final Checklist

### Must-Have (Vor Go-Live):
- [ ] Server läuft und ist erreichbar
- [ ] Application startet ohne Fehler
- [ ] SSL funktioniert
- [ ] Login funktioniert
- [ ] Terminbuchung funktioniert
- [ ] Google Calendar-Integration aktiv
- [ ] Backups eingerichtet

### Should-Have (Erste Woche):
- [ ] Monitoring eingerichtet
- [ ] Logs werden geprüft
- [ ] Performance-Optimierung
- [ ] Team-Training

### Nice-to-Have (Später):
- [ ] CDN für Static-Files
- [ ] Load-Balancer (bei Wachstum)
- [ ] Redis-Cache
- [ ] Erweiterte Analytics

---

**🎊 Deployment abgeschlossen! Viel Erfolg mit dem Business Tool Hub auf VPS!**