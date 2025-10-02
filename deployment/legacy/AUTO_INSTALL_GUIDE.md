# Business Tool Hub - Automatische Installation

## 🚀 Die einfachste Art, den Hub zu installieren!

---

## 📋 Was du brauchst (Voraussetzungen)

### Hardware/Server
- ✅ Frischer Ubuntu 20.04 LTS oder höher Server
- ✅ Mindestens 2 GB RAM
- ✅ Mindestens 10 GB freier Speicherplatz
- ✅ Internet-Verbindung

### Credentials (zum Nachtragen)
- ✅ Google Service Account JSON-Datei
- ✅ Google Calendar IDs (Zentral, Berater, T2-Closer)
- ✅ Benutzer-Zugangsdaten (Username:Password)

### Zugang
- ✅ SSH-Zugang zum Server
- ✅ Sudo-Rechte für deinen Benutzer

---

## ⚡ Express-Installation (1 Command)

### Methode 1: Direct Download & Execute (EMPFOHLEN)

```bash
# Falls noch nicht im Repo:
curl -fsSL https://raw.githubusercontent.com/Lukes-Git-Beginning/slot-booking-webapp/main/deployment/auto_install.sh | bash
```

### Methode 2: Git Clone & Execute

```bash
# Repository klonen
git clone https://github.com/Lukes-Git-Beginning/slot-booking-webapp.git
cd slot-booking-webapp

# Script ausführbar machen
chmod +x deployment/auto_install.sh

# Installation starten
./deployment/auto_install.sh
```

### Methode 3: Lokaler Upload (falls kein Git-Zugang)

```bash
# Auf deinem PC: Script zum Server hochladen
scp deployment/auto_install.sh user@server-ip:~/

# Auf dem Server: Ausführen
ssh user@server-ip
bash ~/auto_install.sh
```

---

## 📺 Was passiert während der Installation?

Das Script führt automatisch folgende Schritte aus:

### Phase 1: System-Updates (2-3 Min)
```
✓ Paket-Listen aktualisieren
✓ System-Updates installieren
✓ Basis-Pakete installieren (Python, Nginx, Git, etc.)
```

### Phase 2: Firewall (30 Sek)
```
✓ UFW Firewall konfigurieren
✓ Ports 22 (SSH), 80 (HTTP), 443 (HTTPS) öffnen
✓ Firewall aktivieren
```

### Phase 3: Benutzer & Verzeichnisse (30 Sek)
```
✓ Application-User erstellen
✓ Log-Verzeichnisse erstellen
✓ Permissions setzen
```

### Phase 4: Code-Deployment (1 Min)
```
✓ Git Repository klonen
✓ Code in Installations-Verzeichnis kopieren
```

### Phase 5: Python-Umgebung (2-3 Min)
```
✓ Virtual Environment erstellen
✓ pip aktualisieren
✓ Alle Dependencies installieren (50+ Pakete)
```

### Phase 6: Konfiguration (30 Sek)
```
✓ .env Datei aus Template erstellen
✓ SECRET_KEY automatisch generieren
✓ Datenverzeichnisse erstellen
```

### Phase 7: Systemd Service (30 Sek)
```
✓ Service-Datei kopieren und anpassen
✓ Service aktivieren (Auto-Start bei Reboot)
```

### Phase 8: Nginx (1 Min)
```
✓ Nginx-Konfiguration kopieren
✓ Reverse-Proxy einrichten
✓ Nginx neu starten
```

### Phase 9: Backup-System (30 Sek)
```
✓ Backup-Script konfigurieren
✓ Cron-Job für tägliche Backups einrichten
```

### Phase 10: Permissions (30 Sek)
```
✓ Ownership setzen
✓ File-Permissions korrigieren
```

**GESAMT-DAUER: 8-12 Minuten** ⏱️

---

## ✅ Nach der Installation

### Schritt 1: .env Konfigurieren (WICHTIG!)

