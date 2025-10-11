# T2 Bucket System - Deployment Guide

## 🎯 Overview

Das neue T2 Bucket System ersetzt das alte Fairness-basierte System durch ein probability-basiertes Zieh-System inspiriert vom Boat-Drawing-System.

### Hauptfeatures
- ✅ **Probability Mappings**: Admin kann Gewichtungen pro Closer setzen
- ✅ **Bucket-System**: Max 10 Draws, dann automatischer Reset
- ✅ **Timeout-System**: Configurable Cooldowns (T1: 0min, T2: 1min)
- ✅ **Animiertes UI**: Moderne Slot-Machine-Animation beim Ziehen
- ✅ **Admin-Dashboard**: Vollständige Bucket-Konfiguration und Statistiken
- ✅ **Nur T2-Closer**: Alex, Christian, David, José, Tim (keine Opener!)

## 📁 Neue Dateien

### Backend
```
app/services/t2_bucket_system.py        # Core bucket logic
app/routes/t2_bucket_routes.py          # New routes
app/routes/t2.py                        # Updated (integrated bucket routes)
```

### Frontend
```
templates/t2/draw_closer.html           # User draw page (animated)
templates/t2/admin_bucket_config.html   # Admin configuration page
templates/t2/dashboard.html             # Updated (new links)
```

### Data
```
data/persistent/t2_bucket_system.json   # Bucket state persistence
```

## 🚀 Deployment Steps

### 1. Files auf Server kopieren

```bash
# Services
scp -i ~/.ssh/server_key app/services/t2_bucket_system.py root@91.98.192.233:/opt/business-hub/app/services/

# Routes
scp -i ~/.ssh/server_key app/routes/t2_bucket_routes.py root@91.98.192.233:/opt/business-hub/app/routes/
scp -i ~/.ssh/server_key app/routes/t2.py root@91.98.192.233:/opt/business-hub/app/routes/

# Templates
scp -i ~/.ssh/server_key templates/t2/draw_closer.html root@91.98.192.233:/opt/business-hub/templates/t2/
scp -i ~/.ssh/server_key templates/t2/admin_bucket_config.html root@91.98.192.233:/opt/business-hub/templates/t2/
scp -i ~/.ssh/server_key templates/t2/dashboard.html root@91.98.192.233:/opt/business-hub/templates/t2/
```

### 2. Service neu starten

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"
```

### 3. Status prüfen

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub --no-pager"
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log"
```

### 4. Testen

```bash
# Im Browser öffnen
http://91.98.192.233/t2/

# Funktionen testen:
1. Dashboard → "Closer ziehen" Button
2. Draw Page → Animation & Draw
3. Admin Dashboard → Bucket Config (nur für Admins)
4. Probability ändern & Bucket resetten
```

## 🔧 Konfiguration

### Bucket-System-Einstellungen

In `app/services/t2_bucket_system.py`:

```python
BUCKET_CONFIG = {
    "max_draws_before_reset": 10,  # Bucket reset nach 10 Draws
    "t1_timeout_minutes": 0,        # T1: Kein Timeout
    "t2_timeout_minutes": 1,        # T2: 1 Minute Timeout
    "min_probability": 0.1,         # Minimum (kann nicht 0 sein!)
    "max_probability": 100.0        # Maximum
}
```

### T2-Only Closers

```python
T2_CLOSERS = {
    "Alex": {...},
    "Christian": {...},
    "David": {...},
    "Jose": {...},
    "Tim": {...}
}
```

**WICHTIG**: Opener (Patrick, Sara, Sonja, Simon, Ann-Kathrin, Dominik) sind NICHT im System!

## 📊 Admin-Funktionen

### Probability Mappings einstellen

1. Als Admin einloggen
2. T2 Dashboard → "Bucket Config (Admin)"
3. Probability-Werte anpassen (Minimum: 0.1)
4. "Update" klicken
5. Bucket wird automatisch neu gebaut

### Bucket manuell resetten

1. Admin Bucket Config öffnen
2. "Reset Bucket" Button klicken
3. Bestätigen
4. Bucket wird mit aktuellen Probabilities neu gebaut

