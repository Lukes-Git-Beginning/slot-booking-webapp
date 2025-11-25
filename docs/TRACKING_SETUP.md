# Tracking-System Automatisierung

## Übersicht

Das Tracking-System erfasst täglich die Termine aus dem Google Calendar und berechnet Metriken wie Auftauchquote, Erfolgsrate, No-Show-Rate etc.

## Problem

Aktuell werden die Tracking-Daten nicht automatisch erfasst. Die letzte Erfassung war am **23. September 2025**.

## Lösung: Tägliche Automatisierung einrichten

### Option 1: Windows Task Scheduler (Empfohlen für Windows Server)

#### Schritt 1: Backfill fehlender Daten

Zuerst müssen die fehlenden Daten erfasst werden:

```bash
# Öffne PowerShell/CMD als Administrator
cd C:\Users\Luke\Documents\Slots\slot_booking_webapp

# Test (Dry Run) - zeigt was passieren würde
python scripts\backfill_tracking.py --start 2025-09-24 --dry-run

# Echte Ausführung - erfasst fehlende Daten
python scripts\backfill_tracking.py --start 2025-09-24
```

**Wichtig:** Das Script braucht die Google Calendar Credentials (GOOGLE_CREDS_BASE64 Environment Variable)

#### Schritt 2: Windows Task Scheduler einrichten

1. **Task Scheduler öffnen:**
   - Windows-Taste drücken
   - "Aufgabenplanung" oder "Task Scheduler" eingeben
   - Als Administrator öffnen

2. **Neue Aufgabe erstellen:**
   - Rechtsklick auf "Aufgabenplanungsbibliothek"
   - "Ordner erstellen" → Name: "SlotBooking"
   - Rechtsklick auf neuen Ordner
   - "Aufgabe erstellen..." (NICHT "Einfache Aufgabe")

3. **Allgemein Tab:**
   - Name: `Slot Booking - Daily Tracking`
   - Beschreibung: `Erfasst täglich Tracking-Daten aus Google Calendar`
   - Sicherheitsoptionen:
     - ☑ Unabhängig von der Benutzeranmeldung ausführen
     - ☑ Mit höchsten Privilegien ausführen
   - Konfigurieren für: `Windows 10` oder `Windows Server 2019`

4. **Trigger Tab:**
   - "Neu..." klicken
   - Aufgabe starten: `Nach einem Zeitplan`
   - Einstellungen:
     - ☑ Täglich
     - Start: Heute um **23:00 Uhr**
     - Wiederholen: Alle 1 Tage
   - Erweiterte Einstellungen:
     - ☑ Aktiviert
   - OK klicken

5. **Aktionen Tab:**
   - "Neu..." klicken
   - Aktion: `Programm starten`
   - Programm/Skript:
     ```
     C:\Users\Luke\AppData\Local\Programs\Python\Python313\python.exe
     ```
   - Argumente hinzufügen:
     ```
     scripts\run_tracking.py
     ```
   - Starten in:
     ```
     C:\Users\Luke\Documents\Slots\slot_booking_webapp
     ```
   - OK klicken

6. **Bedingungen Tab:**
   - ☐ Aufgabe nur starten, falls Computer im Leerlauf ist
   - ☑ Aufgabe starten, auch wenn Computer im Akkubetrieb ist
   - ☐ Beenden, falls Computer in Akkubetrieb wechselt

7. **Einstellungen Tab:**
   - ☑ Ausführung der Aufgabe bei Bedarf zulassen
   - ☑ Aufgabe so schnell wie möglich nach verpasstem Start ausführen
   - Wenn Aufgabe fehlschlägt, Neustart nach: `5 Minuten`
   - Versuche Neustart bis zu: `3 Mal`
   - ☑ Aufgabe beenden, wenn Ausführung länger als: `1 Stunde`
   - Falls ausgeführte Aufgabe nicht endet, beim Anfordern des Beendens: `Aufgabe beenden`

8. **Speichern:**
   - OK klicken
   - Evtl. Administrator-Passwort eingeben

#### Schritt 3: Task testen

```powershell
# Task manuell starten
Get-ScheduledTask -TaskName "Slot Booking - Daily Tracking" | Start-ScheduledTask

# Status prüfen
Get-ScheduledTask -TaskName "Slot Booking - Daily Tracking" | Get-ScheduledTaskInfo

# Logs prüfen
cat C:\Users\Luke\Documents\Slots\slot_booking_webapp\data\tracking\logs\tracking.log
```

### Option 2: Python Scheduler (Für Development)

Erstelle `scripts/scheduler.py`:

```python
import schedule
import time
import logging
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.tracking_system import BookingTracker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_daily_tracking():
    """Führt tägliches Tracking aus"""
    try:
        logging.info("Starting daily tracking...")
        tracker = BookingTracker()
        result = tracker.check_daily_outcomes()
        logging.info(f"Tracking completed: {result}")
    except Exception as e:
        logging.error(f"Tracking failed: {e}")

# Schedule täglich um 23:00
schedule.every().day.at("23:00").do(run_daily_tracking)

logging.info("Scheduler gestartet. Tracking läuft täglich um 23:00 Uhr.")

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
```

Dann als Windows Service mit `nssm` oder als dauerhafte PowerShell-Sitzung laufen lassen.

### Option 3: Cron (für Linux Server)

```bash
# Crontab bearbeiten
crontab -e

# Folgende Zeile hinzufügen (täglich um 23:00)
0 23 * * * cd /path/to/slot_booking_webapp && /usr/bin/python3 scripts/run_tracking.py >> /var/log/slot_tracking.log 2>&1
```

## Backfill-Script Verwendung

### Fehlende Daten nachträglich erfassen

```bash
# Alle Daten ab 01.09.2025 bis heute
python scripts/backfill_tracking.py --start 2025-09-01

# Bestimmter Zeitraum
python scripts/backfill_tracking.py --start 2025-09-24 --end 2025-10-23

# Dry Run (zeigt nur was passieren würde)
python scripts/backfill_tracking.py --start 2025-09-24 --dry-run
```

### Parameter

- `--start`: Start-Datum (Format: YYYY-MM-DD)
- `--end`: End-Datum (optional, default: heute)
- `--dry-run`: Simulation ohne Änderungen

## Logs prüfen

Tracking-Logs finden sich hier:
- `data/tracking/logs/tracking.log`
- Windows Event Log (bei Task Scheduler)

## Troubleshooting

### "Google credentials not found"

**Lösung:** Environment Variable `GOOGLE_CREDS_BASE64` setzen:

```powershell
# In PowerShell (als Administrator)
[System.Environment]::SetEnvironmentVariable("GOOGLE_CREDS_BASE64", "YOUR_BASE64_CREDENTIALS", "Machine")

# System neu starten oder Task Scheduler neu starten
```

### Task läuft nicht

1. Event Viewer öffnen
2. Windows-Protokolle → Anwendung
3. Nach Fehlern vom Task Scheduler suchen

### Daten werden nicht erfasst

1. Prüfe ob Google Calendar API Zugriff hat
2. Prüfe ob `data/tracking/daily_metrics.json` existiert
3. Logs prüfen

## Empfohlene Einrichtung

**Für Produktiv-Server:**
1. Windows Task Scheduler mit `run_tracking.py` (täglich 23:00 Uhr)
2. Backfill-Script einmalig ausführen um fehlende Daten zu erfassen
3. Logs regelmäßig prüfen

**Für Development:**
- Manuell `python scripts/run_tracking.py` wenn nötig
- Oder Python Scheduler im Hintergrund
