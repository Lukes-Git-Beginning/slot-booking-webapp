---
phase: 01-foundation
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - app/models/finanzberatung.py
  - app/models/__init__.py
autonomous: true
requirements: [FOUND-02]
must_haves:
  truths:
    - "6 models exist: FinanzSession, FinanzUploadToken, FinanzDocument, FinanzExtractedData, FinanzScorecard, FinanzTaskTracking"
    - "All tables use finanz_ prefix: finanz_sessions, finanz_upload_tokens, finanz_documents, finanz_extracted_data, finanz_scorecards, finanz_tasks"
    - "User references are String(100), NO ForeignKey (opener_username, closer_username)"
    - "Within-module relationships use proper integer FKs with cascade='all, delete-orphan'"
    - "Enums use native_enum=False with explicit name= argument (finanz_ prefix)"
    - "FinanzSession has VALID_TRANSITIONS dict and transition_to() method"
    - "All 6 models are registered in app/models/__init__.py and listed in __all__"
    - "No id, created_at, or updated_at redefined (inherited from Base)"
  artifacts:
    - app/models/finanzberatung.py (new -- 6 models)
    - app/models/__init__.py (modified -- new imports and __all__ entries)
  key_links:
    - "FinanzSession is root aggregate; all other models FK back to session_id"
    - "Models registered in __init__.py so Alembic autogenerate detects them"
    - "Base class from app/models/base.py provides id, created_at, updated_at automatically"
---

<objective>
Create all 6 Finanzberatung database models and register them for Alembic migration.

Purpose: The database schema is the foundation for all Finanzberatung data -- sessions, upload tokens, documents, extracted data, scorecards, and task tracking. All subsequent phases depend on these models.

Output: New `app/models/finanzberatung.py` with 6 models, updated `app/models/__init__.py` with registrations.
</objective>

<execution_context>
@C:/Users/Luke/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Luke/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation/01-CONTEXT.md
@.planning/phases/01-foundation/01-RESEARCH.md

<interfaces>
<!-- Base class that all models inherit from (DO NOT redefine id/created_at/updated_at) -->

From app/models/base.py:
```python
class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict[str, Any]: ...
```

From app/models/__init__.py (registration pattern):
```python
# Import section example:
from app.models.booking import (
    Booking,
    BookingOutcome
)

# __all__ section example:
__all__ = [
    # ...
    'Booking',
    'BookingOutcome',
    # ...
]
```

Existing model pattern (from app/models/booking.py, t2_booking.py):
- Uses `Mapped[type]` with `mapped_column()` (SQLAlchemy 2.0 style)
- String-based user references, no FK to users
- `Index()` objects in `__table_args__`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create app/models/finanzberatung.py with all 6 models</name>
  <files>app/models/finanzberatung.py</files>
  <action>
Create `app/models/finanzberatung.py` with ALL 6 models in a single file. Follow the exact patterns from the research document.

**Enums (define at top, before model classes):**

1. `SessionStatus` -- ACTIVE, IN_ANALYSIS, ANALYZED, VERIFIED, ARCHIVED
2. `TokenType` -- T1, FOLLOWUP, T2
3. `DocumentType` -- RENTENINFO, DEPOT, VERSICHERUNG, STEUERBESCHEID, GEHALTSABRECHNUNG, KONTOAUSZUG, SONSTIGE
4. `DocumentStatus` -- UPLOADED, EXTRACTING, EXTRACTED, CLASSIFYING, CLASSIFIED, EMBEDDING, EMBEDDED, ANALYZING, ANALYZED, ERROR
5. `TaskStatus` -- PENDING, STARTED, RUNNING, SUCCESS, FAILURE, RETRY, REVOKED
6. `ScorecardCategory` -- ALTERSVORSORGE, ABSICHERUNG, VERMOEGEN_KOSTEN, STEUEROPTIMIERUNG
7. `TrafficLight` -- RED, YELLOW, GREEN

