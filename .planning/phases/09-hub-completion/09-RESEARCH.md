# Phase 09: Hub Integration Completion - Research

**Researched:** 2026-03-03
**Domain:** Flask blueprint access control + Jinja2 template conditional rendering
**Confidence:** HIGH

## Summary

Phase 9 is a pure integration phase — no new infrastructure, no new services, no new models. It expands who can see the Finanzberatung tool tile (HUBI-02) and adds cross-tool navigation links in the Slots and T2 dashboards (HUBI-03). All patterns needed already exist in the codebase and can be directly copied and adapted.

The three implementation touchpoints are: (1) `has_tool_access()` in `app/routes/hub.py` — replace the narrow two-username guard with the full opener+closer+admin union; (2) `finanzberatung_bp.before_request` hook in `app/routes/finanzberatung/__init__.py` — centralized role check that redirects unauthorized users to hub with a flash message; (3) two template edits — add a conditional anchor tag to the quick action bar in `templates/slots/dashboard.html` and the quick nav bar in `templates/t2/dashboard.html`.

**Primary recommendation:** Copy the `@analytics_bp.before_request` pattern for the blueprint guard. Copy the `{% if is_admin %}` conditional block pattern for cross-tool template links. The user list for finanzberatung access is the union of the opener and closer lists from `docs/ROLES_AND_CALENDARS.md`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Cross-link placement:**
- Slots: Add "Finanzberatung starten" button in the quick action bar (next to "Heute" and "Neuer Termin" buttons)
- T2: Add "Zur Finanzberatung" button in the quick navigation bar (next to "Meine Analytics" button)
- Both links use icon + text (lucide file-search icon, matching the tool tile)
- Links only render for users with Finanzberatung access — non-eligible users don't see them at all

**Access control scope:**
- Access granted to: all Openers + all Closers + all Admins (union of the three lists)
- Hardcoded union list in `has_tool_access()`, same pattern as existing T2 access
- Finanzberatung admin routes (`/finanzberatung/admin/*`) remain admin-only — openers/closers get session management routes only

**Route-level protection:**
- Add `before_request` hook on the finanzberatung blueprint for centralized role check
- Upload routes (token-based, CSRF-exempt) excluded from the role check — customers access these without login
- Unauthorized users redirected to hub dashboard with flash message ("Kein Zugriff auf Finanzberatung")

### Claude's Discretion
- Exact button styling (btn-ghost vs btn-primary vs btn-secondary) to match neighboring buttons
- Flash message wording
- Whether to log unauthorized access attempts

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HUBI-02 | Access control: all openers and closers can access the Finanzberatung tool | `has_tool_access()` at hub.py:622-623 needs the hardcoded union list replacing the narrow two-username guard; same pattern as T2 access list at hub.py:592-598 |
| HUBI-03 | Cross-tool links: Slots -> "Finanzberatung starten", T2 -> "Zur Finanzberatung" | Template conditional blocks follow the `{% if is_admin %}` pattern in t2/dashboard.html; route views need to pass a `finanz_access` boolean to templates |
</phase_requirements>

---

## Standard Stack

No new dependencies required. This phase uses existing infrastructure only.

### Core (all pre-installed)
| Component | Location | Purpose |
|-----------|----------|---------|
| Flask blueprints | `app/routes/finanzberatung/__init__.py` | `before_request` hook registration |
| Jinja2 conditionals | `templates/slots/dashboard.html`, `templates/t2/dashboard.html` | Conditional link rendering |
| `has_tool_access()` | `app/routes/hub.py:574-629` | Central access check function |
| `require_admin` decorator | `app/utils/decorators.py` | Admin-only guard (already on `/finanzberatung/admin/*`) |

**Installation:** None required.

---

## Architecture Patterns

### Pattern 1: Blueprint `before_request` Guard (already in codebase)

`app/routes/analytics.py` provides the exact pattern to follow:

```python
# Source: app/routes/analytics.py:15-21
@analytics_bp.before_request
def require_admin():
    """Analytics nur für Admins"""
    user = session.get('user')
    if not user or not is_admin(user):
        from flask import abort
        abort(403)
```

