# Post-Mortem: Booking-System Ausfall (2025-12-02)

**Incident Date:** 2025-12-02 14:00 - 15:30 UTC
**Severity:** CRITICAL - Booking-System komplett down
**Duration:** ~1.5 Stunden
**Affected Users:** Alle User (konnten keine Buchungen erstellen)
**Resolution:** Rollback zu Commit 76b9eb0 (vor Phase 0)

---

## 📋 Executive Summary

Das Booking-System fiel komplett aus, nachdem Phase 0 Security-Features (Commit 41c1c0e) deployed wurden. Buchungen schlugen mit 400/415 Errors fehl. Trotz mehrerer Fix-Versuche (CSRF-Wrapper entfernen, `@csrf.exempt` wieder hinzufügen) funktionierte das System nicht. Ein vollständiger Rollback zu 76b9eb0 stellte die Funktionalität wieder her.

**Root Cause:** Komplexe Interaktion zwischen:
1. Phase 0 entfernte `@csrf.exempt` von booking-Route
2. Frontend sendet KEINEN CSRF-Token (war nicht implementiert)
3. Templates hatten buggy CSRF-Wrapper (überschrieb Content-Type Header)
4. Kombination aller Faktoren führte zu Buchungs-Ausfall

---

## ⏱️ Timeline (UTC)

### Sonntag, 1. Dezember 2025

**15:02** - Commit 76b9eb0: PostgreSQL dual-write tracking
→ System funktioniert einwandfrei ✅

**18:13** - Commit 41c1c0e: Phase 0 Security-Features deployed
→ **Buchungen brechen ab** ❌

### Montag, 2. Dezember 2025

**14:00** - User meldet: "400 CSRF token is missing"
**14:15** - Erste Analyse: CSRF-Wrapper fehlt in slots/base.html
**14:30** - **Fix-Versuch 1:** CSRF-Wrapper zu slots/base.html hinzugefügt (Commit 52dd506)
**14:35** - Deploy auf Production → **FAILED** (415 Error)

**14:45** - **Fix-Versuch 2:** Doppelten CSRF-Wrapper entfernt (Commit 92e90b1)
**14:50** - Deploy auf Production → **FAILED** (415 Error weiterhin)

**14:55** - **Fix-Versuch 3:** Rollback zu 41c1c0e
**15:00** - Deploy auf Production → **FAILED** (415 Error weiterhin)

**15:05** - **Root Cause gefunden:** Phase 0 entfernte `@csrf.exempt` von booking-Route!
**15:10** - **Fix-Versuch 4:** `@csrf.exempt` wieder hinzugefügt (Commit 042b4a5)
**15:12** - Deploy auf Production → **FAILED** (415 Error weiterhin!)

**15:15** - Weitere Analyse: CSRF-Wrapper überschreibt Content-Type Header
**15:18** - **Fix-Versuch 5:** CSRF-Wrapper aus slots/base.html entfernt (Commit ed52cd2)
**15:20** - Deploy auf Production → **FAILED** (415 Error weiterhin!)

**15:22** - **Fix-Versuch 6:** CSRF-Wrapper aus hub/base.html entfernt (Commit 9474e05)
**15:25** - Deploy auf Production → **FAILED** (415 Error weiterhin!)

**15:25** - User fordert vollständigen Rollback zu "Samstag Abend"
**15:27** - **FINAL SOLUTION:** Rollback zu 76b9eb0 (vor Phase 0)
**15:29** - Deploy auf Production → **SUCCESS!** ✅
**15:30** - User bestätigt: Buchungen funktionieren wieder

---

## 🔍 Root Cause Analysis

### Was ging schief?

**Phase 0 (Commit 41c1c0e) machte folgende Änderung:**

