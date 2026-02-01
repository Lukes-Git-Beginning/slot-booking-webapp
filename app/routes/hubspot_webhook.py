# -*- coding: utf-8 -*-
"""
HubSpot Webhook Endpoint

Empfängt Deal-Stage-Änderungen von HubSpot für bidirektionalen Sync.
Validiert die Signatur des Requests und verarbeitet Events.
"""

import hashlib
import hmac
import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

hubspot_webhook_bp = Blueprint('hubspot_webhook', __name__)


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

    # v3 Signatur: HMAC-SHA256 von (method + url + body + timestamp)
    request_body = req.get_data(as_text=True)
    source_string = f"{req.method}{req.url}{request_body}{timestamp}"

    expected = hmac.new(
        secret.encode('utf-8'),
        source_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


@hubspot_webhook_bp.route('/api/hubspot/webhook', methods=['POST'])
def handle_webhook():
    """Empfängt HubSpot Deal-Stage-Änderungen.

    Event-Typen die verarbeitet werden:
    - deal.propertyChange (dealstage) → Lokale Datenbank aktualisieren
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
                    deal_id = str(event.get('objectId', ''))
                    new_stage = event.get('propertyValue', '')
                    previous_stage = event.get('previousPropertyValue', '')

                    logger.info(
                        f"HubSpot deal stage change: {deal_id} "
                        f"{previous_stage} → {new_stage}"
                    )

                    # TODO: Phase 4 - Lokale DB aktualisieren
                    # handle_stage_change(deal_id, new_stage, previous_stage)
                    processed += 1

        except Exception as e:
            logger.error(f"Error processing HubSpot webhook event: {e}")

    return jsonify({'status': 'ok', 'processed': processed}), 200
