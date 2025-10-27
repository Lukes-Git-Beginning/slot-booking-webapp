# My Calendar - Anleitung für Berater

## 📋 Übersicht

**My Calendar** ist ein Kanban-Board das zeigt, welche Termine von welchem Telefonisten gebucht wurden. Es ermöglicht einfaches Status-Management per Drag & Drop.

## 🎯 Wichtig: Warum My Calendar nutzen?

**⚠️ KRITISCH:** Status-Änderungen **NUR über My Calendar** machen, NICHT direkt in Google Calendar!

**Grund:**
- Beim Buchen wird ein unsichtbarer Tag `[Booked by: telefonist.name]` in der Termin-Beschreibung gespeichert
- Dieser Tag ermöglicht es Telefonisten, ihre gebuchten Kunden zu sehen
- **Wenn du direkt in Google Calendar arbeitest, geht dieser Tag verloren!**
- **Wenn du My Calendar nutzt, bleibt der Tag erhalten!**

## 🚀 Zugriff auf My Calendar

1. Einloggen auf https://berater.zfa.gmbh
2. Im Hauptmenü: **"My Calendar"** auswählen
3. Oder direkt: https://berater.zfa.gmbh/slots/my-calendar

## 📊 Kanban-Board verstehen

### 7 Status-Spalten:

| Spalte | Farbe | Bedeutung |
|--------|-------|-----------|
| **Pending** | Grau | Zukünftige Termine (automatisch) |
| **Erschienen** | Grün | Kunde ist zum Termin erschienen |
| **Rückholung** | Lila | Termin für Rückholung/Recall |
| **Sonderkunden** | Gelb | Spezielle Kunden (VIP, etc.) |
| **Verschoben** | Orange | Termin wurde verschoben/abgesagt |
| **Nicht Erschienen** | Rot | Kunde ist nicht erschienen (No-Show) |
| **Ghost** | Dunkelrot | Wiederholter No-Show |

### Statistik-Karten (oben)

Zeigen schnell die Übersicht:
- Anzahl Termine pro Status
- **Show-Rate** (% erschienene Kunden)
- **No-Show-Rate** (% nicht erschienene Kunden)

## 🖱️ Drag & Drop - Status ändern

### Schritt-für-Schritt:

1. **Termin finden**
   - Nach dem Termin sind Kunden in der **"Pending"** Spalte (links)
   - Karte zeigt: Kundenname, Datum, Uhrzeit, Telefonist

2. **Status ändern per Drag & Drop**
   - Klicke auf eine Termin-Karte und **halte die Maustaste**
   - Ziehe die Karte zur gewünschten Spalte
   - Lasse die Maustaste los

3. **Automatische Aktionen**
   - ✅ Status wird sofort in Google Calendar aktualisiert
   - ✅ `[Booked by:]` Tag bleibt erhalten
   - ✅ Farbe im Google Calendar ändert sich:
     - **Erschienen** → Grün (ColorID 2)
     - **Rückholung** → Lila (ColorID 3)
     - **Sonderkunden** → Gelb (ColorID 5)
     - **Verschoben** → Orange (ColorID 6)
     - **Nicht Erschienen** → Rot (ColorID 11)
     - **Ghost** → Rot (ColorID 11) + " ( Ghost )" im Titel

4. **Undo-Funktion (3 Sekunden)**
   - Nach dem Drag & Drop erscheint unten links ein **"Rückgängig"** Button
   - Klicke darauf innerhalb 3 Sekunden um die Änderung rückgängig zu machen
   - Countdown läuft automatisch

## 🔄 Termin umbuchen (Reschedule)

### Sonderfall: Zurück zu "Pending"

Wenn ein Termin **in die "Pending" Spalte** gezogen wird, öffnet sich automatisch ein **Umbuchungs-Modal**:

1. **Neues Datum wählen**
   - Kalender öffnet sich
   - Wähle ein zukünftiges Datum

2. **Zeitslot auswählen**
   - System zeigt verfügbare Zeitslots für das gewählte Datum
   - Klicke auf einen freien Slot

3. **Berater wählen (optional)**
   - Dropdown zeigt verfügbare Berater für den Slot
   - "Auto-Auswahl" lässt System entscheiden

