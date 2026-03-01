---
phase: 02-sessions-upload
plan: 05
subsystem: api
tags: [flask, ajax, token-management, upload]

# Dependency graph
requires:
  - phase: 02-sessions-upload
    provides: FinanzUploadService.deactivate_token() method and session_detail.html with deactivateToken button
provides:
  - POST /sessions/<id>/deactivate-token route wired to upload_service.deactivate_token()
  - Working JS handler that POSTs token_id and reloads on success
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AJAX deactivation follows same fetch+JSON pattern as status transitions and token generation"

key-files:
  created: []
  modified:
    - app/routes/finanzberatung/sessions.py
    - templates/finanzberatung/session_detail.html

key-decisions:
  - "No new decisions -- followed plan exactly"

patterns-established:
  - "Token lifecycle AJAX: generate, deactivate, expire all use same fetch+csrfToken+JSON pattern"

requirements-completed: [SESS-01, SESS-02, SESS-03, SESS-04, SESS-05, UPLD-01, UPLD-02, UPLD-03, UPLD-04, UPLD-05, UPLD-06, UPLD-07, UPLD-08, DASH-05]

# Metrics
duration: 1min
completed: 2026-03-01
---

# Phase 02 Plan 05: Token Deactivation Wiring Summary

**POST route and JS fetch handler wiring deactivateToken button to FinanzUploadService.deactivate_token()**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-01T14:28:47Z
- **Completed:** 2026-03-01T14:29:41Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Added POST /sessions/<id>/deactivate-token route calling upload_service.deactivate_token()
- Replaced stub reload-only JS handler with proper fetch POST including CSRF token
- Full error handling following existing route patterns (try/except, logger, JSON responses)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add deactivate-token route and fix JS handler** - `acfc3fa` (feat)

## Files Created/Modified
- `app/routes/finanzberatung/sessions.py` - Added route 10 (deactivate-token) with @require_login, JSON validation, service call, logging
- `templates/finanzberatung/session_detail.html` - Replaced stub handler with fetch POST to deactivate-token endpoint

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Token deactivation fully wired: button -> JS fetch POST -> Flask route -> service method -> database update -> page reload
- Phase 02 gap closure plan complete -- all session and upload functionality is now fully connected

---
*Phase: 02-sessions-upload*
*Completed: 2026-03-01*
