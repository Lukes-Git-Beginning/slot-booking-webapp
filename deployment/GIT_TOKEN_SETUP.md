# GitHub Token Setup für automatische Backups

## 1. Token auf Server eintragen

**Nachdem du den Token kopiert hast:**

```bash
# Auf Server einloggen
ssh -i ~/.ssh/server_key root@91.98.192.233

# In Repository-Verzeichnis
cd /opt/business-hub

# Git Remote mit Token aktualisieren
# Ersetze <DEIN_GITHUB_USERNAME> und <DEIN_TOKEN>:
git remote set-url origin https://<DEIN_GITHUB_USERNAME>:<DEIN_TOKEN>@github.com/Lukes-Git-Beginning/slot-booking-webapp.git
```

**Beispiel:**
```bash
git remote set-url origin https://Lukes-Git-Beginning:ghp_abc123xyz...@github.com/Lukes-Git-Beginning/slot-booking-webapp.git
```

## 2. Testen

```bash
# Test-Push
git push origin main

# Sollte erfolgreich sein ohne Passwort-Abfrage
```

## 3. Backup-Script testen

```bash
# Manueller Backup-Run
/opt/business-hub/scripts/encrypted_backup.sh

# Prüfen ob zu GitHub gepusht wurde
git log --oneline -3
```

Du solltest einen neuen Commit sehen: `backup: Add encrypted backup backup_YYYYMMDD_HHMMSS`

## 4. Auf GitHub prüfen

Gehe zu: https://github.com/Lukes-Git-Beginning/slot-booking-webapp/tree/main/backups

Du solltest die `.enc` Dateien sehen (verschlüsselt!).

---

## Token erneuern (in 90 Tagen)

1. **Neuen Token generieren** auf GitHub
2. **Remote URL updaten** auf Server (Schritt 1)
3. **Testen** (Schritt 2)
4. **Alten Token löschen** auf GitHub
5. **Neuen Reminder setzen** für 80 Tage später

---

## Troubleshooting

**Problem: Push schlägt fehl mit "Authentication failed"**
```bash
# Prüfe Remote URL
git remote -v

# Sollte zeigen:
# origin  https://USERNAME:TOKEN@github.com/... (push)
```

**Problem: Token im Terminal sichtbar**
```bash
# Verstecke Token in Remote URL durch git credential helper
git config credential.helper store
```

**Problem: "remote: Permission denied"**
- Token hat falsche Scopes (braucht `repo`)
- Token ist abgelaufen
- Username/Token falsch eingegeben
