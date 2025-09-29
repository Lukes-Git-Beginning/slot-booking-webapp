# Business Tool Hub - Installation & Deployment Guide

## 📋 Systemanforderungen

### Hardware (Minimum)
- **CPU**: 2 Cores
- **RAM**: 2 GB (4 GB empfohlen)
- **Disk**: 10 GB freier Speicherplatz
- **Network**: Stabile Internetverbindung für Google Calendar API

### Software
- **OS**: Ubuntu 20.04 LTS oder höher (Debian-basiert empfohlen)
- **Python**: 3.9 oder höher
- **Nginx**: Aktuellste stabile Version
- **Git**: Für Code-Deployment

---

## 🚀 Installation Schritt für Schritt

### 1. System vorbereiten

```bash
# System aktualisieren
sudo apt update && sudo apt upgrade -y

# Python und Dependencies installieren
sudo apt install -y python3 python3-pip python3-venv nginx git

# Firewall konfigurieren
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Benutzer und Verzeichnisse erstellen

```bash
# Dedizierter Benutzer für die Anwendung (Sicherheit)
sudo useradd -m -s /bin/bash business-hub
sudo usermod -aG www-data business-hub

# Zum neuen Benutzer wechseln
sudo su - business-hub

# Application Directory erstellen
mkdir -p ~/business-hub
cd ~/business-hub
```

### 3. Code herunterladen

```bash
# Repository klonen
git clone https://github.com/Lukes-Git-Beginning/slot-booking-webapp.git .

# Oder: Code manuell hochladen (z.B. via SCP/SFTP)
# scp -r /pfad/zum/projekt business-hub@server-ip:~/business-hub/
```

### 4. Python Virtual Environment einrichten

```bash
# Virtual Environment erstellen
python3 -m venv venv

# Virtual Environment aktivieren
source venv/bin/activate

# Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Umgebungsvariablen konfigurieren

```bash
# .env Datei erstellen (siehe .env.example)
nano .env
```

**Erforderliche Variablen (siehe `.env.example` für Details):**
```bash
SECRET_KEY=<generierter-secret-key>
GOOGLE_CREDS_BASE64=<base64-kodierte-credentials>
CENTRAL_CALENDAR_ID=zentralkalenderzfa@gmail.com
USERLIST=user1:pass1,user2:pass2
ADMIN_USERS=admin1,admin2
FLASK_ENV=production
```

**Secret Key generieren:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 6. Google Calendar Service Account einrichten

```bash
# Service Account JSON hochladen
nano service_account.json
# (Inhalt einfügen und speichern)

# Base64-kodieren für Umgebungsvariable
base64 -w 0 service_account.json
# Output in .env als GOOGLE_CREDS_BASE64 eintragen
```

### 7. Datenverzeichnisse erstellen

```bash
# Persistente Datenverzeichnisse
mkdir -p data/persistent data/backups
chmod 755 data
chmod 700 data/persistent data/backups

# Static Directory für Legacy-Kompatibilität
mkdir -p static
chmod 755 static
```

### 8. Daten von Render.com migrieren (Optional)

```bash
# Migrations-Script ausführen
python3 deployment/migrate_from_render.py

# Oder: Daten manuell kopieren
# scp user@render-server:/pfad/zu/daten/* data/persistent/
```

### 9. Anwendung testen

```bash
# Test-Server starten
python3 run.py

# In neuem Terminal: Test-Request
curl http://localhost:5000/health
```

### 10. Systemd Service einrichten

```bash
# Zurück zu root-Benutzer
exit

# Service-Datei kopieren
sudo cp /home/business-hub/business-hub/deployment/business-hub.service /etc/systemd/system/

# Service aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable business-hub
sudo systemctl start business-hub

# Status prüfen
sudo systemctl status business-hub
```

### 11. Nginx Reverse Proxy konfigurieren

```bash
# Nginx-Konfiguration kopieren
sudo cp /home/business-hub/business-hub/deployment/nginx.conf /etc/nginx/sites-available/business-hub

# Symlink erstellen
sudo ln -s /etc/nginx/sites-available/business-hub /etc/nginx/sites-enabled/

# Default-Site deaktivieren (optional)
sudo rm /etc/nginx/sites-enabled/default

# Nginx-Konfiguration testen
sudo nginx -t

# Nginx neu laden
sudo systemctl restart nginx
```

### 12. SSL-Zertifikat einrichten (HTTPS)

```bash
# Certbot installieren
sudo apt install -y certbot python3-certbot-nginx

# SSL-Zertifikat anfordern (Domain anpassen!)
sudo certbot --nginx -d ihre-domain.de -d www.ihre-domain.de

# Auto-Renewal testen
sudo certbot renew --dry-run
```

---

## 🔧 Konfiguration anpassen

