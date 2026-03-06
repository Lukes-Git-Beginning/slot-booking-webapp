# -*- coding: utf-8 -*-
"""
Finanzberatung Models Tests
Tests for model instantiation, constraints, enums, relationships, and DSGVO fields.

Note: SQLAlchemy SAEnum(native_enum=False) stores enum NAMES (ACTIVE) not
values (active). Tests pass enum members directly and compare enum members.
"""

import pytest
from datetime import datetime, timedelta


@pytest.mark.database
class TestFinanzSessionModel:
    """Test suite for FinanzSession model."""

    def test_create_session_minimal(self, db_session):
        """Test creating a session with minimal required fields."""
        from app.models.finanzberatung import FinanzSession, SessionStatus

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Mueller, Hans',
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()

        assert session.id is not None
        assert session.opener_username == 'test.opener'
        assert session.customer_name == 'Mueller, Hans'
        assert session.status == SessionStatus.ACTIVE

    def test_create_session_all_fields(self, db_session):
        """Test creating a session with all fields populated."""
        from app.models.finanzberatung import FinanzSession, SessionStatus

        now = datetime.utcnow()
        session = FinanzSession(
            opener_username='test.opener',
            closer_username='test.closer',
            customer_name='Schmidt, Anna',
            session_type='premium',
            appointment_date=now,
            status=SessionStatus.ACTIVE,
            t1_notes='Test notes T1',
            t2_notes='Test notes T2',
        )
        db_session.add(session)
        db_session.commit()

        assert session.closer_username == 'test.closer'
        assert session.session_type == 'premium'
        assert session.t1_notes == 'Test notes T1'

    def test_dsgvo_fields_default_none(self, db_session):
        """Test that DSGVO fields default to None."""
        from app.models.finanzberatung import FinanzSession, SessionStatus

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test Kunde',
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()

        assert session.deletion_requested_at is None
        assert session.deletion_requested_by is None
        assert session.files_deleted_at is None

    def test_dsgvo_fields_can_be_set(self, db_session):
        """Test that DSGVO fields can be populated."""
        from app.models.finanzberatung import FinanzSession, SessionStatus

        now = datetime.utcnow()
        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test Kunde',
            status=SessionStatus.DELETION_PENDING,
            deletion_requested_at=now,
            deletion_requested_by='admin.user',
        )
        db_session.add(session)
        db_session.commit()

        assert session.deletion_requested_at == now
        assert session.deletion_requested_by == 'admin.user'

    def test_transition_active_to_in_analysis(self):
        """Test valid status transition (no DB needed)."""
        from app.models.finanzberatung import FinanzSession, SessionStatus

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test',
            status=SessionStatus.ACTIVE,
        )
        session.transition_to(SessionStatus.IN_ANALYSIS)
        assert session.status == SessionStatus.IN_ANALYSIS

    def test_transition_to_deletion_pending(self):
        """Test transition to DELETION_PENDING (no DB needed)."""
        from app.models.finanzberatung import FinanzSession, SessionStatus

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test',
            status=SessionStatus.ACTIVE,
        )
        session.transition_to(SessionStatus.DELETION_PENDING)
        assert session.status == SessionStatus.DELETION_PENDING

    def test_invalid_transition_raises(self):
        """Test that invalid transitions raise ValueError (no DB needed)."""
        from app.models.finanzberatung import FinanzSession, SessionStatus

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test',
            status=SessionStatus.ACTIVE,
        )
        with pytest.raises(ValueError, match="Invalid transition"):
            session.transition_to(SessionStatus.VERIFIED)

    def test_to_dict(self, db_session):
        """Test model to_dict conversion."""
        from app.models.finanzberatung import FinanzSession, SessionStatus

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test',
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()

        d = session.to_dict()
        assert d['opener_username'] == 'test.opener'
        assert d['customer_name'] == 'Test'


@pytest.mark.database
class TestSessionStatusEnum:
    """Test SessionStatus enum values."""

    def test_all_statuses_exist(self):
        """Test that all expected statuses are defined."""
        from app.models.finanzberatung import SessionStatus

        expected = {'active', 'in_analysis', 'analyzed', 'verified', 'deletion_pending', 'archived'}
        actual = {s.value for s in SessionStatus}
        assert expected == actual

    def test_deletion_pending_status(self):
        """Test the new DELETION_PENDING status."""
        from app.models.finanzberatung import SessionStatus

        assert SessionStatus.DELETION_PENDING.value == 'deletion_pending'

    def test_valid_transitions_include_deletion_pending(self):
        """Test that DELETION_PENDING is reachable from all active states."""
        from app.models.finanzberatung import FinanzSession, SessionStatus

        for status in [SessionStatus.ACTIVE, SessionStatus.IN_ANALYSIS,
                       SessionStatus.ANALYZED, SessionStatus.VERIFIED]:
            allowed = FinanzSession.VALID_TRANSITIONS.get(status, [])
            assert SessionStatus.DELETION_PENDING in allowed, (
                f"DELETION_PENDING not reachable from {status.value}"
            )


@pytest.mark.database
class TestDocumentTypeEnum:
    """Test DocumentType enum completeness."""

    def test_document_type_count(self):
        """Test that all 40+ document types are defined."""
        from app.models.finanzberatung import DocumentType

        assert len(DocumentType) >= 40

    def test_legacy_types_exist(self):
        """Test that legacy document types are preserved."""
        from app.models.finanzberatung import DocumentType

        legacy = ['renteninfo', 'depot', 'versicherung', 'steuerbescheid',
                  'gehaltsabrechnung', 'kontoauszug', 'sonstige']
        for t in legacy:
            assert DocumentType(t) is not None

    def test_new_categories_exist(self):
        """Test representative types from each new category."""
        from app.models.finanzberatung import DocumentType

        sample_types = [
            'privathaftpflicht', 'kfz_auto', 'riester', 'bu',
            'zzv', 'gewerbeversicherung',
        ]
        for t in sample_types:
            assert DocumentType(t) is not None


