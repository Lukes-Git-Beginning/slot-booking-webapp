# SSH Key Setup für VPS

## 📋 Übersicht

Ich habe einen neuen SSH-Key für den VPS-Zugriff generiert.

**Generierte Dateien:**
- `deployment/vps_key` - Private Key (GEHEIM! Nicht teilen!)
- `deployment/vps_key.pub` - Public Key (kann geteilt werden)

## 🚀 Setup in 2 Schritten

### Schritt 1: SSH Key auf VPS installieren

```bash
cd deployment
bash setup_ssh_key.sh
```

**Was passiert:**
- Du wirst nach dem Root-Passwort des VPS gefragt
- Der Public Key wird auf den VPS hochgeladen
- Danach kannst du dich ohne Passwort verbinden

### Schritt 2: T2-Updates hochladen

```bash
bash upload_t2_updates.sh
```

**Was passiert:**
- Lädt alle neuen T2-Dateien auf den VPS hoch
- Löscht veraltete Dateien
- Startet business-hub Service neu
- Zeigt Status an

## 📝 Manuelles Setup (falls Automatik nicht funktioniert)

### Public Key manuell hochladen

```bash
# Public Key anzeigen
cat deployment/vps_key.pub

# Auf VPS einloggen (mit Passwort)
ssh root@91.98.192.233

# Auf VPS: authorized_keys Datei bearbeiten
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys

# Public Key einfügen (komplette Zeile von vps_key.pub)
# Speichern: Ctrl+O, Enter, Ctrl+X

# Permissions setzen
chmod 600 ~/.ssh/authorized_keys

# Ausloggen
exit
```

### Test der SSH-Verbindung

```bash
ssh -i deployment/vps_key root@91.98.192.233
```

Wenn das funktioniert, kannst du danach `upload_t2_updates.sh` ausführen.

## 🔒 Sicherheitshinweise

- ⚠️ **NIEMALS** `vps_key` (Private Key) teilen oder committen!
- ✅ Der Private Key ist bereits in `.gitignore` eingetragen
- ✅ Nur der Public Key (`vps_key.pub`) darf geteilt werden
- ✅ Der Private Key hat Permissions 600 (nur du kannst ihn lesen)

## ❓ Troubleshooting

### "Permission denied (publickey)"

```bash
# Permissions prüfen
ls -la deployment/vps_key
# Sollte: -rw------- (600)

# Falls falsch:
chmod 600 deployment/vps_key
```

### "ssh-copy-id: command not found" (Windows Git Bash)

Manuelles Setup verwenden (siehe oben).

### "Connection refused" oder "Timeout"

```bash
# Prüfe ob VPS erreichbar ist
ping 91.98.192.233

# Prüfe ob SSH-Port offen ist
telnet 91.98.192.233 22
```

## 🎯 Was wird hochgeladen?

**Backend:**
- `app/routes/t2.py` - Komplette Neuentwicklung mit Fairness-Algorithmus

**Frontend Templates:**
- `templates/t2/dashboard.html` - Neues Dashboard mit Würfel-System
- `templates/t2/booking.html` - Vereinfachter Booking-Prozess
- `templates/t2/calendar.html` - Kalender-Ansicht
- `templates/t2/stats.html` - Statistik-Seite
- `templates/t2/no_tickets.html` - No-Tickets Seite
- `templates/t2/base.html` - Base Template (mit Theme Toggle)

**Entfernt:**
- `templates/t2/closer_detail.html` - Nicht mehr benötigt

## ✅ Nach dem Upload

1. Teste das T2-System: http://91.98.192.233/t2/
2. Prüfe den Service-Status:
   ```bash
   ssh -i deployment/vps_key root@91.98.192.233 "systemctl status business-hub"
   ```
3. Logs ansehen falls Fehler:
   ```bash
   ssh -i deployment/vps_key root@91.98.192.233 "journalctl -u business-hub -n 50"
   ```

---

**SSH Key Fingerprint:**
```
SHA256:+g8znjzIGn5guU53Wmb4+iAZFWOiOyknKG5wOOlNvs0
```
