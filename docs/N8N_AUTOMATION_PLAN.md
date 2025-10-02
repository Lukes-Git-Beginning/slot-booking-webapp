# n8n Automatisierungs-Plan für Luke's Workflows

## Kontext
- **Rolle:** Full Stack Dev + Terminplaner + Zoom Host @ Zentrum für finanzielle Aufklärung
- **Problem:** 9-20:30 Uhr durchgehend online (11,5h täglich)
- **Ziel:** Automatisierung repetitiver Tasks → mehr Fokuszeit, weniger Stress

## Aktuelle Workflows

### Zoom Host Zeiten
- **Mo + Mi:** 11, 14, 16, 18, 20 Uhr
- **Di + Do:** 09, 11, 14, 16, 18, 20 Uhr
- **Fr:** 9, 11, 14 Uhr

### Tägliche Aufgaben
- **17:20-18:30:** Kunden anrufen (Termin am nächsten Tag "aufheizen")
- **Durchgehend:** WhatsApp (Hubspot), Outlook E-Mails, T1/T2 Kommunikation
- **Problem:** Hubspot generiert nicht immer Tasks für Rückholtermine → manuelles Cross-Checking nötig

### Termin-Status in Google Calendar
- **Farben:** Rot/Orange = Probleme
- **Titel-Präfixe:** "Ghost", "nicht erschienen", etc.
- **Events werden nicht gelöscht**, nur farblich/textlich markiert

### Hubspot Status-Mappings
- **Verschiebung:** → "T1 Verschoben"
- **Absage:** → "Verloren vor T1"
- **Storno:** → wie Absage

---

## n8n Automatisierungs-Workflows

### Setup: Hetzner Server
```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e WEBHOOK_URL=https://n8n.deine-domain.de \
  n8nio/n8n
```

**Benötigte Integrationen:**
- Google Calendar (OAuth)
- Hubspot (API Key)
- WhatsApp Business API / Hubspot WhatsApp
- Outlook/Microsoft 365 (OAuth)

---

### Workflow 1: Anruf-Liste Generator
**Trigger:** Täglich um 18:10 Uhr

**Logik:**
```
Cron Trigger (18:10)
  ↓
Google Calendar: Alle Events für MORGEN abrufen
  ↓
Hubspot: Alle Tasks für MORGEN abrufen
  ↓
Function: Vergleichen
  - Finde Events, die KEINE entsprechende Hubspot Task haben
  - (betrifft hauptsächlich Rückholtermine wegen Hubspot Bug)
  ↓
IF: Fehlende Tasks gefunden?
  ↓
WhatsApp/Slack: "⚠️ Fehlende Aufgaben für morgen: [Liste mit Namen + Zeiten]"
```

**Output-Format:**
```
⚠️ Fehlende Hubspot-Tasks für morgen (XX.XX.):

- 11:00 Uhr: Max Mustermann (Rückholtermin)
- 16:00 Uhr: Anna Schmidt (Rückholtermin)

→ Bitte manuell anrufen!
```

---

### Workflow 2: Smart Message Handler (WhatsApp/Outlook)

**Trigger:** Webhook bei neuer Nachricht (Hubspot/Outlook)

**Logik:**
```
Webhook Trigger (neue Nachricht)
  ↓
AI/Regex Extract:
  - Kundenname extrahieren
  - Absicht erkennen (Bestätigung/Absage/Verschiebung/Komplex)
  ↓
Switch nach Absicht:

┌─ BESTÄTIGUNG ─────────────────────────┐
│ Antwort:                              │
│ "Vielen Dank für Ihre Rückmeldung     │
│  Herr/Frau {name}"                    │
│                                       │
│ Hubspot: Notiz hinzufügen             │
│ Keine Benachrichtigung an Luke        │
└───────────────────────────────────────┘

┌─ ABSAGE / VERSCHIEBUNG ───────────────┐
│ Antwort:                              │
│ "Guten Tag Frau/Herr {name},          │
│                                       │
│ danke für Ihre Rückmeldung. Das ist   │
│ kein Problem – wir finden gerne einen │
│ neuen Termin. Wann würde es Ihnen     │
│ passen?                               │
│                                       │
│ Beste Grüße                           │
│ Luke Hoppe | Terminplanung"           │
│                                       │
│ Hubspot Status:                       │
│  - Absage → "Verloren vor T1"         │
│  - Verschiebung → "T1 Verschoben"     │
│                                       │
│ Google Calendar: Farbe → Rot/Orange   │
│ Benachrichtigung an Luke (Summary)    │
└───────────────────────────────────────┘

┌─ KOMPLEXE FRAGE ──────────────────────┐
│ Direkt an Luke weiterleiten           │
│ Mit Kontext + Vorschlag               │
└───────────────────────────────────────┘
```

**Standard-Fragen die auto-handled werden:**
- "Termin bestätigen" / "Ich komme"
- "Wie lautet der Zoom-Link?"
- "Wann ist mein Termin?"
- "Ich kann nicht" / "Absagen"
- "Verschieben möglich?"

**Ergebnis:** 70-80% der Nachrichten automatisch beantwortet

---

### Workflow 3: Event-Monitor (Google Calendar ↔ Hubspot Sync)

**Trigger:** Alle 5 Minuten

