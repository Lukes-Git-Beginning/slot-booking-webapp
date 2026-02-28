# Phase 1: Foundation - Research

**Researched:** 2026-02-28
**Domain:** Flask config, SQLAlchemy models, Celery task queue, Python dependency management
**Confidence:** HIGH

## Summary

Phase 1 is infrastructure-only: config class, 6 database models, Celery setup, and dependency installation. No UI, no routes, no business logic. The existing codebase has well-established patterns for all four areas -- config classes in `app/config/base.py`, SQLAlchemy 2.0 models in `app/models/`, extension init in `app/core/extensions.py`, and Alembic migrations in `alembic/`. The new Finanzberatung module follows these patterns exactly, with one key difference: **PG-only** (no JSON dual-write).

The Flask 3.1.x official documentation provides a `celery_init_app()` pattern that wraps tasks in Flask app context via a custom `FlaskTask` base class. This is the standard approach and maps directly to the user's decision of placing the init in `app/core/celery_init.py` and calling it from `init_extensions()`.

All required dependencies are already installed locally (Celery 5.6.2, pdfplumber 0.11.9, tiktoken 0.12.0, pytesseract 0.3.13, sentence-transformers 5.2.0, chromadb 1.4.0). The `celery[redis]` extra needs to be added to `requirements.txt`; ML packages go into a new `requirements-ml.txt`.

