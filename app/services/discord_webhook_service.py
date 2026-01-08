# -*- coding: utf-8 -*-
"""
Discord Webhook Service
Sendet Discord-Benachrichtigungen für gelöschte T1-bereit Slots
"""

import os
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class DiscordWebhookService:
    """Service für Discord Webhook Benachrichtigungen"""

    def __init__(self):
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '').strip()
        self.enabled = os.getenv('DISCORD_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        self.timeout = 10  # Sekunden
        self.max_retries = 3

        if not self.webhook_url:
            logger.info("Discord notifications disabled (no webhook URL configured)")
            self.enabled = False
        elif self.enabled:
            logger.info("Discord notifications enabled")

    def send_deletion_notification(
        self,
        deletions: List[Dict],
        scan_timestamp: str
    ) -> bool:
        """
        Sende Discord-Benachrichtigung für gelöschte T1-bereit Slots

        Args:
            deletions: Liste von Deletions mit Format:
                [{'slot': '2025-01-15 09:00', 'consultant': 'Daniel', 'consultant_full': 'Daniel Herbort'}]
            scan_timestamp: Zeitstempel des Scans (z.B. '2025-01-06 09:00:15 UTC')

        Returns:
            True wenn erfolgreich gesendet, False bei Fehler
        """
        if not self.enabled:
            logger.debug("Discord notifications disabled, skipping")
            return False

        if not deletions:
            logger.debug("No deletions to report")
            return False

        try:
            # Erstelle Discord Embed
            payload = self._format_embed(deletions, scan_timestamp)

            # Sende mit Retry-Logik
            return self._send_with_retry(payload)

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}", exc_info=True)
            return False

    def _format_embed(self, deletions: List[Dict], scan_timestamp: str) -> Dict:
        """
        Formatiere Discord Embed

        Args:
            deletions: Liste von Deletions
            scan_timestamp: Scan-Zeitstempel

        Returns:
            Discord Webhook Payload
        """
        deletion_count = len(deletions)

        # Erstelle Felder für jede Deletion
        fields = []
        for deletion in deletions:
            slot = deletion.get('slot', 'Unknown')
            consultant_full = deletion.get('consultant_full', deletion.get('consultant', 'Unknown'))

            fields.append({
                'name': f"📅 {slot}",
                'value': f"**{consultant_full}** removed availability",
                'inline': False
            })

        # Discord Embed (Rot = Warning)
        embed = {
            'title': f"🚨 T1-bereit Slots Removed ({deletion_count})",
            'description': "The following availability has been deleted:",
            'color': 15158332,  # Rot (#E74C3C)
            'fields': fields,
            'footer': {
                'text': f"Detected at {scan_timestamp}"
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        payload = {
            'embeds': [embed]
        }

        return payload

    def _send_with_retry(self, payload: Dict) -> bool:
        """
        Sende Webhook mit Retry-Logik

        Args:
            payload: Discord Webhook Payload

        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )

                # Erfolg
                if response.status_code == 204 or response.status_code == 200:
                    logger.info(f"Discord notification sent successfully (attempt {attempt})")
                    return True

                # Client-Fehler (4xx) -> Keine Retries
                if 400 <= response.status_code < 500:
                    logger.error(
                        f"Discord webhook failed with client error (HTTP {response.status_code}): {response.text}"
                    )
                    return False

                # Server-Fehler (5xx) -> Retry
                if 500 <= response.status_code < 600:
                    logger.warning(
                        f"Discord webhook server error (HTTP {response.status_code}) on attempt {attempt}/{self.max_retries}"
                    )
                    if attempt < self.max_retries:
                        self._wait_before_retry(attempt)
                        continue
                    else:
                        logger.error(f"Discord notification failed after {self.max_retries} retries")
                        return False

            except requests.exceptions.Timeout:
                logger.warning(f"Discord webhook timeout on attempt {attempt}/{self.max_retries}")
                if attempt < self.max_retries:
                    self._wait_before_retry(attempt)
                    continue
                else:
                    logger.error(f"Discord notification failed after {self.max_retries} timeout retries")
                    return False

            except requests.exceptions.RequestException as e:
                logger.error(f"Discord webhook request failed on attempt {attempt}/{self.max_retries}: {e}")
                if attempt < self.max_retries:
                    self._wait_before_retry(attempt)
                    continue
                else:
                    logger.error(f"Discord notification failed after {self.max_retries} retries")
                    return False

        return False

    def _wait_before_retry(self, attempt: int):
        """
        Exponential Backoff vor Retry

        Args:
            attempt: Aktueller Versuch (1-basiert)
        """
        wait_time = 2 ** attempt  # 2s, 4s, 8s
        logger.debug(f"Waiting {wait_time}s before retry...")
        time.sleep(wait_time)


# Singleton-Instanz
discord_webhook_service = DiscordWebhookService()