For Finanzberatung, the guard must redirect (not abort) and must EXCLUDE upload routes. The upload sub-blueprint routes start with `/finanzberatung/upload/` — check `request.path` or `request.endpoint` to skip the guard for those routes.

```python
# Target pattern for app/routes/finanzberatung/__init__.py
@finanzberatung_bp.before_request
def require_finanz_access():
    """Restrict finanzberatung to openers, closers, and admins.
    Upload routes are excluded — customers access those via token without login.
    """
    from flask import request, session, redirect, url_for, flash

    # Skip: upload routes (customer-facing, token-based, no login required)
    # Upload routes are registered on upload_bp with paths like /finanzberatung/upload/<token>
    if request.endpoint and 'upload' in request.endpoint:
        return None  # Allow through

    user = session.get('user')
    if not user or not _has_finanz_access(user):
        flash("Kein Zugriff auf Finanzberatung", "error")
        return redirect(url_for('hub.dashboard'))
```

**Key constraint:** `before_request` on the parent blueprint fires for ALL registered sub-blueprints (sessions, upload, sse, admin). The upload exclusion is mandatory.

### Pattern 2: Hardcoded Role Access List (existing pattern in `has_tool_access`)

```python
# Source: app/routes/hub.py:590-598 (T2 access pattern)
if tool_id == 't2':
    t2_access = [
        'jose.torspecken', 'alexander.nehm', 'david.nehm',
        'tim.kreisel', 'christian.mast', 'daniel.herbort',
        'sonja.mast', 'simon.mast', 'dominik.mikic',
        'ann-kathrin.welge', 'sara.mast',
    ]
    return is_admin or username in t2_access
```

For Finanzberatung, replace the current guard (hub.py:622-623) with the opener+closer union:

```python
# Target: app/routes/hub.py:621-628
if tool_id == 'finanzberatung':
    finanz_access = [
        # Openers (from ROLES_AND_CALENDARS.md)
        'christian.mast', 'tim.kreisel', 'daniel.herbort', 'sonja.mast',
        'simon.mast', 'dominik.mikic', 'ann-kathrin.welge', 'sara.mast',
        # Closers (from ROLES_AND_CALENDARS.md)
        'jose.torspecken', 'alexander.nehm', 'david.nehm',
        'tim.kreisel', 'christian.mast', 'daniel.herbort',  # overlap is fine
    ]
    return is_admin or username in finanz_access
```

Use a `set()` for deduplication or just leave overlap — Python `in` on a list handles it.

### Pattern 3: Template Conditional Link (existing `is_admin` pattern)

```jinja2
{# Source: templates/t2/dashboard.html:27-32 #}
{% if is_admin %}
<a href="{{ url_for('t2.admin_bucket_config') }}" class="btn btn-warning gap-2">
    <i data-lucide="settings" class="w-5 h-5"></i>
    Bucket Config (Admin)
</a>
{% endif %}
```

Template links must be gated by a boolean passed from the route view. Two options:

**Option A (preferred — no template context_processor):** Pass `finanz_access` boolean from each dashboard view function.

T2 dashboard route (`app/routes/t2/core.py:40-50`):
```python
from app.routes.hub import has_tool_access

dashboard_data = {
    'user': user,
    'is_admin': is_admin_user(user),
    'finanz_access': has_tool_access(user, 'finanzberatung'),
    # ... existing keys
}
```

Slots dashboard route: The `slots/dashboard.html` template is NOT currently rendered by any route — the template file exists but there is no route that calls `render_template('slots/dashboard.html', ...)`. **This requires investigation during planning.** The CONTEXT.md references it as if it exists; the template file does exist at `templates/slots/dashboard.html`.

**Option B:** Use a Jinja2 global or context_processor. Not recommended — adds indirection for a one-off need.

### Recommended Project Structure

No new files needed. All changes are in-place edits:

```
app/routes/
├── hub.py                         # Edit: has_tool_access() finanzberatung block
├── finanzberatung/
│   └── __init__.py                # Edit: add before_request hook
├── t2/
│   └── core.py                    # Edit: pass finanz_access to template
└── [slots dashboard route]        # Edit: pass finanz_access to template

templates/
├── slots/dashboard.html           # Edit: add conditional link in quick action bar
└── t2/dashboard.html              # Edit: add conditional link in quick nav bar
```

