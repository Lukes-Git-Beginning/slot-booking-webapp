# -*- coding: utf-8 -*-
"""
Finanzberatung DSGVO Service Tests
Tests for app/services/finanz_dsgvo_service.py
"""

import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


@pytest.fixture
def dsgvo_service():
    from app.services.finanz_dsgvo_service import FinanzDSGVOService
    return FinanzDSGVOService()


@pytest.fixture
def mock_session():
    """Create a mock FinanzSession."""
    session = MagicMock()
    session.id = 1
    session.customer_name = 'Test Kunde'
    session.opener_username = 'test.opener'
    session.status = 'active'
    session.deletion_requested_at = None
    session.deletion_requested_by = None
    session.files_deleted_at = None
    return session


@pytest.fixture
def mock_session_marked():
    """Create a mock FinanzSession marked for deletion."""
    session = MagicMock()
    session.id = 2
    session.customer_name = 'Delete Kunde'
    session.opener_username = 'test.opener'
    session.status = 'deletion_pending'
    session.deletion_requested_at = datetime.now(timezone.utc) - timedelta(days=31)
    session.deletion_requested_by = 'admin.user'
    session.files_deleted_at = None
    return session


class TestMarkForDeletion:
    """Test mark_for_deletion method."""

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_mark_sets_timestamp(self, mock_db, dsgvo_service, mock_session):
        """Test that marking sets deletion_requested_at."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = mock_session

        result = dsgvo_service.mark_for_deletion(1, 'admin.user')

        assert result['session_id'] == 1
        assert result['status'] == 'deletion_pending'
        assert 'deletion_requested_at' in result
        assert 'deletion_due' in result
        db.commit.assert_called_once()

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_mark_sets_admin_user(self, mock_db, dsgvo_service, mock_session):
        """Test that marking records which admin requested it."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = mock_session

        dsgvo_service.mark_for_deletion(1, 'admin.user')

        assert mock_session.deletion_requested_by == 'admin.user'

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_mark_not_found_raises(self, mock_db, dsgvo_service):
        """Test that marking non-existent session raises ValueError."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            dsgvo_service.mark_for_deletion(999, 'admin.user')

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_mark_already_marked_raises(self, mock_db, dsgvo_service, mock_session):
        """Test that marking already-marked session raises ValueError."""
        mock_session.deletion_requested_at = datetime.now(timezone.utc)

        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = mock_session

        with pytest.raises(ValueError, match="already marked"):
            dsgvo_service.mark_for_deletion(1, 'admin.user')


class TestCanExecuteDeletion:
    """Test can_execute_deletion method."""

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_can_delete_after_30_days(self, mock_db, dsgvo_service, mock_session_marked):
        """Test that deletion is allowed after 30 days."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = mock_session_marked

        assert dsgvo_service.can_execute_deletion(2) is True

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_cannot_delete_before_30_days(self, mock_db, dsgvo_service, mock_session):
        """Test that deletion is blocked within 30 days."""
        mock_session.deletion_requested_at = datetime.now(timezone.utc) - timedelta(days=10)

        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = mock_session

        assert dsgvo_service.can_execute_deletion(1) is False

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_cannot_delete_not_marked(self, mock_db, dsgvo_service, mock_session):
        """Test that unmarked session returns False."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = mock_session

        assert dsgvo_service.can_execute_deletion(1) is False

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_cannot_delete_already_deleted(self, mock_db, dsgvo_service, mock_session_marked):
        """Test that already-deleted session returns False."""
        mock_session_marked.files_deleted_at = datetime.now(timezone.utc)

        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = mock_session_marked

        assert dsgvo_service.can_execute_deletion(2) is False

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_cannot_delete_not_found(self, mock_db, dsgvo_service):
        """Test that non-existent session returns False."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = None

        assert dsgvo_service.can_execute_deletion(999) is False