@pytest.mark.database
class TestDocumentStatusEnum:
    """Test DocumentStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all statuses including EMBEDDING/EMBEDDED exist."""
        from app.models.finanzberatung import DocumentStatus

        expected = {
            'uploaded', 'extracting', 'extracted', 'classifying', 'classified',
            'embedding', 'embedded', 'analyzing', 'analyzed', 'error',
        }
        actual = {s.value for s in DocumentStatus}
        assert expected == actual


@pytest.mark.database
class TestFinanzDocumentModel:
    """Test FinanzDocument model."""

    def test_create_document(self, db_session):
        """Test creating a document linked to a session."""
        from app.models.finanzberatung import (
            FinanzSession, FinanzDocument, SessionStatus, DocumentStatus,
        )

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test',
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()

        doc = FinanzDocument(
            session_id=session.id,
            original_filename='test.pdf',
            stored_filename='abc123_test.pdf',
            file_hash='sha256abcdef',
            file_size=1024,
            mime_type='application/pdf',
            status=DocumentStatus.UPLOADED,
        )
        db_session.add(doc)
        db_session.commit()

        assert doc.id is not None
        assert doc.session_id == session.id
        assert doc.original_filename == 'test.pdf'


@pytest.mark.database
class TestFinanzExtractedDataModel:
    """Test FinanzExtractedData model."""

    def test_create_extracted_data(self, db_session):
        """Test creating extracted data with verification fields."""
        from app.models.finanzberatung import (
            FinanzSession, FinanzDocument, FinanzExtractedData,
            SessionStatus, DocumentStatus,
        )

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test',
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()

        doc = FinanzDocument(
            session_id=session.id,
            original_filename='test.pdf',
            stored_filename='abc_test.pdf',
            file_hash='hash123',
            file_size=512,
            mime_type='application/pdf',
            status=DocumentStatus.EXTRACTED,
        )
        db_session.add(doc)
        db_session.commit()

        data = FinanzExtractedData(
            document_id=doc.id,
            field_name='gesellschaft',
            field_value='Allianz',
            field_type='string',
            confidence=0.95,
            verified=False,
        )
        db_session.add(data)
        db_session.commit()

        assert data.id is not None
        assert data.verified is False
        assert data.verified_by is None
        assert data.verified_at is None

    def test_verified_fields(self, db_session):
        """Test setting verification fields."""
        from app.models.finanzberatung import (
            FinanzSession, FinanzDocument, FinanzExtractedData,
            SessionStatus, DocumentStatus,
        )

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test',
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()

        doc = FinanzDocument(
            session_id=session.id,
            original_filename='v.pdf',
            stored_filename='v_stored.pdf',
            file_hash='hash456',
            file_size=256,
            mime_type='application/pdf',
            status=DocumentStatus.EXTRACTED,
        )
        db_session.add(doc)
        db_session.commit()

        now = datetime.utcnow()
        data = FinanzExtractedData(
            document_id=doc.id,
            field_name='beitrag',
            field_value='150.00',
            field_type='currency',
            confidence=0.85,
            verified=True,
            verified_by='admin.user',
            verified_at=now,
        )
        db_session.add(data)
        db_session.commit()

        assert data.verified is True
        assert data.verified_by == 'admin.user'
        assert data.verified_at == now


@pytest.mark.database
class TestRelationships:
    """Test model relationships."""

    def test_session_to_documents(self, db_session):
        """Test session -> documents relationship."""
        from app.models.finanzberatung import (
            FinanzSession, FinanzDocument, SessionStatus, DocumentStatus,
        )

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test',
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()

        doc1 = FinanzDocument(
            session_id=session.id,
            original_filename='doc1.pdf',
            stored_filename='s_doc1.pdf',
            file_hash='h1',
            file_size=100,
            mime_type='application/pdf',
            status=DocumentStatus.UPLOADED,
        )
        doc2 = FinanzDocument(
            session_id=session.id,
            original_filename='doc2.pdf',
            stored_filename='s_doc2.pdf',
            file_hash='h2',
            file_size=200,
            mime_type='application/pdf',
            status=DocumentStatus.UPLOADED,
        )
        db_session.add_all([doc1, doc2])
        db_session.commit()

        docs = session.documents.all()
        assert len(docs) == 2

    def test_document_to_extracted_data(self, db_session):
        """Test document -> extracted_data relationship."""
        from app.models.finanzberatung import (
            FinanzSession, FinanzDocument, FinanzExtractedData,
            SessionStatus, DocumentStatus,
        )

        session = FinanzSession(
            opener_username='test.opener',
            customer_name='Test',
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()

        doc = FinanzDocument(
            session_id=session.id,
            original_filename='test.pdf',
            stored_filename='st.pdf',
            file_hash='hx',
            file_size=50,
            mime_type='application/pdf',
            status=DocumentStatus.EXTRACTED,
        )
        db_session.add(doc)
        db_session.commit()

        ed = FinanzExtractedData(
            document_id=doc.id,
            field_name='gesellschaft',
            field_value='HDI',
            field_type='string',
            confidence=0.9,
        )
        db_session.add(ed)
        db_session.commit()

        extracted = doc.extracted_data.all()
        assert len(extracted) == 1
        assert extracted[0].field_value == 'HDI'
