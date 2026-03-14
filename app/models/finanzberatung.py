# -*- coding: utf-8 -*-
"""
Finanzberatung Models - Financial Advisory Session Management

Models:
- FinanzSession: Root aggregate for a financial advisory session
- FinanzUploadToken: QR-based upload tokens for customer document upload
- FinanzDocument: Uploaded documents with classification and extraction status
- FinanzExtractedData: Structured data extracted from documents
- FinanzScorecard: Traffic-light scorecard per category
- FinanzTaskTracking: Celery task tracking for async processing
"""

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SessionStatus(enum.Enum):
    ACTIVE = 'active'
    IN_ANALYSIS = 'in_analysis'
    ANALYZED = 'analyzed'
    VERIFIED = 'verified'
    DELETION_PENDING = 'deletion_pending'
    ARCHIVED = 'archived'


class TokenType(enum.Enum):
    T1 = 't1'
    FOLLOWUP = 'followup'
    T2 = 't2'


class DocumentType(enum.Enum):
    # Legacy types (Phase 1-2)
    RENTENINFO = 'renteninfo'
    DEPOT = 'depot'
    VERSICHERUNG = 'versicherung'
    STEUERBESCHEID = 'steuerbescheid'
    GEHALTSABRECHNUNG = 'gehaltsabrechnung'
    KONTOAUSZUG = 'kontoauszug'
    SONSTIGE = 'sonstige'
    # Sachversicherungen
    PRIVATHAFTPFLICHT = 'privathaftpflicht'
    HAUSRAT = 'hausrat'
    GLASBRUCH = 'glasbruch'
    WOHNGEBAEUDE = 'wohngebaeude'
    RECHTSSCHUTZ = 'rechtsschutz'
    HAUSBESITZERHAFTPFLICHT = 'hausbesitzerhaftpflicht'
    TIERHALTERHAFTPFLICHT = 'tierhalterhaftpflicht'
    # KFZ
    KFZ_AUTO = 'kfz_auto'
    KFZ_MOTORRAD = 'kfz_motorrad'
    KFZ_ANHAENGER = 'kfz_anhaenger'
    # Altersvorsorge
    RIESTER = 'riester'
    BASISRENTE = 'basisrente'
    FONDSGEBUNDENE_RV = 'fondsgebundene_rv'
    INDEX_RV = 'index_rv'
    KAPITALLEBENSVERSICHERUNG = 'kapitallebensversicherung'
    BAV = 'bav'
    BAUSPARVERTRAG = 'bausparvertrag'
    SPARKONTO = 'sparkonto'
    DEPOTANLAGEN = 'depotanlagen'
    WOHN_RIESTER_BSV = 'wohn_riester_bsv'
    WOHN_RIESTER_DEPOT = 'wohn_riester_depot'
    # Absicherung
    BU = 'bu'
    GRUNDFAEHIGKEITEN = 'grundfaehigkeiten'
    DREAD_DISEASE = 'dread_disease'
    SCHULUNFAEHIGKEIT = 'schulunfaehigkeit'
    EXISTENZSCHUTZ = 'existenzschutz'
    ERWERBSUNFAEHIGKEIT = 'erwerbsunfaehigkeit'
    RLV = 'rlv'
    STERBEGELD = 'sterbegeld'
    UNFALLVERSICHERUNG = 'unfallversicherung'
    # Gesundheit & Zusatz
    ZZV = 'zzv'
    KTG = 'ktg'
    AKZ = 'akz'
    SKZ = 'skz'
    PTG = 'ptg'
    ARKV = 'arkv'
    # Sonstiges
    GEWERBEVERSICHERUNG = 'gewerbeversicherung'
    REISEHAFTPFLICHT = 'reisehaftpflicht'
    REISEGEPAECK = 'reisegepaeck'
    TIERKRANKENVERSICHERUNG = 'tierkrankenversicherung'


class DocumentStatus(enum.Enum):
    UPLOADED = 'uploaded'
    EXTRACTING = 'extracting'
    EXTRACTED = 'extracted'
    CLASSIFYING = 'classifying'
    CLASSIFIED = 'classified'
    EMBEDDING = 'embedding'
    EMBEDDED = 'embedded'
    ANALYZING = 'analyzing'
    ANALYZED = 'analyzed'
    ERROR = 'error'