**Logik:**
```
Cron Trigger (*/5 * * * *)
  ↓
Google Calendar: Geänderte Events (seit letztem Check)
  ↓
FOR EACH geändertes Event:
  ↓
  Parse Event:
    - Farbe geändert? (→ Rot/Orange)
    - Titel enthält Keywords? ("Ghost", "nicht erschienen", "Storno", "Absage")
  ↓
  Hubspot Status Update:
    - "Ghost"/"nicht erschienen" → Status in Hubspot
    - "Storno"/"Absage" → "Verloren vor T1"
    - "Verschoben" → "T1 Verschoben"
  ↓
  IF: Event Status = "Ghost" UND Zeit = 21:00 Uhr?
    ↓
    WhatsApp: Nachfass-Nachricht senden
    "Hallo Herr/Frau {name}, schade dass Sie heute nicht dabei sein konnten..."
```

**Zusätzliche Features:**
- Bei Farbe = Orange: Warnung an Luke (evt. manuell prüfen)
- Log aller Änderungen für Nachvollziehbarkeit

---

### Workflow 4: Focus Mode Bundler

**Trigger:** 11:00, 15:00, 17:00 Uhr

**Logik:**
```
Cron Trigger (11:00, 15:00, 17:00)
  ↓
n8n Database: Alle auto-behandelten Nachrichten seit letztem Report sammeln
  ↓
Format Summary:
  "✅ Automatisch erledigt (seit {letzte_Zeit}):

   📧 3x Terminbestätigungen
   🔄 2x Verschiebungen beantwortet
   ❌ 1x Absage verarbeitet

   ⏳ 1 Nachricht wartet auf dich (komplex)"
  ↓
Slack/WhatsApp: Summary senden
```

**Zusätzlich um 17:00:**
- "📞 Anruf-Liste für heute Abend: [Link]"
- "📅 Morgen {X} Termine geplant"

---

### Workflow 5: Auto-Pilot Mode (während Zoom-Meetings)

**Trigger:** Basierend auf deinem Kalender

**Logik:**
```
Cron Check (alle 5 Min)
  ↓
Check: Bin ich gerade in Zoom-Meeting? (11-14, 16-18, 20-21 Uhr)
  ↓
IF: Meeting aktiv:
  ↓
  Alle Standard-Anfragen: Automatisch bearbeiten (keine Benachrichtigung)
  Dringende/Komplexe: In Queue sammeln
  ↓
IF: Meeting beendet:
  ↓
  WhatsApp: "🔔 Während du weg warst:
             - 5 Nachrichten automatisch beantwortet
             - 2 warten auf dich (siehe Link)"
```

---

## Erwartete Zeitersparnis

| Aufgabe | Vorher | Nachher | Ersparnis |
|---------|--------|---------|-----------|
| **Nachrichten-Handling** | 2-3h täglich | 30min | ~2h |
| **Anruf-Liste vorbereiten** | 15-20min | 2min | ~15min |
| **Status-Updates (Hubspot/Calendar)** | 30min | automatisch | 30min |
| **Zwischen-Checks während Meetings** | 1h (Stress) | 0 | 1h + Fokus |
| **GESAMT** | 11,5h online | ~9h + weniger Stress | **2,5h + Lebensqualität** |

---

## Pilot-Plan (4 Wochen)

### Woche 1: Setup + Workflow #1
- [ ] n8n auf Hetzner installieren (Docker)
- [ ] Subdomain einrichten (z.B. `automation.yourdomain.de`)
- [ ] Google Calendar API connecten
- [ ] Hubspot API connecten
- [ ] **Workflow #1 bauen:** Anruf-Liste Generator (18:10 Uhr)
- [ ] 3 Tage testen mit echten Daten

### Woche 2: Workflow #2 (Message Handler - Phase 1)
- [ ] Outlook API connecten
- [ ] **Nur "Bestätigungen"** auto-handlen
- [ ] Rest weiterleiten wie bisher
- [ ] Monitoring: Wie viele werden automatisch bearbeitet?

### Woche 3: Workflow #2 erweitern + WhatsApp
- [ ] WhatsApp/Hubspot Integration
- [ ] Absagen/Verschiebungen auto-handlen
- [ ] Templates verfeinern
- [ ] AI/Regex für Intent-Erkennung optimieren

### Woche 4: Workflows #3, #4, #5
- [ ] Event-Monitor (Calendar ↔ Hubspot Sync)
- [ ] Focus Mode Bundler
- [ ] Auto-Pilot Mode während Meetings
- [ ] Performance-Monitoring & Tweaks

---

## Offene Fragen für Setup

1. **Subdomain:** Welche Domain steht zur Verfügung? (z.B. `n8n.yourdomain.de`)
2. **Hubspot API:** Admin-Zugriff für API-Keys vorhanden?
3. **WhatsApp:** Läuft über Hubspot-Integration oder eigene Business API?
4. **Server-Specs:** Hetzner Server bereits vorhanden oder muss noch bestellt werden?
5. **Priorität:** Mit welchem Workflow starten? (Empfehlung: #1 Anruf-Liste)

---

## Nächste Schritte

1. **Hetzner Server Zugriff klären**
2. **n8n Setup-Script erstellen** (Docker + Nginx Reverse Proxy)
3. **API-Keys sammeln** (Google, Hubspot, Microsoft)
4. **Workflow #1 als Proof of Concept** bauen
5. **Nach Erfolg:** Schritt für Schritt erweitern

---

**Erstellt am:** 2025-10-01
**Status:** Planung
**Nächstes Review:** Nach Hetzner Setup