```bash
# .env Datei öffnen
nano ~/business-hub/.env
```

**Pflichtfelder ausfüllen:**

```bash
# Secret Key (bereits generiert ✓)
SECRET_KEY=<automatisch-generiert>

# Google Calendar API
GOOGLE_CREDS_BASE64=<base64-encoded-service-account-json>
CENTRAL_CALENDAR_ID=zentralkalenderzfa@gmail.com

# Berater für Slot-Booking Tool
CONSULTANTS=Lukas:lukas@gmail.com,Daniel:daniel@gmail.com

# T2-Closer für T2-Tool
T2_CLOSERS=Adem:adem@gmail.com,Okan:okan@gmail.com

# Benutzer-Accounts
USERLIST=admin:secure-password,user1:password1

# Admin-Benutzer
ADMIN_USERS=admin
```

**Speichern:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Schritt 2: Google Service Account Base64-Kodieren

```bash
# service_account.json hochladen zum Server
scp service_account.json user@server:~/

# Auf dem Server: Base64-kodieren
base64 -w 0 ~/service_account.json

# Output kopieren und in .env eintragen als GOOGLE_CREDS_BASE64
```

### Schritt 3: Anwendung Starten

```bash
# Service starten
sudo systemctl start business-hub

# Status prüfen
sudo systemctl status business-hub

# Sollte "active (running)" anzeigen ✓
```

### Schritt 4: Testen

```bash
# Basis-Test
curl http://localhost/

# Health-Check
curl http://localhost/health

# Sollte JSON mit {"status": "healthy"} zurückgeben
```

### Schritt 5: Im Browser öffnen

```
http://server-ip/
```

**Login mit Zugangsdaten aus USERLIST** 🎉

---

## 🔒 Optional: SSL-Zertifikat (HTTPS)

Wenn du eine Domain hast:

```bash
# SSL-Zertifikat mit Let's Encrypt
sudo certbot --nginx -d deine-domain.de -d www.deine-domain.de

# Auto-Renewal testen
sudo certbot renew --dry-run
```

Nach SSL-Einrichtung ist die Anwendung erreichbar unter:
```
https://deine-domain.de
```

---

## 🛠️ Wichtige Kommandos

### Service-Management
```bash
# Service starten
sudo systemctl start business-hub

# Service stoppen
sudo systemctl stop business-hub

# Service neu starten
sudo systemctl restart business-hub

# Service-Status prüfen
sudo systemctl status business-hub

# Logs ansehen
sudo journalctl -u business-hub -f
```

### Nginx-Management
```bash
# Nginx neu starten
sudo systemctl restart nginx

# Nginx-Status
sudo systemctl status nginx

# Nginx-Config testen
sudo nginx -t

# Error-Logs
sudo tail -f /var/log/nginx/error.log
```

### Backup
```bash
# Manuelles Backup
~/business-hub/deployment/backup.sh

# Backup-Liste
~/business-hub/deployment/backup.sh list

# Backup wiederherstellen
~/business-hub/deployment/backup.sh restore backup_YYYYMMDD_HHMMSS.tar.gz
```

---

## 🚨 Troubleshooting

### Problem: Service startet nicht

```bash
# 1. Logs prüfen
sudo journalctl -u business-hub -n 50

# 2. Häufigste Ursachen:
#    - .env nicht konfiguriert
#    - GOOGLE_CREDS_BASE64 falsch
#    - Python-Dependencies fehlen

# 3. Dependencies neu installieren
cd ~/business-hub
source venv/bin/activate
pip install -r requirements.txt

# 4. Service neu starten
sudo systemctl restart business-hub
```

### Problem: 502 Bad Gateway

```bash
# 1. Gunicorn läuft nicht
sudo systemctl status business-hub

# 2. Falls nicht running, starten:
sudo systemctl start business-hub

# 3. Port-Check
sudo netstat -tulpn | grep :5000
# Sollte gunicorn zeigen
```

### Problem: Google Calendar API Fehler

