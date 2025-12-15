# Migration von Render.com zu VPS
## Business Tool Hub - Schritt-für-Schritt Guide

---

## 🎯 Übersicht

Dieser Guide beschreibt die vollständige Migration des Business Tool Hub von Render.com zu einem selbst gehosteten VPS (Hetzner, Strato, oder anderen Ubuntu-basierten VPS).

**Zeitaufwand:** 2-4 Stunden
**Schwierigkeit:** Mittel
**Downtime:** 10-30 Minuten

---

## 📋 Voraussetzungen

### Auf Render.com (Quelle):
- [x] Zugriff auf Render Dashboard
- [x] SSH-Zugriff auf Render Container (optional)
- [x] Alle Umgebungsvariablen dokumentiert

### Auf VPS (Ziel):
- [x] Frischer Ubuntu 20.04/22.04 Server
- [x] Root/sudo-Zugriff
- [x] Mindestens 2GB RAM, 10GB Storage
- [x] Domain (optional, empfohlen für SSL)

### Lokale Maschine:
- [x] SSH-Client
- [x] Git installiert
- [x] Text-Editor

---

## 🗺️ Migrations-Roadmap

```
Phase 1: VPS Vorbereitung (45 Min)
   └─> Server-Setup, Nginx, Python

Phase 2: Daten-Export von Render (15 Min)
   └─> JSON-Dateien herunterladen

Phase 3: Application Deployment (30 Min)
   └─> Code, Dependencies, .env

Phase 4: Daten-Migration (15 Min)
   └─> JSON-Import, Verifikation

Phase 5: DNS & SSL (30 Min)
   └─> Domain umstellen, SSL

Phase 6: Testing & Go-Live (45 Min)
   └─> Funktionstests, Monitoring
```

---

## Phase 1: VPS Vorbereitung

### 1.1 VPS bestellen & einrichten

**Hetzner Cloud:**
```bash
# 1. Account: https://accounts.hetzner.com/signUp
# 2. Server erstellen:
#    - Image: Ubuntu 22.04 LTS
#    - Type: CX22 (4GB RAM)
#    - Location: Nürnberg (nbg1)
#    - SSH Key: Deinen Public Key hinzufügen
```

**Strato VPS:**
```bash
# 1. Account: https://www.strato.de
# 2. VPS V500 V7 bestellen
# 3. SSH-Zugangsdaten per Mail erhalten
```

### 1.2 Erste Verbindung

```bash
# SSH-Verbindung zum VPS
ssh root@<deine-vps-ip>

# System aktualisieren
apt-get update && apt-get upgrade -y

# Hostname setzen (optional)
hostnamectl set-hostname business-hub

# Timezone auf Berlin setzen
timedatectl set-timezone Europe/Berlin
```

### 1.3 VPS Setup-Script ausführen

```bash
# Setup-Script herunterladen
wget https://raw.githubusercontent.com/.../deployment/vps_setup.sh

# Ausführbar machen
chmod +x vps_setup.sh

# Ausführen
./vps_setup.sh
```

**Was das Script macht:**
- ✅ System-Updates
- ✅ Python 3.11 installieren
- ✅ Nginx installieren
- ✅ Firewall (UFW) konfigurieren
- ✅ Application-User erstellen
- ✅ Verzeichnisse anlegen
- ✅ SSL/Certbot installieren
- ✅ Log-Rotation einrichten

---

## Phase 2: Daten-Export von Render

### 2.1 Render-Daten identifizieren

Auf Render sind die Daten hier gespeichert:
```
/opt/render/project/src/persist/persistent/
├── scores.json
├── champions.json
├── user_badges.json
├── user_levels.json
├── daily_user_stats.json
├── prestige_data.json
├── cosmetic_purchases.json
├── daily_quests.json
├── behavior_patterns.json
├── blocked_dates.json
└── weekly_points.json
```

### 2.2 Methode A: Via GitHub (Empfohlen)

**Die Daten werden bereits via GitHub Actions committed!**

```bash
# Auf deinem lokalen PC:
git clone https://github.com/yourusername/slot-booking-webapp.git
cd slot-booking-webapp

# Neueste Daten pullen
git pull origin main

# Daten sind in:
# - data/persistent/*.json
# - static/*.json (Legacy-Fallback)
```

### 2.3 Methode B: Manueller Download von Render

Falls GitHub Actions noch nicht alle Daten gesichert haben:

