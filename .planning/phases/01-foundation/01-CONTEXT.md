# Phase 1: Foundation - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Config, database models, Celery setup, and all dependencies for the Finanzberatung module -- ready for feature development. No UI, no routes, no business logic. Infrastructure only.

</domain>

<decisions>
## Implementation Decisions

### Config Structure
- New `FinanzConfig` class in `app/config/base.py` (follows HubSpotConfig pattern)
- Explicit `FINANZ_ENABLED=true/false` env var as master feature toggle
- Blueprint only registered when `FINANZ_ENABLED=true`
- Guard in three places: config class, blueprint registration, service init
- `FINANZ_LLM_ENABLED` flag: true = local vLLM (OpenAI-compatible API), false = keyword-based mock classification
- Token TTL defaults as specified: T1=2h (7200s), Followup=14d (1209600s), T2=2h (7200s) -- all env-var overridable
- Env var naming: `FINANZ_` prefix for all settings (FINANZ_LLM_MODEL, FINANZ_CACHE_TTL, etc.)
- Use existing `get_env_bool()`/`get_env_list()` helpers (move above class definitions so they're usable in class-level attrs)

### Database Models
- Single new file: `app/models/finanzberatung.py` with all 6 models
- Table name prefix: `finanz_` on all `__tablename__` values (finanz_sessions, finanz_upload_tokens, finanz_documents, finanz_extracted_data, finanz_scorecards, finanz_tasks)
- User reference: `opener_username`/`closer_username` as `String(100)` -- NO ForeignKey (consistent with all existing models; dual-write migration makes real FKs risky)
- Within-module relationships: proper integer FKs + `relationship()` with `cascade="all, delete-orphan"` (Session is root aggregate)
- Enum handling: Python `enum.Enum` + SQLAlchemy `Enum(native_enum=False)` -- stores as VARCHAR with CHECK constraint, not native PG ENUM
- Explicit enum `name=` argument on each (e.g., `name="finanz_session_status"`) to avoid collisions
- Status transition validation via `VALID_TRANSITIONS` dict on model class
- PG-only -- NO JSON dual-write for new models. Service raises RuntimeError if `USE_POSTGRES=false`
- Migration: Alembic `--autogenerate` for production; `create_all()` as safety net
- Index naming: `idx_finanz_{table}_{column(s)}`

### Celery Setup
- New `app/core/celery_init.py` with `celery_init_app()` function
- FlaskTask base class wraps all tasks in Flask app context
- Called from `init_extensions()` in `app/core/extensions.py` (same pattern as all other services)
- `celery_worker.py` at project root as worker entry point
- Redis DB separation: DB 0 = Sessions/Rate-Limiting (existing), DB 1 = Celery Broker, DB 2 = Celery Results
- `task_acks_late=True` + `task_reject_on_worker_lost=True` for reliability
- JSON serialization only (no pickle)
- `task_track_started=True` for monitoring
- Task definitions use `@shared_task` (not `@celery_app.task`) to avoid circular imports
- Task files in `app/services/` (document_tasks.py, analysis_tasks.py)
- Dev mode: `CELERY_TASK_ALWAYS_EAGER=true` -- tasks run synchronously, no worker needed (like CALENDAR_DRY_RUN pattern)
- Global `task_ignore_result=True`, opt-in per task with `ignore_result=False`
- `result_expires=86400` (24h TTL for results in Redis)
- Timezone: Europe/Berlin, `enable_utc=True`

### Dependencies
- Split requirements: `requirements.txt` (base, unchanged) + `requirements-ml.txt` (new, ML packages)
- Lazy imports for heavy packages: sentence-transformers and chromadb loaded on first use only (3-8s), not at module level
- pdfplumber and tiktoken imported at `init_app()` time (fast, <0.5s)
- pytesseract: import at init_app() with binary check via `get_tesseract_version()`
- PyTorch: CUDA build for production server (RTX 4000 SFF Ada with 20GB VRAM), CPU-only for local dev
- Tesseract OCR: system dependency, not pip. Linux: `apt-get install tesseract-ocr tesseract-ocr-deu`. Windows: `TESSERACT_CMD` env var
- Celery: `celery[redis]` goes into base requirements.txt (needed even without ML)
- Model cache: `HF_HOME` env var to control Hugging Face model download location

### Claude's Discretion
- Exact FinanzConfig attribute list and default values (within the patterns decided above)
- Model field types and exact column definitions
- Celery task retry/timeout defaults per task type
- Index strategy (which columns to index beyond the obvious ones)
- Alembic migration file structure
- Test task implementation for verifying Celery connectivity

</decisions>

<specifics>
## Specific Ideas

- Server upgrade planned: **NVIDIA RTX 4000 SFF Ada** (20GB VRAM), **64GB RAM**, **Intel i5-13500** -- this affects torch build choice (CUDA), vLLM model selection, Celery worker concurrency
- CUDA 12.x compatible build needed: `pip install torch --index-url https://download.pytorch.org/whl/cu124`
- vLLM planned for local inference (Phase 4): 8B model for classification, 70B (quantized) for extraction -- 20GB VRAM should handle 8B easily, 70B needs quantization
- Pre-download embedding model during deployment: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"`
- gunicorn `--preload` flag recommended when ML feature is always-on (share model RAM across workers)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/config/base.py`: Config class pattern with `get_env_bool()`, `get_env_list()`, `get_env_dict()` helpers
- `app/models/base.py`: `Base` declarative class with auto id/created_at/updated_at, `to_dict()`, `get_db_session()`, `init_db()`, `is_postgres_enabled()`
- `app/core/extensions.py`: `init_extensions()` pattern with graceful degradation (try/except + logger.warning)
- `app/models/__init__.py`: Central import registry with `__all__` -- new models must be registered here

### Established Patterns
- Config: One class per domain, os.getenv() with defaults, singleton at bottom of base.py
- Models: SQLAlchemy 2.0 declarative with Mapped[] types, separate files per domain
- Extensions: Global `None` instances, initialized in `init_extensions()`, graceful fallback
- Feature toggles: Boolean env vars parsed with `get_env_bool()` or inline `.lower() in ["true", "1", "yes"]`
- Redis: Already used for sessions + rate limiting via `REDIS_URL` env var

### Integration Points
- `app/core/extensions.py:init_extensions()` -- Celery init goes here
- `app/models/__init__.py` -- New model imports registered here
- `app/config/base.py` (bottom) -- New `finanz_config` singleton
- `app/__init__.py:create_app()` -- Conditional blueprint registration
- `requirements.txt` -- celery[redis] added here
- `.env` -- New FINANZ_* env vars
- systemd `business-hub.service` -- ReadWritePaths for upload dir, new celery.service unit

</code_context>

<deferred>
## Deferred Ideas

- **Platform-wide FK migration**: Rebuild all existing models with proper ForeignKey to Users table once PG migration reaches 100% -- separate milestone, not Finanzberatung scope
- **Server specs as central config**: Consider adding server hardware specs to a shared planning doc that all phases can reference

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-02-28*
