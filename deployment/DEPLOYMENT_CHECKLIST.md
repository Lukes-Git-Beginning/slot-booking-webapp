# Business Tool Hub - Deployment Checklist

## 📋 Pre-Deployment Checklist

### Server-Vorbereitung
- [ ] Ubuntu 20.04 LTS oder höher installiert
- [ ] Mindestens 2 GB RAM verfügbar
- [ ] Mindestens 10 GB freier Speicherplatz
- [ ] Stabile Internetverbindung
- [ ] SSH-Zugang konfiguriert
- [ ] Sudo-Rechte für Installations-User vorhanden

### Netzwerk-Konfiguration
- [ ] Statische IP-Adresse konfiguriert (optional)
- [ ] Firewall-Regeln vorbereitet (Port 80, 443)
- [ ] Domain/Subdomain vorhanden (optional, für SSL)
- [ ] DNS-Einträge konfiguriert (falls Domain vorhanden)

### Credentials & Konfiguration
- [ ] Google Service Account JSON-Datei vorhanden
- [ ] Zentrale Kalender-ID verfügbar
- [ ] Berater-Kalender-IDs dokumentiert
- [ ] T2-Closer-Kalender-IDs dokumentiert
- [ ] USERLIST mit Benutzern/Passwörtern vorbereitet
- [ ] Admin-Benutzer definiert

---

## 🚀 Installation Checklist

### 1. System-Vorbereitung
- [ ] System aktualisiert: `sudo apt update && sudo apt upgrade -y`
- [ ] Python 3.9+ installiert: `python3 --version`
- [ ] Nginx installiert: `nginx -v`
- [ ] Git installiert: `git --version`
- [ ] UFW Firewall konfiguriert

### 2. Benutzer & Verzeichnisse
- [ ] Application-User erstellt: `business-hub`
- [ ] Home-Verzeichnis erstellt: `/home/business-hub/business-hub`
- [ ] Richtige Permissions gesetzt (755 für Verzeichnisse)

### 3. Code-Deployment
- [ ] Repository geklont: `git clone <repo-url>`
- [ ] Virtual Environment erstellt: `python3 -m venv venv`
- [ ] Dependencies installiert: `pip install -r requirements.txt`

### 4. Konfiguration
- [ ] `.env` Datei erstellt (von `.env.example`)
- [ ] SECRET_KEY generiert und eingetragen
- [ ] GOOGLE_CREDS_BASE64 eingetragen
- [ ] CENTRAL_CALENDAR_ID eingetragen
- [ ] CONSULTANTS konfiguriert
- [ ] T2_CLOSERS konfiguriert
- [ ] USERLIST mit Benutzern gefüllt
- [ ] ADMIN_USERS definiert

### 5. Google Calendar Setup
- [ ] Service Account JSON hochgeladen
- [ ] Service Account in Google Calendar freigegeben
- [ ] Google Calendar API aktiviert
- [ ] Kalender-Zugriff getestet

### 6. Datenverzeichnisse
- [ ] `data/persistent` erstellt
- [ ] `data/backups` erstellt
- [ ] Richtige Permissions (700 für data/persistent)
- [ ] Test-Schreibzugriff verifiziert

### 7. Systemd Service
- [ ] Service-Datei kopiert: `/etc/systemd/system/business-hub.service`
- [ ] Service-Datei editiert (Pfade angepasst)
- [ ] Daemon reloaded: `sudo systemctl daemon-reload`
- [ ] Service aktiviert: `sudo systemctl enable business-hub`
- [ ] Service gestartet: `sudo systemctl start business-hub`
- [ ] Service-Status geprüft: `sudo systemctl status business-hub`

### 8. Nginx-Konfiguration
- [ ] Nginx-Config kopiert: `/etc/nginx/sites-available/business-hub`
- [ ] Domain/IP in Config angepasst
- [ ] Symlink erstellt: `/etc/nginx/sites-enabled/business-hub`
- [ ] Nginx-Config getestet: `sudo nginx -t`
- [ ] Nginx neu gestartet: `sudo systemctl restart nginx`

### 9. SSL-Zertifikat (Optional)
- [ ] Certbot installiert: `sudo apt install certbot python3-certbot-nginx`
- [ ] SSL-Zertifikat angefordert: `sudo certbot --nginx -d domain.de`
- [ ] Auto-Renewal getestet: `sudo certbot renew --dry-run`

---

## ✅ Post-Deployment Checklist

### Functional Tests
- [ ] Anwendung erreichbar: `curl http://localhost/`
- [ ] Health-Check funktioniert: `curl http://localhost/health`
- [ ] Login-Seite lädt: `curl http://localhost/login`
- [ ] Hub-Dashboard erreichbar: `http://localhost/hub`
- [ ] Slot-Booking Tool #1 erreichbar: `http://localhost/slots`
- [ ] T2-Closer Tool #2 erreichbar: `http://localhost/t2`

### Integration Tests
- [ ] Login mit Test-User erfolgreich
- [ ] Google Calendar API-Verbindung funktioniert
- [ ] Verfügbarkeit wird korrekt geladen
- [ ] Buchung kann erstellt werden (Test)
- [ ] Gamification-System funktioniert
- [ ] Admin-Dashboard erreichbar (für Admin-User)

