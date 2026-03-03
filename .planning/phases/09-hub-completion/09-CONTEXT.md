# Phase 9: Hub Integration Completion - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Finanzberatung is accessible to all openers/closers via role-based access and discoverable from Slots and T2 pages via cross-tool links. The tool tile already exists (Phase 7) — this phase expands who can see it and adds cross-tool navigation.

</domain>

<decisions>
## Implementation Decisions

### Cross-link placement
- Slots: Add "Finanzberatung starten" button in the quick action bar (next to "Heute" and "Neuer Termin" buttons)
- T2: Add "Zur Finanzberatung" button in the quick navigation bar (next to "Meine Analytics" button)
- Both links use icon + text (lucide file-search icon, matching the tool tile)
- Links only render for users with Finanzberatung access — non-eligible users don't see them at all

### Access control scope
- Access granted to: all Openers + all Closers + all Admins (union of the three lists)
- Hardcoded union list in `has_tool_access()`, same pattern as existing T2 access
- Finanzberatung admin routes (`/finanzberatung/admin/*`) remain admin-only — openers/closers get session management routes only

### Route-level protection
- Add `before_request` hook on the finanzberatung blueprint for centralized role check
- Upload routes (token-based, CSRF-exempt) excluded from the role check — customers access these without login
- Unauthorized users redirected to hub dashboard with flash message ("Kein Zugriff auf Finanzberatung")

### Claude's Discretion
- Exact button styling (btn-ghost vs btn-primary vs btn-secondary) to match neighboring buttons
- Flash message wording
- Whether to log unauthorized access attempts

</decisions>

<specifics>
## Specific Ideas

No specific requirements — standard approach consistent with existing tool access patterns.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `has_tool_access()` in `app/routes/hub.py:574-629`: Central access control function — needs update for finanzberatung entry
- `get_user_tools()` in `app/routes/hub.py:282-398`: Tool tile config — already has finanzberatung tile with correct icon/color/url
- `@require_login` decorator in `app/utils/decorators.py`: Existing auth decorator pattern

### Established Patterns
- Hardcoded username lists for role-based access (T2: lines 592-598, onboarding: lines 602-606)
- Quick action buttons in Slots: `templates/slots/dashboard.html` lines 10-21 (flex wrap gap-3 with btn classes)
- Quick nav buttons in T2: `templates/t2/dashboard.html` lines 22-33 (flex gap-4 with btn classes, admin-conditional)
- Feature flag guard: `FinanzConfig.FINANZ_ENABLED` already filters tile in `get_user_tools()`

### Integration Points
- `app/routes/hub.py:622-623`: Change finanzberatung access from `('Admin', 'luke.hoppe')` to opener+closer+admin union
- `templates/slots/dashboard.html`: Quick action bar at top of content block
- `templates/t2/dashboard.html`: Quick navigation section below header
- `app/routes/finanzberatung/__init__.py`: Add before_request hook (exclude upload_bp)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-hub-completion*
*Context gathered: 2026-03-03*