All enums: `enum.Enum` subclass. All used via `SAEnum(MyEnum, native_enum=False, name="finanz_xxx")`.

**Models:**

1. **FinanzSession** (`finanz_sessions`):
   - `opener_username: Mapped[str]` -- String(100), nullable=False, indexed
   - `closer_username: Mapped[Optional[str]]` -- String(100), nullable=True
   - `customer_name: Mapped[str]` -- String(200), nullable=False
   - `session_type: Mapped[str]` -- String(50), nullable=False, default="standard"
   - `appointment_date: Mapped[Optional[datetime]]` -- DateTime, nullable=True
   - `status: Mapped[str]` -- SAEnum(SessionStatus, native_enum=False, name="finanz_session_status"), default=SessionStatus.ACTIVE.value
   - `t1_notes: Mapped[Optional[str]]` -- Text, nullable=True
   - `t2_notes: Mapped[Optional[str]]` -- Text, nullable=True
   - Relationships: `tokens`, `documents`, `scorecards`, `tasks` (all with cascade="all, delete-orphan")
   - `VALID_TRANSITIONS` dict and `transition_to(new_status)` method
   - Indexes: `idx_finanz_sessions_opener` (opener_username), `idx_finanz_sessions_status` (status), `idx_finanz_sessions_appointment` (appointment_date)

2. **FinanzUploadToken** (`finanz_upload_tokens`):
   - `session_id: Mapped[int]` -- ForeignKey("finanz_sessions.id"), nullable=False
   - `token: Mapped[str]` -- String(64), unique=True, nullable=False, indexed
   - `token_type: Mapped[str]` -- SAEnum(TokenType, native_enum=False, name="finanz_token_type"), nullable=False
   - `expires_at: Mapped[datetime]` -- DateTime, nullable=False
   - `upload_count: Mapped[int]` -- Integer, default=0
   - `max_uploads: Mapped[int]` -- Integer, default=20
   - `is_active: Mapped[bool]` -- Boolean, default=True
   - Relationship: `session` (back_populates="tokens")
   - Indexes: `idx_finanz_tokens_token` (token), `idx_finanz_tokens_expires` (expires_at)
   - Add `@property is_expired` that checks `datetime.utcnow() > self.expires_at`
   - Add `@property is_exhausted` that checks `self.upload_count >= self.max_uploads`
   - Add `@property is_valid` that returns `self.is_active and not self.is_expired and not self.is_exhausted`

3. **FinanzDocument** (`finanz_documents`):
   - `session_id: Mapped[int]` -- ForeignKey("finanz_sessions.id"), nullable=False
   - `token_id: Mapped[Optional[int]]` -- ForeignKey("finanz_upload_tokens.id"), nullable=True
   - `original_filename: Mapped[str]` -- String(255), nullable=False
   - `stored_filename: Mapped[str]` -- String(255), unique=True, nullable=False (UUID-based)
   - `file_hash: Mapped[str]` -- String(64), nullable=False (SHA-256)
   - `file_size: Mapped[int]` -- Integer, nullable=False (bytes)
   - `mime_type: Mapped[str]` -- String(100), nullable=False
   - `document_type: Mapped[Optional[str]]` -- SAEnum(DocumentType, native_enum=False, name="finanz_document_type"), nullable=True (set after classification)
   - `status: Mapped[str]` -- SAEnum(DocumentStatus, native_enum=False, name="finanz_document_status"), default=DocumentStatus.UPLOADED.value
   - `classification_confidence: Mapped[Optional[float]]` -- Float, nullable=True
   - `extracted_text: Mapped[Optional[str]]` -- Text, nullable=True
   - `page_count: Mapped[Optional[int]]` -- Integer, nullable=True
   - Relationships: `session` (back_populates="documents"), `extracted_data` (cascade="all, delete-orphan")
   - Indexes: `idx_finanz_documents_session` (session_id), `idx_finanz_documents_hash` (file_hash), `idx_finanz_documents_status` (status)

