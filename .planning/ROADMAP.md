# Roadmap: ZFA Finanzberatungs-Plattform

## Overview

Build a complete financial consulting module for the ZFA Business Hub. The journey starts with foundation infrastructure (config, models, Celery), then delivers the session-and-upload vertical slice so customers can submit documents via QR code. Next come consultant dashboards (Opener/Closer views), followed by the document processing pipeline (extraction, OCR, classification, embeddings). Once documents are processed, the scorecard and export phase delivers traffic-light analysis with PDF/Excel output. Admin oversight and DSGVO deletion come next, and finally the module integrates into the existing Hub with tool tiles and cross-links.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Config, database models, Celery setup, and dependencies
- [x] **Phase 2: Sessions + Upload** - Session CRUD, token-based upload, QR codes, mobile upload page, SSE notifications
- [x] **Phase 3: Berater Dashboards** - Opener and Closer dashboard views with document checklist and live feed
- [x] **Phase 4: Document Pipeline** - Extraction, OCR, chunking, embeddings, classification, and LLM integration
- [x] **Phase 5: Scorecard + Export** - Traffic-light scorecard generation, PDF and Excel export
- [x] **Phase 6: Admin + DSGVO** - Admin session management and DSGVO-compliant deletion workflow
- [x] **Phase 7: Hub Integration** - Tool tile, access control, and cross-tool links
- [ ] **Phase 8: Config Bridge + DSGVO Path Fix** - Fix config reading pattern and DSGVO file deletion path bug (Gap Closure)
- [ ] **Phase 9: Hub Integration Completion** - Role-based access control and cross-tool links (Gap Closure)

## Phase Details

### Phase 1: Foundation
**Goal**: The Finanzberatung module has its configuration, database schema, background task infrastructure, and all dependencies in place -- ready for feature development
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04
**Success Criteria** (what must be TRUE):
  1. Flask app loads with `finanzberatung` config section accessible (feature toggle, upload limits, token TTLs, LLM settings)
  2. All 6 database models (Session, Token, Document, ExtractedData, Scorecard, TaskTracking) exist and migrate cleanly
  3. Celery worker starts, connects to Redis, and can execute a test task
  4. All new dependencies install without conflicts in the existing virtualenv
**Plans**: 3

Plans:
- [x] 01-01: Config + Dependencies (FOUND-01, FOUND-04) [Wave 1]
- [x] 01-02: Database Models (FOUND-02) [Wave 1]
- [x] 01-03: Celery Setup (FOUND-03) [Wave 2, depends on 01-01]

### Phase 2: Sessions + Upload
**Goal**: Consultants can create financial consulting sessions and customers can upload documents via QR code on their phone -- the complete upload vertical from session creation through document receipt with real-time notification
**Depends on**: Phase 1
**Requirements**: SESS-01, SESS-02, SESS-03, SESS-04, SESS-05, UPLD-01, UPLD-02, UPLD-03, UPLD-04, UPLD-05, UPLD-06, UPLD-07, UPLD-08, DASH-05
**Success Criteria** (what must be TRUE):
  1. Opener can create a session with customer name, type, and date -- session appears in their list with correct status
  2. Opener can generate a QR code that encodes a time-limited upload URL; scanning it on a phone opens a mobile-optimized upload page
  3. Customer can upload PDF/image files on the mobile page (including camera capture) with progress feedback; invalid files are rejected with clear error
  4. Consultant sees real-time SSE notification in the browser when a customer uploads a document
  5. Session workflow progresses through statuses; opener notes transfer to closer view; followup tokens can be generated after T1
**Plans**: 5

Plans:
- [x] 02-01: Blueprint + Service Layer (SESS-05, UPLD-01, UPLD-02, UPLD-04, UPLD-05, UPLD-07) [Wave 1]
- [x] 02-02: Session Routes + Templates (SESS-01, SESS-02, SESS-03, SESS-04, UPLD-01, UPLD-02, UPLD-08) [Wave 2, depends on 02-01]
- [x] 02-03: Upload Routes + Mobile Page (UPLD-03, UPLD-04, UPLD-05, UPLD-07, DASH-05) [Wave 2, depends on 02-01]
- [x] 02-04: SSE Notifications (UPLD-06, SESS-02) [Wave 3, depends on 02-02, 02-03]
- [x] 02-05: Wire token deactivation (gap closure) [Wave 1]

### Phase 3: Berater Dashboards
**Goal**: Opener and Closer consultants have dedicated dashboard views to manage sessions, monitor uploads, and track document completeness
**Depends on**: Phase 2
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04
**Success Criteria** (what must be TRUE):
  1. Opener dashboard shows list of active sessions with inline QR-code generation and live upload feed
  2. Session detail page shows QR code, token countdown timer, SSE upload feed, document checklist, and notes editor
  3. Document checklist shows ampel status per document type (missing / uploaded / classified / verified)
  4. Closer dashboard extends opener view with analysis trigger button, scorecard display area, and export buttons
**Plans**: 1

Plans:
- [x] 03-01: Session detail with document checklist, manual contract creation, field verification, contract card component

### Phase 4: Document Pipeline
**Goal**: Uploaded documents are automatically processed -- text extracted, images OCR'd, content chunked and embedded, documents classified, and financial data extracted -- all running as background Celery tasks
**Depends on**: Phase 2, Phase 3
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06, PIPE-07, PIPE-08, PIPE-09, PIPE-10
**Success Criteria** (what must be TRUE):
  1. Uploading a PDF or image triggers automatic text extraction (pdfplumber + OCR fallback); extracted text is stored and viewable
  2. Documents are classified into financial types (Renteninfo, Depot, Versicherung, etc.) and the classification appears in the document checklist
  3. With FINANZ_LLM_ENABLED=false, the full pipeline works end-to-end using keyword-based mock classification -- no GPU required
  4. Structured financial data (values, costs, returns) is extracted from documents with confidence scores
  5. Vector similarity search finds related documents across sessions
