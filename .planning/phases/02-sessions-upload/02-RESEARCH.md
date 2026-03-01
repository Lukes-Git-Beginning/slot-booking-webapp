# Phase 2: Sessions + Upload - Research

**Researched:** 2026-03-01
**Domain:** Flask session CRUD, file upload with validation, QR code generation, SSE real-time notifications
**Confidence:** HIGH

## Summary

Phase 2 builds the complete upload vertical: consultants create sessions, generate QR codes with time-limited tokens, customers upload documents via mobile-optimized standalone pages, and consultants receive real-time SSE notifications. All database models (`FinanzSession`, `FinanzUploadToken`, `FinanzDocument`) and configuration (`FinanzConfig`) are already built in Phase 1 -- this phase adds the service layer, routes, templates, and real-time infrastructure.

The most significant technical challenge is SSE with the current production deployment. The server runs Gunicorn with `--worker-class sync --workers 4 --threads 2`. SSE requires long-lived HTTP connections. The recommended approach is Redis Pub/Sub for cross-worker event distribution (Redis is already deployed for Celery/sessions), combined with either switching to `gevent` workers or accepting that each SSE connection ties up one of the 8 available threads. Given the small user base (< 15 consultants), the threaded approach is viable initially.

**Primary recommendation:** Use Redis Pub/Sub for SSE event distribution, implement file validation with `python-magic` for magic byte checking, reuse the existing `qrcode` library pattern from `security_service.py`, and CSRF-exempt the public upload endpoint with custom token validation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Mobile Upload UX**: Camera-first layout with large camera button prominently displayed, file picker secondary. Per-file progress as inline cards. Client-side validation before upload. Branded minimal page with ZFA logo, customer name greeting, brief instruction text, gold/teal brand colors. Standalone template (no base.html inheritance) -- touch-optimized with 48px+ buttons per DASH-05
- **QR Code + Token Flow**: Prominent QR card on session detail page with large QR code. Live countdown timer showing 'Gueltig noch: 1:45:23' ticking every second, color changes at 15 min (yellow) and 5 min (red). Auto-show regenerate on expiry with 'Token abgelaufen' state. Customer sees 'Link abgelaufen' with clear message if expired. Followup token available only after T1 token expires or is fully used -- clean sequential flow
- **Session Management**: Table list layout with sortable columns. Minimal 3-field creation form (customer name, session type dropdown Erstberatung/Folgeberatung, appointment date). Opener auto-set from logged-in user. Inline editable notes with auto-save. Opener sees T1 notes (editable), Closer sees T1 notes (read-only) + T2 notes (editable). Own sessions only -- each opener sees only sessions they created, admins see all
- **SSE Notifications**: Dual notification system (toast globally + live feed on session detail). Toast slide-in bottom-right, auto-dismiss 5s, click navigates. Subtle notification sound with toggle-off. Live feed on session detail with rich cards per upload. Auto-reconnect with exponential backoff, visual indicator, missed events fetched on reconnect