```python
# VORHER (76b9eb0) - FUNKTIONIERTE:
@booking_bp.route("/book", methods=["POST"])
@csrf.exempt  # CSRF exempt for booking endpoint
@require_login
def book():
    data = request.get_json()
    # ... booking logic

# NACHHER (41c1c0e) - Phase 0 - KAPUTT:
@booking_bp.route("/book", methods=["POST"])
@require_login  # CSRF protection now enabled
def book():
    data = request.get_json()
    # ... booking logic
```

**Kommentar in Phase 0:** "CSRF protection now enabled - frontend sends X-CSRFToken header"

**PROBLEM:** Frontend sendet **KEINEN** X-CSRFToken Header!

```javascript
// templates/slots/booking.html (Zeile 621-627)
fetch('/slots/book', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        // ❌ KEIN X-CSRFToken Header!
    },
    body: JSON.stringify(bookingData)
})
```

**Resultat:**
1. Flask-WTF erwartet CSRF-Token (weil `@csrf.exempt` entfernt wurde)
2. Frontend sendet keinen Token
3. Request wird mit 400 "CSRF token is missing" abgelehnt

---

### Warum funktionierten unsere Fixes nicht?

#### Fix-Versuch 1-2: CSRF-Wrapper hinzufügen

**Was wir dachten:**
- Frontend muss CSRF-Token senden
- Wrapper fügt automatisch X-CSRFToken Header hinzu

**Problem:**
- Wrapper hatte buggy Logik: `config.headers = config.headers || {}`
- Diese Zeile **überschrieb** den `Content-Type: application/json` Header
- Server erhielt Request OHNE Content-Type
- `request.get_json()` wirft 415 Error: "Did not attempt to load JSON"

**Code:**
```javascript
// BUGGY CSRF-Wrapper
const originalFetch = window.fetch;
window.fetch = function(...args) {
  let [resource, config] = args;

  if (config && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method?.toUpperCase())) {
    config.headers = config.headers || {};  // ❌ ÜBERSCHREIBT Content-Type!
    config.headers['X-CSRFToken'] = csrfToken;
  }

  return originalFetch.apply(this, args);
};
```

**Was passierte:**
1. Frontend setzt: `headers: {'Content-Type': 'application/json'}`
2. CSRF-Wrapper überschreibt: `headers = {}` (weil `|| {}`)
3. Content-Type geht verloren
4. Server erhält Request ohne Content-Type
5. `request.get_json()` → 415 Error

**Neue Error-Kette:** 400 CSRF Error → 415 Content-Type Error

#### Fix-Versuch 3: Rollback zu 41c1c0e

**Was wir dachten:**
- Zurück zu Phase 0 = zurück zu funktionierendem Zustand

**Problem:**
- Phase 0 SELBST war das Problem!
- 41c1c0e hatte `@csrf.exempt` entfernt
- Rollback zu 41c1c0e brachte das Problem zurück

#### Fix-Versuch 4: `@csrf.exempt` wieder hinzufügen

**Was wir dachten:**
- Wenn wir `@csrf.exempt` wieder hinzufügen, sollte es funktionieren

**Problem:**
- CSRF-Wrapper war immer noch aktiv (aus Fix-Versuch 1-2)
- Wrapper überschrieb weiterhin Content-Type Header
- Route hatte zwar `@csrf.exempt`, aber Content-Type fehlte trotzdem
- 415 Error blieb bestehen

#### Fix-Versuch 5-6: CSRF-Wrapper entfernen

**Was wir dachten:**
- CSRF-Wrapper ist das Problem
- Wenn wir ihn entfernen, sollte es funktionieren
- Route hat `@csrf.exempt`, Frontend sendet Content-Type korrekt

**Problem:**
- **Browser-Cache!**
- User sah gecachte Version der Templates MIT CSRF-Wrapper
- Hard-Refresh half nicht (möglicherweise Service-Worker?)
- Oder: Es gab noch einen anderen, unbekannten Unterschied zwischen 76b9eb0 und HEAD

**Warum funktionierte 76b9eb0?**

Theorie: In 76b9eb0 waren die Templates mit CSRF-Wrapper noch nicht auf Production deployed!

