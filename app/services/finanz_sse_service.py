# -*- coding: utf-8 -*-
"""
Finanzberatung SSE Service - Redis Pub/Sub Server-Sent Events Manager

Provides real-time notifications for document uploads via Redis Pub/Sub.
Publishes events on two channels:
- Session channel (finanz:session:{id}): for session detail live feed
- User channel (finanz:user:{username}): for global toast notifications

Graceful degradation: if Redis is unavailable, publish is a no-op.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)


class SSEManager:
    """Redis Pub/Sub based Server-Sent Events manager for Finanzberatung."""

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize SSE manager with Redis connection.

        Args:
            redis_url: Redis connection URL. Falls back to REDIS_URL env var.
        """
        self.redis = None
        self._redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')

        try:
            import redis as redis_lib
            self.redis = redis_lib.Redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=5,
            )
            # Test connection
            self.redis.ping()
            logger.info("SSE Manager: Redis connection established (%s)", self._redis_url)
        except Exception as e:
            logger.warning(
                "SSE Manager: Redis unavailable (%s) -- SSE notifications disabled: %s",
                self._redis_url, e,
            )
            self.redis = None

    def publish(self, session_id: int, event_type: str, data: dict,
                opener_username: Optional[str] = None) -> None:
        """
        Publish an SSE event to session and user channels.

        Args:
            session_id: Target session ID for session-specific channel
            event_type: Event type string (e.g. 'new_upload')
            data: Event payload dict
            opener_username: If provided, also publish to user channel for global toast
        """
        if self.redis is None:
            logger.warning("SSE publish skipped -- Redis unavailable")
            return

        message = json.dumps({
            'event': event_type,
            'data': data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })

        try:
            # Publish to session channel (for live feed on session detail page)
            session_channel = f"finanz:session:{session_id}"
            self.redis.publish(session_channel, message)

            # Publish to user channel (for global toast on any Hub page)
            if opener_username:
                user_channel = f"finanz:user:{opener_username}"
                self.redis.publish(user_channel, message)

            logger.debug(
                "SSE event published: %s on session %s (user: %s)",
                event_type, session_id, opener_username,
            )
        except Exception as e:
            logger.error("SSE publish failed: %s", e, exc_info=True)

    def stream(self, channel: str) -> Generator[str, None, None]:
        """
        Generator that yields SSE-formatted events from a Redis channel.

        Args:
            channel: Redis pub/sub channel to subscribe to

        Yields:
            SSE-formatted event strings
        """
        if self.redis is None:
            yield "retry: 30000\ndata: {\"error\": \"SSE unavailable\"}\n\n"
            return

        pubsub = self.redis.pubsub()
        first_event = True

        try:
            pubsub.subscribe(channel)

            while True:
                message = pubsub.get_message(timeout=30)

                if message is None:
                    # Timeout -- send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
                    continue

                if message['type'] != 'message':
                    continue

                raw_data = message['data']

                try:
                    parsed = json.loads(raw_data)
                    event_type = parsed.get('event', 'message')
                    event_data = json.dumps(parsed.get('data', {}))
                    timestamp = parsed.get('timestamp', datetime.now(timezone.utc).isoformat())
                except (json.JSONDecodeError, AttributeError):
                    event_type = 'message'
                    event_data = json.dumps({'raw': str(raw_data)})
                    timestamp = datetime.now(timezone.utc).isoformat()

                parts = []
                if first_event:
                    parts.append("retry: 5000\n")
                    first_event = False

                parts.append(f"event: {event_type}\n")
                parts.append(f"data: {event_data}\n")
                parts.append(f"id: {timestamp}\n")
                parts.append("\n")

                yield "".join(parts)

        except GeneratorExit:
            logger.debug("SSE stream closed for channel: %s", channel)
        except Exception as e:
            logger.error("SSE stream error on channel %s: %s", channel, e, exc_info=True)
        finally:
            try:
                pubsub.unsubscribe(channel)
                pubsub.close()
            except Exception:
                pass

    def format_upload_event(self, document: Any, customer_name: str = 'Kunde') -> dict:
        """
        Format a FinanzDocument into SSE event data dict.

        Args:
            document: FinanzDocument model instance
            customer_name: Customer name for display in toast notifications

        Returns:
            Dict with document info for SSE event payload
        """
        return {
            'id': document.id,
            'original_filename': document.original_filename,
            'file_size': document.file_size,
            'mime_type': document.mime_type,
            'status': document.status if isinstance(document.status, str) else document.status.value,
            'created_at': document.created_at.isoformat() if document.created_at else None,
            'session_id': document.session_id,
            'customer_name': customer_name,
        }


# Module-level singleton
sse_manager = SSEManager()