### Anti-Patterns to Avoid

- **Guarding upload routes with login checks:** The upload sub-blueprint is CSRF-exempt specifically because customers access it without accounts. The `before_request` hook MUST skip upload endpoints.
- **Admin-only finanzberatung admin routes:** Do NOT remove the `@require_admin` decorator from `app/routes/finanzberatung/admin.py`. The before_request hook applies to all routes; admin routes have double protection — the blueprint hook redirects non-finanz-users, and `@require_admin` further restricts admin sub-routes to admins only.
- **Duplicate usernames in the access list:** Openers and closers overlap (christian.mast, tim.kreisel, daniel.herbort are both). A set union avoids confusion.
- **Modifying `get_user_tools()` instead of `has_tool_access()`:** The tool tile visibility already flows through `has_tool_access()`. Do not add a second code path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Access check function | New `_has_finanz_access()` standalone function | Extend `has_tool_access(tool_id='finanzberatung')` | Single source of truth; already tested |
| Upload route detection in before_request | URL prefix matching | `request.endpoint and 'upload' in request.endpoint` | Reliable; endpoint names are stable |
| Template variable propagation | Context processor | Pass boolean from view function directly | Simpler, more explicit, no magic |

---

## Common Pitfalls

### Pitfall 1: `before_request` Fires for Upload Routes Too
**What goes wrong:** Customer accesses `/finanzberatung/upload/<token>` — no login exists, the hook redirects them to `/login` or hub, QR code upload flow breaks.
**Why it happens:** `before_request` on a parent blueprint runs for ALL sub-blueprints including `upload_bp`.
**How to avoid:** Check `request.endpoint` — upload routes will have endpoints like `finanz_upload.*` or `finanzberatung.finanz_upload.*`. Add early return: `if request.endpoint and 'upload' in request.endpoint: return None`.
**Warning signs:** QR code upload page always redirects instead of showing the upload form.

### Pitfall 2: `slots/dashboard.html` Route Does Not Exist
**What goes wrong:** CONTEXT.md references `templates/slots/dashboard.html` as if it has a rendering route, but code search shows no route renders it. The blueprint names registered under `/slots` are `main`, `booking`, `calendar`, `scoreboard`, `user_profile` — not `slots`.
**Why it happens:** The template was created speculatively (ahead of the route). The template uses `url_for('slots.booking_page')` which would fail at render time (no such endpoint `slots.booking_page`).
**How to avoid:** During planning, identify WHICH actual route should render this template — or add the Finanzberatung link to a template that IS currently rendered (e.g., `templates/index.html` or `templates/slots/calendar_view.html`). The CONTEXT.md says "quick action bar in Slots" — confirm which page that refers to in production.
**Warning signs:** `BuildError: Could not build url for endpoint 'slots.booking_page'` at runtime.

### Pitfall 3: Admin Users Not in Opener/Closer Lists
**What goes wrong:** `alexander.nehm`, `david.nehm`, `simon.mast`, `luke.hoppe` are admins. They are NOT all in the explicit opener/closer lists. Without `is_admin or username in finanz_access`, admins who are not also openers/closers would be excluded.
**Why it happens:** Admin check is separate from role lists.
**How to avoid:** Always use `return is_admin or username in finanz_access` — same as T2 pattern.

### Pitfall 4: `finanz_enabled` Template Variable Missing
**What goes wrong:** The Finanzberatung feature is behind `FINANZ_ENABLED` flag. If the link is shown unconditionally in Slots/T2 templates, it appears even when the feature is disabled.
**Why it happens:** Template conditional only checks `finanz_access`, not whether feature is enabled.
**How to avoid:** Gate the template link on BOTH: `{% if finanz_access and finanz_enabled %}` — or make the route view only pass `finanz_access=True` when `FinanzConfig.FINANZ_ENABLED` is also true.
**Note:** `has_tool_access()` does NOT check `FINANZ_ENABLED` — that check is in `get_user_tools()`. The before_request hook should also check `FINANZ_ENABLED` and skip if disabled.