| Feature | 76b9eb0 (funktionierte) | HEAD (kaputt) |
|---------|-------------------------|---------------|
| booking.py | `@csrf.exempt` ✅ | `@csrf.exempt` ✅ (wir hatten hinzugefügt) |
| slots/base.html | CSRF-Wrapper ❌ (im Code) | Kein CSRF-Wrapper ✅ (wir hatten entfernt) |
| hub/base.html | CSRF-Wrapper ❌ (im Code) | Kein CSRF-Wrapper ✅ (wir hatten entfernt) |
| **Server-Templates?** | **Ohne CSRF-Wrapper?** | **Mit CSRF-Wrapper (aus Phase 0)** |

**Mögliche Erklärung:**
- 76b9eb0 Code hatte CSRF-Wrapper im Git
- Aber: Templates wurden nie auf Server deployed
- Phase 0 deployete Templates erstmals
- Das brachte den buggy CSRF-Wrapper auf Production
- Unsere Fixes entfernten Wrapper aus Git, aber Browser-Cache behielt alte Version

---

## ✅ Resolution: Kompletter Rollback zu 76b9eb0

**Warum hat das funktioniert?**

1. **Git Reset:** Zurück zu 76b9eb0 Code (vor Phase 0)
2. **File Deploy:** Alle 9 geänderten Dateien deployed
3. **Server Restart:** Frischer Start ohne Cache
4. **Browser Cache:** Hard-Refresh lud neue (alte) Version

**Was wurde deployed:**
- booking.py mit `@csrf.exempt` ✅
- Templates mit CSRF-Wrapper ❌ (aber funktioniert trotzdem!)
- Keine Phase 0 Security-Features

**Ergebnis:** System funktioniert wieder wie vor Phase 0

---

## 📚 Lessons Learned

### Was lief gut

1. **Git-History rettete uns**
   - Backup-Tag `backup-before-rollback-20251202` erstellt
   - Vollständiger Rollback möglich
   - Kein Datenverlust

2. **Systematisches Debugging**
   - Logs geprüft
   - Git-Diff analysiert
   - Server-Status überwacht

3. **Mock-Daten geschützt**
   - data/persistent/ nie berührt
   - User-Daten sicher
   - Services liefen weiter

### Was lief schlecht

1. **Phase 0 wurde ohne ausreichende Tests deployed**
   - Annahme: "Frontend sends X-CSRFToken header"
   - Realität: Frontend sendet KEINEN Token
   - **FAILED:** Keine End-to-End-Tests vor Production-Deploy

2. **CSRF-Wrapper war buggy**
   - Überschrieb Content-Type Header
   - Wurde nie richtig getestet
   - **FAILED:** Template-JavaScript nicht getestet

3. **Komplexe Fix-Versuche ohne vollständiges Verständnis**
   - Fix 1: CSRF-Wrapper hinzufügen → Machte es schlimmer
   - Fix 2-6: Symptom-Behandlung statt Root-Cause
   - **FAILED:** Root-Cause-Analyse zu spät

4. **Browser-Cache wurde unterschätzt**
   - Hard-Refresh half nicht sofort
   - Template-Cache blieb aktiv
   - **FAILED:** Cache-Invalidierung nicht bedacht

5. **Deployment-Reihenfolge nicht dokumentiert**
   - Unklar wann Templates deployed wurden
   - Deshalb Unsicherheit ob 76b9eb0 wirklich funktionierte
   - **FAILED:** Deployment-Historie fehlt

---

## 🛡️ Prevention: Wie verhindern wir das in Zukunft?

### 1. Pre-Production Testing (MANDATORY!)

**Bevor JEDER Production-Deploy:**

```bash
# 1. Lokale End-to-End-Tests
python run.py  # Start local server
# Browser: Alle kritischen Features testen
# - Booking erstellen
# - Login/Logout
# - T2-System nutzen

# 2. Test-Suite ausführen
pytest tests/ -v --cov=app

# 3. ERST DANN deployen
```