```bash
# Render Shell öffnen (im Dashboard)
# Oder via SSH (falls aktiviert):

# Dateien packen
cd /opt/render/project/src/persist/persistent/
tar -czf ~/render-data-backup-$(date +%Y%m%d).tar.gz *.json

# Download via Render Dashboard > Shell > Download
# Oder via scp (falls möglich)
```

### 2.4 Backup lokal speichern

```bash
# Auf deinem lokalen PC
mkdir -p ~/render-migration-backup
cd ~/render-migration-backup

# Git-Daten kopieren
cp -r /path/to/repo/data/persistent/*.json .

# Oder manuell heruntergeladenes Archiv entpacken
tar -xzf render-data-backup-*.tar.gz
```

---

## Phase 3: Application Deployment auf VPS

### 3.1 Repository klonen

```bash
# Auf dem VPS als root:
cd /opt/business-hub

# Repository klonen (als application-user)
sudo -u business-hub git clone https://github.com/yourusername/slot-booking-webapp.git .

# Branch checken
sudo -u business-hub git branch
sudo -u business-hub git status
```

### 3.2 Virtual Environment & Dependencies

```bash
# Als application-user
sudo -u business-hub bash << 'EOF'
cd /opt/business-hub

# Virtual Environment erstellen
python3 -m venv venv

# Aktivieren
source venv/bin/activate

# Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt

# Verifizieren
pip list
EOF
```

### 3.3 Umgebungsvariablen konfigurieren

```bash
# .env Datei erstellen
sudo -u business-hub cp /opt/business-hub/.env.example /opt/business-hub/.env

# Editieren
sudo -u business-hub nano /opt/business-hub/.env
```

**Wichtige Variablen von Render übertragen:**

```env
# Secret Key (NEU GENERIEREN!)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Google Calendar (von Render kopieren)
GOOGLE_CREDS_BASE64=<von-render-kopieren>
CENTRAL_CALENDAR_ID=central-calendar@example.com

# Consultants (von Render kopieren)
CONSULTANTS=<von-render-kopieren>

# T2 Closers (von Render kopieren)
T2_CLOSERS=<von-render-kopieren>

# User List (von Render kopieren)
USERLIST=<von-render-kopieren>

# Admin Users
ADMIN_USERS=admin,Jose,Simon,Alex,David

# VPS-spezifisch
PERSIST_BASE=/opt/business-hub/data
FLASK_ENV=production
```

**Render Environment Variables abrufen:**
```bash
# Im Render Dashboard:
# Service > Environment > Alle Variablen kopieren
```

### 3.4 Service Account JSON

```bash
# Falls service_account.json benötigt wird:
sudo -u business-hub nano /opt/business-hub/service_account.json

# Inhalt von Render kopieren
# ODER aus GOOGLE_CREDS_BASE64 dekodieren:
echo "$GOOGLE_CREDS_BASE64" | base64 -d > service_account.json
chmod 600 service_account.json
```

---

## Phase 4: Daten-Migration

### 4.1 Daten auf VPS hochladen

**Methode A: Via Git (bereits da!)**
```bash
# Daten sind bereits im Repository:
ls -la /opt/business-hub/data/persistent/
ls -la /opt/business-hub/static/
```

**Methode B: Via SCP (falls nötig)**
```bash
# Von deinem lokalen PC:
scp ~/render-migration-backup/*.json root@<vps-ip>:/tmp/

# Auf VPS:
sudo -u business-hub cp /tmp/*.json /opt/business-hub/data/persistent/
sudo chown business-hub:www-data /opt/business-hub/data/persistent/*.json
sudo chmod 640 /opt/business-hub/data/persistent/*.json
```

### 4.2 Migrations-Script ausführen

```bash
# Auf VPS
cd /opt/business-hub
sudo -u business-hub venv/bin/python deployment/migrate_from_render.py \
    --source /tmp/render-data \
    --target /opt/business-hub/data/persistent \
    --verify
```

### 4.3 Datenintegrität prüfen

```bash
# Python-Script zur Validierung
sudo -u business-hub venv/bin/python3 << 'EOF'
from app.services.data_persistence import data_persistence

# Datenintegrität prüfen
integrity_ok, issues = data_persistence.validate_data_integrity()

if integrity_ok:
    print("✓ Alle Daten OK!")
else:
    print("✗ Probleme gefunden:")
    for issue in issues:
        print(f"  - {issue}")
EOF
```