class TaskStatus(enum.Enum):
    PENDING = 'pending'
    STARTED = 'started'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILURE = 'failure'
    RETRY = 'retry'
    REVOKED = 'revoked'


class ScorecardCategory(enum.Enum):
    ALTERSVORSORGE = 'altersvorsorge'
    ABSICHERUNG = 'absicherung'
    VERMOEGEN_KOSTEN = 'vermoegen_kosten'
    STEUEROPTIMIERUNG = 'steueroptimierung'


class TrafficLight(enum.Enum):
    RED = 'red'
    YELLOW = 'yellow'
    GREEN = 'green'


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FinanzSession(Base):
    """
    Root aggregate for a financial advisory session.

    A session represents one customer's financial analysis lifecycle,
    from document upload through analysis to verified scorecard.
    """

    __tablename__ = 'finanz_sessions'

    opener_username: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    closer_username: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    customer_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    session_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default='standard'
    )
    appointment_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    status: Mapped[str] = mapped_column(
        SAEnum(SessionStatus, native_enum=False, name='finanz_session_status'),
        default=SessionStatus.ACTIVE,
        nullable=False
    )
    t1_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    t2_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # DSGVO deletion tracking
    deletion_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    deletion_requested_by: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    files_deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Relationships (cascade from root aggregate)
    tokens = relationship(
        'FinanzUploadToken', back_populates='session',
        cascade='all, delete-orphan', lazy='dynamic'
    )
    documents = relationship(
        'FinanzDocument', back_populates='session',
        cascade='all, delete-orphan', lazy='dynamic'
    )
    scorecards = relationship(
        'FinanzScorecard', back_populates='session',
        cascade='all, delete-orphan', lazy='dynamic'
    )
    tasks = relationship(
        'FinanzTaskTracking', back_populates='session',
        cascade='all, delete-orphan', lazy='dynamic'
    )
    foerderfragebogen = relationship(
        'FinanzFoerderFragebogen', back_populates='session',
        uselist=False, cascade='all, delete-orphan'
    )

    # Valid status transitions
    VALID_TRANSITIONS = {
        SessionStatus.ACTIVE: [SessionStatus.IN_ANALYSIS, SessionStatus.DELETION_PENDING, SessionStatus.ARCHIVED],
        SessionStatus.IN_ANALYSIS: [SessionStatus.ANALYZED, SessionStatus.ACTIVE, SessionStatus.DELETION_PENDING, SessionStatus.ARCHIVED],
        SessionStatus.ANALYZED: [SessionStatus.VERIFIED, SessionStatus.IN_ANALYSIS, SessionStatus.DELETION_PENDING, SessionStatus.ARCHIVED],
        SessionStatus.VERIFIED: [SessionStatus.DELETION_PENDING, SessionStatus.ARCHIVED],
        SessionStatus.DELETION_PENDING: [SessionStatus.ARCHIVED],
        SessionStatus.ARCHIVED: [SessionStatus.ACTIVE],
    }

    def transition_to(self, new_status: SessionStatus) -> None:
        """
        Transition session to a new status with validation.

        Args:
            new_status: The target SessionStatus

        Raises:
            ValueError: If the transition is not allowed
        """
        if isinstance(self.status, SessionStatus):
            current = self.status
        else:
            try:
                current = SessionStatus[self.status]
            except KeyError:
                current = SessionStatus(self.status)
        allowed = self.VALID_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition from {current.name} to {new_status.name}. "
                f"Allowed: {[s.name for s in allowed]}"
            )
        self.status = new_status

    __table_args__ = (
        Index('idx_finanz_sessions_opener', 'opener_username'),
        Index('idx_finanz_sessions_status', 'status'),
        Index('idx_finanz_sessions_appointment', 'appointment_date'),
    )

    def __repr__(self) -> str:
        return (
            f"<FinanzSession(id={self.id}, customer='{self.customer_name}', "
            f"status='{self.status}')>"
        )


