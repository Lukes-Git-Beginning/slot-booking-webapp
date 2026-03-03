# Phase 8: Config Bridge + DSGVO Path Fix - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix inconsistent config access patterns across all Finanzberatung services and fix the DSGVO file deletion path bug so files are actually deleted from disk. Three specific gaps from v1.0 audit: config bridge integration, DSGVO path mismatch, FINANZ_LLM_ENABLED config gap.

</domain>

<decisions>
## Implementation Decisions

### Config Access Pattern
- Standardize ALL finanz services on direct class imports (`from app.config.base import Config, FinanzConfig as finanz_config`)
- No more `current_app.config.get('FINANZ_*')` — use `finanz_config.FINANZ_LLM_ENABLED` etc. directly
- Non-finanz values like PERSIST_BASE also via `Config.PERSIST_BASE` (no mixing of access patterns within a service)
- Only fix the 5 services that currently read FINANZ_* values — no proactive imports elsewhere
- No fallback needed in Flask Config class — if all services use direct imports, Flask config doesn't need FINANZ_* values
- Affected services: finanz_classification_service, finanz_field_extraction_service, finanz_extraction_service, finanz_embedding_service, finanz_dsgvo_service

### Path Construction
- Extract shared path helpers as classmethods on FinanzConfig:
  - `get_upload_dir(session_id)` — returns session upload directory path
  - `get_file_path(session_id, filename)` — returns full file path
- Both use `Config.PERSIST_BASE` + `FINANZ_UPLOAD_DIR` + `session_id` internally
- All 3 consumers (upload service, DSGVO service, extraction service) use these helpers
- Single source of truth — future path changes need 1 fix, not 3
- Fix the DSGVO bug: remove incorrect `/persistent/` segment and add missing `session_id`

### LLM Toggle
- Import-time resolution (env var read once at import via `get_env_bool`) — consistent with all other config
- Server restart picks up env var changes — no runtime property needed
- Silent fallback: if FINANZ_LLM_ENABLED=true but vLLM unreachable, fall back to keyword mock + log warning
- Add startup log line in init_app(): "Finanzberatung LLM mode: mock/live" for admin verification

### Claude's Discretion
- Exact classmethod signatures and return types for path helpers
- Whether to add a `get_chromadb_path()` helper alongside upload paths
- Test structure for verifying path alignment
- Order of service refactoring (which service to fix first)

</decisions>

<specifics>
## Specific Ideas

- Current path mismatch: `store_file()` builds `{PERSIST_BASE}/finanz_uploads/{session_id}` but `execute_deletion()` builds `{PERSIST_BASE}/persistent/finanz_uploads` (wrong segment + missing session_id)
- Upload service already uses the correct pattern (direct imports) — use it as reference for other 4 services

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/config/base.py`: FinanzConfig class already has all FINANZ_* values defined — just needs path helper classmethods added
- `app/services/finanz_upload_service.py`: Already uses direct imports (`Config.PERSIST_BASE`, `finanz_config.FINANZ_UPLOAD_DIR`) — reference implementation

### Established Patterns
- Config: Direct class import pattern (`from app.config.base import Config`) used by upload service
- Flask config: `current_app.config.get()` used by 4 other services (to be replaced)
- Feature toggle: `get_env_bool()` helper for boolean env vars

### Integration Points
- `app/config/base.py` (FinanzConfig class) — add path helper classmethods here
- 5 service files — replace `current_app.config.get()` with direct imports
- `app/__init__.py` or blueprint init — add LLM mode startup log line

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-config-dsgvo-fix*
*Context gathered: 2026-03-03*
