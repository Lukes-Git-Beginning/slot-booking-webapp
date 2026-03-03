# -*- coding: utf-8 -*-
"""
Service Layer Tests - HubSpot Queue Service
Tests for app/services/hubspot_queue_service.py
"""

import pytest
from unittest.mock import patch, MagicMock


# ========== FIXTURES ==========

@pytest.fixture
def queue_service():
    """Create HubSpotQueueService instance with mocked persistence."""
    from app.services.hubspot_queue_service import HubSpotQueueService
    return HubSpotQueueService()


@pytest.fixture
def sample_outcome():
    return {
        'customer': 'Max Mustermann',
        'date': '2026-03-03',
        'time': '14:00',
        'outcome': 'ghost',
        'consultant': 'Daniel',
    }


@pytest.fixture
def sample_deal():
    return {
        'id': '12345',
        'dealname': 'Mustermann Deal',
        'dealstage': '349476306',
        'pipeline': 'default',
    }


# ========== ADD TO QUEUE ==========

class TestAddToQueue:

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._save_queue')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue', return_value=[])
    def test_add_item(self, mock_load, mock_save, queue_service, sample_outcome, sample_deal):
        item = queue_service.add_to_queue(
            outcome_data=sample_outcome,
            deal_info=sample_deal,
            suggested_action='ghost_first',
            stage='349476306',
            note='Ghost - automatisch zur Rueckholung',
        )

        assert item['status'] == 'pending'
        assert item['customer'] == 'Max Mustermann'
        assert item['deal_id'] == '12345'
        assert item['suggested_action'] == 'ghost_first'
        assert len(item['id']) == 8
        mock_save.assert_called_once()

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._save_queue')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue', return_value=[])
    def test_add_item_no_deal(self, mock_load, mock_save, queue_service, sample_outcome):
        item = queue_service.add_to_queue(
            outcome_data=sample_outcome,
            deal_info=None,
            suggested_action='ghost_first',
            stage='349476306',
            note='Ghost - kein Deal',
        )

        assert item['deal_id'] is None
        assert item['deal_name'] is None

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._save_queue')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_dedup_pending(self, mock_load, mock_save, queue_service, sample_outcome, sample_deal):
        existing = {
            'id': 'abc12345',
            'status': 'pending',
            'customer': 'Max Mustermann',
            'date': '2026-03-03',
            'time': '14:00',
            'outcome': 'ghost',
        }
        mock_load.return_value = [existing]

        item = queue_service.add_to_queue(
            outcome_data=sample_outcome,
            deal_info=sample_deal,
            suggested_action='ghost_first',
            stage='349476306',
            note='Ghost',
        )

        # Should return existing item, not create new
        assert item['id'] == 'abc12345'
        mock_save.assert_not_called()


# ========== GET QUEUE ==========

class TestGetQueue:

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_get_all(self, mock_load, queue_service):
        mock_load.return_value = [
            {'id': '1', 'status': 'pending'},
            {'id': '2', 'status': 'approved'},
        ]
        result = queue_service.get_queue()
        assert len(result) == 2

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_get_filtered(self, mock_load, queue_service):
        mock_load.return_value = [
            {'id': '1', 'status': 'pending'},
            {'id': '2', 'status': 'approved'},
            {'id': '3', 'status': 'pending'},
        ]
        result = queue_service.get_queue(status='pending')
        assert len(result) == 2

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_pending_count(self, mock_load, queue_service):
        mock_load.return_value = [
            {'id': '1', 'status': 'pending'},
            {'id': '2', 'status': 'approved'},
        ]
        assert queue_service.get_pending_count() == 1


# ========== APPROVE ==========