---

## Phase 5: Systemd Service & Nginx

### 5.1 Systemd Service einrichten

```bash
# Service-Datei kopieren
cp /opt/business-hub/deployment/business-hub.service /etc/systemd/system/

# Pfade anpassen (falls nötig)
nano /etc/systemd/system/business-hub.service

# Service aktivieren
systemctl daemon-reload
systemctl enable business-hub
systemctl start business-hub

# Status prüfen
systemctl status business-hub
```

**Troubleshooting bei Fehlern:**
```bash
# Logs anzeigen
journalctl -u business-hub -f

# Manueller Test
sudo -u business-hub bash << 'EOF'
cd /opt/business-hub
source venv/bin/activate
gunicorn --bind 127.0.0.1:5000 --workers 2 'app:create_app()'
EOF
```

### 5.2 Nginx konfigurieren

```bash
# Nginx-Config kopieren
cp /opt/business-hub/deployment/nginx.conf /etc/nginx/sites-available/business-hub

# Domain anpassen
nano /etc/nginx/sites-available/business-hub
# Ersetze: ihre-domain.de → deine-echte-domain.de

# Oder für IP-basiertes Setup:
sed -i 's/ihre-domain.de/'"$(hostname -I | awk '{print $1}')"'/g' \
    /etc/nginx/sites-available/business-hub

# Symlink erstellen
ln -s /etc/nginx/sites-available/business-hub /etc/nginx/sites-enabled/

# Default-Site entfernen
rm /etc/nginx/sites-enabled/default

# Syntax-Check
nginx -t

# Nginx neu laden
systemctl reload nginx
```

### 5.3 Firewall-Regeln

```bash
# Bereits via vps_setup.sh gesetzt, aber zur Sicherheit:
ufw allow 80/tcp
ufw allow 443/tcp
ufw reload
ufw status
```

---

## Phase 6: DNS & SSL

### 6.1 DNS auf VPS umstellen

**Wichtig: Erst testen, dann DNS umstellen!**

```bash
# VPS-IP ermitteln
hostname -I | awk '{print $1}'

# Z.B.: 192.0.2.100
```

**DNS-Einträge ändern (bei deinem Domain-Provider):**
```
A-Record:
  Host: @ (oder deine-domain.de)
  Points to: 192.0.2.100
  TTL: 3600

A-Record:
  Host: www
  Points to: 192.0.2.100
  TTL: 3600
```

**DNS-Propagation prüfen:**
```bash
# Auf lokalem PC:
nslookup deine-domain.de
dig deine-domain.de

# Warten bis neue IP erscheint (kann 5-60 Minuten dauern)
```

### 6.2 SSL-Zertifikat installieren

```bash
# Auf VPS (erst NACH DNS-Umstellung!):
certbot --nginx -d deine-domain.de -d www.deine-domain.de

# Follow the prompts:
# - Email eingeben
# - Terms akzeptieren
# - HTTPS-Redirect: Ja

# Auto-Renewal testen
certbot renew --dry-run
```

**SSL ohne Domain (Self-Signed für Testing):**
```bash
# Falls keine Domain vorhanden:
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/selfsigned.key \
    -out /etc/ssl/certs/selfsigned.crt

# Nginx-Config anpassen für Self-Signed
```

---

## Phase 7: Testing & Verifikation

### 7.1 Funktionstests

```bash
# HTTP-Check
curl -I http://<vps-ip-oder-domain>/

# Health-Check
curl http://<vps-ip-oder-domain>/health | jq

# Login-Seite
curl -I http://<vps-ip-oder-domain>/login

# Slots-Tool
curl -I http://<vps-ip-oder-domain>/slots/

# T2-Tool
curl -I http://<vps-ip-oder-domain>/t2/
```

### 7.2 Browser-Tests

**Via Browser testen:**
1. ✅ Login funktioniert
2. ✅ Dashboard lädt
3. ✅ Terminbuchung funktioniert
4. ✅ Kalender-Integration aktiv
5. ✅ Gamification-Features laden
6. ✅ Admin-Bereich zugänglich
7. ✅ Feiertags-Sperrung aktiv

### 7.3 Monitoring einrichten

```bash
# Systemd Service überwachen
watch -n 2 'systemctl status business-hub'

# Logs in Echtzeit
tail -f /var/log/business-hub/access.log
tail -f /var/log/business-hub/error.log

# Ressourcen-Nutzung
htop
```