### Statistiken einsehen

- **Current Bucket Composition**: Anzahl Tickets pro Closer
- **Draws until Reset**: Wie viele Draws noch bis automatischer Reset
- **All-Time Distribution**: Gesamt-Zieh-Statistiken pro Closer
- **Recent Draw History**: Letzte 20 Draws mit Details

## 🎮 User-Flow

### 1. Closer ziehen

```
Dashboard → "Closer ziehen" → Animation läuft → Ergebnis mit Confetti → "Book Appointment"
```

### 2. Timeout-System

- Nach einem Draw: Cooldown aktiv (default 1 Minute für T2)
- Countdown wird angezeigt
- Nach Ablauf: Automatischer Reload möglich

### 3. Booking mit gezogenem Closer

- Gezogener Closer wird in Session gespeichert
- Booking Page verwendet automatisch den gezogenen Closer
- Nach erfolgreicher Buchung: Closer aus Session gelöscht

## 🐛 Troubleshooting

### Problem: "Unauthorized" beim Probability-Update

**Lösung**: User muss in `Config.get_admin_users()` oder Fallback-Liste sein

```python
# In t2.py:
def is_admin_user(username: str) -> bool:
    return username in ['admin', 'Jose', 'Simon', 'Alex', 'David']
```

### Problem: Bucket wird nicht zurückgesetzt

**Lösung**: Check `t2_bucket_system.json` Datei:

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "cat /opt/business-hub/data/persistent/t2_bucket_system.json"
```

### Problem: Draw funktioniert nicht

**Logs prüfen**:

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "grep 'T2 Draw\|Draw error' /var/log/business-hub/error.log"
```

### Problem: Timeout läuft nicht ab

**Browser-Session prüfen**: Timeout wird clientseitig gezählt, bei Reload wird von Server geprüft

## 📈 Monitoring

### Bucket-Status überwachen

```bash
# API-Call (als Admin)
curl -X GET http://91.98.192.233/t2/admin/bucket-config \
  -H "Cookie: session=<session-cookie>"
```

### Draw-History auslesen

```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "python3 -c \"from app.services.t2_bucket_system import get_system_stats; import json; print(json.dumps(get_system_stats(), indent=2))\""
```

## 🔄 Rollback-Plan

Falls Probleme auftreten:

```bash
# 1. Alte Dateien wiederherstellen (aus Git)
git checkout HEAD~1 app/routes/t2.py app/routes/t2_bucket_routes.py

# 2. Neue Dateien entfernen
rm app/services/t2_bucket_system.py
rm templates/t2/draw_closer.html
rm templates/t2/admin_bucket_config.html

# 3. Service neu starten
systemctl restart business-hub
```

## ✅ Post-Deployment Checklist

- [ ] Alle Dateien erfolgreich übertragen
- [ ] Service läuft ohne Errors
- [ ] Draw Page lädt korrekt
- [ ] Admin kann Probabilities ändern
- [ ] Timeout-System funktioniert
- [ ] Bucket reset funktioniert
- [ ] Confetti-Animation läuft
- [ ] Booking mit gezogenem Closer möglich
- [ ] Logs zeigen keine kritischen Errors

## 📝 Notes

- **Bucket-Daten werden persistent gespeichert** in `data/persistent/t2_bucket_system.json`
- **Alte Fairness-Logik bleibt als Fallback** in `app/routes/t2.py` (assign_fair_closer)
- **Design integriert mit Hub-System**: Nutzt gleiche CSS-Variables und Styling
- **Mobile-Responsive**: Alle Pages funktionieren auf Mobile

## 🎉 Success Indicators

Nach erfolgreichem Deployment sollten sichtbar sein:

1. ✅ "Closer ziehen" Button im Dashboard
2. ✅ Animierte Draw Page mit Slot-Machine
3. ✅ Admin Bucket Config Link (nur für Admins)
4. ✅ Probability Mappings funktionieren
5. ✅ Bucket reset bei 10 Draws
6. ✅ Timeout-System aktiv
7. ✅ Draw History wird geloggt