---

## Code Examples

### Access List Derivation (from ROLES_AND_CALENDARS.md)

```python
# Source: docs/ROLES_AND_CALENDARS.md - Opener Users
openers = [
    'christian.mast', 'tim.kreisel', 'daniel.herbort', 'sonja.mast',
    'simon.mast', 'dominik.mikic', 'ann-kathrin.welge', 'sara.mast',
]

# Source: docs/ROLES_AND_CALENDARS.md - Closer Users
closers = [
    'jose.torspecken', 'alexander.nehm', 'david.nehm',
    'tim.kreisel', 'christian.mast', 'daniel.herbort',
]

# Union (order-preserving, deduplicated):
finanz_access = list(dict.fromkeys(openers + closers))
# Result: 10 unique usernames
# ['christian.mast', 'tim.kreisel', 'daniel.herbort', 'sonja.mast',
#  'simon.mast', 'dominik.mikic', 'ann-kathrin.welge', 'sara.mast',
#  'jose.torspecken', 'alexander.nehm', 'david.nehm']
```

### T2 Quick Nav Addition

```jinja2
{# Source: templates/t2/dashboard.html:22-33 (existing quick nav pattern) #}
<!-- Quick Navigation -->
<div class="flex gap-4 mb-8 flex-wrap" data-aos="fade-up" data-aos-delay="100">
    <a href="{{ url_for('t2.my_analytics') }}" class="btn btn-primary gap-2 border-2 border-primary/50">
        <i data-lucide="bar-chart-3" class="w-5 h-5"></i>
        Meine Analytics
    </a>
    {% if finanz_access %}
    <a href="{{ url_for('finanzberatung.finanz_sessions.session_list') }}" class="btn btn-ghost gap-2">
        <i data-lucide="file-search" class="w-5 h-5"></i>
        Zur Finanzberatung
    </a>
    {% endif %}
    {% if is_admin %}
    <a href="{{ url_for('t2.admin_bucket_config') }}" class="btn btn-warning gap-2">
        ...
    </a>
    {% endif %}
</div>
```

Note: The URL endpoint for the finanzberatung session list needs verification. The sessions sub-blueprint registers as `finanz_sessions` (`sessions_bp = Blueprint('finanz_sessions', __name__)`). The parent blueprint is `finanzberatung`. The session list route endpoint is `finanzberatung.finanz_sessions.session_list` — verify during implementation.

### Slots Quick Action Bar Addition

```jinja2
{# Source: templates/slots/dashboard.html:10-21 (existing quick actions) #}
<div class="flex flex-wrap gap-3 mb-8" data-aos="fade-up">
    <a href="..." class="btn btn-ghost gap-2">
        <i data-lucide="calendar-days" class="w-5 h-5"></i>
        <span>Heute</span>
    </a>
    <a href="..." class="btn btn-primary gap-2">
        <i data-lucide="plus-circle" class="w-5 h-5"></i>
        <span>Neuer Termin</span>
    </a>
    {% if finanz_access %}
    <a href="{{ url_for('finanzberatung.finanz_sessions.session_list') }}" class="btn btn-ghost gap-2">
        <i data-lucide="file-search" class="w-5 h-5"></i>
        <span>Finanzberatung starten</span>
    </a>
    {% endif %}
</div>
```

### Blueprint `before_request` with Upload Exclusion

```python
# Target: app/routes/finanzberatung/__init__.py (add after sub-blueprint registration)

@finanzberatung_bp.before_request
def require_finanz_access():
    """Restrict finanzberatung to authorized roles; skip upload routes."""
    from flask import request, session, redirect, url_for, flash
    try:
        from app.config.base import FinanzConfig
        if not FinanzConfig.FINANZ_ENABLED:
            flash("Finanzberatung ist nicht aktiviert", "warning")
            return redirect(url_for('hub.dashboard'))
    except Exception:
        pass

    # Upload routes: customer-facing, token-based, no login required
    endpoint = request.endpoint or ''
    if 'upload' in endpoint or 'sse' in endpoint:
        return None

    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))

    from app.routes.hub import has_tool_access
    if not has_tool_access(user, 'finanzberatung'):
        flash("Kein Zugriff auf Finanzberatung", "error")
        return redirect(url_for('hub.dashboard'))
```

