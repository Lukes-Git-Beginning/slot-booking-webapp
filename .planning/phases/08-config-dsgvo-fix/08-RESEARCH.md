# Phase 8: Config Bridge + DSGVO Path Fix - Research

**Researched:** 2026-03-03
**Domain:** Python config patterns, file path management, Flask service refactoring
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Config Access Pattern**
- Standardize ALL finanz services on direct class imports (`from app.config.base import Config, FinanzConfig as finanz_config`)
- No more `current_app.config.get('FINANZ_*')` — use `finanz_config.FINANZ_LLM_ENABLED` etc. directly
- Non-finanz values like PERSIST_BASE also via `Config.PERSIST_BASE` (no mixing of access patterns within a service)
- Only fix the 5 services that currently read FINANZ_* values — no proactive imports elsewhere
- No fallback needed in Flask Config class — if all services use direct imports, Flask config does not need FINANZ_* values
- Affected services: finanz_classification_service, finanz_field_extraction_service, finanz_extraction_service, finanz_embedding_service, finanz_dsgvo_service

**Path Construction**
- Extract shared path helpers as classmethods on FinanzConfig:
  - `get_upload_dir(session_id)` — returns session upload directory path
  - `get_file_path(session_id, filename)` — returns full file path
- Both use `Config.PERSIST_BASE` + `FINANZ_UPLOAD_DIR` + `session_id` internally
- All 3 consumers (upload service, DSGVO service, extraction service) use these helpers
- Single source of truth — future path changes need 1 fix, not 3
- Fix the DSGVO bug: remove incorrect `/persistent/` segment and add missing `session_id`

**LLM Toggle**
- Import-time resolution (env var read once at import via `get_env_bool`) — consistent with all other config
- Server restart picks up env var changes — no runtime property needed
- Silent fallback: if FINANZ_LLM_ENABLED=true but vLLM unreachable, fall back to keyword mock + log warning
- Add startup log line in init_app(): "Finanzberatung LLM mode: mock/live" for admin verification

### Claude's Discretion
- Exact classmethod signatures and return types for path helpers
- Whether to add a `get_chromadb_path()` helper alongside upload paths
- Test structure for verifying path alignment
- Order of service refactoring (which service to fix first)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADMN-03 | Original files are deleted after retention period; extracted values and embeddings are preserved | Path helper classmethods on FinanzConfig enable correct path construction; removing the `/persistent/` segment bug and adding `session_id` makes `execute_deletion()` locate the same files that `store_file()` writes |
</phase_requirements>

---

## Summary

Phase 8 is a pure refactoring phase within a well-understood codebase. There is no external library research needed — everything is internal. The code has already been read and the exact bugs are visible.

The three gaps are: (1) four finanz services use `current_app.config.get('FINANZ_*')` while the upload service already uses the correct direct-import pattern; (2) `execute_deletion()` in `finanz_dsgvo_service.py` builds a wrong path (`{persist_base}/persistent/{upload_dir}/{filename}`) while `store_file()` builds the correct path (`{persist_base}/{upload_dir}/{session_id}/{filename}`) — two errors: extra `/persistent/` segment AND missing `session_id`; (3) `FINANZ_LLM_ENABLED` is defined in `FinanzConfig` at the class level with `get_env_bool()` but the four services that need it try to read it via `current_app.config.get()` which returns `None` unless Flask config explicitly echoes the value.

The reference implementation is `finanz_upload_service.py` line 29: `from app.config.base import Config, FinanzConfig as finanz_config`. The fix for each service is mechanical: replace the `try/except RuntimeError` block that reads from `current_app.config` with a direct reference to `finanz_config.FINANZ_LLM_ENABLED` (and related values), then add two classmethods to `FinanzConfig` for the shared path logic.

**Primary recommendation:** Mechanically apply the upload service pattern to the four remaining services, add two path-helper classmethods to `FinanzConfig`, migrate the three path-construction sites to use the helpers, and add one LLM-mode log line in `init_app()`.

---

## Standard Stack

No new libraries. All tools are already present in the codebase.

### Core (already installed)
| Component | Location | Purpose |
|-----------|----------|---------|
| `app/config/base.py` | `FinanzConfig` class | Central config class — add path helpers here |
| `app/services/finanz_upload_service.py` | Reference implementation | Already uses correct direct-import pattern |
| `app/routes/finanzberatung/__init__.py` | `init_app()` | Place for LLM-mode startup log line |