### Claude's Discretion
- Loading skeleton design for session list and detail views
- Exact spacing, typography, and card styling within brand guidelines
- SSE implementation details (event format, channel naming, heartbeat interval)
- Error state designs for failed uploads (server-side errors after validation passes)
- Session detail page layout and section ordering
- Sound file choice for notification audio
- Reconnect backoff timing parameters

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SESS-01 | Opener can create session with customer name, type, appointment date | FinanzSession model ready, service layer pattern from existing services, 3-field form per CONTEXT.md |
| SESS-02 | Session status progresses through workflow | `FinanzSession.transition_to()` state machine built in Phase 1, routes need to expose transitions |
| SESS-03 | Opener can save T1 notes that transfer to Closer | `t1_notes` field on FinanzSession model, inline auto-save via AJAX per CONTEXT.md |
| SESS-04 | Closer can view T1 summary and add T2 notes | `t2_notes` field on model, role-based template rendering (opener vs closer) |
| SESS-05 | Session tracks assigned opener and closer | `opener_username` / `closer_username` fields on model, auto-set opener from session user |
| UPLD-01 | System generates crypto-secure upload tokens with configurable TTL | `FinanzUploadToken` model ready, `FinanzConfig` has TTL settings, use `secrets.token_urlsafe()` |
| UPLD-02 | QR code generated from upload token URL | Existing `qrcode` library (already in requirements.txt), reuse pattern from `security_service.py` |
| UPLD-03 | Customer uploads via mobile-optimized standalone page | Standalone template with camera-first layout, no base.html, CSRF-exempt with token auth |
| UPLD-04 | Upload validates file type via magic bytes | Use `python-magic` library for server-side magic byte validation, client-side pre-validation |
| UPLD-05 | Files stored with UUID filenames and SHA-256 hash | Standard library: `uuid.uuid4()` for filenames, `hashlib.sha256()` for dedup |
| UPLD-06 | Consultant receives real-time SSE notifications | Redis Pub/Sub for cross-worker distribution, Flask streaming response |
| UPLD-07 | Token enforces max upload count and expiry | `FinanzUploadToken.is_valid` property already built, enforce in upload route |
| UPLD-08 | Opener can generate followup tokens after T1 | Followup token generation with sequential flow logic (T1 must expire/exhaust first) |
| DASH-05 | Mobile upload page is standalone, touch-optimized, camera capture, progress | Standalone HTML template, `<input capture="environment">` for camera, 48px+ touch targets |
</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.1 | Web framework | Project standard |
| SQLAlchemy | 2.0.36 | ORM for FinanzSession, FinanzUploadToken, FinanzDocument | Already used for all models |
| Redis | 5.1.1 | SSE pub/sub message broker + session storage | Already deployed for Celery/sessions |
| qrcode | 8.0 | QR code generation | Already in requirements.txt, pattern in security_service.py |
| Pillow | 11.2.1 | Image processing (thumbnail generation) | Already in requirements.txt |

### New Dependencies Required
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-magic | 0.4.27+ | Magic byte file type validation (UPLD-04) | Server-side upload validation |
| pillow-heif | 0.21+ | HEIC file support for iPhone uploads | Register as Pillow plugin for HEIC reads |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python-magic | puremagic | puremagic is pure Python (no libmagic dependency) but less accurate; python-magic uses the same C library as the `file` command -- more reliable for security-critical validation |
| Custom SSE | Flask-SSE | Flask-SSE adds Redis dependency (already have it) but forces gevent workers; custom SSE gives more control over the threading approach |
| gevent workers | sync+threads | gevent requires monkey-patching (risky with psycopg2), sync+threads simpler but limits concurrent SSE connections to thread count |

**Installation:**
```bash
pip install python-magic pillow-heif
# On Linux (production server):
apt-get install libmagic1  # Required by python-magic
```

**Note on python-magic:** On Windows (dev), use `python-magic-bin` which bundles libmagic. On Linux (production), `libmagic1` is typically already installed. The import is the same: `import magic`.

## Architecture Patterns

### Recommended Project Structure
```
app/
  routes/
    finanzberatung/
      __init__.py          # Blueprint registration (like t2/__init__.py)
      sessions.py          # Session CRUD routes (SESS-01..05)
      upload.py            # Upload routes - public + token-based (UPLD-01..08)
      sse.py               # SSE streaming endpoint (UPLD-06)
  services/
    finanz_session_service.py   # Session business logic
    finanz_upload_service.py    # Upload + file validation logic
    finanz_sse_service.py       # Redis pub/sub SSE manager
templates/
  finanzberatung/
    session_list.html       # Session overview table (extends hub/base.html)
    session_detail.html     # Session detail with QR, notes, upload feed (extends hub/base.html)
    session_create.html     # 3-field creation form (extends hub/base.html)
    upload.html             # STANDALONE mobile upload page (NO base.html)
    upload_expired.html     # STANDALONE token expired page
```

