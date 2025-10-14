# Strato Quick Start Guide

## Domain-Migration für berater.zfa.gmbh (Subdomain bei Strato)

**Situation:**
- ✅ Server läuft: http://91.98.192.233
- 🏢 Domain bei Strato: zfa.gmbh
- 📍 Subdomain: berater.zfa.gmbh
- 🎯 Ziel: https://berater.zfa.gmbh mit SSL

---

## 📝 Schritt 1: DNS bei Strato konfigurieren

### In Strato einloggen

1. **Login:** https://www.strato.de/apps/CustomerService
2. **Domains** → **Domainverwaltung** → `zfa.gmbh` auswählen
3. **DNS-Einstellungen** oder **Subdomain verwalten**

### Subdomain erstellen

**A-Record für `berater`:**
```
Subdomain: berater
Typ: A-Record
Ziel/IP: 91.98.192.233
TTL: 3600 (Standard)
```

**Optional - WWW-Variante:**
```
Subdomain: www.berater
Typ: A-Record
Ziel/IP: 91.98.192.233
TTL: 3600
```

### Speichern & Warten

- Änderungen speichern
- **Wartezeit:** 1-4 Stunden (Strato ist schnell!)
- Bestätigungs-E-Mail abwarten (falls erforderlich)

---

## 🔍 Schritt 2: DNS-Propagation prüfen

**Nach 1-2 Stunden testen:**

```bash
# Von eurem PC aus
nslookup berater.zfa.gmbh 8.8.8.8

# Erwartetes Ergebnis:
# Name: berater.zfa.gmbh
# Address: 91.98.192.233
```

**Online-Tool (alternative):**
- https://dnschecker.org/
- Domain eingeben: `berater.zfa.gmbh`
- Sollte `91.98.192.233` weltweit anzeigen

---

## ⚙️ Schritt 3: .env.production ausfüllen

```bash
cd deployment
# Mit Editor öffnen (VS Code, Notepad++, etc.)
code .env.production
```

**Ausfüllen:**
```bash
# SECRET_KEY generieren (z.B. mit Python)
python -c "import secrets; print(secrets.token_hex(32))"

# Aus aktueller .env auf Server holen:
ssh -i ~/.ssh/server_key root@91.98.192.233 "cat /opt/business-hub/.env | grep USERLIST"
ssh -i ~/.ssh/server_key root@91.98.192.233 "cat /opt/business-hub/.env | grep GOOGLE_CREDS_BASE64"
ssh -i ~/.ssh/server_key root@91.98.192.233 "cat /opt/business-hub/.env | grep CENTRAL_CALENDAR_ID"
ssh -i ~/.ssh/server_key root@91.98.192.233 "cat /opt/business-hub/.env | grep CONSULTANTS"
```

**⚠️ WICHTIG:** `.env.production` NICHT committen!

---

## 🚀 Schritt 4: Migration ausführen

**Wenn DNS korrekt ist (nach 1-4h):**

```bash
cd deployment
chmod +x domain_migration.sh
bash domain_migration.sh
```

**Das Script führt automatisch aus:**
1. ✅ DNS-Check
2. ✅ Backup erstellen
3. ✅ SSL-Zertifikat beantragen (Let's Encrypt)
4. ✅ Nginx aktualisieren
5. ✅ .env hochladen
6. ✅ Services neu starten
7. ✅ HTTPS testen

**Dauer:** 5-10 Minuten

---

## ✅ Schritt 5: Verifizierung

### HTTPS testen

```bash
# Von eurem PC
curl -I https://berater.zfa.gmbh/health

# Sollte HTTP/2 200 zurückgeben
```

### Features testen

- Login: https://berater.zfa.gmbh/auth/login
- Slot-Booking: https://berater.zfa.gmbh/slots
- T2-System: https://berater.zfa.gmbh/t2
- Admin: https://berater.zfa.gmbh/admin

### SSL-Zertifikat prüfen

- Browser öffnen: https://berater.zfa.gmbh
- Schloss-Symbol klicken → Zertifikat anzeigen
- Sollte "Let's Encrypt" anzeigen, gültig 90 Tage

---

## 🆘 Troubleshooting

### DNS zeigt falsche IP

```bash
# Lokalen DNS-Cache leeren
ipconfig /flushdns  # Windows

# Nochmal warten (Strato braucht 1-4h)
# Dann erneut testen
nslookup berater.zfa.gmbh 8.8.8.8
```

### SSL-Zertifikat fehlgeschlagen

**Mögliche Ursachen:**
1. DNS noch nicht propagiert → Warten
2. Port 80/443 nicht offen → Firewall prüfen:
   ```bash
   ssh -i ~/.ssh/server_key root@91.98.192.233 "ufw status"
   ```
3. Let's Encrypt Rate-Limit → Warten (1h)

**Manuell erneut versuchen:**
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233
certbot certonly --nginx -d berater.zfa.gmbh -d www.berater.zfa.gmbh
systemctl reload nginx
```

### Service startet nicht

```bash
# Logs prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233
journalctl -u business-hub -n 50 --no-pager

# .env-Datei prüfen
cat /opt/business-hub/.env

# Manuell starten
systemctl restart business-hub
systemctl status business-hub
```

---

## 🔄 Rollback (falls nötig)

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233

# Backup wiederherstellen
cp /opt/business-hub/backups/domain-migration-$(date +%Y%m%d)/nginx.conf.backup \
   /etc/nginx/sites-available/business-hub

cp /opt/business-hub/backups/domain-migration-$(date +%Y%m%d)/.env.backup \
   /opt/business-hub/.env

# Services neu starten
systemctl reload nginx
systemctl restart business-hub

# Zurück zu IP-only
# App läuft wieder auf: http://91.98.192.233
```

---

## 📞 Wichtige Kommandos

### Logs überwachen

```bash
# Application Logs
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "tail -f /var/log/business-hub/error.log"

# Nginx Logs
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "tail -f /var/log/nginx/business-hub-error.log"

# Service Status
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "systemctl status business-hub"
```

### Emergency-Zugang

**Falls Domain nicht funktioniert:**
- Direkter IP-Zugang: http://91.98.192.233:8080
- Nur für Admins, keine HTTPS

---

## ✨ Nach erfolgreicher Migration

**Checklist:**
- [ ] HTTPS funktioniert: https://berater.zfa.gmbh ✅
- [ ] HTTP → HTTPS Redirect aktiv
- [ ] SSL-Zertifikat gültig (Let's Encrypt)
- [ ] Alle Features getestet
- [ ] Auto-Renewal verifiziert: `certbot renew --dry-run`
- [ ] Emergency-Zugang: http://91.98.192.233:8080

**Zertifikat erneuert sich automatisch!**
- Certbot-Timer prüfen: `systemctl status certbot.timer`
- Kein manueller Eingriff nötig

---

## 🎯 Zusammenfassung

```
1. DNS bei Strato: berater → 91.98.192.233
2. 1-4h warten
3. .env.production ausfüllen
4. bash domain_migration.sh
5. Testen: https://berater.zfa.gmbh
```

**Geschätzte Gesamtzeit:** 1.5 - 5 Stunden (inkl. Wartezeit)

---

**Viel Erfolg mit der Migration! 🚀**
