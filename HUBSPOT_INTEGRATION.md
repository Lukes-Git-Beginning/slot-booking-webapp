# HubSpot Integration - Detaillierter Implementierungsplan

## Übersicht

Integration der Slot-Booking-App mit HubSpot CRM für automatische Deal-Updates basierend auf Termin-Outcomes und Ersetzung der Analytics-Platzhalter durch echte HubSpot-Daten.

---

## 1. Ist-Zustand Analyse

### 1.1 HubSpot Account (Professional)

**Bestehende Pipeline-Stages:**
| Stage | Beschreibung |
|-------|--------------|
| T1 | Erstgespräch mit Opener |
| T1,5 | Unterlagentermin mit gleichem Opener |
| T2 | Termin mit Closer inkl. Konzeptvorstellung |
| T2,5 | Follow-up bei Rückfragen nach T2 |
| T3 | Abschlussgespräch (Vertragsunterzeichnung) |
| T3,5 | Nachbesprechung |
| Abgeschlossen | Unterschriebene Kunden + Service-Termine |
| Verloren vor T1/T2/T3 | Verlorene Deals je Stage |
| Verschiebung T1/T2/T3 | Verschobene Termine |
| Rückholung | Wiederansprache nach Ghost |
| Exit | Ausgestiegene Kunden |
| UL-Termin | Unterlagen-Termin |

**Bestehende Kontakt-Properties:**
- `anrede`, `familienstand`, `lebenssituation`, `anzahl_kinder`
- `geburtsdatum`, `geburtstag_partner`
- `jobbezeichnung`, `beruf_partner`
- `mtl_haushaltseinkommen`, `immobilienanzahl`, `schufaeintraege`
- `datum_t1`, `uhrzeit_t1`, `datum_t2`, `uhrzeit_t2`
- `einstellung`, `verhalten`, `top_potential`, `info`
- `leadstatus`, `terminstatus`
- `telefonist`, `opener`, `closer`
- `exitgrund`

**Bestehende Deal-Properties:**
- `deal_beschreibung` (Telefon + E-Mail)
- `datum_t1`, `uhrzeit_t1`
- `datum_ul_termin`
- `opener`

### 1.2 App Analytics - Platzhalter-Daten

**Datei:** `app/services/analytics_service.py`

| Metrik | Aktueller Wert | Zeile | Quelle benötigt |
|--------|----------------|-------|-----------------|
| `total_leads` | 450 (hardcoded) | 153 | HubSpot Deals Count |
| `avg_deal_value` | 1850€ (mock) | 87 | HubSpot Deal Amount |
| Channel Attribution | Demo-Daten | 376-383 | HubSpot Lead Source Property |
| Customer Segments | Demo-Daten | 434-441 | HubSpot Custom Properties |
| `conversion_rate` Fallback | 25.5% | 93 | HubSpot Pipeline Stats |
| `no_show_rate` Fallback | 12.3% | 94 | Berechnet aus Outcomes |

---

## 2. Gewünschter Outcome-Flow (Automatisierung)

### 2.1 Status: Ghost

```
Termin als "Ghost" markiert (EOD Check um 21:00)
    │
    ├─► War Deal schon mal in "Rückholung"?
    │       │
    │       ├─► NEIN: Deal → "Rückholung" + Note "Ghost"
    │       │
    │       └─► JA: Deal → "Verloren vor T1" + Note "2x Ghost"
```

### 2.2 Status: Nicht erschienen

```
Termin als "Nicht erschienen" markiert (EOD Check)
    │
    └─► Deal → "Verloren vor T1" + Note "Nicht erschienen"
```

### 2.3 Status: Erschienen / Verschoben

```
Keine automatische Aktion (manueller Workflow bleibt)
```

---

## 3. Technische Architektur

### 3.1 Neuer Service: `app/services/hubspot_service.py`