### Architecture of the Bug

The root cause in each service is a `try/except RuntimeError` guard that was written to avoid crashes when called outside a Flask request context (e.g. from a Celery task). The intent was correct but the implementation chose the wrong mechanism — it queries `current_app.config` which only knows about values explicitly registered via `app.config.from_object()`, and the `create_app` factory in `app/__init__.py` calls `app.config.from_object('app.config.base.Config')`, NOT `FinanzConfig`. So `current_app.config.get('FINANZ_LLM_ENABLED')` always returns `None`/the default, regardless of the env var. Direct class-level access (`finanz_config.FINANZ_LLM_ENABLED`) avoids the Flask context entirely and reads the value correctly because `FinanzConfig` class attributes are resolved at import time.

---

## Architecture Patterns

### Recommended Classmethod Signatures for FinanzConfig

```python
# Source: finanz_upload_service.py store_file() — exact path being matched
@classmethod
def get_upload_dir(cls, session_id: int) -> str:
    """Returns the session upload directory path (creates nothing)."""
    return os.path.join(Config.PERSIST_BASE, cls.FINANZ_UPLOAD_DIR, str(session_id))

@classmethod
def get_file_path(cls, session_id: int, filename: str) -> str:
    """Returns the full path for a stored file."""
    return os.path.join(cls.get_upload_dir(session_id), filename)
```

These classmethods need `import os` at the top of `base.py` — already present.

`Config.PERSIST_BASE` is accessible from within `FinanzConfig` because both classes live in the same module and `Config` is defined before `FinanzConfig` in `base.py`. No import changes needed.

### Optional: ChromaDB Path Helper

The embedding service currently builds `os.path.join(persist_base, 'chroma_db')` inline. Adding:

```python
@classmethod
def get_chromadb_path(cls) -> str:
    """Returns the ChromaDB persistence path."""
    return os.path.join(Config.PERSIST_BASE, 'chroma_db')
```

...is low risk and follows the same pattern. Recommended because it eliminates the only remaining `current_app.config` call in the embedding service (`_get_chroma_client`) and makes all path logic centrally testable. The planner can include or skip this at discretion.

### Pattern: Replacing current_app.config Blocks

**Before (broken pattern — used in 4 services):**
```python
try:
    from flask import current_app
    use_llm = current_app.config.get('FINANZ_LLM_ENABLED', False)
except RuntimeError:
    use_llm = False
```

**After (correct pattern — matches upload service):**
```python
from app.config.base import FinanzConfig as finanz_config  # at module top

# Inside method:
use_llm = finanz_config.FINANZ_LLM_ENABLED
```

For the LLM URL/model in `_classify_llm()` and `_extract_llm()`:
```python
# Before (in finanz_classification_service._classify_llm):
base_url = current_app.config.get('FINANZ_LLM_BASE_URL', 'http://localhost:8000/v1')
model = current_app.config.get('FINANZ_LLM_MODEL', 'meta-llama/Llama-3.1-8B-Instruct')

# After:
base_url = finanz_config.FINANZ_LLM_BASE_URL
model = finanz_config.FINANZ_LLM_MODEL
```

### Pattern: Path Construction Migration

**Current bug in `finanz_dsgvo_service.execute_deletion()` (lines 197-205):**
```python
try:
    from flask import current_app
    upload_dir = current_app.config.get('FINANZ_UPLOAD_DIR', 'finanz_uploads')
    persist_base = current_app.config.get('PERSIST_BASE', 'data')
except RuntimeError:
    upload_dir = 'finanz_uploads'
    persist_base = 'data'

base_path = os.path.join(persist_base, 'persistent', upload_dir)
# ...
file_path = os.path.join(base_path, doc.stored_filename)  # WRONG: no session_id
```

Two bugs on one line: `'persistent'` segment (wrong), no `session_id` (wrong).

**Correct path (matching `store_file()`):**
```python
from app.config.base import Config, FinanzConfig as finanz_config

# In execute_deletion():
for doc in documents:
    if doc.stored_filename:
        file_path = finanz_config.get_file_path(session_id, doc.stored_filename)
```

