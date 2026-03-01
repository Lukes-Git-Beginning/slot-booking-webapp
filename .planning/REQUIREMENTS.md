# Requirements: ZFA Finanzberatungs-Plattform

**Defined:** 2026-02-28
**Core Value:** Consultants can walk customers through structured financial document analysis -- from QR upload to automated scorecard.

## v1.0 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: System loads FinanzberatungConfig with feature toggle, upload limits, token TTLs, LLM settings
- [x] **FOUND-02**: Database schema supports sessions, tokens, documents, extracted data, scorecards, and task tracking (6 models)
- [x] **FOUND-03**: Celery worker processes background tasks via Redis broker
- [x] **FOUND-04**: Dependencies installed (celery, pytesseract, pdfplumber, sentence-transformers, chromadb, tiktoken)

### Sessions

- [ ] **SESS-01**: Opener can create a new financial consulting session with customer name, type, and appointment date
- [ ] **SESS-02**: Session status progresses through workflow (active -> in_analysis -> analyzed -> verified -> archived)
- [ ] **SESS-03**: Opener can save T1 notes that transfer to Closer in T2
- [ ] **SESS-04**: Closer can view T1 summary (opener, date, notes) and add T2 notes
- [x] **SESS-05**: Session tracks assigned opener and closer

### Upload

- [x] **UPLD-01**: System generates crypto-secure upload tokens with configurable TTL (T1=2h, Followup=14d, T2=2h)
- [x] **UPLD-02**: QR code is generated from upload token URL (format: `https://upload.zfa.de/finanzberatung/upload/{token}`)
- [ ] **UPLD-03**: Customer can upload documents via mobile-optimized standalone page (no login required)
- [x] **UPLD-04**: Upload validates file type via magic bytes (not just extension) -- PDF, JPG, PNG, TIFF, HEIC
- [x] **UPLD-05**: Uploaded files are stored with UUID filenames and SHA-256 hash for deduplication
- [ ] **UPLD-06**: Consultant receives real-time SSE notifications when customer uploads a document
- [x] **UPLD-07**: Token enforces max upload count (20) and expiry, shows clear error when invalid/expired
- [ ] **UPLD-08**: Opener can generate followup tokens for document resubmission after T1

### Pipeline

- [ ] **PIPE-01**: Text is extracted from PDFs (pdfplumber) with OCR fallback for scanned documents (pytesseract)
- [ ] **PIPE-02**: Images are preprocessed (grayscale, contrast, sharpen) before OCR for better accuracy
- [ ] **PIPE-03**: Extracted text is chunked (tiktoken, 4000 tokens, 200 overlap) preserving paragraph boundaries
- [ ] **PIPE-04**: Document chunks are embedded (sentence-transformers paraphrase-multilingual-MiniLM-L12-v2) and stored in ChromaDB
- [ ] **PIPE-05**: Documents are classified into financial types (Renteninfo, Depot, Versicherung, etc.) via LLM or mock
- [ ] **PIPE-06**: Mock mode (FINANZ_LLM_ENABLED=false) classifies via keyword matching -- no GPU required
- [ ] **PIPE-07**: Live mode calls local vLLM (OpenAI-compatible API) -- 8B for classification, 70B for extraction
- [ ] **PIPE-08**: Structured financial data is extracted from documents (values, costs, returns) with confidence scores
- [ ] **PIPE-09**: Similar documents can be found across sessions via vector similarity search
- [ ] **PIPE-10**: Full pipeline runs as Celery task chain (extract -> classify -> embed -> analyze -> scorecard)

### Scorecard

- [ ] **SCRD-01**: Traffic-light scorecard is generated per session with categories: Altersvorsorge, Absicherung, Vermögen & Kosten, Steueroptimierung
- [ ] **SCRD-02**: Each category gets red/yellow/green rating with qualitative assessment (no euro promises)
- [ ] **SCRD-03**: Overall score aggregates category ratings

### Dashboards

- [ ] **DASH-01**: Opener dashboard shows active sessions with QR-code generator and live upload feed
- [ ] **DASH-02**: Session detail page shows QR code, token countdown, upload feed (SSE), document checklist, notes
- [ ] **DASH-03**: Document checklist shows ampel status per type (missing/uploaded/classified/verified)
- [ ] **DASH-04**: Closer dashboard extends opener view with analysis trigger, scorecard display, and export buttons
- [ ] **DASH-05**: Mobile upload page is standalone (no base.html), touch-optimized (48px+ buttons), with camera capture and progress indicators

### Export

- [ ] **EXPO-01**: Consultant can export session analysis as branded PDF (cover, overview, detail, potential, next steps)
- [ ] **EXPO-02**: Consultant can export session data as Excel (6 sheets: overview, documents, costs, provision, optimization, raw data)
- [ ] **EXPO-03**: Every export is audit-logged

### Admin

