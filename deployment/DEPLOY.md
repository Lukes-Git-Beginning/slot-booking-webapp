# Deployment Guide - Business Tool Hub VPS

## Quick Deploy

```bash
cd deployment
bash deploy.sh
```

Das Script führt automatisch aus:
1. Backup auf VPS erstellen
2. Geänderte Dateien hochladen
3. Service neu starten
4. Status prüfen

---

## SSH-Zugang Setup

### Problem: SSH-Key funktioniert nicht

**Symptom:** `Permission denied (publickey,password)`

**Ursache:**
- Windows `chmod` funktioniert nicht richtig für SSH-Keys
- Der `deployment/vps_key` hat falsche Permissions

**Lösung:** Windows SSH-Key verwenden (`~/.ssh/server_key`)

### SSH-Key auf Server installieren

**Option A: Über Web-Console (empfohlen wenn noch kein Zugang)**

1. In Hetzner/Strato Web-Console einloggen (VNC/Serial Console)

2. Als root einloggen

3. Public Key installieren:
```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Dein persönlicher Key (lokal: ~/.ssh/server_key.pub)
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBHjtxpYUgHv4YCb/yu954ODkOXvVoKMw5VhQ2RlYUus server-key" >> ~/.ssh/authorized_keys

chmod 600 ~/.ssh/authorized_keys
```

4. Testen:
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233
```

**Option B: Wenn Passwort-Login noch funktioniert**

```bash
# Von Windows aus
cat ~/.ssh/server_key.pub | ssh root@91.98.192.233 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
```

---

## Manuelles Deployment

### 1. Backup erstellen

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && tar -czf /opt/business-hub/data/backups/backup-$(date +%Y%m%d-%H%M%S).tar.gz app/ templates/ deployment/"
```

### 2. Dateien hochladen

**Core-Dateien:**
```bash
scp -i ~/.ssh/server_key app/__init__.py root@91.98.192.233:/opt/business-hub/app/
scp -i ~/.ssh/server_key app/routes/auth.py root@91.98.192.233:/opt/business-hub/app/routes/
scp -i ~/.ssh/server_key app/services/data_persistence.py root@91.98.192.233:/opt/business-hub/app/services/
```

**Neue Routes:**
```bash
scp -i ~/.ssh/server_key app/routes/hub.py root@91.98.192.233:/opt/business-hub/app/routes/
scp -i ~/.ssh/server_key app/routes/slots.py root@91.98.192.233:/opt/business-hub/app/routes/
scp -i ~/.ssh/server_key app/routes/t2.py root@91.98.192.233:/opt/business-hub/app/routes/
scp -i ~/.ssh/server_key app/routes/api_gateway.py root@91.98.192.233:/opt/business-hub/app/routes/
```

**Templates:**
```bash
scp -i ~/.ssh/server_key -r templates/hub root@91.98.192.233:/opt/business-hub/templates/
scp -i ~/.ssh/server_key -r templates/slots root@91.98.192.233:/opt/business-hub/templates/
scp -i ~/.ssh/server_key -r templates/t2 root@91.98.192.233:/opt/business-hub/templates/
```

### 3. Service neu starten

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"
```

### 4. Status prüfen

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub"
```

---

## Wichtige Fixes dokumentiert

### Fix 1: User 'business-hub' existiert nicht

**Problem:**
```
business-hub.service: Failed to determine user credentials: No such process
status=217/USER
```

**Ursache:** Service-Datei nutzt `User=business-hub`, aber der User existiert nicht

**Lösung:** Service läuft als `root` (Dateien gehören eh root)
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "sed -i 's/^User=business-hub/User=root/' /etc/systemd/system/business-hub.service && sed -i 's/^Group=www-data/Group=root/' /etc/systemd/system/business-hub.service && systemctl daemon-reload && systemctl restart business-hub"
```

### Fix 2: SSH Permission denied trotz richtigem Key

**Problem:** `deployment/vps_key` funktioniert nicht auf Windows

**Ursache:** Windows `chmod` setzt keine Unix-Permissions

**Lösung:** Windows SSH-Key verwenden
```bash
# Statt:
ssh -i deployment/vps_key root@91.98.192.233

# Nutze:
ssh -i ~/.ssh/server_key root@91.98.192.233
```

---

## Server-Infos

**VPS:** ZFA-Server (91.98.192.233)
**SSH-User:** root
**SSH-Key:** `~/.ssh/server_key` (Windows)
**App-Pfad:** `/opt/business-hub`
**Service:** `business-hub.service`
**Logs:** `/var/log/business-hub/`

**Aktive Routes:**
- http://91.98.192.233/ → Login
- http://91.98.192.233/hub → Hub Dashboard
- http://91.98.192.233/slots → Slot Booking
- http://91.98.192.233/t2 → T2 System
- http://91.98.192.233/api → API Gateway

**Service-Kommandos:**
```bash
# Status
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub"

# Logs
ssh -i ~/.ssh/server_key root@91.98.192.233 "journalctl -u business-hub -f"

# Restart
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"

# Gunicorn-Prozesse
ssh -i ~/.ssh/server_key root@91.98.192.233 "ps aux | grep gunicorn"
```

---

## Troubleshooting

### Service startet nicht

```bash
# Logs checken
ssh -i ~/.ssh/server_key root@91.98.192.233 "journalctl -u business-hub -n 100"

# Python-Fehler
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"
```

### SSH-Verbindung schlägt fehl

```bash
# Verbose Mode
ssh -v -i ~/.ssh/server_key root@91.98.192.233

# Key-Fingerprint prüfen
ssh-keygen -l -f ~/.ssh/server_key.pub
```

### Deployment schlägt fehl

1. Backup vorhanden?
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "ls -lh /opt/business-hub/data/backups/ | tail -5"
```

2. Rollback:
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && tar -xzf data/backups/backup-YYYYMMDD-HHMMSS.tar.gz && systemctl restart business-hub"
```

---

## Best Practices

1. **Immer Backup vor Deployment**
2. **Testen auf Staging-Environment** (falls vorhanden)
3. **Service-Status nach Deployment prüfen**
4. **Logs überwachen** für 5-10 Minuten
5. **Rollback-Plan bereit haben**

---

## Siehe auch

- [VPS_MIGRATION_GUIDE.md](VPS_MIGRATION_GUIDE.md) - Komplette Migration von Render
- [VPS_DEPLOYMENT_CHECKLIST.md](VPS_DEPLOYMENT_CHECKLIST.md) - Deployment-Checkliste
- [SERVER_COMPARISON.md](SERVER_COMPARISON.md) - Server-Vergleich Hetzner vs. Strato
- [README.md](README.md) - Allgemeine VPS-Dokumentation
