# -*- coding: utf-8 -*-
"""
HubSpot Review Queue Service

Verwaltet die Batch-Review-Queue fuer Ghost/No-Show Outcomes.
Items werden vom tracking_system eingefuegt und von Admins im T2-Bereich geprueft.

Persistenz: JSON via data_persistence (hubspot_review_queue.json)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

QUEUE_FILENAME = 'hubspot_review_queue'


class HubSpotQueueService:
    """Batch-Review-Queue fuer HubSpot Outcome-Sync."""

    def _load_queue(self) -> List[Dict[str, Any]]:
        from app.core.extensions import data_persistence
        return data_persistence.load_data(QUEUE_FILENAME, default=[])

    def _save_queue(self, queue: List[Dict[str, Any]]) -> bool:
        from app.core.extensions import data_persistence
        return data_persistence.save_data(QUEUE_FILENAME, queue)

    def _generate_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def _outcome_id(self, outcome_data: Dict[str, Any]) -> str:
        """Erzeuge eine deterministische ID fuer Dedup."""
        customer = outcome_data.get('customer', '')
        date = outcome_data.get('date', '')
        time = outcome_data.get('time', '')
        return f"{date}_{time}_{customer}".replace(' ', '_')

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def add_to_queue(
        self,
        outcome_data: Dict[str, Any],
        deal_info: Optional[Dict[str, Any]],
        suggested_action: str,
        stage: str,
        note: str,
    ) -> Dict[str, Any]:
        """Fuege ein neues Item in die Review-Queue ein.

        Args:
            outcome_data: Dict mit customer, date, time, outcome, consultant
            deal_info: HubSpot Deal-Dict oder None
            suggested_action: 'ghost_first' | 'ghost_repeat' | 'no_show'
            stage: Vorgeschlagene Stage-ID
            note: Vorgeschlagene Notiz

        Returns:
            Das erstellte Queue-Item
        """
        queue = self._load_queue()

        # Dedup: gleicher Outcome bereits vorhanden?
        oid = self._outcome_id(outcome_data)
        for item in queue:
            existing_oid = self._outcome_id({
                'customer': item.get('customer', ''),
                'date': item.get('date', ''),
                'time': item.get('time', ''),
            })
            if existing_oid == oid and item.get('status') == 'pending':
                logger.debug(f"Queue dedup: {oid} already pending")
                return item

        item = {
            'id': self._generate_id(),
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': None,
            'updated_by': None,
            # Outcome
            'customer': outcome_data.get('customer', ''),
            'date': outcome_data.get('date', ''),
            'time': outcome_data.get('time', ''),
            'outcome': outcome_data.get('outcome', ''),
            'consultant': outcome_data.get('consultant', ''),
            # Deal
            'deal_id': deal_info.get('id') if deal_info else None,
            'deal_name': deal_info.get('dealname') if deal_info else None,
            'deal_stage': deal_info.get('dealstage') if deal_info else None,
            # Vorgeschlagene Aktion
            'suggested_action': suggested_action,
            'suggested_stage': stage,
            'suggested_note': note,
            # Override + Sync
            'override_stage': None,
            'override_note': None,
            'sync_result': None,
        }

        queue.append(item)
        self._save_queue(queue)
        logger.info(f"Queue item added: {item['id']} ({item['customer']} - {item['outcome']})")
        return item

    def get_queue(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Hole alle Queue-Items, optional gefiltert nach Status."""
        queue = self._load_queue()
        if status:
            return [i for i in queue if i.get('status') == status]
        return queue

    def get_pending_count(self) -> int:
        """Anzahl ausstehender Items."""
        return len(self.get_queue(status='pending'))

    def approve_item(self, item_id: str, admin_user: str) -> Dict[str, Any]:
        """Genehmige ein Queue-Item und sync nach HubSpot.

        Returns:
            Dict mit success, message, item
        """
        queue = self._load_queue()
        item = next((i for i in queue if i['id'] == item_id), None)

        if not item:
            return {'success': False, 'message': f'Item {item_id} nicht gefunden'}
        if item['status'] != 'pending':
            return {'success': False, 'message': f'Item {item_id} ist nicht pending ({item["status"]})'}

        # Sync nach HubSpot
        sync_result = 'skipped'
        if item.get('deal_id'):
            try:
                from app.services.hubspot_service import hubspot_service
                success = hubspot_service.update_deal_stage(
                    deal_id=item['deal_id'],
                    stage=item['suggested_stage'],
                    note=item['suggested_note'],
                )
                sync_result = 'synced' if success else 'sync_failed'
            except Exception as e:
                logger.error(f"Queue sync failed for {item_id}: {e}")
                sync_result = 'sync_failed'
        else:
            sync_result = 'skipped'
            logger.info(f"Queue item {item_id} approved without deal (no sync)")

        item['status'] = 'approved'
        item['sync_result'] = sync_result
        item['updated_at'] = datetime.now(timezone.utc).isoformat()
        item['updated_by'] = admin_user

        self._save_queue(queue)
        self._audit('hubspot_queue_approved', admin_user, item)

        return {'success': True, 'message': f'Item genehmigt ({sync_result})', 'item': item}

    def skip_item(self, item_id: str, admin_user: str, reason: str = '') -> Dict[str, Any]:
        """Ueberspringe ein Queue-Item."""
        queue = self._load_queue()
        item = next((i for i in queue if i['id'] == item_id), None)

        if not item:
            return {'success': False, 'message': f'Item {item_id} nicht gefunden'}
        if item['status'] != 'pending':
            return {'success': False, 'message': f'Item {item_id} ist nicht pending'}

        item['status'] = 'skipped'
        item['sync_result'] = 'skipped'
        item['updated_at'] = datetime.now(timezone.utc).isoformat()
        item['updated_by'] = admin_user
        if reason:
            item['override_note'] = reason

        self._save_queue(queue)
        self._audit('hubspot_queue_skipped', admin_user, item)

        return {'success': True, 'message': 'Item uebersprungen', 'item': item}

    def override_item(self, item_id: str, admin_user: str, stage: str, note: str = '') -> Dict[str, Any]:
        """Genehmige mit abweichender Stage."""
        queue = self._load_queue()
        item = next((i for i in queue if i['id'] == item_id), None)

        if not item:
            return {'success': False, 'message': f'Item {item_id} nicht gefunden'}
        if item['status'] != 'pending':
            return {'success': False, 'message': f'Item {item_id} ist nicht pending'}

        item['override_stage'] = stage
        item['override_note'] = note or item.get('suggested_note', '')

        # Sync mit Override-Werten
        sync_result = 'skipped'
        if item.get('deal_id'):
            try:
                from app.services.hubspot_service import hubspot_service
                success = hubspot_service.update_deal_stage(
                    deal_id=item['deal_id'],
                    stage=stage,
                    note=item['override_note'],
                )
                sync_result = 'synced' if success else 'sync_failed'
            except Exception as e:
                logger.error(f"Queue override sync failed for {item_id}: {e}")
                sync_result = 'sync_failed'

        item['status'] = 'overridden'
        item['sync_result'] = sync_result
        item['updated_at'] = datetime.now(timezone.utc).isoformat()
        item['updated_by'] = admin_user

        self._save_queue(queue)
        self._audit('hubspot_queue_overridden', admin_user, item)

        return {'success': True, 'message': f'Item mit Override genehmigt ({sync_result})', 'item': item}

    def approve_all(self, admin_user: str) -> Dict[str, Any]:
        """Genehmige alle pending Items die einen Deal haben."""
        queue = self._load_queue()
        pending = [i for i in queue if i['status'] == 'pending' and i.get('deal_id')]

        if not pending:
            return {'success': True, 'message': 'Keine Items zum Genehmigen', 'count': 0}

        synced = 0
        failed = 0
        for item in pending:
            try:
                from app.services.hubspot_service import hubspot_service
                success = hubspot_service.update_deal_stage(
                    deal_id=item['deal_id'],
                    stage=item['suggested_stage'],
                    note=item['suggested_note'],
                )
                item['status'] = 'approved'
                item['sync_result'] = 'synced' if success else 'sync_failed'
                item['updated_at'] = datetime.now(timezone.utc).isoformat()
                item['updated_by'] = admin_user
                if success:
                    synced += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Batch approve failed for {item['id']}: {e}")
                item['status'] = 'approved'
                item['sync_result'] = 'sync_failed'
                item['updated_at'] = datetime.now(timezone.utc).isoformat()
                item['updated_by'] = admin_user
                failed += 1

        self._save_queue(queue)
        self._audit('hubspot_queue_approve_all', admin_user, {
            'synced': synced, 'failed': failed, 'total': len(pending)
        })

        return {
            'success': True,
            'message': f'{synced} synced, {failed} fehlgeschlagen',
            'count': len(pending),
            'synced': synced,
            'failed': failed,
        }

    def clear_completed(self, days_old: int = 30) -> int:
        """Entferne abgeschlossene Items aelter als days_old Tage."""
        queue = self._load_queue()
        cutoff = datetime.now(timezone.utc).timestamp() - (days_old * 86400)

        original_len = len(queue)
        kept = []
        for item in queue:
            if item['status'] == 'pending':
                kept.append(item)
                continue
            updated = item.get('updated_at') or item.get('created_at', '')
            try:
                ts = datetime.fromisoformat(updated).timestamp()
            except (ValueError, TypeError):
                kept.append(item)
                continue
            if ts >= cutoff:
                kept.append(item)

        removed = original_len - len(kept)
        if removed > 0:
            self._save_queue(kept)
            logger.info(f"Queue cleanup: {removed} items removed (older than {days_old} days)")
        return removed

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _audit(self, action: str, user: str, details: Any) -> None:
        try:
            from app.services.audit_service import audit_service
            audit_service.log_event('admin', action, details, user=user)
        except Exception as e:
            logger.warning(f"Audit log failed for {action}: {e}")


# Singleton
hubspot_queue_service = HubSpotQueueService()