4. **Notiz hinzufügen (optional)**
   - Z.B. "Kunde hat um Verschiebung gebeten"

5. **"Umbuchen" klicken**
   - ✅ Alter Termin wird auf "Verschoben" (Orange) gesetzt
   - ✅ Neuer Termin wird erstellt mit gleichem `[Booked by:]` Tag
   - ✅ Telefonist sieht beide Termine in seinem My Calendar

## 📱 Tabellen-Ansicht

Alternativ zur Kanban-Ansicht gibt es eine **Tabellenansicht**:

1. Oben rechts auf **"Tabelle"** klicken
2. Zeigt alle Termine in chronologischer Reihenfolge
3. Filter und Sortierung verfügbar
4. Zurück zum Kanban: **"Kanban"** Button

## ⚡ Best Practices

### ✅ DO's:

- **Immer My Calendar für Status-Änderungen nutzen**
- Drag & Drop für schnelle Workflows
- Undo-Funktion nutzen bei Fehlern
- Reschedule-Modal für Umbuchungen verwenden
- Regelmäßig Statistiken checken (Show-Rate beobachten)

### ❌ DON'Ts:

- **NICHT direkt in Google Calendar Farben ändern** → Tag geht verloren!
- **NICHT direkt in Google Calendar Beschreibung bearbeiten** → Tag geht verloren!
- **NICHT manuell " ( Verschoben )" zum Titel hinzufügen** → System macht das automatisch
- Nicht mehrere Termine gleichzeitig ziehen (nicht unterstützt)

## 🔍 Troubleshooting

### Problem: "Keine Buchungen gefunden"

**Ursachen:**
1. Du hast in den letzten 30 Tagen keine Termine gebucht
2. Alte Termine (vor dem Tag-System) werden nicht angezeigt
3. Tags wurden durch manuelle Google Calendar-Änderungen gelöscht

**Lösung:**
- Ab sofort nur noch My Calendar nutzen
- Neue Buchungen erscheinen automatisch

### Problem: Termin erscheint nicht nach Drag & Drop

**Ursachen:**
1. Netzwerkfehler
2. Google Calendar API timeout

**Lösung:**
- Seite neu laden (F5)
- Browser-Cache leeren falls Problem persistiert
- Bei wiederholten Problemen: Admin kontaktieren

### Problem: Falschen Status gesetzt

**Lösung:**
- **Innerhalb 3 Sekunden:** Undo-Button klicken
- **Nach 3 Sekunden:** Termin nochmal zum richtigen Status ziehen

## 🎓 Workflow-Beispiele

### Beispiel 1: Kunde erschienen

```
1. Termin in "Pending" Spalte finden
2. Karte zu "Erschienen" (Grün) ziehen
3. Automatisch: Google Calendar wird grün (ColorID 2)
4. Tag [Booked by: telefonist] bleibt erhalten
5. Telefonist sieht Termin in seiner Statistik
```

### Beispiel 2: Kunde nicht erschienen

```
1. Termin in "Pending" Spalte finden
2. Karte zu "Nicht Erschienen" (Rot) ziehen
3. Automatisch: Google Calendar wird rot (ColorID 11)
4. Bei weiterem No-Show: Zu "Ghost" ziehen
   → Titel bekommt automatisch " ( Ghost )" Suffix
```

### Beispiel 3: Termin umbuchen

```
1. Termin zu "Pending" ziehen
2. Modal öffnet sich automatisch
3. Neues Datum wählen (z.B. nächste Woche)
4. Freien Slot auswählen (z.B. 14:00)
5. Notiz: "Kunde hat um Verschiebung gebeten"
6. "Umbuchen" klicken
7. Alter Termin: Orange (Verschoben)
   Neuer Termin: Grau (Pending) mit gleichem Tag
```

## 📞 Support

Bei Fragen oder Problemen:
- **Admin:** Luke Hoppe
- **GitHub Issues:** https://github.com/Lukes-Git-Beginning/slot-booking-webapp/issues
- **Dokumentation:** `/docs/`

---

**Version:** v3.3.5
**Letzte Aktualisierung:** 2025-10-27
**Status:** ✅ Live auf https://berater.zfa.gmbh