### Production Settings

**Datei**: `app/config/production.py`

Wichtige Einstellungen:
```python
DEBUG = False  # NIEMALS True in Production!
TESTING = False
SESSION_COOKIE_SECURE = True  # HTTPS erforderlich
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
```

### Logging konfigurieren

Logs befinden sich in:
- **Application**: `/var/log/business-hub/app.log`
- **Nginx Access**: `/var/log/nginx/access.log`
- **Nginx Error**: `/var/log/nginx/error.log`
- **Systemd**: `sudo journalctl -u business-hub -f`

### Backup-Strategie aktivieren

```bash
# Cron-Job für tägliche Backups
sudo crontab -e

# Folgende Zeile hinzufügen (täglich um 2 Uhr nachts)
0 2 * * * /home/business-hub/business-hub/deployment/backup.sh
```

---

## 📊 Monitoring & Wartung

### Health-Check Endpoint

```bash
# System-Status prüfen
curl http://localhost/health

# Erwartete Antwort:
# {"status": "healthy", "checks": {"database": true, "calendar": true, ...}}
```

### Service-Befehle

```bash
# Service neu starten
sudo systemctl restart business-hub

# Service stoppen
sudo systemctl stop business-hub

# Logs ansehen
sudo journalctl -u business-hub -f

# Nginx neu laden
sudo systemctl reload nginx
```

### Performance-Monitoring

```bash
# CPU & Memory Usage
htop

# Disk Usage
df -h

# Network Connections
ss -tulpn | grep :5000
```

---

## 🔒 Sicherheits-Checkliste

- [ ] SECRET_KEY ist stark und einzigartig (min. 32 Zeichen)
- [ ] DEBUG = False in Production
- [ ] Firewall (UFW) ist aktiviert
- [ ] SSH-Login nur mit Keys (Password-Auth deaktiviert)
- [ ] SSL-Zertifikat ist installiert und aktiv
- [ ] service_account.json hat Permissions 600
- [ ] Backup-System ist aktiv und getestet
- [ ] Regelmäßige Security-Updates eingerichtet
- [ ] Nginx Security-Headers konfiguriert
- [ ] Rate-Limiting für API-Endpoints aktiviert

---

## 🚨 Troubleshooting

### Problem: Service startet nicht

```bash
# Logs prüfen
sudo journalctl -u business-hub -n 50

# Permissions prüfen
ls -la /home/business-hub/business-hub/

# Virtual Environment prüfen
source /home/business-hub/business-hub/venv/bin/activate
python3 -c "import flask; print('OK')"
```

### Problem: Google Calendar API Fehler

```bash
# Service Account Credentials testen
python3 -c "from app.core.google_calendar import GoogleCalendarService; print('OK' if GoogleCalendarService().is_configured() else 'FAIL')"

# Permissions in Google Calendar prüfen
# - Service Account Email muss Kalender-Zugriff haben
# - Google Calendar API muss im Cloud-Projekt aktiviert sein
```

### Problem: 502 Bad Gateway (Nginx)

```bash
# Gunicorn-Service prüfen
sudo systemctl status business-hub

# Port-Binding prüfen
sudo netstat -tulpn | grep :5000

# Nginx-Error-Log prüfen
sudo tail -f /var/log/nginx/error.log
```

### Problem: Datenbank-Fehler

```bash
# Persistenz-Layer testen
python3 -c "from app.services.data_persistence import data_persistence; data_persistence.verify_integrity()"

# Permissions prüfen
ls -la data/persistent/

# Backup wiederherstellen
cp data/backups/latest/*.json data/persistent/
```

---

## 📞 Support & Weitere Hilfe

### Wichtige Dateien
- **Logs**: `/var/log/business-hub/`
- **Konfiguration**: `/home/business-hub/business-hub/.env`
- **Daten**: `/home/business-hub/business-hub/data/persistent/`
- **Backups**: `/home/business-hub/business-hub/data/backups/`

### Nützliche Kommandos
```bash
# Alle Services neu starten
sudo systemctl restart business-hub nginx

# Komplettes System neu starten
sudo reboot

# Backup manuell erstellen
python3 -c "from app.core.extensions import data_persistence; data_persistence.create_backup()"
```

### GitHub Issues
Bei Problemen: https://github.com/Lukes-Git-Beginning/slot-booking-webapp/issues

---

## ✅ Installation erfolgreich!

Nach erfolgreicher Installation sollte die Anwendung erreichbar sein unter:
- **HTTP**: `http://ihre-domain.de` (wird zu HTTPS weitergeleitet)
- **HTTPS**: `https://ihre-domain.de`
- **Health-Check**: `https://ihre-domain.de/health`

**Standard-Login verwenden** (in .env konfiguriert via USERLIST)

Viel Erfolg! 🚀