### Pattern 1: Blueprint with Sub-Modules (from T2 pattern)
**What:** Parent blueprint with functional sub-modules, registered via `init_app()`.
**When to use:** All Phase 2 routes.
**Example:**
```python
# app/routes/finanzberatung/__init__.py
from flask import Blueprint

finanzberatung_bp = Blueprint('finanzberatung', __name__, url_prefix='/finanzberatung')

def init_app(app):
    from .sessions import sessions_bp
    from .upload import upload_bp
    from .sse import sse_bp

    finanzberatung_bp.register_blueprint(sessions_bp, url_prefix='')
    finanzberatung_bp.register_blueprint(upload_bp, url_prefix='')
    finanzberatung_bp.register_blueprint(sse_bp, url_prefix='')

    app.register_blueprint(finanzberatung_bp)
```

### Pattern 2: Service Layer (from existing services)
**What:** Business logic in service classes, never in routes.
**When to use:** All data operations.
**Example:**
```python
# app/services/finanz_session_service.py
import logging
from app.models import get_db_session
from app.models.finanzberatung import FinanzSession, SessionStatus

logger = logging.getLogger(__name__)

class FinanzSessionService:
    def create_session(self, opener_username, customer_name, session_type, appointment_date):
        db = get_db_session()
        try:
            session = FinanzSession(
                opener_username=opener_username,
                customer_name=customer_name,
                session_type=session_type,
                appointment_date=appointment_date,
                status=SessionStatus.ACTIVE.value,
            )
            db.add(session)
            db.commit()
            return session
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create session: {e}")
            raise
        finally:
            db.close()
```

### Pattern 3: SSE via Redis Pub/Sub
**What:** Redis channels for cross-worker SSE event distribution.
**When to use:** Real-time upload notifications (UPLD-06).
**Example:**
```python
# app/services/finanz_sse_service.py
import json
import redis
import logging
from flask import Response, stream_with_context

logger = logging.getLogger(__name__)

class SSEManager:
    def __init__(self, redis_url):
        self.redis = redis.from_url(redis_url)

    def publish(self, channel, event_type, data):
        """Publish event to Redis channel (called after upload)."""
        message = json.dumps({
            'event': event_type,
            'data': data,
        })
        self.redis.publish(channel, message)

    def stream(self, channel):
        """Generator that yields SSE events from Redis subscription."""
        pubsub = self.redis.pubsub()
        pubsub.subscribe(channel)
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    payload = json.loads(message['data'])
                    yield f"event: {payload['event']}\ndata: {json.dumps(payload['data'])}\n\n"
                # Heartbeat every 30 seconds to keep connection alive
        except GeneratorExit:
            pubsub.unsubscribe(channel)
            pubsub.close()
```

### Pattern 4: CSRF-Exempt Public Upload Endpoint
**What:** Token-based upload route without CSRF (customers have no session).
**When to use:** The mobile upload page (UPLD-03).
**Example:**
```python
# In app/__init__.py register_blueprints():
from app.core.extensions import csrf
if csrf:
    csrf.exempt(upload_bp)  # Like hubspot_webhook_bp pattern
```

### Pattern 5: Standalone Template (Mobile Upload)
**What:** Self-contained HTML page without base.html inheritance.
**When to use:** Customer-facing upload page (DASH-05).
**Key considerations:**
- Must include its own `<meta viewport>` for mobile
- Must include Tailwind CSS inline or via CDN (no `url_for` since no login session)
- Must NOT reference `csp_nonce` or `current_user` context vars
- Touch targets minimum 48px per WCAG/Material guidelines
- Camera capture: `<input type="file" accept="image/*" capture="environment">`

