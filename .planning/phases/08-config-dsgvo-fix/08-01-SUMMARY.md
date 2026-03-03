---
phase: 08-config-dsgvo-fix
plan: 01
subsystem: config
tags: [finanzberatung, config, dsgvo, path-helpers, flask-config]

# Dependency graph
requires:
  - phase: 01-07
    provides: "FinanzConfig class in app/config/base.py, all finanz services"
provides:
  - "FinanzConfig.get_upload_dir(session_id) classmethod"
  - "FinanzConfig.get_file_path(session_id, filename) classmethod"
  - "FinanzConfig.get_chromadb_path() classmethod"
  - "Fixed DSGVO file deletion path (was extra 'persistent' segment + missing session_id)"
  - "All finanz services read config directly from FinanzConfig class attributes"
  - "19 regression guard tests in test_finanz_config_bridge.py"
affects: [finanzberatung, dsgvo, config]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FinanzConfig as single source of truth for all finanz path construction"
    - "Classmethods on FinanzConfig for path helpers (get_upload_dir/get_file_path/get_chromadb_path)"
    - "Direct class attribute access (FinanzConfig.FINANZ_LLM_ENABLED) instead of current_app.config.get()"

key-files:
  created:
    - tests/test_services/test_finanz_config_bridge.py
  modified:
    - app/config/base.py
    - app/services/finanz_dsgvo_service.py
    - app/services/finanz_extraction_service.py
    - app/services/finanz_classification_service.py
    - app/services/finanz_field_extraction_service.py
    - app/services/finanz_embedding_service.py
    - app/services/finanz_upload_service.py
    - app/routes/finanzberatung/__init__.py

key-decisions:
  - "Path helpers centralized on FinanzConfig class (not Config) since they depend on FINANZ_UPLOAD_DIR"
  - "Comment in DSGVO service notes pre-fix deletions may have produced files_deleted=0 (pre-existing data issue)"
  - "DSGVO path formula is now: {PERSIST_BASE}/{FINANZ_UPLOAD_DIR}/{session_id}/{filename} — matches store_file()"

patterns-established:
  - "All finanz services: from app.config.base import FinanzConfig as finanz_config at module top"
  - "Path construction via finanz_config.get_file_path(session_id, filename) not inline os.path.join"
  - "Never use current_app.config.get() in finanz services — regression guard test enforces this"

requirements-completed:
  - ADMN-03

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 8 Plan 1: Config Bridge + DSGVO Path Fix Summary

**Fixed 3 v1.0 bugs: broken Flask config access in 5 finanz services (config always returned None/defaults), wrong DSGVO file deletion path (extra 'persistent' + missing session_id), and FINANZ_LLM_ENABLED env var having no effect — all services now use direct FinanzConfig class attribute access with 3 new path helper classmethods**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T19:28:23Z
- **Completed:** 2026-03-03T19:31:42Z
- **Tasks:** 2 (1 fix migration + 1 TDD test)
- **Files modified:** 8 (7 service/route files + 1 config file)
- **Files created:** 1 (test file)

## Accomplishments
- Added `get_upload_dir()`, `get_file_path()`, `get_chromadb_path()` classmethods to `FinanzConfig` as single-source path construction
- Fixed DSGVO `execute_deletion()` path bug: old path was `{base}/persistent/{upload_dir}/{filename}` (missing session_id, extra segment), now correct `{base}/{upload_dir}/{session_id}/{filename}`
- Eliminated all `current_app.config.get()` calls from 5 finanz service files — config now works outside Flask request context
- FINANZ_LLM_ENABLED env var now actually enables LLM mode in classification and field extraction services
- LLM mode startup log added to `init_app()` ("Finanzberatung LLM mode: mock/live")
- 19 tests covering path helpers, path alignment, regression guard, and env var behavior — all pass without Flask app context

## Task Commits

Each task was committed atomically:

1. **Task 1: Add path helpers and migrate all 6 service files** - `d0b4a48` (fix)
2. **Task 2: Write config bridge tests (TDD)** - `a5ead36` (test)

## Files Created/Modified
- `app/config/base.py` - Added 3 classmethods to FinanzConfig: get_upload_dir(), get_file_path(), get_chromadb_path()
- `app/services/finanz_dsgvo_service.py` - Fixed execute_deletion() path bug, import FinanzConfig at module top
- `app/services/finanz_extraction_service.py` - Fixed _resolve_path() to use finanz_config.get_file_path()
- `app/services/finanz_classification_service.py` - Use finanz_config.FINANZ_LLM_ENABLED/BASE_URL/MODEL
- `app/services/finanz_field_extraction_service.py` - Use finanz_config.FINANZ_LLM_ENABLED/BASE_URL/MODEL
- `app/services/finanz_embedding_service.py` - Use finanz_config for model name, chroma path, chunk settings
- `app/services/finanz_upload_service.py` - store_file() uses finanz_config.get_upload_dir()
- `app/routes/finanzberatung/__init__.py` - Added FinanzConfig import and LLM mode startup log
- `tests/test_services/test_finanz_config_bridge.py` - 19 tests: path helpers, alignment, regression guard, env vars

## Decisions Made
- Path helpers placed on `FinanzConfig` (not `Config`) since they depend on `FINANZ_UPLOAD_DIR` which lives there
- Added a code comment in DSGVO service noting any pre-fix deletions produced `files_deleted=0` due to wrong path — this is a pre-existing data issue, not a new bug
- Kept the `try/except` around `requests.post()` calls in `_classify_llm()` and `_extract_llm()` — those are LLM fallback guards, not config-reading guards

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All changes were mechanical substitutions of `current_app.config.get()` → direct class attribute access. Verification passed immediately.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Config bridge is now solid: all finanz services work outside Flask request context
- DSGVO file deletion will correctly find and remove files from this point forward
- Pre-existing deletions (before this fix) produced files_deleted=0 and left actual files on disk — a DSGVO risk requiring manual cleanup on the server if any sessions were already processed
- Phase 8 Plan 2 (next) can proceed

---
*Phase: 08-config-dsgvo-fix*
*Completed: 2026-03-03*