```python
class HubSpotService:
    """Service für HubSpot CRM Integration"""

    def __init__(self):
        self.client = None  # HubSpot API Client
        self.access_token = os.getenv('HUBSPOT_ACCESS_TOKEN')

    # === DEAL OPERATIONS ===
    def find_deal_by_contact_email(self, email: str) -> Optional[dict]
    def update_deal_stage(self, deal_id: str, stage: str, note: str = None)
    def was_deal_in_stage(self, deal_id: str, stage: str) -> bool
    def add_deal_note(self, deal_id: str, note: str)

    # === OUTCOME SYNC ===
    def sync_outcome_to_deal(self, booking_data: dict, outcome: str)
    def process_ghost(self, deal_id: str)
    def process_no_show(self, deal_id: str)

    # === ANALYTICS DATA ===
    def get_pipeline_stats(self) -> dict
    def get_total_deals_count(self, stage: str = None) -> int
    def get_avg_deal_value(self) -> float
    def get_lead_source_attribution(self) -> list[dict]
    def get_conversion_rates(self) -> dict
```

### 3.2 Integration in bestehende Services

**`app/services/tracking_system.py`** - Hook nach Outcome-Update:
```python
# In update_booking_outcome() oder EOD-Check:
if outcome == 'ghost':
    hubspot_service.sync_outcome_to_deal(booking, 'ghost')
elif outcome == 'no_show':
    hubspot_service.sync_outcome_to_deal(booking, 'no_show')
```

**`app/services/analytics_service.py`** - Echte Daten statt Platzhalter:
```python
# Zeile 153: Ersetze hardcoded 450
total_leads = hubspot_service.get_total_deals_count(stage='T1') or 450

# Zeile 87: Ersetze hardcoded 1850
avg_deal_value = hubspot_service.get_avg_deal_value() or 1850

# Zeile 376-383: Ersetze Demo-Channel-Daten
channels = hubspot_service.get_lead_source_attribution()
```

### 3.3 Konfiguration

**`.env` Erweiterung:**
```bash
HUBSPOT_ACCESS_TOKEN=pat-xxx-xxx-xxx
HUBSPOT_PORTAL_ID=12345678
HUBSPOT_PIPELINE_ID=default  # oder spezifische Pipeline-ID
```

**`app/core/extensions.py`:**
```python
from app.services.hubspot_service import HubSpotService
hubspot_service = HubSpotService()
```

### 3.4 Webhook-Endpoint: `app/routes/hubspot_webhook.py`

```python
from flask import Blueprint, request, jsonify
import hmac
import hashlib

hubspot_webhook_bp = Blueprint('hubspot_webhook', __name__)

@hubspot_webhook_bp.route('/api/hubspot/webhook', methods=['POST'])
def handle_webhook():
    """Empfängt HubSpot Deal-Stage-Änderungen"""

    # 1. Signature validieren
    if not validate_hubspot_signature(request):
        return jsonify({'error': 'Invalid signature'}), 401

    # 2. Event verarbeiten
    payload = request.json
    for event in payload:
        if event.get('subscriptionType') == 'deal.propertyChange':
            if event.get('propertyName') == 'dealstage':
                deal_id = event.get('objectId')
                new_stage = event.get('propertyValue')
                handle_stage_change(deal_id, new_stage)

    return jsonify({'status': 'ok'}), 200
```

**HubSpot Workflow Setup:**
1. Trigger: Deal Property "dealstage" changed
2. Action: Send Webhook to `https://berater.zfa.gmbh/api/hubspot/webhook`
3. Include: Deal ID, New Stage, Previous Stage

---

## 4. API-Mapping: App → HubSpot

### 4.1 Outcome → Deal Stage Mapping

| App Outcome | HubSpot Stage | HubSpot Internal Name | Bedingung |
|-------------|---------------|----------------------|-----------|
| `ghost` | Rückholung | `rueckholung` | Erste Ghost |
| `ghost` | Verloren vor T1 | `verloren_vor_t1` | War schon in Rückholung |
| `no_show` | Verloren vor T1 | `verloren_vor_t1` | - |
| `appeared` | (keine Änderung) | - | Manuell |
| `rescheduled` | (keine Änderung) | - | Manuell |

### 4.2 HubSpot API Endpoints

| Aktion | Endpoint | Method |
|--------|----------|--------|
| Deal suchen | `/crm/v3/objects/deals/search` | POST |
| Deal updaten | `/crm/v3/objects/deals/{dealId}` | PATCH |
| Note hinzufügen | `/crm/v3/objects/notes` | POST |
| Pipeline Stats | `/crm/v3/pipelines/deals/{pipelineId}` | GET |
| Deal History | `/crm/v3/objects/deals/{dealId}/associations` | GET |