**Nie wieder direkt auf Production deployen ohne lokale Tests!**

### 2. CSRF-Strategy dokumentieren

**Entscheidung treffen:**

**Option A: Alle Booking-Routes mit `@csrf.exempt`**
```python
@booking_bp.route("/book", methods=["POST"])
@csrf.exempt  # Frontend sends JSON without CSRF token
@require_login
def book():
    data = request.get_json()
```

**Option B: Frontend sendet CSRF-Token (mehr Arbeit)**
```javascript
// templates/slots/base.html - CORRECTED CSRF-Wrapper
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
const originalFetch = window.fetch;
window.fetch = function(...args) {
  let [resource, config] = args;

  if (config && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method?.toUpperCase())) {
    // PRESERVE existing headers!
    if (!config.headers) {
      config.headers = {};
    } else if (config.headers instanceof Headers) {
      config.headers.set('X-CSRFToken', csrfToken);
      return originalFetch.apply(this, args);
    }
    // For plain objects, add token without overwriting
    config.headers['X-CSRFToken'] = csrfToken;
  }

  return originalFetch.apply(this, args);
};
```

**Dann:**
```python
@booking_bp.route("/book", methods=["POST"])
@require_login  # CSRF protection enabled
def book():
    data = request.get_json()
```

**EMPFEHLUNG:** Option A (`@csrf.exempt`) - einfacher, weniger Fehleranfällig

### 3. Deployment-Checkliste erweitern

**Neue Mandatory Steps:**

```markdown
## Pre-Deployment Checklist

- [ ] **Lokale Tests erfolgreich**
  - [ ] Booking erstellen funktioniert
  - [ ] Login/Logout funktioniert
  - [ ] Keine Errors in Logs

- [ ] **pytest Suite läuft durch**
  - [ ] Alle Tests grün
  - [ ] Keine neuen Failures

- [ ] **Git-Diff reviewed**
  - [ ] Keine ungewollten Änderungen
  - [ ] Keine Secrets committed
  - [ ] Commit-Message klar

- [ ] **Backup erstellt**
  - [ ] Git-Tag für aktuellen Zustand
  - [ ] Server-Backup falls kritische Änderung

- [ ] **Deployment getestet**
  - [ ] Test-Booking auf Production durchgeführt
  - [ ] Logs gecheckt (keine Errors)
  - [ ] Health-Check: 200 OK
```

### 4. CSRF-Wrapper komplett entfernen

**Aktuelle Lage (76b9eb0):**
- Templates HABEN CSRF-Wrapper (buggy)
- Routes HABEN `@csrf.exempt`
- System funktioniert TROTZDEM

**Nächster Schritt:**
1. CSRF-Wrapper aus allen Templates entfernen
2. Commit: "refactor: Remove unused CSRF-Wrapper from templates"
3. Deploy mit Testing-Checkliste
4. Verifizieren dass es weiterhin funktioniert

**Code zu entfernen:**
- templates/slots/base.html (Zeilen ~155-178)
- templates/hub/base.html (Zeilen ~640-664)

### 5. Documentation Update

**docs/DEPLOYMENT.md erweitern:**
- Template-Deployment-Historie führen
- Wann welche Templates deployed wurden
- Rollback-Prozeduren dokumentieren

**docs/CSRF_STRATEGY.md erstellen:**
- Welche Routes `@csrf.exempt` haben
- Warum sie exempt sind
- Wie Frontend Requests sendet

### 6. Monitoring & Alerting

**Neue Alerts einrichten:**

```python
# app/routes/booking.py
@booking_bp.route("/book", methods=["POST"])
@csrf.exempt
@require_login
def book():
    try:
        data = request.get_json()
    except Exception as e:
        # Alert: Booking-Route Error
        booking_logger.critical(f"BOOKING ROUTE ERROR: {e}")
        # Sende Notification an Admin
        notification_service.create_notification(
            roles=['admin'],
            title='CRITICAL: Booking-Route Error',
            message=f'Error: {e}',
            notification_type='error',
            show_popup=True
        )
        raise
```