class FinanzUploadToken(Base):
    """
    QR-based upload token for customer document upload.

    Customers scan a QR code containing this token to upload
    documents without needing an account.
    """

    __tablename__ = 'finanz_upload_tokens'

    session_id: Mapped[int] = mapped_column(
        ForeignKey('finanz_sessions.id'), nullable=False
    )
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    token_type: Mapped[str] = mapped_column(
        SAEnum(TokenType, native_enum=False, name='finanz_token_type'),
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
    upload_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    max_uploads: Mapped[int] = mapped_column(
        Integer, default=20, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Relationship
    session = relationship('FinanzSession', back_populates='tokens')

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_exhausted(self) -> bool:
        """Check if the upload limit has been reached."""
        return self.upload_count >= self.max_uploads

    @property
    def is_valid(self) -> bool:
        """Check if the token is still usable (active, not expired, not exhausted)."""
        return self.is_active and not self.is_expired and not self.is_exhausted

    __table_args__ = (
        Index('idx_finanz_tokens_token', 'token'),
        Index('idx_finanz_tokens_expires', 'expires_at'),
    )

    def __repr__(self) -> str:
        return (
            f"<FinanzUploadToken(id={self.id}, token='{self.token[:8]}...', "
            f"type='{self.token_type}', valid={self.is_valid})>"
        )


class FinanzDocument(Base):
    """
    Uploaded financial document with classification and extraction status.

    Tracks the full lifecycle from upload through OCR extraction,
    classification, and embedding.
    """

    __tablename__ = 'finanz_documents'

    session_id: Mapped[int] = mapped_column(
        ForeignKey('finanz_sessions.id'), nullable=False
    )
    token_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('finanz_upload_tokens.id'), nullable=True
    )
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    stored_filename: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    file_size: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    mime_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    document_type: Mapped[Optional[str]] = mapped_column(
        SAEnum(DocumentType, native_enum=False, name='finanz_document_type'),
        nullable=True
    )
    status: Mapped[str] = mapped_column(
        SAEnum(DocumentStatus, native_enum=False, name='finanz_document_status'),
        default=DocumentStatus.UPLOADED,
        nullable=False
    )
    classification_confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    page_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # Relationships
    session = relationship('FinanzSession', back_populates='documents')
    extracted_data = relationship(
        'FinanzExtractedData', back_populates='document',
        cascade='all, delete-orphan', lazy='dynamic'
    )

    __table_args__ = (
        Index('idx_finanz_documents_session', 'session_id'),
        Index('idx_finanz_documents_hash', 'file_hash'),
        Index('idx_finanz_documents_status', 'status'),
    )

    def __repr__(self) -> str:
        return (
            f"<FinanzDocument(id={self.id}, filename='{self.original_filename}', "
            f"status='{self.status}')>"
        )


class FinanzExtractedData(Base):
    """
    Structured data extracted from a financial document.

    Each row represents a single field extracted by the LLM,
    with confidence score and source reference.
    """

    __tablename__ = 'finanz_extracted_data'

    document_id: Mapped[int] = mapped_column(
        ForeignKey('finanz_documents.id'), nullable=False
    )
    field_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    field_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    field_type: Mapped[str] = mapped_column(
        String(50), default='string', nullable=False
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    source_page: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    source_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    verified_by: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Relationship
    document = relationship('FinanzDocument', back_populates='extracted_data')

    __table_args__ = (
        Index('idx_finanz_extracted_document', 'document_id'),
        Index('idx_finanz_extracted_field', 'field_name'),
    )

    def __repr__(self) -> str:
        return (
            f"<FinanzExtractedData(id={self.id}, field='{self.field_name}', "
            f"value='{str(self.field_value)[:30]}')>"
        )


class FinanzScorecard(Base):
    """
    Traffic-light scorecard for a financial advisory category.

    Each session can have multiple scorecards (one per category)
    plus an optional overall aggregate score.
    """

    __tablename__ = 'finanz_scorecards'

    session_id: Mapped[int] = mapped_column(
        ForeignKey('finanz_sessions.id'), nullable=False
    )
    category: Mapped[str] = mapped_column(
        SAEnum(ScorecardCategory, native_enum=False, name='finanz_scorecard_category'),
        nullable=False
    )
    rating: Mapped[str] = mapped_column(
        SAEnum(TrafficLight, native_enum=False, name='finanz_traffic_light'),
        nullable=False
    )
    assessment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    details: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    is_overall: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationship
    session = relationship('FinanzSession', back_populates='scorecards')

    __table_args__ = (
        Index('idx_finanz_scorecards_session', 'session_id'),
    )

    def __repr__(self) -> str:
        return (
            f"<FinanzScorecard(id={self.id}, category='{self.category}', "
            f"rating='{self.rating}')>"
        )


class FinanzFoerderFragebogen(Base):
    """
    Structured subsidy questionnaire for a financial advisory session.

    Captures customer data needed to determine eligibility for German
    subsidy programs (Riester, Rürup, BAV, VL, KfW, etc.).
    """

    __tablename__ = 'finanz_foerderfragebogen'

    session_id: Mapped[int] = mapped_column(
        ForeignKey('finanz_sessions.id'), unique=True, nullable=False
    )

    # Step 1: Persoenliche Daten
    geburtsdatum: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    familienstand: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    kinder_anzahl: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kinder_geburtsjahre: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Step 2: Berufliche Situation
    beschaeftigung: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    rv_pflichtig: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    bruttojahreseinkommen: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    zve: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    arbeitgeber_vl: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    arbeitgeber_bav: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Step 3: Kinder & Familie
    kinder_im_haushalt_u18: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kinder_in_ausbildung: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    v0800_beantragt: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    schwangerschaft_geplant: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Step 4: Wohnsituation
    wohnsituation: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    immobilie_geplant: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    bausparvertrag: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Step 5: Bestehende Vorsorge
    hat_riester: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    hat_ruerup: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    hat_bav: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    hat_bu: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    hat_pflegezusatz: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    hat_vl_vertrag: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Ergebnis
    eligible_foerderungen: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    potential_yearly_benefit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Meta
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationship
    session = relationship('FinanzSession', back_populates='foerderfragebogen')

    __table_args__ = (
        Index('idx_finanz_ffb_session', 'session_id'),
    )

    def to_answers_dict(self) -> dict:
        """Convert model fields to dict for eligibility calculation."""
        return {
            'geburtsdatum': self.geburtsdatum,
            'familienstand': self.familienstand,
            'kinder_anzahl': self.kinder_anzahl,
            'kinder_geburtsjahre': self.kinder_geburtsjahre,
            'beschaeftigung': self.beschaeftigung,
            'rv_pflichtig': self.rv_pflichtig,
            'bruttojahreseinkommen': self.bruttojahreseinkommen,
            'zve': self.zve,
            'arbeitgeber_vl': self.arbeitgeber_vl,
            'arbeitgeber_bav': self.arbeitgeber_bav,
            'kinder_im_haushalt_u18': self.kinder_im_haushalt_u18,
            'kinder_in_ausbildung': self.kinder_in_ausbildung,
            'v0800_beantragt': self.v0800_beantragt,
            'schwangerschaft_geplant': self.schwangerschaft_geplant,
            'wohnsituation': self.wohnsituation,
            'immobilie_geplant': self.immobilie_geplant,
            'bausparvertrag': self.bausparvertrag,
            'hat_riester': self.hat_riester,
            'hat_ruerup': self.hat_ruerup,
            'hat_bav': self.hat_bav,
            'hat_bu': self.hat_bu,
            'hat_pflegezusatz': self.hat_pflegezusatz,
            'hat_vl_vertrag': self.hat_vl_vertrag,
        }

    def __repr__(self) -> str:
        return (
            f"<FinanzFoerderFragebogen(id={self.id}, session_id={self.session_id}, "
            f"completed={'yes' if self.completed_at else 'no'})>"
        )


class FinanzTaskTracking(Base):
    """
    Celery task tracking for async document processing.

    Tracks the lifecycle of background tasks (extraction, classification,
    embedding, analysis) with retry tracking and error capture.
    """

    __tablename__ = 'finanz_tasks'

    session_id: Mapped[int] = mapped_column(
        ForeignKey('finanz_sessions.id'), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    task_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    status: Mapped[str] = mapped_column(
        SAEnum(TaskStatus, native_enum=False, name='finanz_task_status'),
        default=TaskStatus.PENDING,
        nullable=False
    )
    result: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Relationship
    session = relationship('FinanzSession', back_populates='tasks')

    __table_args__ = (
        Index('idx_finanz_tasks_session', 'session_id'),
        Index('idx_finanz_tasks_celery_id', 'task_id'),
        Index('idx_finanz_tasks_status', 'status'),
    )

    def __repr__(self) -> str:
        return (
            f"<FinanzTaskTracking(id={self.id}, task='{self.task_name}', "
            f"status='{self.status}')>"
        )
