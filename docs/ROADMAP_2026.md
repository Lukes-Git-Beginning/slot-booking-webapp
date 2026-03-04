# Roadmap 2026 — Business Tool Hub

**Version:** 1.0
**Letzte Aktualisierung:** 2026-03-04
**Kapazität:** 12–20h/Woche (Mini-Job, seit 01.03.2026)
**Planungshorizont:** Q1–Q4 2026
**Priorisierung:** Impact für Nutzer × Machbarkeit

---

## Aktueller Stand (März 2026)

- **Core Slots + T2** — produktiv seit November 2025
- **Gamification** — Badges, XP, Levels, Weekly Rankings, Cosmetics Shop
- **PostgreSQL Migration** — ~61% fertig, Dual-Write aktiv
- **CI/CD Pipeline** — GitHub Actions, CodeRabbit Review
- **CSP Nonce-Migration** — vollständig abgeschlossen
- **Test-Suite** — 561 Tests, ~98% Coverage auf kritischen Pfaden
- **Finanzberatung v1.0** — 9 Phasen, feature-complete
- **HubSpot G.1–G.3** — Deal-Suche, Outcome-Sync, Analytics

---

## Q1 2026 — Abschluss & Stabilisierung (März)

**Ziel:** Laufende Arbeiten abschließen, solide Basis für Q2

| # | Feature | Aufwand | Details |
|---|---------|---------|---------|
| 1.1 | Finanzberatung Go-Live | 8–12h | Alembic Migration, CSS Rebuild, Celery-Worker auf Server, Upload-Verzeichnis Permissions |
| 1.2 | HubSpot G.4 Webhook-Handler | 6–10h | Stage-Change Events empfangen, Deal-Status live synchronisieren |
| 1.3 | PostgreSQL Migration Phase 1 | 8–12h | Tracking-System (114KB, größte JSON-Abhängigkeit) auf PG-first umstellen |
| 1.4 | Code-Quality Quick Wins | 4–6h | tracking_system.py aufteilen, Magic Numbers in Config, CSRF-Header für /slots/book |

---

## Q2 2026 — Analytics & Dashboards (April–Juni)

**Ziel:** Management bekommt Echtzeit-Überblick, datengetriebene Entscheidungen

| # | Feature | Aufwand | Details |
|---|---------|---------|---------|
| 2.1 | Team-Leaderboard Live-Dashboard | 15–20h | Echtzeit-Scoreboard: Buchungen, Outcomes, Conversion-Rate pro Berater/Coach. Täglich/Wöchentlich/Monatlich filterbar. ApexCharts-Visualisierung. WebSocket oder Auto-Refresh. |
| 2.2 | Umsatz-Attribution Dashboard | 12–16h | HubSpot Deal-Werte aggregieren: Umsatz pro Berater, pro Coach, pro Zeitraum. Pipeline-Funnel Visualisierung (Lead → Termin → Stattgefunden → Abschluss). Drop-off Raten. |
| 2.3 | Zeitraum-Vergleiche | 8–10h | Diese Woche vs. letzte Woche, Monat vs. Vormonat. Trend-Pfeile, prozentuale Veränderung. Sparkline-Charts für schnelle Trend-Erkennung. |
| 2.4 | PostgreSQL Migration Phase 2 | 12–16h | Achievement-System, Weekly Points, Prestige auf PG-first. Ziel: 85%+ migriert. |
| 2.5 | Executive Auto-Reports | 8–12h | Wöchentlicher Performance-Report automatisch generiert (Celery Cron). PDF/Email an Management. Discord-Summary. |
| 2.6 | E2E Test Suite | 10–14h | Playwright oder Selenium Tests für kritische Flows: Login → Buchen → Gamification. CI/CD Integration. |

---

## Q3 2026 — AI & Predictive Analytics (Juli–September)

**Ziel:** Intelligente Vorhersagen und Automatisierung

