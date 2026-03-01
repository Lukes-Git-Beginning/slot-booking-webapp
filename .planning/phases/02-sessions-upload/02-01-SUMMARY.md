---
phase: 02-sessions-upload
plan: 01
subsystem: api
tags: [flask-blueprint, sqlalchemy, qrcode, python-magic, file-upload, session-management]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "FinanzSession, FinanzUploadToken, FinanzDocument models and FinanzConfig"
provides:
  - "Finanzberatung blueprint package with conditional registration"
  - "FinanzSessionService with 7 CRUD/lifecycle methods"
  - "FinanzUploadService with 7 token/file methods (QR, magic bytes, SHA-256)"
affects: [02-02, 02-03, 02-04, 03-analysis-pipeline]

# Tech tracking
tech-stack:
  added: [python-magic, pillow-heif]
  patterns: [blueprint-package-with-lazy-sub-imports, service-layer-with-get_db_session, magic-byte-validation, uuid-filenames-sha256-dedup]

key-files:
  created:
    - app/routes/finanzberatung/__init__.py
    - app/services/finanz_session_service.py
    - app/services/finanz_upload_service.py
  modified:
    - app/__init__.py
    - requirements.txt

key-decisions:
  - "Lazy sub-blueprint imports in init_app() to avoid crashes when sub-blueprint files do not exist yet"
  - "CSRF exemption applied to upload sub-blueprint inside init_app, not in register_blueprints"
  - "Token TTL resolved at call time via lambda map for runtime config flexibility"
  - "File deduplication by SHA-256 hash within same session"

patterns-established:
  - "Finanzberatung blueprint lazy-import pattern: try/except ImportError with warning log"
  - "Service method pattern: get_db_session() + try/except/rollback/finally-close"
  - "German error messages for customer-facing token/upload validation"

requirements-completed: [SESS-05, UPLD-01, UPLD-02, UPLD-04, UPLD-05, UPLD-07]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 02 Plan 01: Blueprint + Services Summary

**Finanzberatung blueprint with conditional registration, session CRUD service, and upload service with QR tokens, magic-byte validation, and SHA-256 file dedup**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-01T13:56:34Z
- **Completed:** 2026-03-01T13:59:40Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Finanzberatung blueprint package created with lazy sub-blueprint imports and CSRF exemption for upload
- FinanzSessionService with full CRUD, notes authorization, status transitions, and closer assignment
- FinanzUploadService with crypto-secure token generation, QR code, magic-byte file validation, UUID storage, SHA-256 dedup

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Finanzberatung blueprint package and register in app** - `490d08d` (feat)
2. **Task 2: Create FinanzSessionService and FinanzUploadService** - `7a33cf6` (feat)

## Files Created/Modified
- `app/routes/finanzberatung/__init__.py` - Blueprint package with lazy sub-blueprint registration and CSRF exemption
- `app/services/finanz_session_service.py` - Session CRUD, notes management, status transitions, closer assignment (7 methods)
- `app/services/finanz_upload_service.py` - Token generation, QR code, magic-byte validation, UUID file storage (7 methods)
- `app/__init__.py` - Conditional blueprint registration when FINANZ_ENABLED=true
- `requirements.txt` - Added python-magic and pillow-heif dependencies

## Decisions Made
- Lazy sub-blueprint imports in init_app() to prevent crashes when sub-blueprint files (sessions.py, upload.py, sse.py) do not exist yet (created in Plans 02-03)
- CSRF exemption applied inside the blueprint's own init_app to keep upload-specific concerns localized
- Token TTL resolved via lambda map at call time rather than static values, supporting runtime config changes
- File deduplication checks SHA-256 hash within the same session to prevent duplicate uploads

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Blueprint registered and importable; sub-blueprint files (sessions.py, upload.py, sse.py) ready for Plans 02-04
- Both services are importable and expose all methods; routes can wire directly to them
- python-magic must be installed on the server (`pip install python-magic` on Linux, `pip install python-magic-bin` on Windows)

## Self-Check: PASSED

All created files verified on disk. All commit hashes verified in git log.

---
*Phase: 02-sessions-upload*
*Completed: 2026-03-01*
