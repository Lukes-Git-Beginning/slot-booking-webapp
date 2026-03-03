---
phase: 09-hub-completion
plan: "01"
subsystem: auth
tags: [flask, jinja2, access-control, blueprint, finanzberatung, role-based-access]

# Dependency graph
requires:
  - phase: 07-admin-dsgvo
    provides: Finanzberatung blueprint and session routes built in Phase 7
  - phase: 08-config-dsgvo-fix
    provides: FinanzConfig class with FINANZ_ENABLED feature flag
provides:
  - Role-based access control expanded to all openers (8) + closers (6) + admins
  - Blueprint before_request guard protecting all /finanzberatung/* routes except upload
  - finanz_access global template context variable available in all templates
  - Cross-tool navigation links in Slots day view and T2 dashboard
affects:
  - deployment (no new dependencies, just config change — FINANZ_ENABLED must be true on server)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "before_request hook on Blueprint for route-level access control with upload exclusion"
    - "Global context processor injects role-based boolean for template gating"
    - "Explicit admin username inclusion in access list when Config.get_admin_users() uses legacy names"

key-files:
  created: []
  modified:
    - app/routes/hub.py
    - app/__init__.py
    - app/routes/finanzberatung/__init__.py
    - templates/index.html
    - templates/t2/dashboard.html

key-decisions:
  - "luke.hoppe added explicitly to finanz_access list because Config.get_admin_users() returns legacy names (Jose, Simon, etc.) not dot-notation usernames"
  - "before_request guard uses 'upload' substring check on endpoint name to exclude all upload routes"
  - "finanz_access injected as global context variable (not per-route) for use in Slots and T2 templates without modifying their route views"
  - "btn-ghost (no btn-sm) in T2 nav to match existing nav bar sizing; btn-sm btn-ghost in Slots to match Quick Actions bar"

patterns-established:
  - "Access list pattern: explicit username list + is_admin OR — same in both has_tool_access() and user_has_tool_access()"
  - "Blueprint guard pattern: feature flag check → endpoint exclusion → login check → role check"

requirements-completed: [HUBI-02, HUBI-03]

# Metrics
duration: 2min
completed: 2026-03-03
---

# Phase 9 Plan 01: Hub Completion Summary

**Finanzberatung access expanded to all 11 opener+closer consultants with blueprint guard, global finanz_access context variable, and cross-tool nav links in Slots and T2 dashboards**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-03T21:42:16Z
- **Completed:** 2026-03-03T21:43:54Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- has_tool_access() and user_has_tool_access() now grant finanzberatung access to all 11 opener+closer users (christian.mast, tim.kreisel, daniel.herbort, sonja.mast, simon.mast, dominik.mikic, ann-kathrin.welge, sara.mast, jose.torspecken, alexander.nehm, david.nehm) plus luke.hoppe and Config admins
- Blueprint before_request guard on finanzberatung_bp redirects unauthorized users to hub with flash message; upload routes excluded for customer QR flow
- finanz_access boolean injected into all templates globally via context processor — no route-level changes needed in Slots or T2 views
- "Finanzberatung starten" link added to Slots day view Quick Actions bar (file-search icon, btn-sm btn-ghost)
- "Zur Finanzberatung" link added to T2 dashboard Quick Navigation bar (file-search icon, btn-ghost)

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand access control and add blueprint guard** - `f7ed912` (feat)
2. **Task 2: Add cross-tool navigation links to Slots and T2 templates** - `641bc29` (feat)

## Files Created/Modified

- `app/routes/hub.py` - finanzberatung block in has_tool_access() expanded from 2 users to 12 (11 consultants + luke.hoppe explicit)
- `app/__init__.py` - finanzberatung block added to user_has_tool_access(); finanz_access added to inject_global_vars() context processor
- `app/routes/finanzberatung/__init__.py` - before_request hook added after blueprint creation; flask imports expanded
- `templates/index.html` - Conditional "Finanzberatung starten" link in Quick Actions bar (lines 353-357)
- `templates/t2/dashboard.html` - Conditional "Zur Finanzberatung" link in Quick Navigation bar (lines 27-32)

## Decisions Made

- **luke.hoppe explicit in access list:** Config.get_admin_users() returns legacy display names (Jose, Simon, Alex, David) not dot-notation usernames. luke.hoppe would not match is_admin without explicit inclusion. Added to finanz_access list directly.
- **btn-ghost without btn-sm in T2:** T2 nav bar uses larger buttons; kept consistent with existing nav sizing. Slots Quick Actions uses btn-sm to match existing action buttons there.
- **finanz_access as global context:** Avoids modifying Slots and T2 route view functions. The inject_global_vars() context processor already handles per-user context; clean extension.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added luke.hoppe to finanz_access list**
- **Found during:** Task 1 verification (automated assertion script)
- **Issue:** luke.hoppe is an admin per ROLES_AND_CALENDARS.md but Config.get_admin_users() returns legacy names (Jose, Simon, Alex, David) — is_admin was False for luke.hoppe, causing assertion failure
- **Fix:** Added 'luke.hoppe' explicitly to the finanz_access list under "Admins not covered by opener/closer lists" comment
- **Files modified:** app/routes/hub.py
- **Verification:** Assertion `has_tool_access('luke.hoppe', 'finanzberatung') == True` now passes
- **Committed in:** f7ed912 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Essential fix — luke.hoppe would have been locked out of the tool they administer. No scope creep.

## Issues Encountered

None — plan executed cleanly after the luke.hoppe access fix.

## User Setup Required

None - no external service configuration required. FINANZ_ENABLED must be true in server .env for links to appear (already set per Phase 7 memory note).

## Next Phase Readiness

- Phase 09-01 complete — Finanzberatung is now accessible to all eligible consultants
- No further hub completion work pending in this phase
- Deployment needed to activate on server: `git pull` + restart (no migrations, no new dependencies)

---
*Phase: 09-hub-completion*
*Completed: 2026-03-03*

## Self-Check: PASSED

All files verified present. Both task commits (f7ed912, 641bc29) confirmed in git log.