class TestApproveItem:

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._audit')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._save_queue')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_approve_with_deal(self, mock_load, mock_save, mock_audit, queue_service):
        mock_load.return_value = [{
            'id': 'item1',
            'status': 'pending',
            'deal_id': '12345',
            'suggested_stage': '349476306',
            'suggested_note': 'Ghost',
        }]

        with patch('app.services.hubspot_service.hubspot_service') as mock_hs:
            mock_hs.update_deal_stage.return_value = True
            result = queue_service.approve_item('item1', 'admin')

        assert result['success'] is True
        assert result['item']['status'] == 'approved'
        assert result['item']['sync_result'] == 'synced'
        mock_audit.assert_called_once()

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._audit')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._save_queue')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_approve_no_deal(self, mock_load, mock_save, mock_audit, queue_service):
        mock_load.return_value = [{
            'id': 'item2',
            'status': 'pending',
            'deal_id': None,
            'suggested_stage': '349476306',
            'suggested_note': 'Ghost',
        }]

        result = queue_service.approve_item('item2', 'admin')

        assert result['success'] is True
        assert result['item']['sync_result'] == 'skipped'

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_approve_not_found(self, mock_load, queue_service):
        mock_load.return_value = []
        result = queue_service.approve_item('nonexistent', 'admin')
        assert result['success'] is False

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_approve_already_processed(self, mock_load, queue_service):
        mock_load.return_value = [{'id': 'item1', 'status': 'approved'}]
        result = queue_service.approve_item('item1', 'admin')
        assert result['success'] is False


# ========== SKIP ==========

class TestSkipItem:

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._audit')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._save_queue')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_skip(self, mock_load, mock_save, mock_audit, queue_service):
        mock_load.return_value = [{'id': 'item1', 'status': 'pending'}]

        result = queue_service.skip_item('item1', 'admin', 'Nicht relevant')

        assert result['success'] is True
        assert result['item']['status'] == 'skipped'
        assert result['item']['override_note'] == 'Nicht relevant'


# ========== OVERRIDE ==========

class TestOverrideItem:

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._audit')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._save_queue')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_override_with_deal(self, mock_load, mock_save, mock_audit, queue_service):
        mock_load.return_value = [{
            'id': 'item1',
            'status': 'pending',
            'deal_id': '12345',
            'suggested_stage': '349476306',
            'suggested_note': 'Ghost',
        }]

        with patch('app.services.hubspot_service.hubspot_service') as mock_hs:
            mock_hs.update_deal_stage.return_value = True
            result = queue_service.override_item('item1', 'admin', '680987595', 'Override note')

        assert result['success'] is True
        assert result['item']['status'] == 'overridden'
        assert result['item']['override_stage'] == '680987595'


# ========== APPROVE ALL ==========

class TestApproveAll:

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._audit')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._save_queue')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_approve_all(self, mock_load, mock_save, mock_audit, queue_service):
        mock_load.return_value = [
            {'id': '1', 'status': 'pending', 'deal_id': '111', 'suggested_stage': 's1', 'suggested_note': 'n1'},
            {'id': '2', 'status': 'pending', 'deal_id': '222', 'suggested_stage': 's2', 'suggested_note': 'n2'},
            {'id': '3', 'status': 'pending', 'deal_id': None, 'suggested_stage': 's3', 'suggested_note': 'n3'},
        ]

        with patch('app.services.hubspot_service.hubspot_service') as mock_hs:
            mock_hs.update_deal_stage.return_value = True
            result = queue_service.approve_all('admin')

        assert result['success'] is True
        assert result['count'] == 2  # Only items with deal_id
        assert result['synced'] == 2

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_approve_all_empty(self, mock_load, queue_service):
        mock_load.return_value = []
        result = queue_service.approve_all('admin')
        assert result['success'] is True
        assert result['count'] == 0


# ========== CLEAR COMPLETED ==========

class TestClearCompleted:

    @patch('app.services.hubspot_queue_service.HubSpotQueueService._save_queue')
    @patch('app.services.hubspot_queue_service.HubSpotQueueService._load_queue')
    def test_clear_old(self, mock_load, mock_save, queue_service):
        mock_load.return_value = [
            {'id': '1', 'status': 'pending', 'created_at': '2026-03-03T10:00:00+00:00'},
            {'id': '2', 'status': 'approved', 'updated_at': '2025-01-01T10:00:00+00:00', 'created_at': '2025-01-01'},
            {'id': '3', 'status': 'approved', 'updated_at': '2026-03-03T10:00:00+00:00', 'created_at': '2026-03-03'},
        ]

        removed = queue_service.clear_completed(days_old=30)
        assert removed == 1  # Only item 2 is old enough
        mock_save.assert_called_once()
        saved_queue = mock_save.call_args[0][0]
        assert len(saved_queue) == 2
        ids = [i['id'] for i in saved_queue]
        assert '1' in ids  # pending kept
        assert '3' in ids  # recent kept