**Plans**: 1

Plans:
- [x] 04-01: Extraction, classification, field extraction, embedding services + Celery task chains

### Phase 5: Scorecard + Export
**Goal**: Consultants get an automated traffic-light financial scorecard per session and can export analysis results as branded PDF or structured Excel
**Depends on**: Phase 4
**Requirements**: SCRD-01, SCRD-02, SCRD-03, EXPO-01, EXPO-02, EXPO-03
**Success Criteria** (what must be TRUE):
  1. After pipeline completes, a traffic-light scorecard is generated with categories (Altersvorsorge, Absicherung, Vermögen & Kosten, Steueroptimierung) each rated red/yellow/green
  2. Scorecard shows qualitative assessments per category and an overall aggregated score
  3. Consultant can export session analysis as branded PDF with cover page, overview, detail sections, potential, and next steps
  4. Consultant can export session data as Excel workbook with 6 sheets (overview, documents, costs, provision, optimization, raw data)
  5. Every export action is recorded in the audit log
**Plans**: 1

Plans:
- [x] 05-01: Scorecard service + Excel/PDF export services with audit logging

### Phase 6: Admin + DSGVO
**Goal**: Admins can oversee all financial consulting sessions and manage DSGVO-compliant document deletion with full audit trail
**Depends on**: Phase 5
**Requirements**: ADMN-01, ADMN-02, ADMN-03, ADMN-04
**Success Criteria** (what must be TRUE):
  1. Admin can view all sessions across all consultants with working filters for status, opener, and date range
  2. Admin can execute DSGVO deletion workflow: mark session as verified, 30-day countdown starts, batch delete runs after expiry
  3. After deletion, original files are gone but extracted values and embeddings are preserved for analytics
  4. Every deletion action (mark, execute, batch) is recorded in the audit trail
**Plans**: 1

Plans:
- [x] 06-01: Admin routes, DSGVO service, deletion workflow (implemented directly)

### Phase 7: Hub Integration
**Goal**: The Finanzberatung module is fully integrated into the ZFA Hub -- discoverable via tool tile, accessible with correct permissions, and cross-linked from related tools
**Depends on**: Phase 6
**Requirements**: HUBI-01, HUBI-02, HUBI-03
**Success Criteria** (what must be TRUE):
  1. "Finanzberatung" tool tile appears on the Hub dashboard with file-scan icon in primary gold color
  2. All openers and closers can access the Finanzberatung tool; other roles cannot
  3. Cross-tool links work: Slots page shows "Finanzberatung starten" link, T2 page shows "Zur Finanzberatung" link
**Plans**: 1

Plans:
- [x] 07-01: Tool tile, feature flag access control (implemented directly)

### Phase 8: Config Bridge + DSGVO Path Fix
**Goal**: All Finanzberatung services read configuration consistently from FinanzConfig/Config classes, and DSGVO file deletion correctly locates and removes physical files
**Depends on**: Phase 6
**Requirements**: ADMN-03
**Gap Closure**: Closes gaps from v1.0 audit — config bridge integration gap, DSGVO path bug, FINANZ_LLM_ENABLED config gap
**Success Criteria** (what must be TRUE):
  1. All services that need FINANZ_UPLOAD_DIR, FINANZ_LLM_ENABLED, or PERSIST_BASE read from finanz_config/Config directly — no current_app.config.get() for FinanzConfig values
  2. DSGVO execute_deletion() constructs the same file path as upload service store_file() — files are actually deleted from disk
  3. FINANZ_LLM_ENABLED env var is respected — setting it to true enables LLM classification/extraction mode
**Plans**: 1

Plans:
- [ ] 08-01: Fix config bridge pattern + DSGVO path alignment [Wave 1]

### Phase 9: Hub Integration Completion
**Goal**: Finanzberatung is accessible to all openers/closers via role-based access and discoverable from Slots and T2 pages via cross-tool links
**Depends on**: Phase 7
**Requirements**: HUBI-02, HUBI-03
**Gap Closure**: Closes gaps from v1.0 audit — access control scope, cross-tool links
**Success Criteria** (what must be TRUE):
  1. All users with opener or closer role can access the Finanzberatung tool tile; other roles cannot
  2. Slots page shows "Finanzberatung starten" link for eligible users
  3. T2 page shows "Zur Finanzberatung" link for eligible users
**Plans**: 1

Plans:
- [ ] 09-01: Role-based access + cross-tool links in Slots/T2 templates [Wave 1]

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-03-01 |
| 2. Sessions + Upload | 5/5 | Complete | 2026-03-01 |
| 3. Berater Dashboards | 1/1 | Complete | 2026-03-03 |
| 4. Document Pipeline | 1/1 | Complete | 2026-03-03 |
| 5. Scorecard + Export | 1/1 | Complete | 2026-03-03 |
| 6. Admin + DSGVO | 1/1 | Complete | 2026-03-03 |
| 7. Hub Integration | 1/1 | Complete | 2026-03-03 |
| 8. Config Bridge + DSGVO Fix | 0/1 | Not started | - |
| 9. Hub Integration Completion | 0/1 | Not started | - |