**Primary recommendation:** Follow existing codebase patterns exactly. The only net-new infrastructure is Celery -- everything else (config, models, migrations) has established templates in the codebase.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- New `FinanzConfig` class in `app/config/base.py` (follows HubSpotConfig pattern)
- Explicit `FINANZ_ENABLED=true/false` env var as master feature toggle
- Blueprint only registered when `FINANZ_ENABLED=true`
- Guard in three places: config class, blueprint registration, service init
- `FINANZ_LLM_ENABLED` flag: true = local vLLM (OpenAI-compatible API), false = keyword-based mock classification
- Token TTL defaults as specified: T1=2h (7200s), Followup=14d (1209600s), T2=2h (7200s) -- all env-var overridable
- Env var naming: `FINANZ_` prefix for all settings (FINANZ_LLM_MODEL, FINANZ_CACHE_TTL, etc.)
- Use existing `get_env_bool()`/`get_env_list()` helpers (move above class definitions so they're usable in class-level attrs)
- Single new file: `app/models/finanzberatung.py` with all 6 models
- Table name prefix: `finanz_` on all `__tablename__` values
- User reference: `opener_username`/`closer_username` as `String(100)` -- NO ForeignKey
- Within-module relationships: proper integer FKs + `relationship()` with `cascade="all, delete-orphan"`
- Enum handling: Python `enum.Enum` + SQLAlchemy `Enum(native_enum=False)` with explicit `name=` argument
- Status transition validation via `VALID_TRANSITIONS` dict on model class
- PG-only -- NO JSON dual-write for new models. Service raises RuntimeError if `USE_POSTGRES=false`
- Migration: Alembic `--autogenerate` for production; `create_all()` as safety net
- Index naming: `idx_finanz_{table}_{column(s)}`
- New `app/core/celery_init.py` with `celery_init_app()` function
- FlaskTask base class wraps all tasks in Flask app context
- Called from `init_extensions()` in `app/core/extensions.py`
- `celery_worker.py` at project root as worker entry point
- Redis DB separation: DB 0 = Sessions/Rate-Limiting (existing), DB 1 = Celery Broker, DB 2 = Celery Results
- `task_acks_late=True` + `task_reject_on_worker_lost=True` for reliability
- JSON serialization only (no pickle)
- `task_track_started=True` for monitoring
- Task definitions use `@shared_task` (not `@celery_app.task`) to avoid circular imports
- Task files in `app/services/` (document_tasks.py, analysis_tasks.py)
- Dev mode: `CELERY_TASK_ALWAYS_EAGER=true` -- tasks run synchronously, no worker needed
- Global `task_ignore_result=True`, opt-in per task with `ignore_result=False`
- `result_expires=86400` (24h TTL for results in Redis)
- Timezone: Europe/Berlin, `enable_utc=True`
- Split requirements: `requirements.txt` (base) + `requirements-ml.txt` (ML packages)
- Lazy imports for heavy packages: sentence-transformers and chromadb loaded on first use only
- pdfplumber and tiktoken imported at `init_app()` time
- pytesseract: import at init_app() with binary check via `get_tesseract_version()`
- PyTorch: CUDA build for production server, CPU-only for local dev
- Tesseract OCR: system dependency, not pip
- Celery: `celery[redis]` goes into base requirements.txt
- Model cache: `HF_HOME` env var to control Hugging Face model download location

### Claude's Discretion
- Exact FinanzConfig attribute list and default values (within the patterns decided above)
- Model field types and exact column definitions
- Celery task retry/timeout defaults per task type
- Index strategy (which columns to index beyond the obvious ones)
- Alembic migration file structure
- Test task implementation for verifying Celery connectivity

### Deferred Ideas (OUT OF SCOPE)
- **Platform-wide FK migration**: Rebuild all existing models with proper ForeignKey to Users table once PG migration reaches 100% -- separate milestone, not Finanzberatung scope
- **Server specs as central config**: Consider adding server hardware specs to a shared planning doc that all phases can reference
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | System loads FinanzberatungConfig with feature toggle, upload limits, token TTLs, LLM settings | Existing `HubSpotConfig` pattern in `app/config/base.py` (line 232-253); helper functions `get_env_bool()`/`get_env_list()` available at module level; singleton pattern at bottom of file |
| FOUND-02 | Database schema supports sessions, tokens, documents, extracted data, scorecards, and task tracking (6 models) | SQLAlchemy 2.0 `Mapped[]` pattern used throughout `app/models/`; `Base` class in `base.py` provides auto `id`/`created_at`/`updated_at`; Alembic autogenerate already configured in `alembic/env.py` with wildcard import; `Enum(native_enum=False)` verified working with explicit `name=` |
| FOUND-03 | Celery worker processes background tasks via Redis broker | Flask 3.1.x official `celery_init_app()` pattern verified; Celery 5.6.2 installed; Redis already used (DB 0) for sessions/rate-limiting; `init_extensions()` in `extensions.py` is the established integration point |
| FOUND-04 | Dependencies installed (celery, pytesseract, pdfplumber, sentence-transformers, chromadb, tiktoken) | All packages verified installed locally; Celery 5.6.2 (no `[redis]` extra yet in requirements.txt); pdfplumber 0.11.9, tiktoken 0.12.0, pytesseract 0.3.13, sentence-transformers 5.2.0, chromadb 1.4.0 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.1 | Web framework | Already in use; official Celery integration docs |
| SQLAlchemy | 2.0.45 | ORM / Database models | Already in use; 2.0 `Mapped[]` types throughout |
| Alembic | 1.18.0 | Database migrations | Already configured (`alembic/` dir, `alembic.ini`, `env.py`) |
| Celery | 5.6.2 | Distributed task queue | Already installed; Flask 3.1.x has official integration pattern |
| Redis | 6.4.0 (client) | Message broker + result backend | Already in use (DB 0 for sessions); `celery[redis]` extra needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pdfplumber | 0.11.9 | PDF text extraction | Phase 4 (Pipeline); imported at init_app() time |
| tiktoken | 0.12.0 | Token counting for chunking | Phase 4 (Pipeline); imported at init_app() time |
| pytesseract | 0.3.13 | OCR for scanned documents | Phase 4 (Pipeline); needs system Tesseract binary |
| sentence-transformers | 5.2.0 | Text embeddings | Phase 4 (Pipeline); lazy import (heavy, 3-8s load) |
| chromadb | 1.4.0 | Vector database | Phase 4 (Pipeline); lazy import (heavy) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Celery | RQ (Redis Queue) | RQ is simpler but lacks task chains, retry policies, and monitoring (Flower). Celery is standard for Flask + complex pipelines |
| chromadb | pgvector | pgvector keeps everything in PostgreSQL but requires extension install. ChromaDB is simpler for initial implementation |
| `native_enum=True` | `native_enum=False` | Native PG ENUM is faster but requires `CREATE TYPE` migration and can't be easily modified. VARCHAR+CHECK is safer with Alembic |

**Installation (for requirements.txt):**
```bash
# Add to requirements.txt (base)
celery[redis]>=5.4.0

# New requirements-ml.txt
pdfplumber>=0.11.0
tiktoken>=0.7.0
pytesseract>=0.3.10
sentence-transformers>=3.0.0
chromadb>=0.5.0
torch  # CUDA or CPU build depending on environment
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── config/
│   └── base.py              # Add FinanzConfig class + finanz_config singleton
├── core/
│   ├── extensions.py         # Add celery init call
│   └── celery_init.py        # NEW: celery_init_app() function
├── models/
│   ├── __init__.py           # Register new model imports
│   └── finanzberatung.py     # NEW: All 6 models
├── services/
│   ├── document_tasks.py     # NEW: Celery task stubs (Phase 4)
│   └── analysis_tasks.py     # NEW: Celery task stubs (Phase 4)
├── __init__.py               # Conditional blueprint registration
celery_worker.py              # NEW: Worker entry point (project root)
requirements.txt              # Add celery[redis]
requirements-ml.txt           # NEW: ML packages
alembic/versions/             # NEW: Migration file (autogenerate)
```

### Pattern 1: Config Class (from existing codebase)
**What:** Domain-specific config class with env var overrides and singleton instance
**When to use:** Every new module/domain
**Example:**
```python
# Source: app/config/base.py (HubSpotConfig pattern, line 232-253)
class FinanzConfig:
    """Konfiguration fuer Finanzberatungs-Modul"""
    FINANZ_ENABLED: bool = get_env_bool("FINANZ_ENABLED", False)
    FINANZ_LLM_ENABLED: bool = get_env_bool("FINANZ_LLM_ENABLED", False)
    FINANZ_TOKEN_TTL_T1: int = int(os.getenv("FINANZ_TOKEN_TTL_T1", "7200"))
    # ... more settings ...

# Singleton at bottom of file
finanz_config = FinanzConfig()
```

### Pattern 2: SQLAlchemy 2.0 Model (from existing codebase)
**What:** Declarative model with `Mapped[]` type annotations, inheriting from `Base`
**When to use:** All new database models
**Example:**
```python
# Source: app/models/booking.py, t2_booking.py, t2_bucket.py
from app.models.base import Base
from sqlalchemy import String, Integer, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

class SessionStatus(enum.Enum):
    ACTIVE = "active"
    IN_ANALYSIS = "in_analysis"
    ANALYZED = "analyzed"
    VERIFIED = "verified"
    ARCHIVED = "archived"

class FinanzSession(Base):
    __tablename__ = "finanz_sessions"

    # String ref to user (no FK -- consistent with existing models)
    opener_username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        SAEnum(SessionStatus, native_enum=False, name="finanz_session_status"),
        nullable=False,
        default=SessionStatus.ACTIVE.value
    )

    # Relationships (within module, real FKs)
    documents: Mapped[list["FinanzDocument"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_finanz_sessions_opener", "opener_username"),
        Index("idx_finanz_sessions_status", "status"),
    )
```

### Pattern 3: Flask-Celery Integration (from Flask 3.1.x official docs)
**What:** `celery_init_app()` function with FlaskTask wrapper for app context
**When to use:** Initializing Celery with Flask application factory
**Example:**
```python
# Source: https://flask.palletsprojects.com/en/stable/patterns/celery/
from celery import Celery, Task
from flask import Flask

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app
```

### Pattern 4: Extension Init (from existing codebase)
**What:** Graceful degradation with try/except and logger.warning
**When to use:** All service/extension initialization
**Example:**
```python
# Source: app/core/extensions.py (HubSpot pattern, line 81-88)
# Initialize Celery (graceful degradation if Redis unavailable)
try:
    from app.core.celery_init import celery_init_app
    celery_init_app(app)
except Exception as e:
    logger.info(f"Celery not initialized: {e}")
```

### Pattern 5: Model Registration (from existing codebase)
**What:** Import new models in `app/models/__init__.py` with `__all__` registration
**When to use:** Every time new models are added
**Example:**
```python
# Source: app/models/__init__.py
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

### Anti-Patterns to Avoid
- **Using `@celery_app.task` instead of `@shared_task`:** Causes circular imports when tasks reference the app. Always use `@shared_task`.
- **Importing heavy ML libraries at module level:** sentence-transformers and chromadb take 3-8s to load. Use lazy imports to avoid slowing down Flask startup.
- **Using `native_enum=True` with Alembic:** Native PG ENUMs require manual `CREATE TYPE` / `ALTER TYPE` in migrations and can't be auto-detected cleanly. Use `native_enum=False` (VARCHAR + CHECK constraint).
- **Forgetting to register models in `__init__.py`:** Alembic autogenerate only detects models that are imported when `Base.metadata` is inspected. The wildcard `from app.models import *` in `alembic/env.py` depends on `__init__.py` exporting all models.
- **Using pickle serializer for Celery:** Security risk. JSON-only serialization is locked in the decisions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task queue with retry/chain | Custom threading/queue | Celery `@shared_task` with `bind=True, max_retries=3` | Error handling, retry backoff, monitoring, chain composition |
| Flask app context in tasks | Manual `with app.app_context()` per task | `FlaskTask` base class in `celery_init_app()` | Automatic, consistent, official Flask pattern |
| Database migrations | Manual `CREATE TABLE` SQL | Alembic `--autogenerate` | Tracks schema versions, supports up/down, production-safe |
| Enum type validation | Custom setter with if/elif | SQLAlchemy `Enum(native_enum=False)` + Python `enum.Enum` | Database-level CHECK constraint, Python-level type safety |
| Config parsing | Custom YAML/TOML loader | `os.getenv()` + `get_env_bool()`/`get_env_list()` | Consistent with existing codebase, 12-factor app |
| Feature toggle guarding | Ad-hoc `if` checks | `FINANZ_ENABLED` in 3 canonical places (config, blueprint reg, service init) | Prevents partial initialization, clear on/off semantics |

**Key insight:** This phase is entirely about wiring up infrastructure that has established patterns in both the existing codebase and the Flask/Celery ecosystem. The only novelty is combining them for the Finanzberatung domain.

## Common Pitfalls

### Pitfall 1: Helper Functions Defined Below Usage
**What goes wrong:** `get_env_bool()` and `get_env_list()` are defined at the bottom of `app/config/base.py` (lines 287-310), after all class definitions. If `FinanzConfig` uses them as class-level defaults, Python raises `NameError` because the class body executes at import time.
**Why it happens:** Python evaluates class body top-to-bottom at import time.
**How to avoid:** Move `get_env_bool()`, `get_env_list()`, `get_env_dict()` above all class definitions (before `class Config:`). This is explicitly called out in the user decisions.
**Warning signs:** `NameError: name 'get_env_bool' is not defined` when importing the config module.

### Pitfall 2: Alembic Not Detecting New Models
**What goes wrong:** Running `alembic revision --autogenerate` produces an empty migration (no new tables).
**Why it happens:** New models are defined in `app/models/finanzberatung.py` but not imported in `app/models/__init__.py`. The `alembic/env.py` does `from app.models import *` which relies on `__init__.py` to surface all models.
**How to avoid:** Always register new model imports in `app/models/__init__.py` and add them to `__all__`.
**Warning signs:** Migration file with empty `upgrade()` function.

### Pitfall 3: Celery Config Key Name
**What goes wrong:** Celery ignores configuration. Tasks run with defaults.
**Why it happens:** Flask's Celery integration reads from `app.config["CELERY"]` (a dict). If you set config keys at the top level (`app.config['broker_url'] = ...`) instead of inside the `CELERY` dict, they are ignored.
**How to avoid:** All Celery settings go inside `app.config["CELERY"] = { ... }`. The Flask official pattern uses `celery_app.config_from_object(app.config["CELERY"])`.
**Warning signs:** Task always eager even in production, wrong broker, results not stored.

### Pitfall 4: Redis DB Collision
**What goes wrong:** Celery broker messages appear in session store or vice versa.
**Why it happens:** All Redis clients use DB 0 by default. If `REDIS_URL=redis://localhost:6379/0` is used for both sessions and Celery broker, data mixes.
**How to avoid:** Use separate DB numbers: DB 0 = Sessions/Rate-Limiting (existing), DB 1 = Celery Broker, DB 2 = Celery Results. Construct URLs from base `REDIS_URL` by appending `/1` and `/2`.
**Warning signs:** `flushdb` on Celery backend wipes sessions. Random deserialization errors.

### Pitfall 5: Enum Name Collisions in PostgreSQL
**What goes wrong:** `alembic upgrade head` fails with `type "session_status" already exists`.
**Why it happens:** SQLAlchemy generates enum type names from the Python enum class name by default. If two modules define `SessionStatus`, the PG type name collides.
**How to avoid:** Use explicit `name=` parameter: `Enum(SessionStatus, native_enum=False, name="finanz_session_status")`. The `finanz_` prefix prevents collisions.
**Warning signs:** Alembic migration failure on `CREATE TYPE`.

### Pitfall 6: Eager Mode Not Propagating Exceptions
**What goes wrong:** Tasks fail silently in dev mode. Errors are swallowed.
**Why it happens:** `task_always_eager=True` runs tasks synchronously but by default wraps results without propagating exceptions.
**How to avoid:** Always pair `task_always_eager=True` with `task_eager_propagates=True` so exceptions bubble up during development.
**Warning signs:** Tasks "succeed" but nothing happens. No error in logs.

### Pitfall 7: Base Class Auto-Fields Conflict
**What goes wrong:** `id`, `created_at`, or `updated_at` columns appear twice in migration.
**Why it happens:** The custom `Base` class in `app/models/base.py` defines `id`, `created_at`, `updated_at` on all models. If a new model also defines any of these, SQLAlchemy sees a conflict.
**How to avoid:** Never redefine `id`, `created_at`, or `updated_at` in subclasses. They are inherited from `Base`.
**Warning signs:** `sqlalchemy.exc.ArgumentError: Column 'id' is already present in the mapping`.

## Code Examples

### FinanzConfig Class Pattern
```python
# Follows HubSpotConfig pattern from app/config/base.py
class FinanzConfig:
    """Konfiguration fuer Finanzberatungs-Modul"""

    # Master toggle
    FINANZ_ENABLED: bool = get_env_bool("FINANZ_ENABLED", False)

    # LLM toggle
    FINANZ_LLM_ENABLED: bool = get_env_bool("FINANZ_LLM_ENABLED", False)
    FINANZ_LLM_MODEL: str = os.getenv("FINANZ_LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    FINANZ_LLM_BASE_URL: str = os.getenv("FINANZ_LLM_BASE_URL", "http://localhost:8000/v1")

    # Upload limits
    FINANZ_MAX_FILE_SIZE_MB: int = int(os.getenv("FINANZ_MAX_FILE_SIZE_MB", "50"))
    FINANZ_MAX_UPLOADS_PER_TOKEN: int = int(os.getenv("FINANZ_MAX_UPLOADS_PER_TOKEN", "20"))
    FINANZ_ALLOWED_EXTENSIONS: list = get_env_list(
        "FINANZ_ALLOWED_EXTENSIONS", ["pdf", "jpg", "jpeg", "png", "tiff", "heic"]
    )

    # Token TTLs (seconds)
    FINANZ_TOKEN_TTL_T1: int = int(os.getenv("FINANZ_TOKEN_TTL_T1", "7200"))         # 2h
    FINANZ_TOKEN_TTL_FOLLOWUP: int = int(os.getenv("FINANZ_TOKEN_TTL_FOLLOWUP", "1209600"))  # 14d
    FINANZ_TOKEN_TTL_T2: int = int(os.getenv("FINANZ_TOKEN_TTL_T2", "7200"))         # 2h

    # Embedding / Vector
    FINANZ_EMBEDDING_MODEL: str = os.getenv(
        "FINANZ_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
    )
    FINANZ_CHUNK_SIZE: int = int(os.getenv("FINANZ_CHUNK_SIZE", "4000"))
    FINANZ_CHUNK_OVERLAP: int = int(os.getenv("FINANZ_CHUNK_OVERLAP", "200"))

    # Cache
    FINANZ_CACHE_TTL: int = int(os.getenv("FINANZ_CACHE_TTL", "1800"))  # 30 min

    # Upload directory (relative to PERSIST_BASE)
    FINANZ_UPLOAD_DIR: str = os.getenv("FINANZ_UPLOAD_DIR", "finanz_uploads")

# Singleton (at bottom of base.py, after class definition)
finanz_config = FinanzConfig()
```

### Celery Init Module
```python
# app/core/celery_init.py
# Source: https://flask.palletsprojects.com/en/stable/patterns/celery/
import logging
from celery import Celery, Task
from flask import Flask

logger = logging.getLogger(__name__)


def celery_init_app(app: Flask) -> Celery:
    """Initialize Celery with Flask app context.

    All tasks automatically run within Flask app context,
    enabling access to database, config, and other extensions.
    """
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app
```

### CELERY Config in Flask App
```python
# In create_app() or config class
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
# Strip trailing /N if present to get base URL
redis_base = redis_url.rsplit("/", 1)[0] if redis_url.count("/") > 2 else redis_url

app.config["CELERY"] = {
    "broker_url": f"{redis_base}/1",
    "result_backend": f"{redis_base}/2",
    "task_ignore_result": True,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    "task_track_started": True,
    "result_expires": 86400,
    "timezone": "Europe/Berlin",
    "enable_utc": True,
    # Dev mode: run tasks synchronously
    "task_always_eager": os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower()
        in ["true", "1", "yes"],
    "task_eager_propagates": True,
}
```

### Worker Entry Point
```python
# celery_worker.py (project root)
from dotenv import load_dotenv
load_dotenv()

from app import create_app

flask_app = create_app()
celery_app = flask_app.extensions["celery"]
```

### Test Task (Celery Connectivity Verification)
```python
# app/services/test_tasks.py
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(ignore_result=False)
def health_check_task():
    """Simple test task to verify Celery worker connectivity."""
    logger.info("Celery health check task executed successfully")
    return {"status": "ok", "message": "Celery worker is running"}
```

### Status Transition Validation Pattern
```python
# On model class
class FinanzSession(Base):
    VALID_TRANSITIONS = {
        SessionStatus.ACTIVE: [SessionStatus.IN_ANALYSIS, SessionStatus.ARCHIVED],
        SessionStatus.IN_ANALYSIS: [SessionStatus.ANALYZED, SessionStatus.ACTIVE],
        SessionStatus.ANALYZED: [SessionStatus.VERIFIED, SessionStatus.IN_ANALYSIS],
        SessionStatus.VERIFIED: [SessionStatus.ARCHIVED],
        SessionStatus.ARCHIVED: [],  # Terminal state
    }

    def transition_to(self, new_status: SessionStatus) -> None:
        """Validate and apply status transition."""
        current = SessionStatus(self.status)
        if new_status not in self.VALID_TRANSITIONS.get(current, []):
            raise ValueError(
                f"Invalid transition: {current.value} -> {new_status.value}. "
                f"Allowed: {[s.value for s in self.VALID_TRANSITIONS[current]]}"
            )
        self.status = new_status.value
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@celery_app.task` decorator | `@shared_task` decorator | Celery 4.0+ / Flask 3.0+ | Avoids circular imports in app factory pattern |
| Flask-Celery extension | Built-in `celery_init_app()` pattern | Flask 2.3+ (2023) | No third-party extension needed; official Flask docs |
| `CELERY_BROKER_URL` flat config | `app.config["CELERY"]` dict | Flask 2.3+ | Namespaced config; cleaner separation |
| SQLAlchemy 1.x `Column()` syntax | SQLAlchemy 2.0 `Mapped[]` + `mapped_column()` | SQLAlchemy 2.0 (2023) | Type-safe, IDE autocompletion, consistent with project |
| `native_enum=True` (default) | `native_enum=False` recommended | Experience-based | Avoids PG `CREATE TYPE` migration complexity |

**Deprecated/outdated:**
- `Flask-Celery` PyPI package: Abandoned, do not use. Flask has built-in Celery support.
- `celery.app.task.Task` direct subclass: Use `celery.Task` or let `celery_init_app()` handle it.
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` flat env vars: Flask 3.x expects them inside `app.config["CELERY"]` dict.

## Open Questions

1. **Alembic migration on a running server without downtime**
   - What we know: The server runs with `USE_POSTGRES=true` and Alembic migrations are applied manually via `alembic upgrade head`.
   - What's unclear: Whether the 6 new tables can be created while the existing app is running (they should be safe since they're additive -- no existing table modifications).
   - Recommendation: Additive-only migrations (CREATE TABLE) are safe to run without downtime. Verify by running `alembic upgrade head` on a test database first.

2. **Celery worker systemd service**
   - What we know: The Flask app runs via `business-hub.service` (systemd). A Celery worker needs its own systemd unit.
   - What's unclear: Exact service file content, user/group, environment, restart policy.
   - Recommendation: Create `celery-worker.service` alongside `business-hub.service`. Use same user (`www-data`), same env file, `ExecStart=/opt/business-hub/venv/bin/celery -A celery_worker:celery_app worker --loglevel=info`. Defer to deployment phase.

3. **Redis availability in local dev**
   - What we know: Local `.env` has `REDIS_URL` commented out. Celery needs a broker.
   - What's unclear: Whether dev machines have Redis installed.
   - Recommendation: `CELERY_TASK_ALWAYS_EAGER=true` in local `.env` eliminates the need for Redis in development. Tasks run synchronously in the Flask process. This mirrors the `CALENDAR_DRY_RUN=true` pattern.

## Sources

### Primary (HIGH confidence)
- **Existing codebase** (`app/config/base.py`, `app/models/`, `app/core/extensions.py`, `alembic/`) -- All patterns verified by direct inspection of current code
- **Flask 3.1.x official docs** (https://flask.palletsprojects.com/en/stable/patterns/celery/) -- `celery_init_app()` pattern, FlaskTask class, factory pattern integration
- **Local package versions** -- Verified via `pip show`: Celery 5.6.2, SQLAlchemy 2.0.45, Alembic 1.18.0, Flask 3.1.1, all ML packages present

### Secondary (MEDIUM confidence)
- **Celery 5.x configuration** -- `task_acks_late`, `task_reject_on_worker_lost`, `task_always_eager`, `task_eager_propagates` verified via local Python execution
- **SQLAlchemy Enum pattern** -- `Enum(native_enum=False, name=...)` verified via local Python execution
- **Redis URL DB number parsing** -- `redis://localhost:6379/1` correctly parses to `db=1`, verified via local Python execution

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or local execution

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already installed and used in the project
- Architecture: HIGH -- All patterns directly copied from existing codebase
- Pitfalls: HIGH -- Derived from actual codebase structure and verified configuration
- Celery integration: HIGH -- Official Flask docs + local verification

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable infrastructure, no fast-moving dependencies)