```bash
# 1. Test ob Service Account konfiguriert ist
cd ~/business-hub
source venv/bin/activate
python3 -c "from app.core.google_calendar import GoogleCalendarService; print('OK' if GoogleCalendarService().is_configured() else 'FAIL')"

# 2. Falls FAIL:
#    - GOOGLE_CREDS_BASE64 in .env prüfen
#    - Base64-Encoding korrekt?
#    - Service Account in Google Calendar freigegeben?
```

### Problem: Permissions

```bash
# Permissions zurücksetzen
cd ~/business-hub
sudo chown -R $USER:www-data .
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
chmod +x deployment/*.sh
chmod 600 .env
```

---

## 📊 Installation-Übersicht

| Phase | Dauer | Was passiert |
|-------|-------|--------------|
| 1. System-Updates | 2-3 Min | Pakete aktualisieren |
| 2. Firewall | 30 Sek | UFW konfigurieren |
| 3. Benutzer/Dirs | 30 Sek | Verzeichnisse erstellen |
| 4. Code-Deployment | 1 Min | Git-Repository klonen |
| 5. Python-Env | 2-3 Min | Dependencies installieren |
| 6. Konfiguration | 30 Sek | .env erstellen |
| 7. Systemd | 30 Sek | Service einrichten |
| 8. Nginx | 1 Min | Reverse-Proxy |
| 9. Backup | 30 Sek | Cron-Job einrichten |
| 10. Permissions | 30 Sek | Rechte setzen |
| **GESAMT** | **8-12 Min** | Vollautomatisch |

---

## ✅ Installations-Checkliste

### Vor der Installation
- [ ] Ubuntu-Server bereit
- [ ] Internet-Verbindung vorhanden
- [ ] SSH-Zugang funktioniert
- [ ] Sudo-Rechte verfügbar

### Während der Installation
- [ ] Script ausgeführt: `./auto_install.sh`
- [ ] Keine Fehler aufgetreten
- [ ] Alle 10 Phasen abgeschlossen

### Nach der Installation
- [ ] .env Datei konfiguriert
- [ ] GOOGLE_CREDS_BASE64 eingetragen
- [ ] USERLIST ausgefüllt
- [ ] Service gestartet: `sudo systemctl start business-hub`
- [ ] Health-Check OK: `curl localhost/health`
- [ ] Im Browser getestet
- [ ] Login funktioniert

### Optional
- [ ] SSL-Zertifikat eingerichtet
- [ ] Domain konfiguriert
- [ ] Backup getestet

---

## 🎯 Nächste Schritte nach erfolgreicher Installation

### Für Admin
1. **Benutzer anlegen** - Weitere User in USERLIST hinzufügen
2. **Kalender prüfen** - Google Calendar-Integration testen
3. **Backup-Strategie** - Ersten Backup-Test durchführen

### Für Entwickler
4. **Code anpassen** - Weitere Features entwickeln
5. **Updates deployen** - Git pull + Service restart
6. **Monitoring einrichten** - Health-Checks automatisieren

---

## 💡 Pro-Tipps

### Schneller Updates deployen
```bash
cd ~/business-hub
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart business-hub
```

### Performance-Monitoring
```bash
# System-Ressourcen
htop

# Anwendungs-Metriken
curl http://localhost/health/metrics | jq
```

### Logs in Echtzeit verfolgen
```bash
# Application-Logs
sudo journalctl -u business-hub -f

# Nginx-Logs
sudo tail -f /var/log/nginx/access.log
```

---

## 📞 Support

Bei Problemen:

1. **Logs prüfen:** `sudo journalctl -u business-hub -n 50`
2. **Health-Check:** `curl localhost/health`
3. **Installation-Log:** `cat /tmp/business-hub-install.log`

**Alles funktioniert? Perfekt! 🎉**

---

**Geschätzte Gesamt-Zeit von 0 zu Production: 15-20 Minuten** ⚡