class TestExecuteDeletion:
    """Test execute_deletion method."""

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_execute_deletes_files(self, mock_db, dsgvo_service, mock_session_marked, tmp_path):
        """Test that execute_deletion removes files from disk."""
        db = MagicMock()
        mock_db.return_value = db

        # Setup session query
        db.query.return_value.filter.return_value.first.return_value = mock_session_marked

        # Create mock documents
        doc1 = MagicMock()
        doc1.stored_filename = 'test_file.pdf'
        doc1.original_filename = 'original.pdf'

        # Use tmp_path for file operations
        test_file = tmp_path / 'test_file.pdf'
        test_file.write_text('test content')

        db.query.return_value.filter.return_value.all.return_value = [doc1]

        with patch('app.services.finanz_dsgvo_service.os.path.join',
                   return_value=str(test_file)), \
             patch('app.services.finanz_dsgvo_service.os.path.exists',
                   return_value=True), \
             patch('app.services.finanz_dsgvo_service.os.remove') as mock_remove:

            result = dsgvo_service.execute_deletion(2)

            assert result['session_id'] == 2
            assert result['files_deleted'] == 1
            assert result['status'] == 'archived'
            mock_remove.assert_called_once()

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_execute_anonymizes_filenames(self, mock_db, dsgvo_service, mock_session_marked):
        """Test that execute_deletion sets filenames to [GELOESCHT]."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = mock_session_marked

        doc = MagicMock()
        doc.stored_filename = 'stored.pdf'
        doc.original_filename = 'original.pdf'
        db.query.return_value.filter.return_value.all.return_value = [doc]

        with patch('app.services.finanz_dsgvo_service.os.path.exists', return_value=False):
            dsgvo_service.execute_deletion(2)

        assert doc.original_filename == '[GELOESCHT]'
        assert doc.stored_filename is None

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_execute_not_found_raises(self, mock_db, dsgvo_service):
        """Test that executing deletion on non-existent session raises."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            dsgvo_service.execute_deletion(999)

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_execute_not_marked_raises(self, mock_db, dsgvo_service, mock_session):
        """Test that executing deletion on unmarked session raises."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.first.return_value = mock_session

        with pytest.raises(ValueError, match="not marked"):
            dsgvo_service.execute_deletion(1)


class TestGetDeletionQueue:
    """Test get_deletion_queue method."""

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_empty_queue(self, mock_db, dsgvo_service):
        """Test empty deletion queue."""
        db = MagicMock()
        mock_db.return_value = db
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        queue = dsgvo_service.get_deletion_queue()
        assert queue == []

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_queue_with_items(self, mock_db, dsgvo_service):
        """Test deletion queue with pending items."""
        db = MagicMock()
        mock_db.return_value = db

        session = MagicMock()
        session.id = 1
        session.customer_name = 'Test'
        session.opener_username = 'opener'
        session.deletion_requested_at = datetime.now(timezone.utc) - timedelta(days=15)
        session.deletion_requested_by = 'admin'
        session.files_deleted_at = None

        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [session]
        db.query.return_value.filter.return_value.count.return_value = 3

        queue = dsgvo_service.get_deletion_queue()
        assert len(queue) == 1
        assert queue[0]['session_id'] == 1
        assert queue[0]['days_remaining'] > 0
        assert queue[0]['can_delete'] is False

    @patch('app.services.finanz_dsgvo_service.get_db_session')
    def test_queue_expired_item(self, mock_db, dsgvo_service):
        """Test deletion queue with expired items shows can_delete=True."""
        db = MagicMock()
        mock_db.return_value = db

        session = MagicMock()
        session.id = 1
        session.customer_name = 'Expired'
        session.opener_username = 'opener'
        session.deletion_requested_at = datetime.now(timezone.utc) - timedelta(days=35)
        session.deletion_requested_by = 'admin'
        session.files_deleted_at = None

        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [session]
        db.query.return_value.filter.return_value.count.return_value = 0

        queue = dsgvo_service.get_deletion_queue()
        assert len(queue) == 1
        assert queue[0]['can_delete'] is True
        assert queue[0]['days_remaining'] == 0


class TestBatchDeleteExpired:
    """Test batch_delete_expired method."""

    @patch.object(
        __import__('app.services.finanz_dsgvo_service', fromlist=['FinanzDSGVOService']).FinanzDSGVOService,
        'get_deletion_queue',
    )
    @patch.object(
        __import__('app.services.finanz_dsgvo_service', fromlist=['FinanzDSGVOService']).FinanzDSGVOService,
        'execute_deletion',
    )
    def test_batch_processes_only_expired(self, mock_execute, mock_queue, dsgvo_service):
        """Test that batch only processes expired sessions."""
        mock_queue.return_value = [
            {'session_id': 1, 'can_delete': True, 'customer_name': 'A'},
            {'session_id': 2, 'can_delete': False, 'customer_name': 'B'},
            {'session_id': 3, 'can_delete': True, 'customer_name': 'C'},
        ]
        mock_execute.return_value = {'session_id': 1, 'files_deleted': 2, 'status': 'archived'}

        result = dsgvo_service.batch_delete_expired()

        assert result['total_expired'] == 2
        assert mock_execute.call_count == 2

    @patch.object(
        __import__('app.services.finanz_dsgvo_service', fromlist=['FinanzDSGVOService']).FinanzDSGVOService,
        'get_deletion_queue',
    )
    def test_batch_empty_queue(self, mock_queue, dsgvo_service):
        """Test batch with no expired sessions."""
        mock_queue.return_value = []

        result = dsgvo_service.batch_delete_expired()

        assert result['total_expired'] == 0
        assert result['processed'] == 0
