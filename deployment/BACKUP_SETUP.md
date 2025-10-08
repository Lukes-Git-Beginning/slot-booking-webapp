# Encrypted Backup System - Setup Guide

## 🔐 Verschlüsseltes Backup-System

Alle Backups werden mit **AES-256-CBC Verschlüsselung** gesichert.

---

## ✅ Was ist bereits konfiguriert:

1. **Automatische verschlüsselte Backups**
   - Täglich um 03:00 UTC
   - AES-256 Verschlüsselung
   - 30 Tage Aufbewahrung
   - Systemd Timer: `encrypted-backup.timer`

2. **Encryption Key**
   - Gespeichert auf Server: `/root/.business-hub-backup-key`
   - **WICHTIG:** Key sicher aufbewahren!

3. **Backup-Location**
   - Server: `/opt/business-hub/backups/*.tar.gz.enc`
   - Format: `backup_YYYYMMDD_HHMMSS.tar.gz.enc`

---

## 🔑 Encryption Key (WICHTIG!)

**Dein Encryption Key:**
```
VqpAJOkCq9LiXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXw=
```

**⚠️ OHNE DIESEN KEY KANNST DU BACKUPS NICHT ENTSCHLÜSSELN!**

**Speichere ihn:**
- In deinem Passwort-Manager
- In sicherer lokaler Datei
- NICHT im Git Repository!

---

## 📤 Git-Push einrichten (Optional aber empfohlen)

### Schritt 1: GitHub Personal Access Token erstellen

1. Gehe zu: https://github.com/settings/tokens
2. "Generate new token (classic)"
3. Scope auswählen: **`repo`** (full control)
4. Token kopieren (nur einmal sichtbar!)

### Schritt 2: Git Remote mit Token konfigurieren

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233

cd /opt/business-hub

# Ersetze <USERNAME> und <TOKEN>:
git remote set-url origin https://<USERNAME>:<TOKEN>@github.com/Lukes-Git-Beginning/slot-booking-webapp.git

# Testen:
git push origin main
```

### Schritt 3: Test-Backup mit Git-Push

```bash
/opt/business-hub/scripts/encrypted_backup.sh
```

Sollte nun automatisch zu GitHub pushen.

---

## 🔓 Backup entschlüsseln

### Auf dem Server:

```bash
cd /tmp

# Entschlüsseln
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
  -in /opt/business-hub/backups/backup_20251008_135506.tar.gz.enc \
  -out backup.tar.gz \
  -pass file:/root/.business-hub-backup-key

# Entpacken
tar -xzf backup.tar.gz
```

### Lokal (mit gespeichertem Key):

```bash
# 1. Backup von Server herunterladen
scp -i ~/.ssh/server_key \
  root@91.98.192.233:/opt/business-hub/backups/backup_20251008_135506.tar.gz.enc \
  ./

# 2. Encryption Key lokal speichern
echo "VqpAJOkCq9LiXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXw=" > backup-key.txt

# 3. Entschlüsseln
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
  -in backup_20251008_135506.tar.gz.enc \
  -out backup.tar.gz \
  -pass file:backup-key.txt

# 4. Entpacken
tar -xzf backup.tar.gz
```

---

## 📊 Backup-Status prüfen

```bash
# Timer-Status
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status encrypted-backup.timer"

# Letzter Backup-Run
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status encrypted-backup.service"

# Alle verschlüsselten Backups
ssh -i ~/.ssh/server_key root@91.98.192.233 "ls -lh /opt/business-hub/backups/*.enc"

# Backup-Größe gesamt
ssh -i ~/.ssh/server_key root@91.98.192.233 "du -sh /opt/business-hub/backups/"
```

---

## 🚨 Notfall-Recovery

### Kompletter Server-Verlust:

1. **Neuen Server aufsetzen**
2. **Git Repository klonen**
   ```bash
   git clone https://github.com/Lukes-Git-Beginning/slot-booking-webapp.git
   cd slot-booking-webapp
   ```

3. **Neuestes Backup entschlüsseln**
   ```bash
   # Key lokal erstellen
   echo "VqpAJOkCq9LiXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXw=" > /root/.business-hub-backup-key
   chmod 600 /root/.business-hub-backup-key

   # Entschlüsseln
   openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
     -in backups/backup_LATEST.tar.gz.enc \
     -out backup.tar.gz \
     -pass file:/root/.business-hub-backup-key

   # Wiederherstellen
   tar -xzf backup.tar.gz
   ```

4. **Application neu deployen** (siehe deployment/README.md)

---

## ⚙️ Manuelle Backup-Erstellung

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233
/opt/business-hub/scripts/encrypted_backup.sh
```

---

## 🔄 Backup-Frequenz ändern

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233

# Timer-Datei bearbeiten
nano /etc/systemd/system/encrypted-backup.timer

# Beispiel: Alle 6 Stunden statt täglich
# Ändere: OnCalendar=*-*-* 03:00:00
# Zu:     OnCalendar=*-*-* 03,09,15,21:00:00

# Timer neu laden
systemctl daemon-reload
systemctl restart encrypted-backup.timer
```

---

## 📈 Was wird gesichert?

- ✅ Alle JSON-Daten: `/data/persistent/*.json`
- ✅ `.env` Datei (mit Credentials)
- ✅ Verschlüsselt mit AES-256
- ✅ PBKDF2 Key-Derivation (100.000 Iterationen)
- ❌ Logs (zu groß, nicht wichtig)
- ❌ Virtual Environment (kann neu erstellt werden)
- ❌ Git-History (schon auf GitHub)

---

## 🛡️ Sicherheits-Features

1. **AES-256-CBC** - Military-Grade Encryption
2. **PBKDF2** - 100.000 Iterationen gegen Brute-Force
3. **Salt** - Unique Salt pro Backup
4. **Key-File** - Nur auf Server (600 Permissions)
5. **Encrypted-at-Rest** - Auch auf GitHub sicher

---

## ❓ Häufige Fragen

**Q: Ist Git mit verschlüsselten Backups sicher?**
A: Ja! Die Dateien sind mit AES-256 verschlüsselt. Selbst bei GitHub-Hack sind Daten sicher (ohne Key nicht entschlüsselbar).

**Q: Was wenn ich den Encryption Key verliere?**
A: Backups sind dann NICHT wiederherstellbar! Key unbedingt sicher aufbewahren.

**Q: Kann ich alte Backups löschen?**
A: Script löscht automatisch Backups >30 Tage. Manuelle Löschung möglich:
```bash
rm /opt/business-hub/backups/backup_YYYYMMDD_HHMMSS.tar.gz.enc
```

**Q: Wie groß sind die Backups?**
A: Aktuell ~16KB komprimiert+verschlüsselt. Mit mehr Daten wachsen sie.

**Q: Backup läuft nicht?**
A: Prüfen:
```bash
systemctl status encrypted-backup.timer
systemctl status encrypted-backup.service
journalctl -u encrypted-backup.service -n 50
```

---

**🎉 Deine Daten sind jetzt sicher gesichert!**