4. **FinanzExtractedData** (`finanz_extracted_data`):
   - `document_id: Mapped[int]` -- ForeignKey("finanz_documents.id"), nullable=False
   - `field_name: Mapped[str]` -- String(100), nullable=False (e.g., "monatliche_rente", "depot_wert")
   - `field_value: Mapped[Optional[str]]` -- Text, nullable=True (stored as string, parsed by consumers)
   - `field_type: Mapped[str]` -- String(50), default="string" (string, number, date, currency)
   - `confidence: Mapped[Optional[float]]` -- Float, nullable=True (0.0 - 1.0)
   - `source_page: Mapped[Optional[int]]` -- Integer, nullable=True
   - `source_text: Mapped[Optional[str]]` -- Text, nullable=True (the text snippet the value was extracted from)
   - Relationship: `document` (back_populates="extracted_data")
   - Indexes: `idx_finanz_extracted_document` (document_id), `idx_finanz_extracted_field` (field_name)

5. **FinanzScorecard** (`finanz_scorecards`):
   - `session_id: Mapped[int]` -- ForeignKey("finanz_sessions.id"), nullable=False
   - `category: Mapped[str]` -- SAEnum(ScorecardCategory, native_enum=False, name="finanz_scorecard_category"), nullable=False
   - `rating: Mapped[str]` -- SAEnum(TrafficLight, native_enum=False, name="finanz_traffic_light"), nullable=False
   - `assessment: Mapped[Optional[str]]` -- Text, nullable=True (qualitative description)
   - `details: Mapped[Optional[str]]` -- Text, nullable=True (JSON string with breakdown data)
   - `is_overall: Mapped[bool]` -- Boolean, default=False (True for aggregated overall score)
   - Relationship: `session` (back_populates="scorecards")
   - Indexes: `idx_finanz_scorecards_session` (session_id)

6. **FinanzTaskTracking** (`finanz_tasks`):
   - `session_id: Mapped[int]` -- ForeignKey("finanz_sessions.id"), nullable=False
   - `task_id: Mapped[str]` -- String(255), nullable=False (Celery task ID)
   - `task_name: Mapped[str]` -- String(100), nullable=False (e.g., "extract_text", "classify_document")
   - `status: Mapped[str]` -- SAEnum(TaskStatus, native_enum=False, name="finanz_task_status"), default=TaskStatus.PENDING.value
   - `result: Mapped[Optional[str]]` -- Text, nullable=True (JSON string)
   - `error: Mapped[Optional[str]]` -- Text, nullable=True
   - `started_at: Mapped[Optional[datetime]]` -- DateTime, nullable=True
   - `completed_at: Mapped[Optional[datetime]]` -- DateTime, nullable=True
   - `retry_count: Mapped[int]` -- Integer, default=0
   - Relationship: `session` (back_populates="tasks")
   - Indexes: `idx_finanz_tasks_session` (session_id), `idx_finanz_tasks_celery_id` (task_id), `idx_finanz_tasks_status` (status)

**Critical rules:**
- Import `Base` from `app.models.base`
- Import `Mapped, mapped_column, relationship` from `sqlalchemy.orm`
- Import `String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Enum as SAEnum, Index` from `sqlalchemy`
- Import `Optional` from `typing` and `datetime` from `datetime`
- Import `enum` for Python enums
- Use `Mapped[Optional[type]]` for nullable fields
- Do NOT redefine `id`, `created_at`, or `updated_at` (inherited from Base)
- Use `__table_args__` tuple with Index objects (not inline `index=True` on columns that also need explicit naming)
- For simple indexed columns where the default index name is fine, `index=True` on mapped_column is acceptable
  </action>
  <verify>
    <automated>cd C:/Users/Luke/Documents/Slots/slot_booking_webapp && python -c "
