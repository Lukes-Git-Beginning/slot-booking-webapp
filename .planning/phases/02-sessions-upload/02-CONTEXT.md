# Phase 2: Sessions + Upload - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Consultants can create financial consulting sessions and customers can upload documents via QR code on their phone. This covers: session CRUD, token-based upload with QR codes, mobile-optimized upload page, and real-time SSE notifications when documents arrive. Dashboards (Phase 3), document processing pipeline (Phase 4), and analysis (Phase 5) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Mobile Upload UX
- Camera-first layout: large camera button prominently displayed, file picker secondary
- Per-file progress as inline cards: each file becomes a card showing thumbnail/icon, filename, progress bar, status (uploading/done/error)
- Client-side validation before upload: validate file type and size before starting upload, show toast/modal with clear error message ('Nur PDF und Bilder erlaubt' / 'Datei zu groß'), file never enters upload queue
- Branded minimal page: ZFA logo at top, customer name greeting ('Hallo Herr Müller'), brief instruction text ('Laden Sie Ihre Unterlagen hoch'), gold/teal brand colors. Professional but friendly
- Standalone template (no base.html inheritance) — touch-optimized with 48px+ buttons per DASH-05

### QR Code + Token Flow
- Prominent QR card on session detail page: large QR code in dedicated card, one-click to regenerate
- Live countdown timer: shows 'Gültig noch: 1:45:23' ticking every second, color changes at 15 min (yellow) and 5 min (red)
- Auto-show regenerate on expiry: QR card switches to 'Token abgelaufen' state with prominent 'Neuen Token erstellen' button, old QR grays out
- Customer sees 'Link abgelaufen' with clear message if they try an expired URL
- Followup token available only after T1 token expires or is fully used — clean sequential flow, prevents confusion between active tokens

### Session Management
- Table list layout for session overview: sortable columns (customer, status, date, documents, opener)
- Minimal 3-field creation form: customer name, session type (dropdown: Erstberatung/Folgeberatung), appointment date. Opener auto-set from logged-in user. Closer assigned later
- Inline editable notes with auto-save: notes area directly on session detail page, auto-saves on blur or after short delay
- Opener sees T1 notes section (editable), Closer sees T1 notes (read-only) + T2 notes (editable)
- Own sessions only: each opener sees only sessions they created. Admins see all sessions

### SSE Notifications
- Dual notification system: toast notifications globally (any page) + live feed on session detail page
- Toast: slide-in bottom-right corner, shows 'Neues Dokument: filename von Kundenname', auto-dismiss after 5s, click navigates to session
- Subtle notification sound with toggle-off option in settings
- Live feed on session detail: rich cards per upload showing file icon (PDF/image), original filename, file size, upload timestamp, status badge. Stacks chronologically
- Auto-reconnect with exponential backoff on connection drop, visual indicator ('Verbindung unterbrochen...' / 'Wieder verbunden'), missed events fetched on reconnect

### Claude's Discretion
- Loading skeleton design for session list and detail views
- Exact spacing, typography, and card styling within brand guidelines
- SSE implementation details (event format, channel naming, heartbeat interval)
- Error state designs for failed uploads (server-side errors after validation passes)
- Session detail page layout and section ordering
- Sound file choice for notification audio
- Reconnect backoff timing parameters

</decisions>

<specifics>
## Specific Ideas

- Camera button should be the dominant action on mobile — customers will mostly photograph paper documents during the appointment
- QR code should be large enough that the consultant can show their screen to the customer (no printing necessary)
- The upload page should feel trustworthy to customers who may not be tech-savvy — clear, simple, minimal choices
- Token countdown with color coding gives urgency awareness without requiring the consultant to actively monitor

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- **QR code generation** (`app/services/security_service.py:144-157`): existing pattern using `qrcode` library with base64 encoding for HTML embedding — directly reusable for upload token QR codes
- **Database models** (`app/models/finanzberatung.py`): all 6 models with enums, relationships, and state machine (FinanzSession.transition_to()) already built in Phase 1
- **Celery infrastructure** (`app/core/celery_init.py`, `app/services/finanz_tasks.py`): configured with Flask app context wrapping, shared_task pattern, health check task
- **Auth decorators** (`app/utils/decorators.py`): `@require_login`, `@require_admin` ready to use
- **CSRF protection**: Flask-WTF configured globally

### Established Patterns
- **Blueprint structure**: parent blueprint with sub-modules (see `app/routes/t2/` and `app/routes/admin/`)
- **Service pattern**: singleton instances with error handling and logging (see `data_persistence.py`)
- **Config pattern**: static class attributes with env var fallback in `app/config/base.py`
- **Template inheritance**: all areas use `hub/base.html` → Tailwind + DaisyUI, except standalone pages
- **Logging**: `logging.getLogger(__name__)` throughout, never `print()`
- **Extension init**: try/catch with graceful degradation in `app/core/extensions.py`

### Integration Points
- **Blueprint registration**: `app/__init__.py:register_blueprints()` — add finanzberatung_bp with try/catch pattern
- **Template context**: `register_template_context()` provides `current_user`, `is_admin`, `csp_nonce`, `notifications`
- **Database access**: `from app.models import get_db_session` for PostgreSQL queries
- **Upload directory**: needs to be added to systemd `ReadWritePaths` on production server

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-sessions-upload*
*Context gathered: 2026-03-01*
