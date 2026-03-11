# ROADMAP — Central Business Tool Hub

**Version:** 3.3.19 | **Stand:** 11.03.2026 | **Production:** https://berater.zfa.gmbh/

---

## Projektstatus

Das System ist **produktionsreif und stabil**. Flask 3.1.1 + PostgreSQL + Redis + Tailwind/DaisyUI.
CI/CD via GitHub Actions mit automatischem Deploy, CodeRabbit Review und Discord-Notifications.
728 Tests, ~98% Coverage auf kritischen Pfaden.

---

## Abgeschlossene Meilensteine

| Block | Thema | Fertig seit |
|-------|-------|-------------|
| **A** | PostgreSQL + Redis Migration (25 Models, 24 Tables, Dual-Write) | Nov 2025 |
| **B+C** | T2 Blueprint (Calendly Booking, Bucket-System, Analytics) | Nov 2025 |
| **D** | Code Cleanup (Template-Migration auf Tailwind/DaisyUI, Routing-Cleanup, Legacy entfernt) | Feb 2026 |
| **E** | CI/CD Pipeline (GitHub Actions CI + Deploy, CodeRabbit AI Review, Discord Webhooks) | Feb 2026 |
| **F.3** | Test Coverage — 561 Tests, 0 Failures | Feb 2026 |
| **F.4** | Parsing-Bug behoben | Feb 2026 |
| **F.5** | Score-Recovery + Startup-Validierung + Datei-Ownership-Prävention | Feb 2026 |
| **F.1** | CSP Nonce-Migration (Tailwind pre-compiled, Nonce-basierte CSP, onclick→data-action) | Feb 2026 |
| **G.1-G.3** | HubSpot Deal-Suche, Outcome-Sync, Analytics | Mär 2026 |
| **H** | Finanzberatung v1.0 (9 Phasen, feature-complete) | Mär 2026 |
| **I** | Code-Quality / Tech Debt Tier 1-3: MVP-Badge Fix, Cosmetics Dual-Write, Level PG-Sync, tracking_system.py→11-Modul Package, T2-Legacy Cleanup, 728 Tests | Mär 2026 |

---

## Offene Aufgaben

### G — HubSpot Integration

**Status:** Offen (10 Stub-Methoden in `app/services/hubspot_service.py`)

| Phase | Methoden | Beschreibung |
|-------|----------|--------------|
| 1 | `search_deals_by_email/phone/datetime` | CRM-Suche |
| 2 | `update_deal_stage`, `add_note_to_deal`, `get_stage_history` | Deal-Management |
| 3 | `get_pipeline_stats`, `get_deals_by_stage_count`, `get_avg_deal_value`, `get_lead_source_attribution` | Pipeline-Analytics |
| 4 | Webhook-Handler (`hubspot_webhook.py:106`) | Lokale DB-Updates bei Stage-Änderungen |

3 deferred PostgreSQL-Migrationen hängen von HubSpot ab.

---

### T2 Modular Admin — offene Stubs (501)

4 Routen in `app/routes/t2/admin.py` ohne Legacy-Pendant (Nice-to-Have, kein Business-Blocker):

| Route | Beschreibung |
|-------|--------------|
| `weekly_report()` | Wöchentlicher T2-Report |
| `generate_pdf()` | PDF-Export |
| `update_calendar()` | Kalender-Config schreibend |
| `notification_test()` | Test-Notification versenden |

---

## Code-Qualität

Aus dem System-Audit (`docs/SYSTEM_AUDIT_2026-02.md`):

| ID | Thema | Status |
|----|-------|--------|
| Q1 | `tracking_system.py` aufteilen (2.477 Zeilen) | **Erledigt (Mär 2026)** — 11-Modul Package mit Fassaden-Pattern |
| Q5 | Magic Numbers in `config/constants.py` zentralisieren | Offen |
| Q3 | Booking-Handler weiter in Service extrahieren (teilweise erledigt) | Offen |
| S5 | CSRF-Token-Header für `/slots/book` Endpoint | Offen |

Vollständige Liste (Q1-Q8, S5-S6) siehe System-Audit.

---

### H — Finanzberatung

**Status:** Phase 1-5 erledigt, Phase 6+7 offen | **Go-Live:** frühestens KW 12 (Mitte März 2026)

| Phase | Beschreibung | Status |
|-------|-------------|--------|
| 1 | Foundation (Config, Models, Celery) | Erledigt |
| 2 | Sessions + Upload (QR, Mobile, SSE) | Erledigt |
| 3 | Berater Dashboards (Opener/Closer, Checklist, Verifikation) | Erledigt |
| 4 | Document Pipeline (Extraction, OCR, Classification, Embedding) | Erledigt |
| 5 | Scorecard + Export (Ampel, PDF, Excel) | Erledigt |
| 6 | Admin + DSGVO (Session-Übersicht, Löschworkflow) | **Offen** |
| 7 | Hub Integration (Tool-Tile, Rollen, Cross-Links) | **Offen** |

Noch offen vor Go-Live: Alembic-Migration, CSS-Rebuild, Tests, Server-Setup (Celery Worker, Redis, Upload-Dir).

Detaillierte Planung: `.planning/ROADMAP.md`

---

## Priorisierung

**Nächste sinnvolle Schritte (nach Impact sortiert):**

1. **H — Finanzberatung Phase 6+7** — Feature-Completion für Go-Live
2. **G — HubSpot Phase 1** (Search-APIs) — direkter Business-Value
3. **Q1/Q5** — Refactoring bei Gelegenheit