---

## Open Questions

1. **Which template/route renders `slots/dashboard.html`?**
   - What we know: The file `templates/slots/dashboard.html` exists with quick action bar at lines 10-21. No route in `app/routes/` renders it (confirmed by code search). It references `url_for('slots.booking_page')` and `url_for('slots.day_view')` — neither endpoint exists under the name `slots.*`.
   - What's unclear: Is this template rendered at all in production? Is there a planned route not yet implemented? Or does "Slots page" in HUBI-03 actually mean a different template?
   - Recommendation: During planning (task creation), confirm with the CONTEXT.md intent. If the template is not rendered, the plan must either (a) add a route that renders it, or (b) redirect to an existing template that IS rendered (e.g., `templates/slots/calendar_view.html` or `templates/index.html`). Option (b) is lower risk for this phase.

2. **Finanzberatung session list endpoint name**
   - What we know: `sessions_bp = Blueprint('finanz_sessions', __name__)` in `app/routes/finanzberatung/sessions.py`. Parent blueprint is `finanzberatung`. Route decorator is `@sessions_bp.route('/sessions')`.
   - What's unclear: When a sub-blueprint is registered on a parent blueprint, the endpoint becomes `finanzberatung.finanz_sessions.session_list` — need to verify Flask sub-blueprint endpoint naming.
   - Recommendation: During implementation use `url_for('finanzberatung.finanz_sessions.session_list')` and test locally. If that fails, use `url_for('.finanz_sessions.session_list')` or a hardcoded path `/finanzberatung/sessions`.

3. **SSE routes exclusion in `before_request`**
   - What we know: `sse_bp` is also registered as a sub-blueprint. SSE routes provide real-time upload feeds to logged-in consultants — these ARE protected.
   - What's unclear: Should SSE be excluded from the `before_request` hook like upload routes, or should it be protected? SSE is only accessed by logged-in consultants during an active session.
   - Recommendation: Only exclude upload routes (token-based, customer-facing). SSE and sessions routes should both be protected by the access check.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `app/routes/hub.py:574-629` — `has_tool_access()` function, existing access list patterns
- Direct code inspection: `app/routes/analytics.py:15-21` — `before_request` guard pattern
- Direct code inspection: `app/routes/finanzberatung/__init__.py` — blueprint registration, CSRF exemption for upload sub-blueprint
- Direct code inspection: `app/routes/finanzberatung/sessions.py:40` — `sessions_bp = Blueprint('finanz_sessions', __name__)`
- Direct code inspection: `app/routes/finanzberatung/admin.py:22` — `@require_admin` already on admin routes
- Direct code inspection: `templates/t2/dashboard.html:22-33` — quick nav bar, `{% if is_admin %}` pattern
- Direct code inspection: `templates/slots/dashboard.html:10-21` — quick action bar
- Direct code inspection: `docs/ROLES_AND_CALENDARS.md` — canonical opener (8 users) and closer (6 users) lists
- Direct code inspection: `app/routes/t2/core.py:38-50` — T2 dashboard view, template context keys

### Secondary (MEDIUM confidence)
- Flask sub-blueprint endpoint naming: endpoint format `parent.child.function_name` — verified conceptually; exact string requires runtime test
- `slots/dashboard.html` rendering gap: determined by exhaustive grep across all route files; no render_template call found

---

## Metadata

**Confidence breakdown:**
- Access control change (HUBI-02): HIGH — exact line to edit identified (hub.py:622), exact user lists from authoritative ROLES_AND_CALENDARS.md
- before_request hook (HUBI-02): HIGH — identical pattern exists in analytics.py:15-21; upload exclusion logic is straightforward
- T2 template link (HUBI-03): HIGH — existing `{% if is_admin %}` pattern, T2 dashboard view passes `is_admin` already
- Slots template link (HUBI-03): MEDIUM — template exists but no route renders it; requires resolution during planning
- Finanzberatung URL endpoint name: MEDIUM — requires runtime verification of Flask sub-blueprint naming

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable codebase — no breaking framework changes expected)
