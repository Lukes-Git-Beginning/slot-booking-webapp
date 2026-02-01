# -*- coding: utf-8 -*-
"""
HubSpot CRM Integration Service

Verwaltet die bidirektionale Synchronisation zwischen der Booking-App und HubSpot CRM.
Graceful Degradation: Wenn kein API-Token konfiguriert ist, werden Fallback-Werte verwendet.

Phasen:
  Phase 1: Grundstruktur + Deal-Suche (aktuell: Stub)
  Phase 2: Outcome-Sync (Ghost/No-Show → Deal Stage)
  Phase 3: Analytics-Daten aus HubSpot
  Phase 4: Webhook für bidirektionalen Sync
"""

import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class HubSpotService:
    """Service für HubSpot CRM Integration.

    Alle Methoden sind so implementiert, dass sie ohne API-Zugang
    Fallback-Werte zurückgeben (graceful degradation).
    """

    def __init__(self):
        from app.config.base import hubspot_config
        self.config = hubspot_config
        self.client = None
        self._initialized = False

    def init_app(self, app=None):
        """Initialisiere den HubSpot Client wenn Token vorhanden."""
        if not self.config.HUBSPOT_ENABLED:
            logger.info("HubSpot integration disabled (no HUBSPOT_ACCESS_TOKEN configured)")
            return

        try:
            from hubspot import HubSpot
            self.client = HubSpot(access_token=self.config.HUBSPOT_ACCESS_TOKEN)
            self._initialized = True
            logger.info("HubSpot client initialized successfully")
        except ImportError:
            logger.warning(
                "hubspot-api-client not installed. "
                "Install with: pip install hubspot-api-client>=8.0.0"
            )
        except Exception as e:
            logger.error(f"Failed to initialize HubSpot client: {e}")

    @property
    def is_available(self) -> bool:
        """Prüfe ob HubSpot-Integration verfügbar ist."""
        return self._initialized and self.client is not None

    # ================================================================
    # DEAL OPERATIONS
    # ================================================================

    def find_deal_by_contact_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Suche einen HubSpot-Deal über die E-Mail des Kontakts.

        Priorität 1 der Deal-Identifikation (~99% Trefferquote).

        Args:
            email: E-Mail-Adresse des Kontakts

        Returns:
            Deal-Dict oder None wenn nicht gefunden
        """
        if not self.is_available:
            logger.debug("HubSpot not available, skipping deal search by email")
            return None

        # TODO: Implementierung mit echtem API-Call (Phase 1)
        # 1. Contact über Email suchen
        # 2. Assoziierte Deals des Contacts laden
        # 3. Aktiven T1-Deal zurückgeben
        logger.info(f"HubSpot deal search by email: {email} (stub - not implemented)")
        return None

    def find_deal_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Suche einen HubSpot-Deal über die Telefonnummer des Kontakts.

        Priorität 2 der Deal-Identifikation (~95% Trefferquote).

        Args:
            phone: Telefonnummer des Kontakts

        Returns:
            Deal-Dict oder None wenn nicht gefunden
        """
        if not self.is_available:
            return None

        # TODO: Implementierung mit echtem API-Call (Phase 1)
        logger.info(f"HubSpot deal search by phone: {phone} (stub)")
        return None

    def find_deal_by_date_time(self, date: str, time: str) -> Optional[Dict[str, Any]]:
        """Suche einen HubSpot-Deal über T1 Datum + Uhrzeit.

        Priorität 3 der Deal-Identifikation (~95% Trefferquote).

        Args:
            date: Datum im Format YYYY-MM-DD
            time: Uhrzeit im Format HH:MM

        Returns:
            Deal-Dict oder None wenn nicht gefunden
        """
        if not self.is_available:
            return None

        # TODO: Implementierung mit echtem API-Call (Phase 1)
        # Suche über Deal-Properties: datum_t1 + uhrzeit_t1
        logger.info(f"HubSpot deal search by date/time: {date} {time} (stub)")
        return None

    def find_deal_for_booking(self, booking_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mehrstufige Deal-Suche mit Fallback-Kette.

        Versucht nacheinander: Email → Telefon → Datum+Zeit → Name

        Args:
            booking_data: Dict mit customer_name, email, phone, date, time, consultant

        Returns:
            Deal-Dict oder None
        """
        if not self.is_available:
            return None

        # Priorität 1: Email
        email = booking_data.get('email')
        if email:
            deal = self.find_deal_by_contact_email(email)
            if deal:
                return deal

        # Priorität 2: Telefon
        phone = booking_data.get('phone')
        if phone:
            deal = self.find_deal_by_phone(phone)
            if deal:
                return deal

        # Priorität 3: Datum + Uhrzeit
        date = booking_data.get('date')
        time = booking_data.get('time')
        if date and time:
            deal = self.find_deal_by_date_time(date, time)
            if deal:
                return deal

        logger.warning(
            f"No HubSpot deal found for booking: "
            f"{booking_data.get('customer_name', 'unknown')}"
        )
        return None

    def update_deal_stage(self, deal_id: str, stage: str, note: str = None) -> bool:
        """Aktualisiere die Pipeline-Stage eines Deals.

        Args:
            deal_id: HubSpot Deal ID
            stage: Internal Name der Ziel-Stage (z.B. 'rueckholung')
            note: Optionale Notiz zum Hinzufügen

        Returns:
            True bei Erfolg, False bei Fehler
        """
        if not self.is_available:
            logger.debug(f"HubSpot not available, skipping stage update for deal {deal_id}")
            return False

        # TODO: Implementierung mit echtem API-Call (Phase 2)
        # PATCH /crm/v3/objects/deals/{dealId}
        # Body: {"properties": {"dealstage": stage}}
        logger.info(f"HubSpot deal stage update: {deal_id} → {stage} (stub)")

        if note:
            self.add_deal_note(deal_id, note)

        return False

    def was_deal_in_stage(self, deal_id: str, stage: str) -> bool:
        """Prüfe ob ein Deal jemals in einer bestimmten Stage war.

        Wichtig für Ghost-Logik: War Deal schon in 'Rückholung'?

        Args:
            deal_id: HubSpot Deal ID
            stage: Internal Name der Stage

        Returns:
            True wenn Deal jemals in dieser Stage war
        """
        if not self.is_available:
            return False

        # TODO: Implementierung (Phase 2)
        # HubSpot API bietet keine direkte Stage-History
        # Lösung: Lokale Tracking-Tabelle oder Deal-Notes parsen
        logger.info(f"HubSpot stage history check: {deal_id} in {stage}? (stub)")
        return False

    def add_deal_note(self, deal_id: str, note: str) -> bool:
        """Füge eine Notiz zu einem Deal hinzu.

        Args:
            deal_id: HubSpot Deal ID
            note: Notiz-Text

        Returns:
            True bei Erfolg
        """
        if not self.is_available:
            return False

        # TODO: Implementierung (Phase 2)
        # POST /crm/v3/objects/notes
        # + Association mit Deal
        logger.info(f"HubSpot add note to deal {deal_id}: {note[:50]}... (stub)")
        return False

    # ================================================================
    # OUTCOME SYNC
    # ================================================================

    def sync_outcome_to_deal(self, booking_data: Dict[str, Any], outcome: str) -> bool:
        """Synchronisiere ein Termin-Outcome zu HubSpot.

        Hauptmethode für die Outcome-Synchronisation.

        Args:
            booking_data: Buchungsdaten (customer_name, email, phone, date, time)
            outcome: Outcome-Typ ('ghost', 'no_show', 'appeared', 'rescheduled')

        Returns:
            True bei erfolgreicher Synchronisation
        """
        if not self.is_available:
            logger.debug(f"HubSpot not available, skipping outcome sync: {outcome}")
            return False

        deal = self.find_deal_for_booking(booking_data)
        if not deal:
            logger.warning(
                f"Cannot sync outcome '{outcome}' - no HubSpot deal found for "
                f"{booking_data.get('customer_name', 'unknown')}"
            )
            return False

        deal_id = deal.get('id')

        if outcome == 'ghost':
            return self.process_ghost(deal_id)
        elif outcome == 'no_show':
            return self.process_no_show(deal_id)
        else:
            # 'appeared' und 'rescheduled' erfordern keine automatische Aktion
            logger.debug(f"No automatic HubSpot action for outcome: {outcome}")
            return True

    def process_ghost(self, deal_id: str) -> bool:
        """Verarbeite Ghost-Outcome.

        Logik:
        - 1. Ghost → Deal → 'Rückholung' + Note 'Ghost'
        - 2. Ghost (war schon in Rückholung) → Deal → 'Verloren vor T1' + Note '2x Ghost'

        Args:
            deal_id: HubSpot Deal ID

        Returns:
            True bei Erfolg
        """
        if not self.is_available:
            return False

        was_in_rueckholung = self.was_deal_in_stage(deal_id, "rueckholung")

        if was_in_rueckholung:
            # 2. Ghost → Verloren
            stage = self.config.STAGE_MAPPING["ghost_repeat"]
            return self.update_deal_stage(deal_id, stage, note="2x Ghost - automatisch verschoben")
        else:
            # 1. Ghost → Rückholung
            stage = self.config.STAGE_MAPPING["ghost_first"]
            return self.update_deal_stage(deal_id, stage, note="Ghost - automatisch zur Rückholung")

    def process_no_show(self, deal_id: str) -> bool:
        """Verarbeite No-Show-Outcome.

        Logik: Deal → 'Verloren vor T1' + Note 'Nicht erschienen'

        Args:
            deal_id: HubSpot Deal ID

        Returns:
            True bei Erfolg
        """
        if not self.is_available:
            return False

        stage = self.config.STAGE_MAPPING["no_show"]
        return self.update_deal_stage(
            deal_id, stage, note="Nicht erschienen - automatisch verschoben"
        )

    # ================================================================
    # ANALYTICS DATA
    # ================================================================

    def get_pipeline_stats(self) -> Optional[Dict[str, Any]]:
        """Hole Pipeline-Statistiken aus HubSpot.

        Returns:
            Dict mit Stage-Counts oder None
        """
        if not self.is_available:
            return None

        # TODO: Implementierung (Phase 3)
        # GET /crm/v3/pipelines/deals/{pipelineId}
        logger.debug("HubSpot pipeline stats requested (stub)")
        return None

    def get_total_deals_count(self, stage: str = None) -> Optional[int]:
        """Hole Anzahl der Deals (optional gefiltert nach Stage).

        Args:
            stage: Optional - nur Deals in dieser Stage zählen

        Returns:
            Anzahl Deals oder None (Fallback auf Mock-Daten)
        """
        if not self.is_available:
            return None

        # TODO: Implementierung (Phase 3)
        # POST /crm/v3/objects/deals/search mit Stage-Filter
        logger.debug(f"HubSpot deals count requested, stage={stage} (stub)")
        return None

    def get_avg_deal_value(self) -> Optional[float]:
        """Hole durchschnittlichen Deal-Wert.

        Returns:
            Durchschnittlicher Deal-Wert in EUR oder None
        """
        if not self.is_available:
            return None

        # TODO: Implementierung (Phase 3)
        logger.debug("HubSpot avg deal value requested (stub)")
        return None

    def get_lead_source_attribution(self) -> Optional[List[Dict[str, Any]]]:
        """Hole Lead-Source Attribution aus HubSpot.

        Returns:
            Liste von Dicts mit channel, leads, conversion_rate oder None
        """
        if not self.is_available:
            return None

        # TODO: Implementierung (Phase 3)
        # Aggregation über Contact Property 'leadsource'
        logger.debug("HubSpot lead source attribution requested (stub)")
        return None

    def get_conversion_rates(self) -> Optional[Dict[str, float]]:
        """Hole Conversion-Rates aus der Pipeline.

        Returns:
            Dict mit t1_to_t2, t2_to_close, etc. oder None
        """
        if not self.is_available:
            return None

        # TODO: Implementierung (Phase 3)
        logger.debug("HubSpot conversion rates requested (stub)")
        return None

    def get_customer_segments(self) -> Optional[List[Dict[str, Any]]]:
        """Hole Kundensegmente basierend auf HubSpot Contact Properties.

        Aggregiert nach: familienstand, lebenssituation, einkommen

        Returns:
            Liste von Segment-Dicts oder None
        """
        if not self.is_available:
            return None

        # TODO: Implementierung (Phase 3)
        logger.debug("HubSpot customer segments requested (stub)")
        return None


# Singleton-Instanz
hubspot_service = HubSpotService()