- [ ] **ADMN-01**: Admin can view all sessions with filters (status, opener, date)
- [ ] **ADMN-02**: Admin can manage DSGVO deletion workflow (mark verified -> 30-day timer -> batch delete)
- [ ] **ADMN-03**: Original files are deleted after retention period; extracted values and embeddings are preserved
- [ ] **ADMN-04**: Audit trail records every deletion action

### Hub Integration

- [ ] **HUBI-01**: Tool tile "Finanzberatung" appears on hub dashboard (lucide: file-scan, primary gold)
- [ ] **HUBI-02**: Access control: all openers and closers can access the tool
- [ ] **HUBI-03**: Cross-tool links: Slots -> "Finanzberatung starten", T2 -> "Zur Finanzberatung"

## v2 Requirements

Deferred to future release.

### Automation

- **AUTO-01**: Celery-beat runs daily batch deletion of expired documents
- **AUTO-02**: Automatic session archival after 90 days inactivity

### Content

- **CONT-01**: T1/T2 consultant scripts integrated into session workflow
- **CONT-02**: Guided wizard for customer document submission

### Advanced Analysis

- **ADVN-01**: Cross-session comparison for returning customers
- **ADVN-02**: Trend analysis across consultant portfolio

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time chat with customers | Upload flow is one-directional; chat adds complexity without value |
| Customer portal/login | Customers only interact via token-based upload links |
| Multi-language | German market only |
| Cloud LLM APIs | DSGVO -- customer financial documents must stay on-premise |
| Mobile native app | Web-based upload page is sufficient; camera capture works via HTML5 |
| Automated investment recommendations | Legal compliance risk; scorecard is qualitative only |
| Payment/billing integration | Out of scope for consulting tool |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1: Foundation | Complete |
| FOUND-02 | Phase 1: Foundation | Complete |
| FOUND-03 | Phase 1: Foundation | Complete |
| FOUND-04 | Phase 1: Foundation | Complete |
| SESS-01 | Phase 2: Sessions + Upload | Pending |
| SESS-02 | Phase 2: Sessions + Upload | Pending |
| SESS-03 | Phase 2: Sessions + Upload | Pending |
| SESS-04 | Phase 2: Sessions + Upload | Pending |
| SESS-05 | Phase 2: Sessions + Upload | Complete |
| UPLD-01 | Phase 2: Sessions + Upload | Complete |
| UPLD-02 | Phase 2: Sessions + Upload | Complete |
| UPLD-03 | Phase 2: Sessions + Upload | Pending |
| UPLD-04 | Phase 2: Sessions + Upload | Complete |
| UPLD-05 | Phase 2: Sessions + Upload | Complete |
| UPLD-06 | Phase 2: Sessions + Upload | Pending |
| UPLD-07 | Phase 2: Sessions + Upload | Complete |
| UPLD-08 | Phase 2: Sessions + Upload | Pending |
| DASH-05 | Phase 2: Sessions + Upload | Pending |
| DASH-01 | Phase 3: Berater Dashboards | Pending |
| DASH-02 | Phase 3: Berater Dashboards | Pending |
| DASH-03 | Phase 3: Berater Dashboards | Pending |
| DASH-04 | Phase 3: Berater Dashboards | Pending |
| PIPE-01 | Phase 4: Document Pipeline | Pending |
| PIPE-02 | Phase 4: Document Pipeline | Pending |
| PIPE-03 | Phase 4: Document Pipeline | Pending |
| PIPE-04 | Phase 4: Document Pipeline | Pending |
| PIPE-05 | Phase 4: Document Pipeline | Pending |
| PIPE-06 | Phase 4: Document Pipeline | Pending |
| PIPE-07 | Phase 4: Document Pipeline | Pending |
| PIPE-08 | Phase 4: Document Pipeline | Pending |
| PIPE-09 | Phase 4: Document Pipeline | Pending |
| PIPE-10 | Phase 4: Document Pipeline | Pending |
| SCRD-01 | Phase 5: Scorecard + Export | Pending |
| SCRD-02 | Phase 5: Scorecard + Export | Pending |
| SCRD-03 | Phase 5: Scorecard + Export | Pending |
| EXPO-01 | Phase 5: Scorecard + Export | Pending |
| EXPO-02 | Phase 5: Scorecard + Export | Pending |
| EXPO-03 | Phase 5: Scorecard + Export | Pending |
| ADMN-01 | Phase 6: Admin + DSGVO | Pending |
| ADMN-02 | Phase 6: Admin + DSGVO | Pending |
| ADMN-03 | Phase 6: Admin + DSGVO | Pending |
| ADMN-04 | Phase 6: Admin + DSGVO | Pending |
| HUBI-01 | Phase 7: Hub Integration | Pending |
| HUBI-02 | Phase 7: Hub Integration | Pending |
| HUBI-03 | Phase 7: Hub Integration | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after roadmap creation*