### Performance Tests
- [ ] Seitenladezeit < 2 Sekunden
- [ ] API-Response-Zeit < 500ms
- [ ] Keine Memory-Leaks erkennbar
- [ ] CPU-Auslastung im Normalbereich (<50%)

### Security Tests
- [ ] HTTPS-Redirect funktioniert (falls SSL aktiv)
- [ ] Session-Cookies sind secure
- [ ] Keine sensiblen Daten in Logs
- [ ] Firewall-Regeln aktiv
- [ ] SSH-Zugang gesichert (Key-based)

### Monitoring Setup
- [ ] Health-Check Endpoint getestet: `/health`
- [ ] Metrics Endpoint getestet: `/health/metrics`
- [ ] Log-Dateien werden geschrieben: `/var/log/business-hub/`
- [ ] Backup-Script funktioniert: `./deployment/backup.sh`
- [ ] Backup-Cron-Job eingerichtet

---

## 🔄 Data Migration Checklist (von Render.com)

### Vorbereitung
- [ ] Render.com-Daten exportiert
- [ ] Migrations-Script vorbereitet: `migrate_from_render.py`
- [ ] Ziel-Verzeichnis existiert: `data/persistent/`

### Migration ausführen
- [ ] Dry-Run durchgeführt: `python migrate_from_render.py --dry-run`
- [ ] Keine Fehler im Dry-Run
- [ ] Tatsächliche Migration: `python migrate_from_render.py --source <path> --target <path>`
- [ ] Alle kritischen Dateien migriert
- [ ] JSON-Integrität verifiziert

### Post-Migration
- [ ] Anwendung mit migrierten Daten neugestartet
- [ ] Benutzer-Daten vorhanden
- [ ] Buchungs-Historie vorhanden
- [ ] Gamification-Daten intakt
- [ ] Keine Datenverluste

---

## 📊 Go-Live Checklist

### Final Checks
- [ ] Alle Services laufen: `systemctl status business-hub nginx`
- [ ] Keine Fehler in Logs: `journalctl -u business-hub -n 50`
- [ ] Backup-System aktiv und getestet
- [ ] Monitoring funktioniert
- [ ] SSL-Zertifikat gültig (falls vorhanden)

### Communication
- [ ] Benutzer über neue Server-Adresse informiert
- [ ] Dokumentation aktualisiert
- [ ] Support-Kontakt dokumentiert
- [ ] Notfall-Prozeduren dokumentiert

### Rollback Plan
- [ ] Alter Server noch verfügbar (für 7 Tage)
- [ ] DNS-Wechsel rückgängig machbar
- [ ] Backup der alten Daten vorhanden
- [ ] Rollback-Anleitung dokumentiert

---

## 🛠️ Maintenance Checklist

### Tägliche Checks (5 Min)
- [ ] Service-Status prüfen: `systemctl status business-hub`
- [ ] Festplattenspeicher prüfen: `df -h`
- [ ] Kurzer Funktionstest (Login, Dashboard)

### Wöchentliche Checks (15 Min)
- [ ] Logs prüfen: `journalctl -u business-hub -n 100`
- [ ] Backup-Größe prüfen: `du -sh data/backups/`
- [ ] Performance-Metriken prüfen: `/health/metrics`
- [ ] Alte Backups bereinigt (automatisch)

### Monatliche Checks (30 Min)
- [ ] System-Updates: `sudo apt update && sudo apt upgrade`
- [ ] SSL-Zertifikat-Ablauf prüfen (falls vorhanden)
- [ ] Security-Updates installiert
- [ ] Backup-Restore-Test durchgeführt

### Vierteljährliche Checks (2 Stunden)
- [ ] Vollständige Security-Audit
- [ ] Performance-Optimierung
- [ ] Code-Updates vom Repository
- [ ] Umfassende Backup-Verifikation

---

## 🚨 Troubleshooting Quick Reference

### Service startet nicht
```bash
# Logs prüfen
sudo journalctl -u business-hub -n 50

# Permissions prüfen
ls -la /home/business-hub/business-hub/

# Virtual Environment prüfen
source venv/bin/activate
python -c "import flask; print('OK')"
```

### 502 Bad Gateway
```bash
# Gunicorn-Status prüfen
sudo systemctl status business-hub

# Port-Binding prüfen
sudo netstat -tulpn | grep :5000

# Nginx-Logs prüfen
sudo tail -f /var/log/nginx/error.log
```

### Google Calendar API Fehler
```bash
# Service Account testen
python -c "from app.core.google_calendar import GoogleCalendarService; print('OK' if GoogleCalendarService().is_configured() else 'FAIL')"
```

### Daten-Fehler
```bash
# Persistenz-Layer testen
python -c "from app.services.data_persistence import data_persistence; data_persistence.verify_integrity()"

# Backup wiederherstellen
cp data/backups/latest/*.json data/persistent/
sudo systemctl restart business-hub
```

---

## ✅ Sign-Off

### Deployment abgeschlossen von:
- **Name:** _______________________
- **Datum:** _______________________
- **Signatur:** _______________________

### Verifiziert von:
- **Name:** _______________________
- **Datum:** _______________________
- **Signatur:** _______________________

### Notizen:
```
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
```

---

**🎉 Deployment erfolgreich abgeschlossen!**

Production URL: ______________________________________________

Health Check: ______________________________________________/health

Admin Dashboard: ______________________________________________/admin