---

## Phase 8: Render.com deaktivieren

**Erst NACH erfolgreicher Migration und 24h Testbetrieb!**

### 8.1 Parallel-Betrieb (empfohlen)

```bash
# Beide Systeme parallel laufen lassen für 1-2 Wochen
# VPS ist aktiv, Render als Backup

# Nach Testphase:
# 1. GitHub Actions anpassen (auf VPS zeigen)
# 2. Render Service pausieren (nicht löschen!)
# 3. Nach 1 Monat: Render komplett löschen
```

### 8.2 Render Service stoppen

```bash
# Im Render Dashboard:
# Service > Settings > Suspend Service

# Daten-Backup von Render VORHER nochmal ziehen!
```

---

## 🆘 Troubleshooting

### Problem: Application startet nicht

```bash
# Logs prüfen
journalctl -u business-hub -n 100 --no-pager

# Häufige Probleme:
# 1. .env fehlt oder falsch
sudo -u business-hub cat /opt/business-hub/.env

# 2. Python Dependencies fehlen
sudo -u business-hub bash -c 'cd /opt/business-hub && source venv/bin/activate && pip list'

# 3. Permissions falsch
ls -la /opt/business-hub/
ls -la /opt/business-hub/data/

# Permissions korrigieren:
chown -R business-hub:www-data /opt/business-hub
chmod 755 /opt/business-hub
chmod 700 /opt/business-hub/data/persistent
```

### Problem: Nginx 502 Bad Gateway

```bash
# Application-Service prüfen
systemctl status business-hub

# Nginx-Logs
tail -f /var/log/nginx/business-hub-error.log

# Gunicorn läuft?
ps aux | grep gunicorn

# Port 5000 offen?
netstat -tlnp | grep 5000
```

### Problem: Google Calendar Integration fehlt

```bash
# GOOGLE_CREDS_BASE64 prüfen
sudo -u business-hub bash -c 'cd /opt/business-hub && source venv/bin/activate && python3 -c "
from app.core.google_calendar import GoogleCalendarService
service = GoogleCalendarService()
print(\"OK\" if service.is_configured() else \"FAIL\")
"'
```

### Problem: Daten fehlen

```bash
# Persistente Daten prüfen
ls -la /opt/business-hub/data/persistent/

# Falls leer: Bootstrap von static/
sudo -u business-hub bash -c 'cd /opt/business-hub && source venv/bin/activate && python3 -c "
from app.services.data_persistence import data_persistence
data_persistence.bootstrap_from_static_if_missing()
"'
```

---

## 📊 Performance-Optimierung (Post-Migration)

### Nach erfolgreicher Migration:

```bash
# 1. Gunicorn Workers erhöhen (falls genug RAM)
# In: /etc/systemd/system/business-hub.service
# Ändern: --workers 4 (von 2)

# 2. Nginx Caching aktivieren
# In: /etc/nginx/sites-available/business-hub
# Static-Files caching ist bereits aktiv

# 3. Database-Queries optimieren (falls nötig)
# Monitoring der JSON-File-Operations

# 4. Auto-Backups einrichten
crontab -e
# Add: 0 2 * * * /opt/business-hub/deployment/vps_backup.sh
```

---

## ✅ Migrations-Checkliste

- [ ] VPS bestellt und eingerichtet
- [ ] vps_setup.sh erfolgreich ausgeführt
- [ ] Daten von Render exportiert
- [ ] Repository auf VPS geklont
- [ ] .env Datei konfiguriert
- [ ] Daten auf VPS migriert
- [ ] Datenintegrität verifiziert
- [ ] Systemd Service läuft
- [ ] Nginx konfiguriert
- [ ] DNS umgestellt
- [ ] SSL-Zertifikat installiert
- [ ] Alle Funktionstests erfolgreich
- [ ] Monitoring aktiv
- [ ] 24h Testbetrieb erfolgreich
- [ ] Render Service deaktiviert

---

## 📞 Support

Bei Problemen:
1. **Logs prüfen:** `journalctl -u business-hub -f`
2. **Dokumentation:** Siehe `deployment/README.md`
3. **GitHub Issues:** https://github.com/yourusername/slot-booking-webapp/issues

---

**🎉 Glückwunsch zur erfolgreichen Migration!**