### Anti-Patterns to Avoid
- **Business logic in routes:** All session CRUD, token generation, file validation MUST go through service layer
- **In-memory SSE without Redis:** Will not work across Gunicorn workers -- always use Redis Pub/Sub
- **Trusting file extensions for validation:** UPLD-04 explicitly requires magic byte validation; extension-only checking is a security vulnerability
- **Nested Flask app context in tests:** Use the existing `client` fixture pattern from conftest.py; never nest `with client:` inside an existing test client context
- **Using `print()` instead of `logging.getLogger(__name__)`:** Project rule from CLAUDE.md

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| QR code generation | Custom QR algorithm | `qrcode` library (already installed) | Complex encoding spec, existing pattern in `security_service.py:144-157` |
| File type detection | Extension-based checking | `python-magic` with libmagic | Magic bytes are the only reliable method; extensions are trivially spoofed |
| Crypto-secure tokens | Custom token generation | `secrets.token_urlsafe(48)` | Standard library, cryptographically secure |
| SHA-256 hashing | Custom hashing | `hashlib.sha256()` | Standard library, battle-tested |
| UUID filenames | Custom random naming | `uuid.uuid4()` | Guaranteed uniqueness, standard pattern |
| SSE event format | Custom streaming format | SSE spec (`event:`, `data:`, `\n\n`) | Browser `EventSource` API expects exact format |
| HEIC support | Custom HEIC parser | `pillow-heif` plugin | HEIC is Apple's proprietary format; library handles container parsing |
| Redis pub/sub | Custom message queue | `redis.pubsub()` | Already have Redis deployed, pub/sub is native feature |

**Key insight:** The upload pipeline has many deceptively complex pieces (magic byte validation, HEIC handling, SHA-256 dedup, UUID naming, SSE formatting). Each individually looks simple but has edge cases. Using established libraries eliminates entire categories of bugs.

## Common Pitfalls

### Pitfall 1: CSP Blocking SSE EventSource
**What goes wrong:** The browser's `EventSource` connection to `/finanzberatung/sse/stream` is blocked by Content-Security-Policy.
**Why it happens:** Current CSP has `connect-src 'self'` which should allow same-origin SSE, but if the SSE endpoint is on a different port or the streaming response doesn't set proper headers, it fails silently.
**How to avoid:** Verify `connect-src 'self'` covers the SSE endpoint (same origin). Ensure the SSE response sets `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`. Test in browser dev tools Network tab.
**Warning signs:** EventSource `onerror` fires immediately without any messages received.

### Pitfall 2: Gunicorn Sync Workers Blocking on SSE
**What goes wrong:** Each SSE connection holds a worker thread indefinitely. With 4 workers x 2 threads = 8 threads, 8 concurrent SSE connections would exhaust all capacity.
**Why it happens:** SSE is a long-lived HTTP connection. Sync workers block until the response generator completes (which it never does for SSE).
**How to avoid:** Two options: (a) Switch to `--worker-class gevent` (requires `gevent` package and careful monkey-patching), or (b) Keep sync workers but limit SSE connections and add aggressive timeouts (e.g., reconnect every 60s with `retry:` field). With < 15 consultants and not all viewing sessions simultaneously, option (b) is viable.
**Warning signs:** Application becomes unresponsive under normal load when multiple consultants have session detail pages open.