### 4.3 Deal-Kontakt Verknüpfung

**Identifikation:** Mehrschichtige Suche für maximale Trefferquote:

| Priorität | Methode | Datenquelle App | HubSpot Property |
|-----------|---------|-----------------|------------------|
| 1 | E-Mail | `booking.email` | `email` (Contact) |
| 2 | Telefon | `booking.phone` | `phone` (Contact) |
| 3 | T1 Datum + Uhrzeit | `booking.date` + `booking.time` | `datum_t1` + `uhrzeit_t1` |
| 4 | Kundenname | `booking.customer_name` | `firstname` + `lastname` |

```python
# Pseudo-Code für Deal-Suche (Priorisiert)
def find_deal_for_booking(booking):
    # Priorität 1: Via E-Mail (eindeutigster Match)
    if booking.get('email'):
        contact = hubspot.search_contacts(email=booking['email'])
        if contact:
            deals = hubspot.get_associated_deals(contact['id'])
            return find_active_t1_deal(deals)

    # Priorität 2: Via Telefonnummer
    if booking.get('phone'):
        contact = hubspot.search_contacts(phone=booking['phone'])
        if contact:
            deals = hubspot.get_associated_deals(contact['id'])
            return find_active_t1_deal(deals)

    # Priorität 3: Via T1 Datum + Uhrzeit (sehr präzise)
    deals = hubspot.search_deals(
        filters=[
            {'property': 'datum_t1', 'value': booking['date']},      # z.B. 2026-01-21
            {'property': 'uhrzeit_t1', 'value': booking['time']}     # z.B. 18:00
        ]
    )
    if len(deals) == 1:
        return deals[0]  # Eindeutiger Match
    elif len(deals) > 1:
        # Mehrere Deals am gleichen Tag/Zeit → Name-Match
        return match_by_name(deals, booking['customer_name'])

    # Priorität 4: Fallback via Name + Datum
    deals = hubspot.search_deals(
        filters=[
            {'property': 'datum_t1', 'value': booking['date']},
            {'property': 'opener', 'value': booking['consultant']}
        ]
    )
    return match_by_name(deals, booking['customer_name'])
```

**Matching-Qualität:**
- E-Mail/Telefon: ~99% Trefferquote
- Datum + Uhrzeit: ~95% (falls keine überlappenden Termine)
- Name + Datum: ~85% (Fallback bei fehlenden Kontaktdaten)

---

## 5. Analytics-Erweiterung

### 5.1 Neue Metriken aus HubSpot

| Metrik | HubSpot Source | Anzeige in |
|--------|---------------|------------|
| Total Leads (T1) | Deal Count Stage=T1 | Dashboard |
| Conversion T1→T2 | Pipeline Stage Stats | Executive |
| Avg Deal Value | Deal Amount Property | Executive |
| Lead Source | Contact `leadsource` Property | Lead Insights |
| Time-to-Close | Deal Created → Closed Won | Executive |
| Ghost-Quote | Custom Calculation | Team Performance |

### 5.2 Zu ersetzende Platzhalter in `analytics_service.py`

**Zeile 153-167 - Funnel Data:**
```python
# ALT:
total_leads = 450  # Mock

# NEU:
total_leads = hubspot_service.get_total_deals_count(stage='T1')
t1_appeared = hubspot_service.get_deals_with_outcome('appeared', 'T1')
t2_booked = hubspot_service.get_total_deals_count(stage='T2')
```

**Zeile 376-383 - Channel Attribution:**
```python
# ALT: Hardcoded Demo-Daten

# NEU:
return hubspot_service.get_lead_source_attribution()
# Returns: [{'channel': 'Dialfire', 'leads': X, 'conversion_rate': Y}, ...]
```

**Zeile 434-441 - Customer Segments:**
```python
# NEU: Basierend auf HubSpot Contact Properties
return hubspot_service.get_customer_segments()
# Aggregiert nach: familienstand, lebenssituation, einkommen
```

---

## 6. Implementierungs-Phasen

### Phase 1: Grundstruktur
- [ ] `hubspot_service.py` erstellen mit Basis-Client
- [ ] Environment-Variablen konfigurieren
- [ ] API-Verbindung testen
- [ ] Deal-Suche nach E-Mail/Telefon implementieren

