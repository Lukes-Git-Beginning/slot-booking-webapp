---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [config, celery, redis, pdfplumber, tiktoken, sentence-transformers, chromadb, torch]

# Dependency graph
requires: []
provides:
  - "FinanzConfig class with 15 env-var-backed settings (feature toggles, upload limits, token TTLs, LLM, embedding, cache)"
  - "finanz_config singleton importable from app.config.base"
  - "get_env_bool/get_env_list/get_env_dict available as class-level defaults"
  - "celery[redis] in requirements.txt for background task infrastructure"
  - "requirements-ml.txt with 6 ML/document processing packages"
affects: [01-02, 01-03, 02-sessions-upload, 04-document-pipeline]

# Tech tracking
tech-stack:
  added: [celery, redis, pdfplumber, tiktoken, pytesseract, sentence-transformers, chromadb, torch]
  patterns: [env-var-backed config class with singleton, split requirements for optional ML deps]

key-files:
  created: [requirements-ml.txt]
  modified: [app/config/base.py, requirements.txt]

key-decisions:
  - "Helper functions moved above all class definitions so they can be used as class-level defaults in FinanzConfig"
  - "ML packages in separate requirements-ml.txt to keep base install lightweight"

patterns-established:
  - "FinanzConfig pattern: get_env_bool for toggles, int(os.getenv()) for numerics, get_env_list for lists"
  - "Split requirements: base requirements.txt for core app, requirements-ml.txt for optional ML/document processing"

requirements-completed: [FOUND-01, FOUND-04]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 1 Plan 01: Config + Dependencies Summary

**FinanzConfig with 15 env-var settings (toggles, upload limits, token TTLs, LLM, embedding) plus celery[redis] and ML requirements split**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T12:47:41Z
- **Completed:** 2026-03-01T12:50:57Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- FinanzConfig class with all 15 settings (FINANZ_ENABLED, FINANZ_LLM_ENABLED, upload limits, token TTLs, embedding config, cache TTL, upload dir)
- Helper functions (get_env_bool, get_env_list, get_env_dict) relocated above all class definitions for use as class-level defaults
- celery[redis]>=5.4.0 added to requirements.txt for Celery task infrastructure
- requirements-ml.txt created with 6 ML packages (pdfplumber, tiktoken, pytesseract, sentence-transformers, chromadb, torch)

## Task Commits

Each task was committed atomically:

1. **Task 1: Move helper functions and add FinanzConfig to app/config/base.py** - `fa8a04d` (feat) - committed in prior session as part of combined commit
2. **Task 2: Update requirements.txt and create requirements-ml.txt** - `99400c5` (feat)

## Files Created/Modified
- `app/config/base.py` - FinanzConfig class added, helpers moved to top, finanz_config singleton
- `requirements.txt` - celery[redis]>=5.4.0 in new Task Queue section
- `requirements-ml.txt` - New file with 6 ML/document processing packages

## Decisions Made
- Helper functions relocated to top of base.py (before all class definitions) so they can be used as class-level default values in FinanzConfig
- ML packages kept in separate requirements-ml.txt to avoid slowing down base app installs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Task 1 config changes were already committed in a prior session (commit fa8a04d, combined with 01-02 database models). No re-work needed; verified the existing state matched the plan specification exactly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- FinanzConfig is ready; FINANZ_ENABLED=false by default so no impact on existing app
- celery[redis] installed; Celery setup (Plan 01-03) depends on this
- ML packages listed but NOT installed yet (optional, only needed when FINANZ_ENABLED=true)
- Database models (Plan 01-02) can proceed independently

## Self-Check: PASSED

All files exist. All commit hashes verified.

---
*Phase: 01-foundation*
*Completed: 2026-03-01*