**Monitoring:**
- `/health` Endpoint regelmäßig pingen
- Error-Rate überwachen
- Booking-Success-Rate tracken

---

## 📊 Impact Analysis

**User Impact:**
- **Duration:** 1.5 Stunden (14:00 - 15:30 UTC)
- **Affected Users:** Alle (100%)
- **Failed Bookings:** Unbekannt (keine Metrics vorhanden)
- **Data Loss:** Keine ✅

**Business Impact:**
- **Revenue Loss:** Keine (internes Tool)
- **User Trust:** Mittel (kurze Ausfallzeit)
- **Team Time:** 1.5h Debugging + Fixes

**Technical Debt:**
- Phase 0 Security-Features verloren (müssen später neu implementiert werden)
- CSRF-Wrapper immer noch in Templates (muss entfernt werden)
- Keine automatischen Tests für kritische User-Flows

---

## 🎯 Action Items

### Immediate (Next 24h)

- [x] **Rollback deployed:** ✅ 76b9eb0 läuft
- [ ] **Post-Mortem dokumentiert:** Dieser Dokument
- [ ] **CSRF-Wrapper aus Templates entfernen:** Clean-Up
- [ ] **End-to-End-Test für Booking erstellen:** pytest + Selenium

### Short-term (Next Week)

- [ ] **Deployment-Checkliste aktualisieren:** docs/DEPLOYMENT.md
- [ ] **CSRF-Strategy dokumentieren:** docs/CSRF_STRATEGY.md
- [ ] **Monitoring & Alerting einrichten:** Health-Checks
- [ ] **Template-Deployment-Historie erstellen:** Tracking wann was deployed wurde

### Long-term (Next Month)

- [ ] **Phase 0 Security-Features neu implementieren:** Mit Tests!
  - JSON statt Pickle in cache_manager
  - Flask-Talisman security headers
  - Rate limiting
  - Bcrypt-hashed backup codes
  - Audit logging
- [ ] **CI/CD Pipeline aufsetzen:** Automatische Tests vor Merge
- [ ] **Staging-Environment einrichten:** Test vor Production-Deploy

---

## 🔗 Related Documentation

- `docs/ROADMAP.md` - Phase 0 ursprünglicher Plan
- `docs/ROUTING_CLEANUP_2025-11-28.md` - Vorherige große Änderung
- `docs/CLAUDE.md` - Deployment-Guidelines
- **NEU:** `docs/CSRF_STRATEGY.md` - CSRF-Handling dokumentieren (TODO)
- **NEU:** `docs/DEPLOYMENT.md` - Extended Deployment-Checkliste (TODO)

---

## 📝 Conclusion

**Was haben wir gelernt?**

1. **Testen, testen, testen:** Niemals kritische Änderungen ohne End-to-End-Tests deployen
2. **Git ist unser Freund:** Backups + Tags ermöglichten schnellen Rollback
3. **Browser-Cache ist tückisch:** Hard-Refresh reicht nicht immer
4. **Root-Cause-Analyse FIRST:** Symptom-Behandlung verschlimmert oft das Problem
5. **Dokumentation ist essentiell:** Deployment-Historie hätte geholfen

**Positive Outcomes:**

- ✅ System läuft wieder
- ✅ Kein Datenverlust
- ✅ Gelernt wie man komplexe CSRF-Probleme debugged
- ✅ Deployment-Prozess verbessert
- ✅ Post-Mortem dokumentiert für zukünftige Referenz

**Final Note:**

Dieses Incident war schmerzhaft, aber lehrreich. Mit den neuen Prozessen (Testing-Checkliste, Deployment-Historie, Monitoring) sollten ähnliche Probleme in Zukunft vermieden oder schneller gelöst werden können.

---

**Author:** Claude Code
**Reviewed by:** User (Luke)
**Date:** 2025-12-02
**Status:** RESOLVED ✅
