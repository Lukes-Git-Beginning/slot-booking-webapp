# Business Tool Hub - Domain Migration

## Production-Deployment mit Domain: berater.zfa.gmbh

---

## 🎯 Übersicht

Dieses Verzeichnis enthält alle notwendigen Scripts und Dokumentation für die Domain-Migration der Business Hub Plattform von IP-only zu **berater.zfa.gmbh** mit SSL/TLS.

**Aktueller Status:**
- ✅ Testserver läuft: http://91.98.192.233
- 🔄 Domain-Migration: In Vorbereitung
- 🎯 Ziel-Domain: https://berater.zfa.gmbh

**Zeitaufwand:** 1-2 Stunden (+ 24h DNS-Propagation)
**Schwierigkeit:** Mittel
**Kosten:** Keine (Let's Encrypt SSL kostenlos)

---

## 📦 Deployment-Dateien

### 🚀 Domain-Migration (NEU)
```
deployment/
├── README.md                       # Diese Datei - Deployment-Übersicht
├── DNS_SETUP.md                    # DNS-Konfiguration für berater.zfa.gmbh
├── domain_migration.sh             # Automatisches Migrations-Script
├── nginx_production.conf           # Nginx mit SSL für berater.zfa.gmbh
└── .env.production                 # Production-Umgebungsvariablen Template
```

### 🔧 VPS-Setup (Bereits deployed)
```
deployment/
├── vps_setup.sh                    # VPS Basis-Setup (Nginx, Python, Firewall)
├── auto_install.sh                 # Vollautomatische Installation
├── vps_backup.sh                   # Automatisches Backup-System
├── migrate_from_render.py          # Datenmigration von Render.com
└── business-hub.service            # Systemd Service-Datei
```

### 📋 Legacy-Dokumentation
```
deployment/
├── SERVER_COMPARISON.md            # Hetzner vs. Strato Vergleich
├── VPS_MIGRATION_GUIDE.md          # Schritt-für-Schritt Migration
├── VPS_DEPLOYMENT_CHECKLIST.md     # Setup-Checkliste
└── legacy/                         # Archiv: Alte Home-Server-Dateien
```

---

## 🚀 Domain-Migration zu berater.zfa.gmbh

### Phase 1: DNS-Konfiguration (JETZT)

```bash
# 1. DNS-Einträge erstellen (bei eurem Domain-Provider)
berater.zfa.gmbh     → A-Record → 91.98.192.233
www.berater.zfa.gmbh → A-Record → 91.98.192.233
berater.zfa.gmbh     → CAA     → letsencrypt.org
```

📖 **Detaillierte Anleitung:** [DNS_SETUP.md](DNS_SETUP.md)

### Phase 2: Vorbereitung (HEUTE)

```bash
# 1. .env.production ausfüllen
cd deployment
nano .env.production
# SECRET_KEY, USERLIST, GOOGLE_CREDS, etc. eintragen
# WICHTIG: Datei NICHT committen!

# 2. DNS-Propagation prüfen
nslookup berater.zfa.gmbh 8.8.8.8
# Sollte 91.98.192.233 zurückgeben

# 3. Script ausführbar machen
chmod +x domain_migration.sh
```

### Phase 3: Migration (NACH 24H DNS-PROPAGATION)

```bash
# Von lokalem PC aus
cd deployment
bash domain_migration.sh
```

**Das Script führt automatisch aus:**
- ✅ DNS-Check
- ✅ Backup erstellen
- ✅ Certbot installieren (falls nötig)
- ✅ SSL-Zertifikat beantragen (Let's Encrypt)
- ✅ Nginx-Config aktualisieren
- ✅ .env-Datei hochladen
- ✅ Services neu starten
- ✅ HTTPS-Test durchführen

**Fertig!** Die Anwendung läuft auf `https://berater.zfa.gmbh`

---

## 📋 Migrations-Checkliste

- [ ] DNS A-Records konfiguriert
- [ ] DNS CAA-Record konfiguriert
- [ ] 24h auf DNS-Propagation gewartet
- [ ] `deployment/.env.production` ausgefüllt
- [ ] `domain_migration.sh` ausgeführt
- [ ] HTTPS funktioniert: https://berater.zfa.gmbh
- [ ] Alle Features getestet
- [ ] Auto-Renewal verifiziert

---

## 🔧 Legacy: VPS-Setup (bereits erledigt)

<details>
<summary>Für Neu-Installation auf anderem Server</summary>

### Vollautomatische Installation

```bash
# 1. VPS bestellen (z.B. Hetzner CX22)
# 2. SSH einloggen
ssh root@<deine-vps-ip>

# 3. Auto-Install-Script ausführen
wget https://raw.githubusercontent.com/yourusername/slot-booking-webapp/main/deployment/auto_install.sh
bash auto_install.sh

# 4. .env Datei konfigurieren
nano /opt/business-hub/.env

# 5. Service starten
systemctl start business-hub
systemctl status business-hub
```

### Manuelle Installation

👉 **[VPS_MIGRATION_GUIDE.md](VPS_MIGRATION_GUIDE.md)** - Vollständiger Migrations-Guide
👉 **[VPS_DEPLOYMENT_CHECKLIST.md](VPS_DEPLOYMENT_CHECKLIST.md)** - Alle Schritte zum Abhaken

</details>

---

## 🏆 Server-Empfehlung

**Empfohlene Konfiguration:** Hetzner Cloud CX22

| Provider | Modell | RAM | CPU | SSD | Preis/Monat |
|----------|--------|-----|-----|-----|-------------|
| **Hetzner** ⭐ | CX22 | 4 GB | 2 vCPU | 40 GB NVMe | 6,94 € |
| Strato | V500 V7 | 4 GB | 2 vCPU | 80 GB SATA | 11,90 € |

**Warum Hetzner?**
- ✅ Günstigster Preis bei bester Performance
- ✅ NVMe SSD (4-6x schneller als SATA)
- ✅ Deutsche Rechenzentren (Falkenstein/Nürnberg)
- ✅ Exzellente API & Tooling
- ✅ Einfaches Scaling

👉 **Detaillierter Vergleich:** [SERVER_COMPARISON.md](SERVER_COMPARISON.md)

---

## 📋 Migrations-Checkliste

Migriert ihr von **Render.com**? Hier die Quick-Checklist:

- [ ] VPS bestellt (Hetzner CX22 empfohlen)
- [ ] `vps_setup.sh` ausgeführt
- [ ] Daten von Render exportiert (via Git oder manuell)
- [ ] Repository auf VPS geklont
- [ ] `.env` Datei konfiguriert
- [ ] Daten auf VPS hochgeladen
- [ ] Systemd Service läuft
- [ ] Nginx konfiguriert
- [ ] DNS umgestellt (falls Domain)
- [ ] SSL-Zertifikat installiert
- [ ] Alle Tests erfolgreich
- [ ] Render Service deaktiviert (nach Testphase)

👉 **Vollständige Anleitung:** [VPS_MIGRATION_GUIDE.md](VPS_MIGRATION_GUIDE.md)

---

## 🔧 Deployment-Architektur

```
┌─────────────────────────────────────────┐
│         Internet / User                  │
└────────────────┬────────────────────────┘
                 │
         ┌───────▼───────┐
         │   Nginx :80   │  ← Reverse Proxy + SSL
         │   Nginx :443  │     (Let's Encrypt)
         └───────┬───────┘
                 │
    ┌────────────▼───────────────┐
    │  Gunicorn :5000            │  ← Flask App
    │  Workers: 2-4              │     (systemd managed)
    └────────────┬───────────────┘
                 │
    ┌────────────▼───────────────┐
    │  Business Tool Hub         │  ← Python Application
    │  - Slot-Booking            │
    │  - T2-Closer               │
    │  - Gamification            │
    │  - Analytics               │
    └────────────┬───────────────┘
                 │
    ┌────────────▼───────────────┐
    │  Data Layer                │
    │  /opt/business-hub/data/   │  ← JSON-basiert
    │  - persistent/             │     Auto-Backups
    │  - backups/                │
    └────────────────────────────┘
```

---

## 🛠️ Wichtige Kommandos

### Service Management
```bash
# Status prüfen
systemctl status business-hub

# Service neu starten
systemctl restart business-hub

# Logs anzeigen
journalctl -u business-hub -f

# Service aktivieren (Auto-Start)
systemctl enable business-hub
```

### Nginx
```bash
# Config testen
nginx -t

# Nginx neu laden
systemctl reload nginx

# Logs anzeigen
tail -f /var/log/nginx/business-hub-access.log
tail -f /var/log/nginx/business-hub-error.log
```

### Backups
```bash
# Backup erstellen
/usr/local/bin/vps_backup.sh data

# Alle Backups anzeigen
ls -lh /opt/business-hub/backups/

# Backup wiederherstellen
tar -xzf business-hub_data_20240101_120000.tar.gz
# Dann Dateien nach /opt/business-hub/data/persistent/ kopieren
```

### Monitoring
```bash
# Ressourcen überwachen
htop

# Disk-Space prüfen
df -h

# Application-Health
curl http://localhost:5000/health
```

---

## 🔒 Sicherheit

### Automatisch konfiguriert (via vps_setup.sh):
- ✅ UFW Firewall (Port 22, 80, 443)
- ✅ Nginx Security Headers
- ✅ SSL/TLS (Let's Encrypt)
- ✅ Non-root Application User
- ✅ Automatische Security-Updates

### Empfohlene zusätzliche Maßnahmen:
```bash
# SSH-Key-Only (Password-Auth deaktivieren)
nano /etc/ssh/sshd_config
# PasswordAuthentication no
systemctl restart sshd

# Fail2Ban installieren (Brute-Force-Schutz)
apt-get install fail2ban -y
systemctl enable fail2ban

# SSH-Port ändern (optional)
nano /etc/ssh/sshd_config
# Port 2222
```

---

## 📊 Performance-Erwartungen

### Hetzner CX22 (4 GB RAM):
```
Concurrent Users:    100-200
Response Time:       100-300ms (avg)
RAM Usage:           1.5-2.5 GB
CPU Load:            0.2-0.8 (idle-normal)
Uptime:              99.9%+
```

### Skalierung:
- **Start:** CX22 (4GB) - 6,94 €/Monat
- **Wachstum:** CX32 (8GB) - 13,88 €/Monat
- **Scale-out:** Load Balancer + 2x CX22

---

## 🆘 Troubleshooting

### Application startet nicht
```bash
# Logs prüfen
journalctl -u business-hub -n 100 --no-pager

# Häufige Ursachen:
# 1. .env fehlt oder falsch
cat /opt/business-hub/.env

# 2. Python Dependencies fehlen
cd /opt/business-hub
source venv/bin/activate
pip list

# 3. Permissions falsch
chown -R business-hub:www-data /opt/business-hub
```

### Nginx 502 Bad Gateway
```bash
# Gunicorn läuft?
systemctl status business-hub
netstat -tlnp | grep 5000

# Gunicorn-Logs
journalctl -u business-hub -f
```

### Google Calendar Integration fehlt
```bash
# Credentials prüfen
cd /opt/business-hub
source venv/bin/activate
python3 -c "from app.core.google_calendar import GoogleCalendarService; print('OK' if GoogleCalendarService().is_configured() else 'FAIL')"
```

👉 **Mehr Troubleshooting:** [VPS_MIGRATION_GUIDE.md#troubleshooting](VPS_MIGRATION_GUIDE.md#troubleshooting)

---

## 📞 Support & Weiterführende Docs

### Dokumentation
- **Server-Vergleich:** [SERVER_COMPARISON.md](SERVER_COMPARISON.md)
- **Migrations-Guide:** [VPS_MIGRATION_GUIDE.md](VPS_MIGRATION_GUIDE.md)
- **Deployment-Checklist:** [VPS_DEPLOYMENT_CHECKLIST.md](VPS_DEPLOYMENT_CHECKLIST.md)
- **Main Documentation:** [../CLAUDE.md](../CLAUDE.md)

### Links
- **Hetzner Cloud:** https://www.hetzner.com/cloud
- **Hetzner Docs:** https://docs.hetzner.com
- **Let's Encrypt:** https://letsencrypt.org
- **GitHub Issues:** https://github.com/yourusername/slot-booking-webapp/issues

---

## 🎉 Nach erfolgreichem Deployment

**Glückwunsch!** Dein Business Tool Hub läuft jetzt auf einem professionellen VPS.

**Nächste Schritte:**
1. ✅ **Monitoring einrichten** - Uptime-Checks, Alerts
2. ✅ **Backups verifizieren** - Restore-Test durchführen
3. ✅ **Performance optimieren** - Workers anpassen falls nötig
4. ✅ **Team informieren** - Neue URLs & Zugänge kommunizieren
5. ✅ **Render deaktivieren** - Nach erfolgreicher Testphase

**Viel Erfolg mit dem Business Tool Hub auf VPS! 🚀**