**Current bug in `finanz_extraction_service._resolve_path()` (lines 115-122):**
```python
try:
    from flask import current_app
    persist_base = current_app.config.get('PERSIST_BASE', 'data')
    upload_dir = current_app.config.get('FINANZ_UPLOAD_DIR', 'finanz_uploads')
except RuntimeError:
    persist_base = 'data'
    upload_dir = 'finanz_uploads'
return os.path.join(persist_base, upload_dir, str(doc.session_id), doc.stored_filename)
```

The path formula is actually correct here (it has `session_id`), but it uses the wrong config-access mechanism. After migration:
```python
def _resolve_path(self, doc: FinanzDocument) -> str:
    return finanz_config.get_file_path(doc.session_id, doc.stored_filename)
```

### Pattern: LLM Mode Startup Log Line

Location: `app/routes/finanzberatung/__init__.py`, inside `init_app()`, after blueprints registered:

```python
from app.config.base import FinanzConfig as finanz_config

mode = "live" if finanz_config.FINANZ_LLM_ENABLED else "mock"
app.logger.info("Finanzberatung LLM mode: %s", mode)
```

This goes at the end of `init_app()`, before `return finanzberatung_bp`.

### Anti-Patterns to Avoid

- **Accessing `FinanzConfig` values through `current_app.config`:** The Flask app factory only registers `Config` (the base class), not `FinanzConfig`. FINANZ_* keys are never present in `app.config` unless manually added.
- **Adding FINANZ_* keys to Flask Config class:** The locked decision says "no fallback needed in Flask Config class." Do not add these keys to `Config` or to the `create_app()` factory.
- **Using `try/except RuntimeError` for context detection:** This was the wrong pattern. Direct class-level access requires no Flask context, making the guard unnecessary.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path construction | Custom path functions per-service | `FinanzConfig.get_upload_dir()` / `get_file_path()` classmethods | Three sites currently diverge — centralize once |
| Config reading | Per-service fallback logic | Direct `finanz_config.ATTR` access | Classlevel attrs need no context, no try/except |
| LLM reachability check | Active health-check on import | Silent fallback already in `_classify_llm()` / `_extract_llm()` | Both methods already catch exceptions and fall back to keyword/pattern mode |

---

## Common Pitfalls

### Pitfall 1: Forgetting the Import Statement
**What goes wrong:** Adding `finanz_config.FINANZ_LLM_ENABLED` without adding the import at the top of the file — `NameError` at runtime.
**Why it happens:** The existing `try/except` blocks have `from flask import current_app` inside the method body. When removing those blocks, the module-level import must be added.
**How to avoid:** Each service file needs `from app.config.base import Config, FinanzConfig as finanz_config` at the top, before use.
**Warning signs:** `NameError: name 'finanz_config' is not defined` during test run.

### Pitfall 2: Removing the LLM Fallback Logic
**What goes wrong:** The `_classify_llm()` and `_extract_llm()` methods already catch exceptions and fall back to keyword/pattern mode. Removing the try/except in those methods would break the fallback chain.
**Why it happens:** Confusion between the config-reading try/except (to remove) and the LLM-call try/except (to keep).
**How to avoid:** Only remove the `try/except RuntimeError` blocks that wrap `current_app.config.get()` calls. The `except Exception` blocks around `requests.post()` calls are separate and must stay.
**Warning signs:** If `FINANZ_LLM_ENABLED=true` and vLLM is down, no graceful degradation.

### Pitfall 3: DSGVO Path Fix Doesn't Cover Already-Written Documents
**What goes wrong:** After fixing `execute_deletion()`, documents uploaded BEFORE the fix will still not be found on disk because the DSGVO service was looking in the wrong place. Any DSGVO deletions that ran before Phase 8 will have `files_deleted=0` (files not found) but will have set `stored_filename = None`, so re-running deletion is impossible.
**Why it happens:** The fix is not retroactive — it changes future behavior.
**How to avoid:** This is a pre-existing data issue, not a code issue. Log it in code comments. The planner should note this in task descriptions so future operators understand the gap.
**Warning signs:** `files_deleted=0` in DSGVO audit logs from before the fix date.