from app.models.finanzberatung import (
    FinanzSession, FinanzUploadToken, FinanzDocument,
    FinanzExtractedData, FinanzScorecard, FinanzTaskTracking,
    SessionStatus, TokenType, DocumentType, DocumentStatus,
    TaskStatus, ScorecardCategory, TrafficLight
)
# Verify table names
assert FinanzSession.__tablename__ == 'finanz_sessions'
assert FinanzUploadToken.__tablename__ == 'finanz_upload_tokens'
assert FinanzDocument.__tablename__ == 'finanz_documents'
assert FinanzExtractedData.__tablename__ == 'finanz_extracted_data'
assert FinanzScorecard.__tablename__ == 'finanz_scorecards'
assert FinanzTaskTracking.__tablename__ == 'finanz_tasks'
# Verify enums
assert SessionStatus.ACTIVE.value == 'active'
assert TokenType.T1.value == 't1'
assert DocumentType.RENTENINFO.value == 'renteninfo'
assert TrafficLight.GREEN.value == 'green'
# Verify transition validation exists
assert hasattr(FinanzSession, 'VALID_TRANSITIONS')
assert hasattr(FinanzSession, 'transition_to')
# Verify token properties
assert hasattr(FinanzUploadToken, 'is_valid')
print('All 6 models + 7 enums verified OK')
"</automated>
  </verify>
  <done>
    - 6 models exist in app/models/finanzberatung.py with correct table names
    - 7 enums defined with native_enum=False and explicit name= argument
    - FinanzSession has VALID_TRANSITIONS and transition_to()
    - FinanzUploadToken has is_expired, is_exhausted, is_valid properties
    - All relationships defined with cascade="all, delete-orphan" from Session
    - No id/created_at/updated_at redefined
  </done>
</task>

<task type="auto">
  <name>Task 2: Register models in app/models/__init__.py</name>
  <files>app/models/__init__.py</files>
  <action>
Add the following import block after the existing T2 Booking import (after `from app.models.t2_booking import T2Booking`):

```python
# Finanzberatung Models
from app.models.finanzberatung import (
    FinanzSession,
    FinanzUploadToken,
    FinanzDocument,
    FinanzExtractedData,
    FinanzScorecard,
    FinanzTaskTracking,
)
```

Add the following entries to `__all__` list, after the `'T2Booking',` entry:

```python
    # Finanzberatung
    'FinanzSession',
    'FinanzUploadToken',
    'FinanzDocument',
    'FinanzExtractedData',
    'FinanzScorecard',
    'FinanzTaskTracking',
```

This ensures Alembic autogenerate detects all 6 new models via the `from app.models import *` in `alembic/env.py`.
  </action>
  <verify>
    <automated>cd C:/Users/Luke/Documents/Slots/slot_booking_webapp && python -c "
from app.models import (
    FinanzSession, FinanzUploadToken, FinanzDocument,
    FinanzExtractedData, FinanzScorecard, FinanzTaskTracking
)
from app.models import __all__ as model_all
assert 'FinanzSession' in model_all
assert 'FinanzTaskTracking' in model_all
print('Model registration OK')
"</automated>
  </verify>
  <done>
    - All 6 Finanzberatung models importable from app.models
    - All 6 model names listed in __all__
    - Existing model imports still work (no regressions)
  </done>
</task>

</tasks>

<verification>
1. `python -c "from app.models.finanzberatung import FinanzSession; print(FinanzSession.__tablename__)"` prints `finanz_sessions`
2. `python -c "from app.models import FinanzSession, FinanzDocument; print('imports OK')"` -- registration works
3. `python -c "from app.models import Base; tables = [t for t in Base.metadata.tables if t.startswith('finanz_')]; assert len(tables) == 6; print(f'{len(tables)} finanz tables registered')"` -- all 6 tables in metadata
4. `python -c "from app.models import Booking, T2Booking; print('existing models OK')"` -- no regressions
</verification>

<success_criteria>
- All 6 models exist with correct table names, columns, enums, relationships, and indexes
- Models are registered in __init__.py and detectable by Alembic autogenerate
- FinanzSession has status transition validation
- FinanzUploadToken has validity properties
- No regressions on existing models
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation/01-02-SUMMARY.md`
</output>
