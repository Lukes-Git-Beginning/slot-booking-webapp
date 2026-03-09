# -*- coding: utf-8 -*-
"""
HubSpot CRM Integration Service

Verwaltet die bidirektionale Synchronisation zwischen der Booking-App und HubSpot CRM.
Graceful Degradation: Wenn kein API-Token konfiguriert ist, werden Fallback-Werte verwendet.

Phasen:
  Phase 1: Grundstruktur + Deal-Suche (implementiert)
  Phase 2: Outcome-Sync (Ghost/No-Show → Deal Stage)
  Phase 3: Analytics-Daten aus HubSpot
  Phase 4: Webhook für bidirektionalen Sync
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Properties to fetch from HubSpot deals
DEAL_PROPERTIES = [
    'dealname', 'dealstage', 'pipeline', 'amount',
    'datum_t1_neu', 'uhrzeit_t1', 'telefonist_neu',
    'closedate', 'createdate',
]


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
        self._cache: Dict[str, Any] = {}
        self._cache_ts: Dict[str, float] = {}

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
    # INTERNAL HELPERS
    # ================================================================

    def _resolve_telefonist_name(self, raw_value: str) -> str:
        """Resolve telefonist_neu value (phone number or ID) to a human-readable name.

        Uses HubSpot Owners API first, then contacts search as fallback.
        Results are cached for 1 hour.
        """
        if not raw_value or raw_value == 'Unbekannt':
            return raw_value or 'Unbekannt'

        # If value already contains letters, it's likely a name — use directly
        if any(c.isalpha() for c in raw_value):
            logger.debug(f"Telefonist value '{raw_value}' contains letters, using as name directly")
            return raw_value

        # Check cache (only for numeric IDs that need API lookup)
        cache_key = f'telefonist_name_{raw_value}'
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        name = raw_value  # Default fallback: show raw value

        try:
            # Try Owners API (if telefonist_neu is an owner ID)
            try:
                owner = self.client.crm.owners.owners_api.get_by_id(
                    owner_id=raw_value
                )
                if owner:
                    first = owner.first_name or ''
                    last = owner.last_name or ''
                    resolved = f"{first} {last}".strip()
                    if resolved:
                        name = resolved
                        self._cache_set(cache_key, name)
                        return name
            except Exception:
                pass

            # Try contacts search by phone number
            results = self._search_contacts('phone', raw_value)
            if results:
                props = results[0].properties or {}
                first = props.get('firstname', '')
                last = props.get('lastname', '')
                resolved = f"{first} {last}".strip()
                if resolved:
                    name = resolved

        except Exception as e:
            logger.debug(f"Could not resolve telefonist name for '{raw_value}': {e}")

        self._cache_set(cache_key, name)
        return name

    def _normalize_deal(self, deal) -> Dict[str, Any]:
        """Convert a HubSpot SimplePublicObject to a standardized dict."""
        props = deal.properties or {}
        return {
            'id': deal.id,
            'dealname': props.get('dealname', ''),
            'dealstage': props.get('dealstage', ''),
            'pipeline': props.get('pipeline', ''),
            'amount': props.get('amount'),
            'datum_t1': props.get('datum_t1_neu'),
            'uhrzeit_t1': props.get('uhrzeit_t1'),
            'telefonist': props.get('telefonist_neu'),
            'createdate': props.get('createdate'),
            'closedate': props.get('closedate'),
        }

    def _search_contacts(self, property_name: str, value: str) -> List:
        """Search HubSpot contacts by a single property filter.

        Returns list of SimplePublicObject results.
        """
        from hubspot.crm.contacts import PublicObjectSearchRequest

        search_request = PublicObjectSearchRequest(
            filter_groups=[{
                "filters": [{
                    "propertyName": property_name,
                    "operator": "EQ",
                    "value": value,
                }]
            }],
            properties=["email", "firstname", "lastname", "phone"],
        )
        response = self.client.crm.contacts.search_api.do_search(
            public_object_search_request=search_request
        )
        return response.results or []

    def _get_associated_deals(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get all deals associated with a contact, return as normalized dicts."""
        # Get association IDs
        assoc_response = self.client.crm.associations.v4.basic_api.get_page(
            object_type="contacts",
            object_id=contact_id,
            to_object_type="deals",
        )

        deal_ids = []
        for assoc in (assoc_response.results or []):
            deal_ids.append(assoc.to_object_id)

        if not deal_ids:
            return []

        # Fetch full deal objects
        deals = []
        for deal_id in deal_ids:
            try:
                deal = self.client.crm.deals.basic_api.get_by_id(
                    deal_id=deal_id,
                    properties=DEAL_PROPERTIES,
                )
                deals.append(self._normalize_deal(deal))
            except Exception as e:
                logger.warning(f"Could not fetch deal {deal_id}: {e}")

        return deals

    def _find_deals_for_contact(self, property_name: str, value: str) -> Optional[Dict[str, Any]]:
        """Search a contact by property, return the first associated deal (or None)."""
        contacts = self._search_contacts(property_name, value)
        if not contacts:
            return None

        # Check associated deals for each matching contact
        for contact in contacts:
            deals = self._get_associated_deals(contact.id)
            if deals:
                # Prefer deals in the configured pipeline
                pipeline_id = self.config.HUBSPOT_PIPELINE_ID
                pipeline_deals = [d for d in deals if d.get('pipeline') == pipeline_id]
                if pipeline_deals:
                    return pipeline_deals[0]
                return deals[0]

        return None

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

        try:
            deal = self._find_deals_for_contact("email", email)
            if deal:
                logger.info(f"HubSpot deal found by email {email}: {deal['id']}")
            else:
                logger.debug(f"No HubSpot deal found for email: {email}")
            return deal
        except Exception as e:
            logger.error(f"HubSpot deal search by email failed: {e}")
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

        try:
            deal = self._find_deals_for_contact("phone", phone)
            if deal:
                logger.info(f"HubSpot deal found by phone {phone}: {deal['id']}")
            else:
                logger.debug(f"No HubSpot deal found for phone: {phone}")
            return deal
        except Exception as e:
            logger.error(f"HubSpot deal search by phone failed: {e}")
            return None

    def find_deal_by_date_time(self, date: str, time: str) -> Optional[Dict[str, Any]]:
        """Suche einen HubSpot-Deal über T1 Datum + Uhrzeit.

        Priorität 3 der Deal-Identifikation (~95% Trefferquote).
        Sucht über Deal-Properties: datum_t1_neu + uhrzeit_t1

        Args:
            date: Datum im Format YYYY-MM-DD
            time: Uhrzeit im Format HH:MM

        Returns:
            Deal-Dict oder None wenn nicht gefunden
        """
        if not self.is_available:
            return None

        try:
            from hubspot.crm.deals import PublicObjectSearchRequest

            # HubSpot date properties use midnight UTC epoch milliseconds
            dt = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            date_epoch_ms = str(int(dt.timestamp() * 1000))

            search_request = PublicObjectSearchRequest(
                filter_groups=[{
                    "filters": [
                        {
                            "propertyName": "datum_t1_neu",
                            "operator": "EQ",
                            "value": date_epoch_ms,
                        },
                        {
                            "propertyName": "uhrzeit_t1",
                            "operator": "EQ",
                            "value": time,
                        },
                    ]
                }],
                properties=DEAL_PROPERTIES,
            )

            response = self.client.crm.deals.search_api.do_search(
                public_object_search_request=search_request
            )

            if response.results:
                deal = self._normalize_deal(response.results[0])
                logger.info(f"HubSpot deal found by date/time {date} {time}: {deal['id']}")
                return deal

            logger.debug(f"No HubSpot deal found for date/time: {date} {time}")
            return None

        except Exception as e:
            logger.error(f"HubSpot deal search by date/time failed: {e}")
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
            stage: Stage-ID (numerisch) oder Key aus STAGE_MAPPING
            note: Optionale Notiz zum Hinzufügen

        Returns:
            True bei Erfolg, False bei Fehler
        """
        if not self.is_available:
            logger.debug(f"HubSpot not available, skipping stage update for deal {deal_id}")
            return False

        try:
            from hubspot.crm.deals import SimplePublicObjectInput

            # Resolve stage name to ID if needed
            stage_id = self.config.STAGE_MAPPING.get(stage, stage)

            self.client.crm.deals.basic_api.update(
                deal_id=deal_id,
                simple_public_object_input=SimplePublicObjectInput(
                    properties={"dealstage": stage_id}
                ),
            )
            logger.info(f"HubSpot deal {deal_id} stage updated to {stage_id}")

            if note:
                self.add_deal_note(deal_id, note)

            return True

        except Exception as e:
            logger.error(f"HubSpot stage update failed for deal {deal_id}: {e}")
            return False

    def was_deal_in_stage(self, deal_id: str, stage: str) -> bool:
        """Prüfe ob ein Deal jemals in einer bestimmten Stage war.

        Nutzt HubSpot's hs_v2_date_entered_{stage_id} Properties.
        Wenn dieses Property einen Wert hat, war der Deal in der Stage.

        Args:
            deal_id: HubSpot Deal ID
            stage: Stage-Key (z.B. 'rueckholung') oder numerische Stage-ID

        Returns:
            True wenn Deal jemals in dieser Stage war
        """
        if not self.is_available:
            return False

        try:
            stage_id = self.config.STAGE_MAPPING.get(stage, stage)
            history_prop = f"hs_v2_date_entered_{stage_id}"

            deal = self.client.crm.deals.basic_api.get_by_id(
                deal_id=deal_id,
                properties=[history_prop],
            )

            value = (deal.properties or {}).get(history_prop)
            was_in = bool(value and value.strip())
            logger.info(f"HubSpot stage history: deal {deal_id} in {stage} ({stage_id})? {was_in}")
            return was_in

        except Exception as e:
            logger.error(f"HubSpot stage history check failed for deal {deal_id}: {e}")
            return False

    def add_deal_note(self, deal_id: str, note: str) -> bool:
        """Füge eine Notiz zu einem Deal hinzu.

        Erstellt ein Note-Objekt und assoziiert es mit dem Deal.

        Args:
            deal_id: HubSpot Deal ID
            note: Notiz-Text

        Returns:
            True bei Erfolg
        """
        if not self.is_available:
            return False

        try:
            from hubspot.crm.objects.notes import SimplePublicObjectInput as NoteInput

            now_ms = str(int(datetime.now(timezone.utc).timestamp() * 1000))

            note_obj = self.client.crm.objects.notes.basic_api.create(
                simple_public_object_input=NoteInput(
                    properties={
                        "hs_timestamp": now_ms,
                        "hs_note_body": note,
                    }
                )
            )

            # Associate note with deal (type 214 = note_to_deal)
            self.client.crm.associations.v4.basic_api.create(
                object_type="notes",
                object_id=note_obj.id,
                to_object_type="deals",
                to_object_id=deal_id,
                association_spec=[{
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": 214,
                }],
            )

            logger.info(f"HubSpot note {note_obj.id} added to deal {deal_id}")
            return True

        except Exception as e:
            logger.error(f"HubSpot add note failed for deal {deal_id}: {e}")
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
    # CACHE HELPERS
    # ================================================================

    def _cache_get(self, key: str) -> Optional[Any]:
        """Return cached value if still valid, else None."""
        ts = self._cache_ts.get(key)
        if ts and (time.time() - ts) < self.config.HUBSPOT_CACHE_TTL:
            return self._cache.get(key)
        return None

    def _cache_set(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache_ts[key] = time.time()

    def _search_deals(self, filters: List[Dict] = None, properties: List[str] = None,
                      limit: int = 100) -> List:
        """Search deals with optional filters. Returns list of raw result objects.

        Handles pagination automatically for larger result sets.
        """
        from hubspot.crm.deals import PublicObjectSearchRequest

        all_results = []
        after = None
        props = properties or DEAL_PROPERTIES

        while True:
            request_kwargs = {
                'properties': props,
                'limit': limit,
            }
            if filters:
                request_kwargs['filter_groups'] = [{"filters": filters}]
            if after:
                request_kwargs['after'] = after

            search_request = PublicObjectSearchRequest(**request_kwargs)
            response = self.client.crm.deals.search_api.do_search(
                public_object_search_request=search_request
            )

            all_results.extend(response.results or [])

            # HubSpot pagination
            if response.paging and response.paging.next and response.paging.next.after:
                after = response.paging.next.after
            else:
                break

        return all_results

    # ================================================================
    # ANALYTICS DATA
    # ================================================================

    def get_pipeline_stats(self) -> Optional[Dict[str, Any]]:
        """Hole Pipeline-Statistiken aus HubSpot.

        Returns:
            Dict mit {stage_label: count} oder None
        """
        if not self.is_available:
            return None

        cached = self._cache_get('pipeline_stats')
        if cached is not None:
            return cached

        try:
            # Get pipeline stages
            pipeline_response = self.client.crm.pipelines.pipeline_stages_api.get_all(
                object_type="deals",
                pipeline_id=self.config.HUBSPOT_PIPELINE_ID,
            )

            stats = {}
            for stage in (pipeline_response.results or []):
                stage_id = stage.id
                label = stage.label

                # Count deals in this stage
                count_filters = [
                    {"propertyName": "dealstage", "operator": "EQ", "value": stage_id},
                    {"propertyName": "pipeline", "operator": "EQ", "value": self.config.HUBSPOT_PIPELINE_ID},
                ]
                from hubspot.crm.deals import PublicObjectSearchRequest
                req = PublicObjectSearchRequest(
                    filter_groups=[{"filters": count_filters}],
                    limit=1,
                    properties=["dealstage"],
                )
                resp = self.client.crm.deals.search_api.do_search(
                    public_object_search_request=req
                )
                stats[label] = resp.total

            self._cache_set('pipeline_stats', stats)
            logger.info(f"HubSpot pipeline stats loaded: {len(stats)} stages")
            return stats

        except Exception as e:
            logger.error(f"HubSpot pipeline stats failed: {e}")
            return None

    def get_total_deals_count(self, stage: str = None) -> Optional[int]:
        """Hole Anzahl der Deals (optional gefiltert nach Stage).

        Args:
            stage: Optional - Stage-Key oder Stage-ID

        Returns:
            Anzahl Deals oder None
        """
        if not self.is_available:
            return None

        cache_key = f'deals_count_{stage or "all"}'
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            from hubspot.crm.deals import PublicObjectSearchRequest

            filters = [
                {"propertyName": "pipeline", "operator": "EQ",
                 "value": self.config.HUBSPOT_PIPELINE_ID},
            ]
            if stage:
                stage_id = self.config.STAGE_MAPPING.get(stage, stage)
                filters.append(
                    {"propertyName": "dealstage", "operator": "EQ", "value": stage_id}
                )

            req = PublicObjectSearchRequest(
                filter_groups=[{"filters": filters}],
                limit=1,
                properties=["dealstage"],
            )
            resp = self.client.crm.deals.search_api.do_search(
                public_object_search_request=req
            )
            count = resp.total
            self._cache_set(cache_key, count)
            logger.info(f"HubSpot deals count (stage={stage}): {count}")
            return count

        except Exception as e:
            logger.error(f"HubSpot deals count failed: {e}")
            return None

    def get_avg_deal_value(self) -> Optional[float]:
        """Hole durchschnittlichen Deal-Wert.

        Returns:
            Durchschnittlicher Deal-Wert in EUR oder None
        """
        if not self.is_available:
            return None

        cached = self._cache_get('avg_deal_value')
        if cached is not None:
            return cached

        try:
            filters = [
                {"propertyName": "pipeline", "operator": "EQ",
                 "value": self.config.HUBSPOT_PIPELINE_ID},
                {"propertyName": "amount", "operator": "GT", "value": "0"},
            ]
            results = self._search_deals(filters=filters, properties=['amount'])

            if not results:
                logger.debug("No deals with amount found")
                return None

            total = 0.0
            count = 0
            for deal in results:
                amount_str = (deal.properties or {}).get('amount')
                if amount_str:
                    try:
                        amount = float(amount_str)
                        if amount > 0:
                            total += amount
                            count += 1
                    except (ValueError, TypeError):
                        continue

            if count == 0:
                return None

            avg = round(total / count, 2)
            self._cache_set('avg_deal_value', avg)
            logger.info(f"HubSpot avg deal value: {avg} EUR ({count} deals)")
            return avg

        except Exception as e:
            logger.error(f"HubSpot avg deal value failed: {e}")
            return None

    def get_lead_source_attribution(self) -> Optional[List[Dict[str, Any]]]:
        """Hole Lead-Source Attribution aus HubSpot.

        Groups contacts by hs_analytics_source, counts associated deals.

        Returns:
            Liste von Dicts mit channel, leads, conversion_rate oder None
        """
        if not self.is_available:
            return None

        cached = self._cache_get('lead_source_attribution')
        if cached is not None:
            return cached

        try:
            from hubspot.crm.contacts import PublicObjectSearchRequest as ContactSearch

            # Known HubSpot analytics sources
            sources = [
                'PAID_SEARCH', 'PAID_SOCIAL', 'ORGANIC_SEARCH',
                'REFERRALS', 'DIRECT_TRAFFIC', 'OTHER_CAMPAIGNS',
                'SOCIAL_MEDIA', 'EMAIL_MARKETING', 'OFFLINE',
            ]

            attribution = []
            for source in sources:
                req = ContactSearch(
                    filter_groups=[{"filters": [{
                        "propertyName": "hs_analytics_source",
                        "operator": "EQ",
                        "value": source,
                    }]}],
                    limit=1,
                    properties=["hs_analytics_source"],
                )
                resp = self.client.crm.contacts.search_api.do_search(
                    public_object_search_request=req
                )
                lead_count = resp.total
                if lead_count == 0:
                    continue

                # Estimate conversion: sample up to 10 contacts, check for deals
                sample_req = ContactSearch(
                    filter_groups=[{"filters": [{
                        "propertyName": "hs_analytics_source",
                        "operator": "EQ",
                        "value": source,
                    }]}],
                    limit=10,
                    properties=["hs_analytics_source"],
                )
                sample_resp = self.client.crm.contacts.search_api.do_search(
                    public_object_search_request=sample_req
                )

                contacts_with_deals = 0
                sample_size = len(sample_resp.results or [])
                for contact in (sample_resp.results or []):
                    try:
                        assocs = self.client.crm.associations.v4.basic_api.get_page(
                            object_type="contacts",
                            object_id=contact.id,
                            to_object_type="deals",
                        )
                        if assocs.results:
                            contacts_with_deals += 1
                    except Exception:
                        continue

                conversion = round((contacts_with_deals / sample_size * 100), 1) if sample_size > 0 else 0

                # Readable channel name
                channel_name = source.replace('_', ' ').title()
                attribution.append({
                    'channel': channel_name,
                    'leads': lead_count,
                    'conversion_rate': conversion,
                    'cost_per_lead': 0,
                })

            attribution.sort(key=lambda x: x['leads'], reverse=True)
            self._cache_set('lead_source_attribution', attribution)
            logger.info(f"HubSpot lead attribution loaded: {len(attribution)} channels")
            return attribution if attribution else None

        except Exception as e:
            logger.error(f"HubSpot lead source attribution failed: {e}")
            return None

    def get_conversion_rates(self) -> Optional[Dict[str, float]]:
        """Hole Conversion-Rates aus der Pipeline.

        Uses hs_v2_date_entered_{stage_id} properties to determine
        how many deals passed through each stage.

        Returns:
            Dict mit stage transition rates oder None
        """
        if not self.is_available:
            return None

        cached = self._cache_get('conversion_rates')
        if cached is not None:
            return cached

        try:
            # Get all pipeline stages in order
            pipeline_response = self.client.crm.pipelines.pipeline_stages_api.get_all(
                object_type="deals",
                pipeline_id=self.config.HUBSPOT_PIPELINE_ID,
            )
            stages = sorted(pipeline_response.results or [], key=lambda s: s.display_order)

            if len(stages) < 2:
                return None

            # For each stage, count deals that entered it
            history_props = [f"hs_v2_date_entered_{s.id}" for s in stages]

            # Search deals in this pipeline with history properties
            from hubspot.crm.deals import PublicObjectSearchRequest
            req = PublicObjectSearchRequest(
                filter_groups=[{"filters": [{
                    "propertyName": "pipeline", "operator": "EQ",
                    "value": self.config.HUBSPOT_PIPELINE_ID,
                }]}],
                limit=100,
                properties=history_props,
            )
            resp = self.client.crm.deals.search_api.do_search(
                public_object_search_request=req
            )

            # Count deals per stage entry
            stage_counts = {}
            for stage in stages:
                prop = f"hs_v2_date_entered_{stage.id}"
                count = 0
                for deal in (resp.results or []):
                    val = (deal.properties or {}).get(prop)
                    if val and val.strip():
                        count += 1
                stage_counts[stage.label] = count

            # Compute transition rates
            rates = {}
            stage_labels = [s.label for s in stages]
            for i in range(1, len(stage_labels)):
                prev_count = stage_counts.get(stage_labels[i - 1], 0)
                curr_count = stage_counts.get(stage_labels[i], 0)
                key = f"{stage_labels[i-1]}_to_{stage_labels[i]}".lower().replace(' ', '_')
                rates[key] = round((curr_count / prev_count * 100), 1) if prev_count > 0 else 0

            self._cache_set('conversion_rates', rates)
            logger.info(f"HubSpot conversion rates loaded: {rates}")
            return rates

        except Exception as e:
            logger.error(f"HubSpot conversion rates failed: {e}")
            return None

    def get_pipeline_stages(self) -> Optional[List[Dict[str, Any]]]:
        """Hole Pipeline-Stages mit IDs und Labels.

        Returns:
            Liste von {id, label, display_order} oder None
        """
        if not self.is_available:
            return None

        cached = self._cache_get('pipeline_stages')
        if cached is not None:
            return cached

        try:
            pipeline_response = self.client.crm.pipelines.pipeline_stages_api.get_all(
                object_type="deals",
                pipeline_id=self.config.HUBSPOT_PIPELINE_ID,
            )
            stages = []
            for stage in sorted(pipeline_response.results or [], key=lambda s: s.display_order):
                stages.append({
                    'id': stage.id,
                    'label': stage.label,
                    'display_order': stage.display_order,
                })

            # Use longer TTL (60 min) for stages since they rarely change
            self._cache['pipeline_stages'] = stages
            self._cache_ts['pipeline_stages'] = time.time()
            logger.info(f"HubSpot pipeline stages loaded: {len(stages)} stages")
            return stages

        except Exception as e:
            logger.error(f"HubSpot pipeline stages failed: {e}")
            return None

    def get_stage_label(self, stage_id: str) -> str:
        """Get the label for a pipeline stage ID."""
        if not stage_id:
            return ''
        stages = self.get_pipeline_stages()
        if stages:
            for stage in stages:
                if stage['id'] == stage_id:
                    return stage['label']
        # Return raw stage_id as fallback so something is visible
        return stage_id

    def get_campaign_stats(self, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """Hole Kampagnen-Performance-Statistiken.

        Gruppiert Deals nach Kampagnen-Property, berechnet Leads, Deals, Conversions.

        Args:
            days: Zeitraum in Tagen

        Returns:
            Liste von Kampagnen-Dicts oder None
        """
        if not self.is_available:
            return None

        cache_key = f'campaign_stats_{days}'
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            from hubspot.crm.deals import PublicObjectSearchRequest

            # Calculate date filter
            cutoff = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=days)
            cutoff_ms = str(int(cutoff.timestamp() * 1000))

            # Fetch deals created in the time range with campaign-related properties
            campaign_props = DEAL_PROPERTIES + [
                'hs_analytics_source', 'hs_analytics_source_data_1',
                'hs_analytics_source_data_2',
            ]

            filters = [
                {"propertyName": "pipeline", "operator": "EQ",
                 "value": self.config.HUBSPOT_PIPELINE_ID},
                {"propertyName": "createdate", "operator": "GTE",
                 "value": cutoff_ms},
            ]

            results = self._search_deals(filters=filters, properties=campaign_props)

            # Group by campaign source
            campaigns = {}
            for deal_obj in results:
                props = deal_obj.properties or {}
                # Use source_data_1 as campaign name (often contains campaign name)
                # Fallback to hs_analytics_source
                campaign = (
                    props.get('hs_analytics_source_data_1')
                    or props.get('hs_analytics_source')
                    or 'Unbekannt'
                )
                campaign = campaign.strip() or 'Unbekannt'

                if campaign not in campaigns:
                    campaigns[campaign] = {
                        'campaign': campaign,
                        'source': props.get('hs_analytics_source', ''),
                        'deals': 0,
                        'revenue': 0.0,
                        'telefonisten': {},
                    }

                campaigns[campaign]['deals'] += 1

                # Revenue
                amount = props.get('amount')
                if amount:
                    try:
                        campaigns[campaign]['revenue'] += float(amount)
                    except (ValueError, TypeError):
                        pass

                # Telefonist breakdown
                telefonist = props.get('telefonist_neu', 'Unbekannt')
                if telefonist:
                    campaigns[campaign]['telefonisten'][telefonist] = \
                        campaigns[campaign]['telefonisten'].get(telefonist, 0) + 1

            # Resolve telefonist names (batch: collect unique values)
            all_telefonist_values = set()
            for data in campaigns.values():
                all_telefonist_values.update(data['telefonisten'].keys())

            telefonist_names = {}
            for raw in all_telefonist_values:
                telefonist_names[raw] = self._resolve_telefonist_name(raw)

            # Convert to list and sort
            result = []
            for name, data in campaigns.items():
                # Convert telefonisten dict to sorted list with resolved names
                tel_list = [
                    {'name': telefonist_names.get(k, k), 'deals': v}
                    for k, v in sorted(data['telefonisten'].items(), key=lambda x: x[1], reverse=True)
                ]
                result.append({
                    'campaign': data['campaign'],
                    'source': data['source'],
                    'deals': data['deals'],
                    'revenue': round(data['revenue'], 2),
                    'avg_deal_value': round(data['revenue'] / data['deals'], 2) if data['deals'] > 0 else 0,
                    'telefonisten': tel_list[:5],
                })

            result.sort(key=lambda x: x['deals'], reverse=True)
            self._cache_set(cache_key, result)
            logger.info(f"HubSpot campaign stats loaded: {len(result)} campaigns ({days} days)")
            return result

        except Exception as e:
            logger.error(f"HubSpot campaign stats failed: {e}")
            return None

    def get_deals_in_date_range(self, start: str, end: str) -> Optional[List[Dict[str, Any]]]:
        """Hole alle Deals in einem Datumsbereich (für my-calendar Enrichment).

        Ein einzelner paginierter API-Call, cached.

        Args:
            start: Startdatum YYYY-MM-DD
            end: Enddatum YYYY-MM-DD

        Returns:
            Liste von normalisierten Deal-Dicts oder None
        """
        if not self.is_available:
            return None

        cache_key = f'deals_range_{start}_{end}'
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            from hubspot.crm.deals import PublicObjectSearchRequest

            # Convert dates to epoch ms
            start_dt = datetime.strptime(start, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(end, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            start_ms = str(int(start_dt.timestamp() * 1000))
            end_ms = str(int(end_dt.timestamp() * 1000))

            filters = [
                {"propertyName": "pipeline", "operator": "EQ",
                 "value": self.config.HUBSPOT_PIPELINE_ID},
                {"propertyName": "datum_t1_neu", "operator": "GTE",
                 "value": start_ms},
                {"propertyName": "datum_t1_neu", "operator": "LTE",
                 "value": end_ms},
            ]

            results = self._search_deals(filters=filters)
            deals = [self._normalize_deal(d) for d in results]

            self._cache_set(cache_key, deals)
            logger.info(f"HubSpot deals in range {start} - {end}: {len(deals)} deals")
            return deals

        except Exception as e:
            logger.error(f"HubSpot deals in date range failed: {e}")
            return None

    def match_bookings_to_deals(
        self, bookings: List[Dict[str, Any]], deals: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Match Buchungen zu Deals anhand von Datum + Uhrzeit + Name.

        Reines Python-Matching, keine API-Calls.

        Args:
            bookings: Liste von Booking-Dicts mit date, hour, customer_name
            deals: Liste von normalisierten Deal-Dicts

        Returns:
            Dict mapping booking_key (date_hour) → deal_info
        """
        matches = {}

        # Build lookup by date + time from deals
        deal_lookup = {}
        for deal in deals:
            date = deal.get('datum_t1')
            time_val = deal.get('uhrzeit_t1')
            if date and time_val:
                # Normalize date format (HubSpot may return as epoch or date string)
                try:
                    if date.isdigit():
                        dt = datetime.fromtimestamp(int(date) / 1000, tz=timezone.utc)
                        date = dt.strftime('%Y-%m-%d')
                except (ValueError, AttributeError):
                    pass

                key = f"{date}_{time_val}"
                deal_lookup[key] = deal

        # Match bookings
        for booking in bookings:
            bdate = booking.get('date', '')
            bhour = booking.get('hour', '')
            if bdate and bhour:
                # Normalize German date format (dd.mm.yyyy) to ISO (yyyy-mm-dd)
                if '.' in bdate:
                    parts = bdate.split('.')
                    if len(parts) == 3:
                        bdate = f"{parts[2]}-{parts[1]}-{parts[0]}"
                key = f"{bdate}_{bhour}"
                if key in deal_lookup:
                    matches[key] = deal_lookup[key]
                    continue

                # Fuzzy: try matching by date + name
                bname = booking.get('customer_name', '').lower().strip()
                if bname:
                    for deal in deals:
                        dname = (deal.get('dealname') or '').lower().strip()
                        deal_date = deal.get('datum_t1', '')
                        try:
                            if deal_date and deal_date.isdigit():
                                dt = datetime.fromtimestamp(int(deal_date) / 1000, tz=timezone.utc)
                                deal_date = dt.strftime('%Y-%m-%d')
                        except (ValueError, AttributeError):
                            pass

                        if deal_date == bdate and bname and bname in dname:
                            matches[key] = deal
                            break

        return matches

    def get_customer_segments(self) -> Optional[List[Dict[str, Any]]]:
        """Hole Kundensegmente basierend auf HubSpot Contact Properties.

        Groups contacts by lifecyclestage, counts per segment,
        and calculates avg deal value + conversion per segment.

        Returns:
            Liste von Segment-Dicts oder None
        """
        if not self.is_available:
            return None

        cached = self._cache_get('customer_segments')
        if cached is not None:
            return cached

        try:
            from hubspot.crm.contacts import PublicObjectSearchRequest as ContactSearch

            segment_props = {
                'Familie': {"propertyName": "familienstand", "operator": "EQ", "value": "verheiratet"},
                'Selbstaendige': {"propertyName": "lebenssituation", "operator": "EQ", "value": "selbstaendig"},
                'Angestellte': {"propertyName": "lebenssituation", "operator": "EQ", "value": "angestellt"},
                'Rentner': {"propertyName": "lebenssituation", "operator": "EQ", "value": "rentner"},
            }

            segments = []
            for segment_name, filter_def in segment_props.items():
                req = ContactSearch(
                    filter_groups=[{"filters": [filter_def]}],
                    limit=10,
                    properties=["email", "lifecyclestage"],
                )
                resp = self.client.crm.contacts.search_api.do_search(
                    public_object_search_request=req
                )
                contact_count = resp.total

                if contact_count == 0:
                    continue

                # Sample contacts for deal stats
                contacts_with_deals = 0
                deal_values = []
                for contact in (resp.results or []):
                    try:
                        deals = self._get_associated_deals(contact.id)
                        if deals:
                            contacts_with_deals += 1
                            for d in deals:
                                if d.get('amount'):
                                    try:
                                        deal_values.append(float(d['amount']))
                                    except (ValueError, TypeError):
                                        pass
                    except Exception:
                        continue

                sample_size = len(resp.results or [])
                conversion = round((contacts_with_deals / sample_size * 100), 1) if sample_size > 0 else 0
                avg_val = round(sum(deal_values) / len(deal_values), 2) if deal_values else 0

                segments.append({
                    'segment': segment_name,
                    'count': contact_count,
                    'avg_value': avg_val,
                    'conversion': conversion,
                })

            segments.sort(key=lambda x: x['count'], reverse=True)
            self._cache_set('customer_segments', segments)
            logger.info(f"HubSpot customer segments loaded: {len(segments)} segments")
            return segments if segments else None

        except Exception as e:
            logger.error(f"HubSpot customer segments failed: {e}")
            return None


# Singleton-Instanz
hubspot_service = HubSpotService()