### Pitfall 3: CSRF Token on Upload Page
**What goes wrong:** The mobile upload page tries to submit a POST but Flask-WTF rejects it because the customer has no CSRF token (they're not logged in).
**Why it happens:** Flask-WTF's global CSRFProtect checks all POST requests by default.
**How to avoid:** CSRF-exempt the upload blueprint (like `hubspot_webhook_bp` pattern in `app/__init__.py:333-336`). The upload token itself serves as the authentication mechanism. Also ensure the upload route validates the token server-side before processing.
**Warning signs:** 400 Bad Request on upload submission from mobile.

### Pitfall 4: MAX_CONTENT_LENGTH Too Small for Financial Documents
**What goes wrong:** Large PDF scans (multi-page financial statements) exceed the 16MB `MAX_CONTENT_LENGTH` in production config.
**Why it happens:** `FinanzConfig.FINANZ_MAX_FILE_SIZE_MB` is 50MB but Flask's `MAX_CONTENT_LENGTH` in production.py is 16MB. Flask rejects the request before the route even runs.
**How to avoid:** Update `MAX_CONTENT_LENGTH` in production config to at least 50MB to match `FINANZ_MAX_FILE_SIZE_MB`, or implement per-blueprint content length limits. Alternatively, enforce the 50MB limit in the upload route after reading the file.
**Warning signs:** 413 Request Entity Too Large error in production that doesn't reproduce in development.

### Pitfall 5: File Ownership on Upload Directory
**What goes wrong:** Uploaded files are created with wrong ownership, causing read/write failures later.
**Why it happens:** The server runs as `business-hub:www-data` (from service file). New directories must be created with correct ownership and added to `ReadWritePaths` in systemd.
**How to avoid:** Add `finanz_uploads` directory to deployment checklist: `mkdir -p /opt/business-hub/data/finanz_uploads && chown -R business-hub:www-data /opt/business-hub/data/finanz_uploads`. Add path to `ReadWritePaths` in `business-hub.service`.
**Warning signs:** `PermissionError` when saving uploaded files in production.

### Pitfall 6: HEIC Files from iPhones
**What goes wrong:** iPhone users upload `.heic` files that fail validation or can't be processed downstream.
**Why it happens:** HEIC is Apple's default photo format since iOS 11. The `python-magic` library may identify it as `image/heif` or `application/octet-stream`. Without `pillow-heif`, Pillow can't open these files for thumbnail generation.
**How to avoid:** Install `pillow-heif` and call `register_heif_opener()` at app startup. Include `image/heif` and `image/heic` in allowed MIME types for magic byte validation. Note: modern iOS often converts to JPEG when uploading through `<input type="file">`, but `capture="environment"` may bypass this conversion.
**Warning signs:** Uploads from iPhones succeed but thumbnails fail to generate, or files are rejected as invalid type.

### Pitfall 7: SSE Reconnect Missing Events
**What goes wrong:** When a client disconnects and reconnects, they miss events that occurred during the disconnection.
**Why it happens:** Redis Pub/Sub is fire-and-forget -- messages are not persisted. If the client was disconnected, those messages are gone.
**How to avoid:** On reconnect, the client should fetch recent uploads via a REST endpoint (e.g., `GET /finanzberatung/sessions/<id>/documents?since=<timestamp>`). The SSE reconnect handler should call this endpoint with the `Last-Event-ID` header or a stored timestamp.
**Warning signs:** Consultant refreshes page and sees fewer uploads than expected.

## Code Examples

### Token Generation and QR Code
```python
# Reuse existing pattern from security_service.py:144-157
import secrets
import qrcode
import io
import base64
from datetime import datetime, timedelta
from app.config.base import finanz_config

def generate_upload_token(session_id, token_type, db_session):
    """Generate crypto-secure upload token with QR code."""
    token_value = secrets.token_urlsafe(48)

    ttl_map = {
        'T1': finanz_config.FINANZ_TOKEN_TTL_T1,
        'FOLLOWUP': finanz_config.FINANZ_TOKEN_TTL_FOLLOWUP,
        'T2': finanz_config.FINANZ_TOKEN_TTL_T2,
    }
    ttl = ttl_map.get(token_type, 7200)

    token = FinanzUploadToken(
        session_id=session_id,
        token=token_value,
        token_type=token_type,
        expires_at=datetime.utcnow() + timedelta(seconds=ttl),
        max_uploads=finanz_config.FINANZ_MAX_UPLOADS_PER_TOKEN,
    )
    db_session.add(token)
    db_session.commit()

    # Generate QR code as base64 (same pattern as security_service.py)
    upload_url = f"https://berater.zfa.gmbh/finanzberatung/upload/{token_value}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(upload_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return token, qr_base64
```

### Magic Byte File Validation
```python
import magic

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'image/heif',
    'image/heic',
}

def validate_file_type(file_storage):
    """Validate file type via magic bytes, not extension."""
    # Read first 2048 bytes for magic number detection
    header = file_storage.read(2048)
    file_storage.seek(0)  # Reset file pointer

    detected_mime = magic.from_buffer(header, mime=True)

    if detected_mime not in ALLOWED_MIME_TYPES:
        return False, detected_mime

    return True, detected_mime
```

### SSE Streaming Endpoint
```python
from flask import Response, stream_with_context, request

@sse_bp.route('/stream/<int:session_id>')
@require_login
def stream(session_id):
    """SSE endpoint for real-time upload notifications."""
    channel = f"finanz:session:{session_id}"

    def event_stream():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(channel)
        try:
            # Send initial connection event
            yield "event: connected\ndata: {}\n\n"
            while True:
                message = pubsub.get_message(timeout=30)
                if message and message['type'] == 'message':
                    yield f"data: {message['data'].decode()}\n\n"
                else:
                    # Heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return Response(
        stream_with_context(event_stream()),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
        }
    )
```

### Client-Side SSE with Auto-Reconnect
```javascript
function connectSSE(sessionId) {
    const evtSource = new EventSource(`/finanzberatung/sse/stream/${sessionId}`);
    let reconnectDelay = 1000;  // Start at 1s

    evtSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        showUploadNotification(data);
        reconnectDelay = 1000;  // Reset on success
    };

    evtSource.addEventListener('connected', function() {
        showConnectionStatus('connected');
        // Fetch missed events since last known timestamp
        fetchMissedUploads(sessionId);
    });

    evtSource.onerror = function() {
        showConnectionStatus('disconnected');
        evtSource.close();
        // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
        setTimeout(() => connectSSE(sessionId), reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 30000);
    };
}
```

### Mobile Upload Page Camera Input
```html
<!-- Camera-first layout for DASH-05 -->
<div class="flex flex-col gap-4 p-4">
    <!-- Primary: Camera capture -->
    <label class="btn btn-primary btn-lg w-full h-16 text-lg flex items-center justify-center gap-3"
           style="min-height: 48px;">
        <svg><!-- camera icon --></svg>
        Foto aufnehmen
        <input type="file" accept="image/*" capture="environment"
               class="hidden" onchange="handleFileSelect(this)">
    </label>

    <!-- Secondary: File picker -->
    <label class="btn btn-outline btn-secondary w-full h-14 text-base flex items-center justify-center gap-3"
           style="min-height: 48px;">
        <svg><!-- folder icon --></svg>
        Datei auswaehlen
        <input type="file" accept=".pdf,.jpg,.jpeg,.png,.tiff,.heic,image/*,application/pdf"
               multiple class="hidden" onchange="handleFileSelect(this)">
    </label>
</div>
```

### File Upload with Progress (Client-Side)
```javascript
function uploadFile(file, token) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('token', token);

    const xhr = new XMLHttpRequest();
    const card = createUploadCard(file);

    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            updateCardProgress(card, percent);
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            updateCardStatus(card, 'success');
        } else {
            const error = JSON.parse(xhr.responseText);
            updateCardStatus(card, 'error', error.message);
        }
    };

    xhr.onerror = function() {
        updateCardStatus(card, 'error', 'Upload fehlgeschlagen');
    };

    xhr.open('POST', `/finanzberatung/upload/${token}/submit`);
    xhr.send(formData);
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WebSockets for push | SSE for server-to-client unidirectional | Stable since HTML5 | Simpler setup, works through proxies, auto-reconnect built into EventSource API |
| Extension-based file validation | Magic byte validation | Always was best practice, now enforced | Prevents disguised malicious file uploads |
| Polling for updates | SSE with Redis Pub/Sub | Redis Pub/Sub mature since Redis 2.0 | Real-time updates without polling overhead |
| `capture="camera"` | `capture="environment"` | HTML Media Capture spec update | `"environment"` opens rear camera (for document scanning), `"user"` for selfie |

**Deprecated/outdated:**
- `datetime.utcnow()`: Deprecated in Python 3.12+, but project already uses it consistently in models -- keep consistent for now, refactor later
- `lazy='dynamic'` in SQLAlchemy 2.0: Project decided to use this in Phase 1 for query flexibility -- keep consistent

## Open Questions

1. **Gevent vs Threaded Workers for SSE**
   - What we know: Current deployment uses sync workers with 2 threads each (8 total). SSE ties up one thread per connection. With < 15 consultants, not all viewing sessions simultaneously.
   - What's unclear: Whether switching to gevent workers would break existing psycopg2 connections or other blocking I/O.
   - Recommendation: Start with sync+threads approach. If SSE connection count becomes an issue, migrate to gevent workers in a separate deployment task. Add SSE connection timeout (60s) with `retry: 5000` header to limit held threads.

2. **Upload URL Domain**
   - What we know: UPLD-02 specifies format `https://upload.zfa.de/finanzberatung/upload/{token}` but production is at `https://berater.zfa.gmbh/`.
   - What's unclear: Whether a separate upload subdomain will be set up.
   - Recommendation: Use `https://berater.zfa.gmbh/finanzberatung/upload/{token}` for now. The QR URL should be configurable via env var (`FINANZ_UPLOAD_BASE_URL`).

3. **Nginx Buffering for SSE**
   - What we know: Nginx (likely in front of Gunicorn) buffers responses by default, which breaks SSE streaming.
   - What's unclear: Current nginx configuration on the server.
   - Recommendation: Add `X-Accel-Buffering: no` response header on SSE endpoints (Flask side). Also document nginx config: `proxy_buffering off;` for the SSE route.

4. **python-magic on Windows (Development)**
   - What we know: `python-magic` requires `libmagic`. On Linux it's system-installed. On Windows, `python-magic-bin` bundles it.
   - What's unclear: Whether `python-magic-bin` is needed in requirements.txt or just developer documentation.
   - Recommendation: Add `python-magic` to requirements.txt. Document that Windows developers need `pip install python-magic-bin` separately. The import (`import magic`) is identical.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `app/models/finanzberatung.py` -- all 6 models verified with fields, relationships, indexes
- Existing codebase: `app/config/base.py:FinanzConfig` -- all config values verified
- Existing codebase: `app/services/security_service.py:144-157` -- QR code generation pattern
- Existing codebase: `app/__init__.py` -- blueprint registration, CSP headers, CSRF setup
- Existing codebase: `deployment/business-hub.service` -- Gunicorn sync workers, 4 workers, 2 threads
- [MDN: HTML capture attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/capture) -- camera capture spec
- [Flask-WTF CSRF docs](https://flask-wtf.readthedocs.io/en/0.15.x/csrf/) -- CSRF exemption patterns

### Secondary (MEDIUM confidence)
- [Max Halford: Flask SSE without deps](https://maxhalford.github.io/blog/flask-sse-no-deps/) -- verified SSE streaming pattern
- [Flask-SSE docs](https://flask-sse.readthedocs.io/en/latest/quickstart.html) -- Redis requirement for multi-worker
- [python-magic PyPI](https://pypi.org/project/python-magic/) -- magic byte validation library
- [pillow-heif PyPI](https://pypi.org/project/pillow-heif/) -- HEIC support for Pillow
- [HackerOne: Secure File Uploads in Flask](https://www.hackerone.com/blog/secure-file-uploads-flask-filtering-and-validation-techniques) -- security best practices

### Tertiary (LOW confidence)
- SSE performance with sync workers under load -- needs production testing to validate thread exhaustion threshold

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all core libraries already in requirements.txt, only adding python-magic and pillow-heif
- Architecture: HIGH -- blueprint/service patterns directly observed in existing codebase (T2 pattern)
- Pitfalls: HIGH -- CSP, CSRF, MAX_CONTENT_LENGTH, file ownership all verified against actual config files
- SSE deployment: MEDIUM -- sync worker approach viable for small team but needs monitoring

**Research date:** 2026-03-01
**Valid until:** 2026-03-31 (stable libraries, no fast-moving dependencies)