| # | Feature | Aufwand | Details |
|---|---------|---------|---------|
| 3.1 | No-Show Prediction | 15–20h | ML-Modell basierend auf historischen Daten: Wochentag, Uhrzeit, Berater, Kunde, Buchungszeitpunkt. Wahrscheinlichkeit als Badge im Slot anzeigen. Optional: Extra-Erinnerung bei hohem Risiko. |
| 3.2 | Finanzberatung LLM aktivieren | 12–16h | Mock-Klassifizierung durch echte LLM ersetzen (Claude API oder lokales Modell). Dokumenten-Similarity-Search via ChromaDB. Automatische Vertragstyp-Erkennung. |
| 3.3 | Intelligente Berater-Zuweisung | 12–16h | AI-basiert: Berater-Matching anhand Performance-History, Spezialisierung, aktuelle Auslastung, Conversion-Rate. Vorschlag statt Zufallszuweisung. |
| 3.4 | Beste-Buchungszeit-Analyse | 6–8h | Statistische Analyse: Welche Uhrzeiten/Wochentage haben höchste Conversion. Heatmap-Visualisierung. Empfehlung für Berater. |
| 3.5 | PostgreSQL Migration abschließen | 10–14h | Verbleibende Services auf PG-first. JSON-Fallback als Read-Only Backup. Ziel: 100%. |

---

## Q4 2026 — Advanced Features & Polish (Oktober–Dezember)

**Ziel:** Plattform auf Enterprise-Niveau heben

| # | Feature | Aufwand | Details |
|---|---------|---------|---------|
| 4.1 | Conversion-Prognosen | 10–14h | Predictive Model: Abschluss-Wahrscheinlichkeit pro Deal basierend auf historischen Patterns. Dashboard-Integration. |
| 4.2 | Automatische Meeting-Notes | 10–14h | AI-generierte Zusammenfassungen nach Terminen (Input: Outcome-Tracking Daten). Automatisch in HubSpot Deal-Notes schreiben. |
| 4.3 | Advanced Gamification | 8–12h | Team-Challenges (Berater vs. Berater Wochen-Wettbewerbe). Saison-System (Quartals-Reset mit Rewards). Achievement-Animationen verbessern. |
| 4.4 | Admin Control Panel v2 | 10–14h | Zentrale System-Konfiguration über UI statt .env Dateien. Feature-Flag Management. User-Rollen visuell verwalten. |
| 4.5 | Monitoring & Alerting | 8–10h | Sentry-Dashboards ausbauen. Uptime-Monitoring. Performance-Budgets. Automatische Slack/Discord Alerts bei Fehlern. |
| 4.6 | Dokumentation & Onboarding | 6–8h | Interaktive Hilfe in der App. Tooltip-Tour für neue User. Video-Tutorials oder GIF-Guides. |

---

## Zukunftsvision 2027+ (Langfristig)

- **Kunden-Portal** — Kunden sehen eigene Termine, Dokumente, Status
- **WhatsApp Business API** — Direkte Termin-Bestätigung via WhatsApp (ergänzend zu HubSpot)
- **Multi-Standort** — Plattform für mehrere Büros/Filialen
- **API-First** — RESTful API für Drittanbieter-Integrationen
- **Mobile App** — PWA oder Native App (falls Bedarf entsteht)
- **Mandantenfähigkeit** — White-Label für andere Finanzberatungs-Unternehmen

---

## Priorisierungs-Matrix

| Feature | Business Impact | Technischer Aufwand | Priorität |
|---------|----------------|---------------------|-----------|
| Team-Leaderboard Live | Hoch (Management-Sichtbarkeit) | Mittel | **P1** |
| Umsatz-Attribution | Hoch (Geschäftsentscheidungen) | Mittel | **P1** |
| PostgreSQL 100% | Mittel (technische Schuld) | Mittel | **P1** |
| No-Show Prediction | Hoch (Umsatz-Rettung) | Hoch | **P2** |
| Finanz LLM aktivieren | Mittel (Feature-Vertiefung) | Mittel | **P2** |
| Intelligente Zuweisung | Mittel (Effizienz) | Hoch | **P2** |
| E2E Tests | Mittel (Stabilität) | Mittel | **P2** |
| Executive Auto-Reports | Mittel (Management) | Niedrig | **P2** |
| Conversion-Prognosen | Hoch (strategisch) | Hoch | **P3** |
| Admin Panel v2 | Niedrig (DX) | Mittel | **P3** |
