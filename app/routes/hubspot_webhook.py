# -*- coding: utf-8 -*-
"""
HubSpot Webhook Endpoint

Empfängt Deal-Stage-Änderungen von HubSpot für bidirektionalen Sync.
Validiert die Signatur des Requests und verarbeitet Events.
Erstellt Queue-Items für Admin-Review (gleicher Ansatz wie G.2).
"""

import hashlib
import hmac
import logging
import time
from collections import OrderedDict
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

hubspot_webhook_bp = Blueprint('hubspot_webhook', __name__)

# Idempotency: track processed event hashes to prevent replay (max 1000 entries)
_processed_events = OrderedDict()
_MAX_PROCESSED = 1000


def _event_key(event: dict) -> str:
    """Generate a unique key for deduplication."""
    return f"{event.get('objectId')}:{event.get('propertyName')}:{event.get('propertyValue')}:{event.get('occurredAt', '')}"


def _is_duplicate(event: dict) -> bool:
    """Check if this event was already processed."""
    key = _event_key(event)
    if key in _processed_events:
        return True
    _processed_events[key] = time.time()
    # Evict oldest entries if over limit
    while len(_processed_events) > _MAX_PROCESSED:
        _processed_events.popitem(last=False)
    return False


def validate_hubspot_signature(req) -> bool:
    """Validiere die HubSpot Webhook-Signatur (v3).

    HubSpot signiert Webhook-Requests mit HMAC-SHA256.
    Docs: https://developers.hubspot.com/docs/api/webhooks#security

    Args:
        req: Flask request object

    Returns:
        True wenn Signatur gültig
    """
    from app.config.base import hubspot_config

    secret = hubspot_config.HUBSPOT_WEBHOOK_SECRET
    if not secret:
        logger.warning("HUBSPOT_WEBHOOK_SECRET not configured, rejecting webhook")
        return False

    signature = req.headers.get('X-HubSpot-Signature-v3', '')
    timestamp = req.headers.get('X-HubSpot-Request-Timestamp', '')

    if not signature or not timestamp:
        logger.warning("Missing HubSpot signature headers")
        return False

    # Timestamp-Freshness: max 5 Minuten alt (Replay-Schutz)
    try:
        ts = int(timestamp)
        if abs(time.time() * 1000 - ts) > 300_000:
            logger.warning(f"HubSpot webhook timestamp too old: {timestamp}")
            return False
    except (ValueError, TypeError):
        logger.warning(f"Invalid HubSpot webhook timestamp: {timestamp}")
        return False

    # v3 Signatur: HMAC-SHA256 von (method + url + body + timestamp)
    request_body = req.get_data(as_text=True)
    source_string = f"{req.method}{req.url}{request_body}{timestamp}"

    expected = hmac.new(
        secret.encode('utf-8'),
        source_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


def handle_stage_change(deal_id: str, new_stage: str, previous_stage: str) -> bool:
    """Verarbeite eine HubSpot Deal-Stage-Änderung.

    Holt Deal-Details via API, mappt die Stage auf einen lokalen Outcome-Typ,
    und erstellt ein Queue-Item für Admin-Review.

    Args:
        deal_id: HubSpot Deal ID
        new_stage: Neue Stage-ID
        previous_stage: Vorherige Stage-ID

    Returns:
        True wenn erfolgreich verarbeitet
    """
    from app.config.base import hubspot_config
    from app.services.hubspot_service import hubspot_service
    from app.services.hubspot_queue_service import hubspot_queue_service
    from app.services.audit_service import audit_service

    # Deal-Details von HubSpot holen
    deal_info = hubspot_service.get_deal(deal_id)
    if not deal_info:
        logger.warning(f"Could not fetch deal {deal_id} from HubSpot, skipping")
        return False

    # Stage → lokaler Outcome-Typ mappen
    reverse_mapping = hubspot_config.REVERSE_STAGE_MAPPING
    suggested_outcome = reverse_mapping.get(new_stage, 'unknown')

    # Outcome-Daten aus Deal extrahieren
    customer_name = deal_info.get('dealname', '')
    datum_t1 = deal_info.get('datum_t1', '')
    uhrzeit_t1 = deal_info.get('uhrzeit_t1', '')

    outcome_data = {
        'customer': customer_name,
        'date': datum_t1 or '',
        'time': uhrzeit_t1 or '',
        'outcome': suggested_outcome,
        'consultant': deal_info.get('telefonist', ''),
    }

    # Queue-Item erstellen (Admin-Review, wie G.2)
    note = f"HubSpot Stage-Change: {previous_stage} → {new_stage}"

    try:
        queue_item = hubspot_queue_service.add_to_queue(
            outcome_data=outcome_data,
            deal_info=deal_info,
            suggested_action=suggested_outcome,
            stage=new_stage,
            note=note,
        )

        logger.info(
            f"HubSpot webhook queued: deal {deal_id} → "
            f"{suggested_outcome} (queue item {queue_item.get('id')})"
        )

        # Audit-Log
        audit_service.log(
            'hubspot_webhook_processed',
            'webhook',
            {
                'deal_id': deal_id,
                'new_stage': new_stage,
                'previous_stage': previous_stage,
                'suggested_outcome': suggested_outcome,
                'queue_item_id': queue_item.get('id'),
                'customer': customer_name,
            }
        )

        return True

    except Exception as e:
        logger.error(f"Failed to queue HubSpot stage change for deal {deal_id}: {e}")
        return False


@hubspot_webhook_bp.route('/api/hubspot/webhook', methods=['POST'])
def handle_webhook():
    """Empfängt HubSpot Deal-Stage-Änderungen.

    Event-Typen die verarbeitet werden:
    - deal.propertyChange (dealstage) → Queue-Item für Admin-Review
    """
    # Signatur validieren
    if not validate_hubspot_signature(request):
        logger.warning(f"Invalid HubSpot webhook signature from {request.remote_addr}")
        return jsonify({'error': 'Invalid signature'}), 401

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({'error': 'Empty payload'}), 400

    # HubSpot sendet Events als Array
    events = payload if isinstance(payload, list) else [payload]

    processed = 0
    for event in events:
        try:
            subscription_type = event.get('subscriptionType', '')

            if subscription_type == 'deal.propertyChange':
                property_name = event.get('propertyName', '')

                if property_name == 'dealstage':
                    if _is_duplicate(event):
                        logger.info(f"Skipping duplicate HubSpot event: {_event_key(event)}")
                        continue
                    deal_id = str(event.get('objectId', ''))
                    new_stage = event.get('propertyValue', '')
                    previous_stage = event.get('previousPropertyValue', '')

                    logger.info(
                        f"HubSpot deal stage change: {deal_id} "
                        f"{previous_stage} → {new_stage}"
                    )

                    if handle_stage_change(deal_id, new_stage, previous_stage):
                        processed += 1

        except Exception as e:
            logger.error(f"Error processing HubSpot webhook event: {e}")

    return jsonify({'status': 'ok', 'processed': processed}), 200