### Phase 2: Outcome-Sync
- [ ] `sync_outcome_to_deal()` implementieren
- [ ] Ghost-Logik (Rückholung vs. Verloren)
- [ ] No-Show-Logik
- [ ] Hook in `tracking_system.py` EOD-Check einbauen
- [ ] Note-Erstellung mit Begründung

### Phase 3: Analytics-Integration
- [ ] `get_pipeline_stats()` implementieren
- [ ] `get_avg_deal_value()` implementieren
- [ ] `get_lead_source_attribution()` implementieren
- [ ] Platzhalter in `analytics_service.py` ersetzen
- [ ] Fallback-Logik beibehalten (falls HubSpot unavailable)

### Phase 4: Webhook für Bidirektionalen Sync
- [ ] Webhook-Endpoint erstellen: `POST /api/hubspot/webhook`
- [ ] Signature-Validierung für HubSpot-Requests
- [ ] Handler für Deal-Stage-Änderungen
- [ ] HubSpot Workflow konfigurieren (Trigger bei Stage-Change)
- [ ] Lokale Datenbank-Updates bei externen Änderungen

### Phase 5: Testing & Deployment
- [ ] Unit Tests für HubSpot Service
- [ ] Integration Tests mit Sandbox
- [ ] Server-Deployment mit neuen ENV-Vars
- [ ] Monitoring für API-Rate-Limits
- [ ] Webhook-Test mit HubSpot Webhook Tester

---

## 7. Kritische Dateien

| Datei | Änderung |
|-------|----------|
| `app/services/hubspot_service.py` | **NEU** - Kompletter Service |
| `app/routes/hubspot_webhook.py` | **NEU** - Webhook-Endpoint |
| `app/services/analytics_service.py` | Platzhalter ersetzen |
| `app/services/tracking_system.py` | Hook für Outcome-Sync |
| `app/core/extensions.py` | hubspot_service registrieren |
| `app/__init__.py` | Webhook-Blueprint registrieren |
| `.env` | HUBSPOT_ACCESS_TOKEN + WEBHOOK_SECRET |
| `requirements.txt` | `hubspot-api-client` hinzufügen |

---

## 8. Verifikation

### 8.1 Outcome-Sync testen
1. Testbuchung erstellen mit bekanntem HubSpot-Deal
2. Outcome auf "Ghost" setzen
3. Prüfen: Deal in HubSpot → "Rückholung" + Note
4. Erneut Ghost → Prüfen: Deal → "Verloren vor T1" + Note "2x Ghost"

### 8.2 Analytics testen
1. `/analytics/` aufrufen
2. Prüfen: `total_leads` zeigt echte HubSpot-Zahl (nicht 450)
3. Prüfen: Channel Attribution zeigt echte Lead Sources
4. Prüfen: Avg Deal Value zeigt echten Durchschnitt

### 8.3 Error Handling
1. HubSpot-Token ungültig → Fallback auf Mock-Daten
2. Rate-Limit erreicht → Graceful degradation
3. Deal nicht gefunden → Logging + Skip

---

## 9. Entscheidungen (Geklärt)

1. **Deal-Identifikation:** ✅ Suche via Kontaktdaten
   - Primär: E-Mail/Telefon des Kunden
   - Sekundär: T1 Datum + Uhrzeit
   - Tertiär: Kundenname + Opener
   - Deals werden automatisch via HubSpot-Workflow erstellt

2. **Historische Daten:** ✅ Nein, nur ab Aktivierung
   - Keine rückwirkende Synchronisation
   - Nur neue Outcomes werden gesynct

3. **Bidirektionaler Sync:** ✅ Ja, Webhook einrichten
   - HubSpot informiert App über manuelle Stage-Änderungen
   - Erfordert: Webhook-Endpoint in App + HubSpot Workflow-Trigger

---

## 10. Dependencies

```txt
# requirements.txt Ergänzung
hubspot-api-client>=8.0.0
```

**HubSpot API Scopes benötigt:**
- `crm.objects.deals.read`
- `crm.objects.deals.write`
- `crm.objects.contacts.read`
- `crm.objects.notes.write`
- `crm.schemas.deals.read` (für Pipeline-Info)
