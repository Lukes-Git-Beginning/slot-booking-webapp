# HubSpot Integration - Executive Summary

## Was wird gebaut?

Automatische Verknüpfung zwischen der Booking-App und HubSpot CRM, damit:
1. **Termin-Outcomes automatisch in HubSpot aktualisiert werden**
2. **Analytics-Dashboard mit echten Daten aus HubSpot gefüllt wird**
3. **Beide Systeme synchron bleiben** (bidirektional)

---

## Kernfunktionen

### 1. Automatische Deal-Updates bei Terminstatus

| Status in App | Aktion in HubSpot |
|---------------|-------------------|
| **Ghost** (1. Mal) | Deal → "Rückholung" + Notiz |
| **Ghost** (2. Mal) | Deal → "Verloren vor T1" + Notiz "2x Ghost" |
| **Nicht erschienen** | Deal → "Verloren vor T1" + Notiz |
| Erschienen/Verschoben | Keine automatische Aktion (manuell) |

**Zeitpunkt:** Automatischer Check am Ende jedes Tages (21:00 Uhr)

### 2. Analytics mit echten Daten

**Aktuell:** Platzhalter-Daten auf `/analytics/`

**Neu:** Echte Werte aus HubSpot:
- Anzahl Leads (T1-Deals)
- Durchschnittlicher Deal-Wert
- Conversion-Raten (T1→T2→Close)
- Lead-Source Attribution

### 3. Bidirektionaler Sync

Wenn jemand in HubSpot manuell einen Deal verschiebt, wird die App automatisch informiert (Webhook).

---

## Technischer Ansatz

**Deal-Identifikation:** Wie findet die App den richtigen HubSpot-Deal?

| Priorität | Methode | Genauigkeit |
|-----------|---------|-------------|
| 1 | E-Mail/Telefon des Kunden | ~99% |
| 2 | T1 Datum + Uhrzeit | ~95% |
| 3 | Kundenname + Opener | ~85% |

---

## Implementierungsphasen

| Phase | Inhalt | Komplexität |
|-------|--------|-------------|
| **Phase 1** | API-Verbindung + Deal-Suche | Mittel |
| **Phase 2** | Outcome-Sync (Ghost/No-Show) | Mittel |
| **Phase 3** | Analytics-Daten aus HubSpot | Niedrig-Mittel |
| **Phase 4** | Webhook für Sync von HubSpot→App | Mittel |
| **Phase 5** | Testing + Deployment | Niedrig |

---

## Voraussetzungen

### Von IT/Entwicklung
- [ ] HubSpot Private App erstellen (für API-Zugang)
- [ ] API-Token generieren
- [ ] Server-Konfiguration anpassen

### Von HubSpot-Admin
- [ ] Webhook-Workflow erstellen (Deal-Stage-Trigger)
- [ ] Sicherstellen dass alle Properties korrekt benannt sind

---

## Benötigte HubSpot-Berechtigungen

| Scope | Verwendung |
|-------|------------|
| `crm.objects.deals.read` | Deals lesen/suchen |
| `crm.objects.deals.write` | Deal-Stage updaten |
| `crm.objects.contacts.read` | Kontakte für Matching |
| `crm.objects.notes.write` | Notizen hinzufügen |

---

## Risiken & Mitigation

| Risiko | Mitigation |
|--------|------------|
| Deal wird nicht gefunden | Fallback-Logik mit mehreren Matching-Methoden |
| HubSpot API nicht erreichbar | Graceful Degradation - Analytics zeigt Fallback-Werte |
| Rate-Limits | Caching + Batch-Verarbeitung |

---

## Erwarteter Nutzen

1. **Weniger manuelle Arbeit:** Keine manuellen Deal-Updates bei Ghost/No-Show
2. **Bessere Datenqualität:** Einheitliche Daten in App und HubSpot
3. **Echte Analytics:** Belastbare Zahlen statt Platzhalter
4. **Berater-Performance:** Conversion-Tracking pro Opener möglich

---

## Nächste Schritte

1. **Entscheidung:** Soll die Integration wie beschrieben umgesetzt werden?
2. **HubSpot API-Zugang:** Private App + Token erstellen
3. **Implementierung starten:** Phase 1 beginnen