### Pitfall 4: session_id Type Mismatch in Path Helpers
**What goes wrong:** `session_id` comes from the DB as an `int`; `os.path.join()` requires strings. The current `store_file()` already does `str(session_id)` correctly.
**Why it happens:** If the classmethod forgets `str(session_id)`, Python raises `TypeError: expected str, bytes or os.PathLike object, not int`.
**How to avoid:** Classmethod signature takes `session_id: int` and internally does `str(session_id)`.

### Pitfall 5: Embedding Service Has TWO current_app.config Calls
**What goes wrong:** `finanz_embedding_service.py` has `current_app.config.get()` in two separate methods: `_get_model()` (line 59) and `_get_chroma_client()` (line 74), plus a third in `embed_document()` (lines 161-164). All three must be migrated.
**Why it happens:** Easy to miss the `_get_model()` and `_get_chroma_client()` lazy-init methods when only looking at the main `embed_document()` method.
**How to avoid:** Count all `current_app.config.get` occurrences per file before starting the migration. In `finanz_embedding_service.py` there are 3 occurrences.

---

## Code Examples

Verified from actual source files (read in this session):

### Current config.get Occurrences Per Service (confirmed by reading each file)

| Service File | Occurrences | Lines Affected |
|--------------|-------------|----------------|
| `finanz_classification_service.py` | 3 | L66 (use_llm), L161 (base_url), L162 (model) — in `_classify_llm()` |
| `finanz_field_extraction_service.py` | 3 | L94 (use_llm), L405 (base_url), L406 (model) — in `_extract_llm()` |
| `finanz_extraction_service.py` | 2 | L117 (persist_base), L118 (upload_dir) — in `_resolve_path()` |
| `finanz_embedding_service.py` | 3 | L59 (model_name in `_get_model()`), L74 (persist_base in `_get_chroma_client()`), L161-164 (chunk_size/overlap in `embed_document()`) |
| `finanz_dsgvo_service.py` | 2 + path bug | L199 (upload_dir), L200 (persist_base), L205 (wrong path formula) |

Total: 13 individual `current_app.config.get()` calls across 5 files.

### Correct Upload Service Pattern (Reference — already correct)
```python
# app/services/finanz_upload_service.py line 29
from app.config.base import Config, FinanzConfig as finanz_config

# In store_file():
persist_base = Config.PERSIST_BASE
upload_dir = os.path.join(
    persist_base, finanz_config.FINANZ_UPLOAD_DIR, str(session_id)
)
```

### FinanzConfig Path Helpers (to add to base.py)
```python
# app/config/base.py — add to FinanzConfig class

@classmethod
def get_upload_dir(cls, session_id: int) -> str:
    """Return the session upload directory path."""
    return os.path.join(Config.PERSIST_BASE, cls.FINANZ_UPLOAD_DIR, str(session_id))

@classmethod
def get_file_path(cls, session_id: int, filename: str) -> str:
    """Return the full filesystem path for a stored document."""
    return os.path.join(cls.get_upload_dir(session_id), filename)
```

### Migrated DSGVO execute_deletion() File Loop (corrected)
```python
# app/services/finanz_dsgvo_service.py — after fix
from app.config.base import FinanzConfig as finanz_config  # add to top of file

# In execute_deletion():
files_deleted = 0
for doc in documents:
    if doc.stored_filename:
        file_path = finanz_config.get_file_path(session_id, doc.stored_filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                files_deleted += 1
                logger.debug("Deleted file: %s", file_path)
        except OSError as e:
            logger.error("Failed to delete file %s: %s", file_path, e)
```

### Migrated _resolve_path() (corrected)
```python
# app/services/finanz_extraction_service.py — after fix
from app.config.base import FinanzConfig as finanz_config  # add to top

def _resolve_path(self, doc: FinanzDocument) -> str:
    return finanz_config.get_file_path(doc.session_id, doc.stored_filename)
```

### Migrated embed_document() Chunk Config (corrected)
```python
# app/services/finanz_embedding_service.py — after fix
from app.config.base import FinanzConfig as finanz_config  # add to top

# In embed_document():
chunks = self.chunk_text(
    text,
    finanz_config.FINANZ_CHUNK_SIZE,
    finanz_config.FINANZ_CHUNK_OVERLAP,
)

# In _get_model():
model_name = finanz_config.FINANZ_EMBEDDING_MODEL
self._model = SentenceTransformer(model_name)

# In _get_chroma_client():
chroma_path = finanz_config.get_chromadb_path()  # or inline os.path.join(Config.PERSIST_BASE, 'chroma_db')
```

