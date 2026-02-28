# ZFA Business Hub — Finanzberatungs-Plattform

## What This Is

Central Business Tool Hub for ZFA financial consultants. A Flask-based web platform that manages slot booking, T2 appointment tracking, gamification, and HubSpot CRM integration. The new Finanzberatung module adds document-based financial consulting: customers scan QR codes, upload financial documents via mobile, a local LLM analyzes them, and consultants receive a traffic-light scorecard as conversation basis.

## Core Value

Consultants can walk customers through a structured financial document analysis in T1/T2 appointments — from QR-code upload to automated scorecard — without manual document review.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. Inferred from existing codebase. -->

- ✓ Slot booking system with Google Calendar integration — v1.0
- ✓ T2 appointment management (Opener/Closer workflow) — v1.0
- ✓ Gamification (coins, badges, XP, leaderboard) — v1.0
- ✓ Admin dashboard with role-based access — v1.0
- ✓ HubSpot CRM integration (deal sync, ghost tracking) — v1.0
- ✓ 2FA authentication with TOTP — v1.0
- ✓ Audit logging for all admin actions — v1.0

### Active

<!-- Current scope: Finanzberatung v1.0 milestone -->

- [ ] Financial consulting sessions (create, manage, track status)
- [ ] Token-based document upload via QR code (no login needed)
- [ ] Document processing pipeline (extraction, OCR, classification)
- [ ] LLM-powered financial analysis with mock fallback
- [ ] Traffic-light scorecard generation per session
- [ ] Opener dashboard (QR, live upload feed, document checklist)
- [ ] Closer dashboard (analysis, scorecard, export)
- [ ] PDF and Excel export of analysis results
- [ ] Admin session management with DSGVO-compliant deletion workflow
- [ ] Hub integration (tool tile, cross-tool links)

### Out of Scope

<!-- Explicit boundaries -->

- Real-time chat with customers — Not needed; QR-upload flow is one-directional
- Customer portal/login — Customers only interact via token-based upload links
- Multi-language support — German only (ZFA is German market)
- Cloud LLM (OpenAI/Claude API) — Must be local/on-premise for DSGVO compliance
- Automated T1/T2 scripts — Content will be added later, infrastructure first

## Context

- **Existing prototype**: `C:\Users\Luke\Documents\Claude\KI Dokumentenanalyse` — FastAPI-based document pipeline with extraction, OCR, chunking, embeddings, ChromaDB. Services will be ported (async→sync, FastAPI→Flask).
- **T1/T2 scripts**: Not yet available. The platform builds infrastructure; consultant scripts/checklists come later.
- **Upload domain**: `upload.zfa.de` — separate Nginx server block proxying to the same Gunicorn.
- **LLM toggle**: `FINANZ_LLM_ENABLED=false` for development. Mock mode uses keyword-based classification. Live mode calls local vLLM via OpenAI-compatible HTTP API.
- **Redis**: Already available on server (used for rate limiting). Will also serve as Celery broker.

## Constraints

- **Stack**: Flask 3.1.1 + SQLAlchemy 2.0 + PostgreSQL — must integrate as Blueprint in existing app
- **Privacy**: DSGVO-compliant — local LLM only, 30-day document retention, 2-stage deletion
- **Server**: Single Hetzner VPS — Celery worker runs as separate systemd service
- **Prototype port**: 5 services from FastAPI prototype adapted to sync Flask pattern
- **No GPU initially**: CPU-only embeddings + mock LLM until VPS upgrade

## Current Milestone: v1.0 Finanzberatung

**Goal:** Build the complete financial consulting platform — from QR-code document upload through LLM analysis to exportable scorecard.

**Target features:**
- Session management (T1 Opener → T2 Closer workflow)
- Token-based mobile document upload with QR codes
- Automated document pipeline (extract → classify → embed)
- LLM financial analysis with traffic-light scorecard
- PDF/Excel export for consultants
- Admin oversight with DSGVO deletion workflow
- Hub integration (tool tile, cross-tool links)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Blueprint integration (not microservice) | Single VPS, shared auth, no extra deployment complexity | — Pending |
| Celery + Redis for background jobs | Redis already on server, Celery is industry standard for Python | — Pending |
| SSE for real-time upload feed | Simpler than WebSockets, no extra library, works through Nginx | — Pending |
| Token-based upload auth (no login) | Customers scan QR on phone — must work without account/session | — Pending |
| Local vLLM (not cloud API) | DSGVO requirement — customer financial docs never leave the server | — Pending |
| ChromaDB for vector search | Already proven in prototype, embeddable, no external service | — Pending |
| Mock LLM mode | Allows full development/testing without GPU server | — Pending |
| Port prototype services | 80% of extraction/embedding logic already works, proven in production | — Pending |

---
*Last updated: 2026-02-28 after milestone v1.0 initialization*