---

## State of the Art

No library changes in this phase. This section documents the internal pattern evolution.

| Old Pattern | New Pattern | Impact |
|-------------|-------------|--------|
| `current_app.config.get('FINANZ_*')` per service | `finanz_config.FINANZ_*` direct class access | Works in Celery/test contexts; reads actual env var |
| Per-service path construction (3 divergent sites) | `FinanzConfig.get_file_path()` classmethod | Single source of truth; DSGVO bug eliminated |
| LLM toggle always resolves to False in services | `finanz_config.FINANZ_LLM_ENABLED` at import time | Setting env var actually enables live LLM mode |

---

## Execution Order (Discretion Guidance)

Recommended service order for the planner:

1. **`app/config/base.py`** — Add path helper classmethods first. Zero risk; nothing calls them yet.
2. **`finanz_dsgvo_service.py`** — Fixes the ADMN-03 bug. Highest priority.
3. **`finanz_extraction_service.py`** — Path + config migration. Uses the new helpers.
4. **`finanz_classification_service.py`** — Config migration only (no path change). Mechanical.
5. **`finanz_field_extraction_service.py`** — Config migration only. Mechanical.
6. **`finanz_embedding_service.py`** — Config migration, 3 occurrences. Check all three lazy-init methods.
7. **`app/routes/finanzberatung/__init__.py`** — Add LLM mode log line. Last, trivial.

This ordering ensures: (a) helpers exist before consumers; (b) the bug-fix services come first; (c) mechanical refactors come after critical ones.

---

## Open Questions

1. **ChromaDB path helper: include or skip?**
   - What we know: The embedding service has a `current_app.config.get('PERSIST_BASE')` in `_get_chroma_client()` that is separate from the upload path logic but follows the same broken pattern.
   - What's unclear: Whether to add `get_chromadb_path()` to `FinanzConfig` (cleaner) or just inline `os.path.join(Config.PERSIST_BASE, 'chroma_db')` (simpler).
   - Recommendation: Add the classmethod. It keeps all finanz path logic in one place and is one extra line. Claude's discretion per CONTEXT.md.

2. **upload_service.py: should it migrate to use the new helpers?**
   - What we know: `store_file()` already builds the correct path but inline (not via classmethod). It is the reference implementation. After adding classmethods, the upload service would ideally use them too.
   - What's unclear: Whether the plan should include this migration or leave the upload service alone.
   - Recommendation: Migrate upload service too. It removes the last inline path construction and makes the classmethod the single source. Low risk — just replacing existing code with an equivalent call.

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `app/config/base.py` — FinanzConfig class, all attributes confirmed present
- Direct code reading: `app/services/finanz_upload_service.py` — reference pattern confirmed at line 29
- Direct code reading: `app/services/finanz_dsgvo_service.py` — both bugs confirmed at lines 199-205
- Direct code reading: `app/services/finanz_extraction_service.py` — wrong pattern confirmed at lines 115-122
- Direct code reading: `app/services/finanz_classification_service.py` — 3 occurrences confirmed at lines 65-68, 161-162
- Direct code reading: `app/services/finanz_field_extraction_service.py` — 3 occurrences confirmed at lines 94-97, 405-406
- Direct code reading: `app/services/finanz_embedding_service.py` — 3 occurrences confirmed at lines 59-64, 73-78, 161-165
- Direct code reading: `app/__init__.py` — confirms `app.config.from_object('app.config.base.Config')` (not FinanzConfig)
- Direct code reading: `app/routes/finanzberatung/__init__.py` — init_app() structure confirmed

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions — all implementation decisions pre-verified by user discussion

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — No new libraries; all patterns read directly from source
- Architecture: HIGH — Bugs confirmed by reading actual code; fix pattern matches existing reference implementation
- Pitfalls: HIGH — Derived from reading all 5 service files and counting exact occurrences

**Research date:** 2026-03-03
**Valid until:** Indefinite — internal refactor, no external dependencies to expire
