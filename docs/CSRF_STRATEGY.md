# CSRF Strategy Documentation

**Last Updated:** 2025-12-08
**Version:** 1.0
**Status:** Post-Incident Documentation (2025-12-02 Rollback)

---

## 📋 Executive Summary

This document outlines the CSRF (Cross-Site Request Forgery) protection strategy for the Central Business Tool Hub. It was created following the critical incident on **2025-12-02** where improper CSRF handling caused a 1.5-hour booking system outage.

**Key Takeaway:** The system uses **selective CSRF protection** - certain JSON API endpoints are exempt while form-based endpoints remain protected.

---

## 🛡️ Current Implementation (Post-Incident)

### CSRF-Exempt Routes

The following routes are exempt from CSRF protection using `@csrf.exempt`:

| Route | Method | Reason |
|-------|--------|--------|
| `/slots/book` | POST | JSON API - Frontend sends no CSRF token |
| `/api/*` | ALL | All API endpoints - JSON-based |
| `/t2/api/*` | POST | T2 Booking APIs - JSON-based |

### Protected Routes

All other POST/PUT/DELETE routes require CSRF tokens:

| Route Pattern | Protection | Token Delivery |
|---------------|-----------|----------------|
| Form submissions | ✅ Protected | `<meta name="csrf-token">` |
| Login/Logout | ✅ Protected | Form hidden field |
| Admin actions | ✅ Protected | Form hidden field |

---

## 🔍 Why Routes Are Exempt

### JSON API Pattern

The booking system (`/slots/book`) and other API endpoints use a **JSON request pattern**:

```javascript
// Frontend Request Pattern (templates/slots/booking.html)
fetch('/slots/book', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(bookingData)
})
```

**Problem:** The frontend does NOT send an `X-CSRFToken` header.

**Solution:** Routes are marked `@csrf.exempt` and rely on **session-based authentication** instead.

### Session-Based Authentication

All exempt routes still require:
- Valid session cookie
- Authenticated user (`@require_login` decorator)
- Same-origin policy enforcement

---

## ⚠️ Incident Summary (2025-12-02)

### What Happened

**Commit:** `41c1c0e` (Phase 0 Security Features)

**Change:** Removed `@csrf.exempt` from `/slots/book` route

```python
# BEFORE (Working)
@booking_bp.route("/book", methods=["POST"])
@csrf.exempt  # CSRF exempt for booking endpoint
@require_login
def book():
    data = request.get_json()

# AFTER (Broken)
@booking_bp.route("/book", methods=["POST"])
@require_login  # Comment: "CSRF protection now enabled - frontend sends X-CSRFToken header"
def book():
    data = request.get_json()
```

**Assumption:** "Frontend sends X-CSRFToken header"

**Reality:** Frontend sends NO CSRF token → All bookings failed with 400 error

### Root Cause Chain

1. Phase 0 removed `@csrf.exempt` without frontend changes
2. Flask-WTF expected CSRF token in request
3. Frontend sent JSON without `X-CSRFToken` header
4. All booking requests rejected with "CSRF token is missing"
5. **Impact:** 1.5 hours of booking system downtime

### Resolution

**Action:** Complete rollback to commit `76b9eb0` (before Phase 0)

**Result:** System restored, `@csrf.exempt` remains in place

---

## 📐 Design Decisions

### Why Not Add CSRF Tokens to Frontend?

**Option A:** Keep `@csrf.exempt` (Current approach)
- ✅ Simple, works immediately
- ✅ Session-based auth still secure
- ✅ Less code to maintain
- ❌ Technically less protection against CSRF

**Option B:** Implement CSRF tokens in frontend
- ✅ Full CSRF protection
- ❌ Requires modifying all fetch calls
- ❌ Risk of breaking Content-Type headers
- ❌ More complexity

**Decision:** Option A - Keep `@csrf.exempt` for JSON APIs

**Rationale:**
1. Session cookies have `SameSite=Lax` (prevents most CSRF)
2. Login required on all exempt routes
3. JSON APIs less vulnerable to CSRF than form submissions
4. Proven stable in production for 3+ months

---

## 🧪 Testing Checklist

Before deploying ANY changes to CSRF handling:

### Pre-Deployment Tests

- [ ] **Test booking flow end-to-end**
  - [ ] Create booking (Success)
  - [ ] Verify Google Calendar updated
  - [ ] Check no console errors

- [ ] **Test Content-Type header**
  - [ ] Verify `Content-Type: application/json` preserved
  - [ ] Check `request.get_json()` works
  - [ ] No 415 errors

- [ ] **Test session authentication**
  - [ ] Authenticated user can book
  - [ ] Unauthenticated user redirected to login
  - [ ] Session expiry handled correctly

- [ ] **Test with fresh browser session**
  - [ ] Hard refresh (Ctrl+Shift+R)
  - [ ] Test in incognito mode
  - [ ] Verify no cached JavaScript issues

### Post-Deployment Verification

- [ ] Monitor error logs for 15 minutes
- [ ] Create test booking on production
- [ ] Verify health endpoint: `/health`
- [ ] Check Sentry for new errors

---

## 🔧 Implementation Guide

### For Exempt Routes (JSON APIs)

```python
from flask_wtf.csrf import CSRFProtect, csrf

# Initialize CSRF protection globally
csrf = CSRFProtect(app)

# Exempt specific route
@blueprint.route('/api/endpoint', methods=['POST'])
@csrf.exempt  # Important: Must come BEFORE @require_login
@require_login
def api_endpoint():
    data = request.get_json()
    # ... handle request
```

**Order matters:** `@csrf.exempt` must be applied BEFORE other decorators.

### For Protected Routes (Forms)

```html
<!-- Template with CSRF token -->
<form method="POST" action="/submit">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- Form fields -->
</form>
```

```python
# Route (no @csrf.exempt)
@blueprint.route('/submit', methods=['POST'])
@require_login
def submit_form():
    # CSRF protection automatic
    form_data = request.form
    # ... handle submission
```

---

## 🚫 Common Pitfalls

### Pitfall 1: Buggy CSRF Wrapper

**Problem:** JavaScript CSRF wrapper overwrites headers

```javascript
// BUGGY CODE (DO NOT USE)
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
window.fetch = function(resource, config) {
    if (config && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method)) {
        config.headers = config.headers || {};  // ❌ OVERWRITES Content-Type!
        config.headers['X-CSRFToken'] = csrfToken;
    }
    return originalFetch.apply(this, arguments);
};
```

**Impact:** `Content-Type: application/json` lost → 415 errors

**Solution:** Don't use global fetch wrapper for exempt routes

### Pitfall 2: Removing @csrf.exempt Without Testing

**Problem:** Assumption that frontend sends tokens

**Reality:** Check actual frontend code first!

**Solution:** Grep for `X-CSRFToken` in templates before removing `@csrf.exempt`

```bash
# Verify frontend sends CSRF token
grep -r "X-CSRFToken" templates/
```

### Pitfall 3: Browser Cache Issues

**Problem:** Old JavaScript cached, changes not visible

**Solution:**
- Test with hard refresh (Ctrl+Shift+R)
- Test in incognito mode
- Add cache-busting query params if needed

---

## 📊 Security Analysis

### Current Protections

| Attack Vector | Protection | Effectiveness |
|---------------|-----------|---------------|
| **CSRF (Form-based)** | CSRF tokens | ✅ High |
| **CSRF (JSON API)** | Session + SameSite cookies | ⚠️ Medium |
| **XSS** | Content-Security-Policy | ✅ High |
| **Session Hijacking** | Secure cookies + HTTPS | ✅ High |

### Risk Assessment

**JSON API CSRF Risk:** **LOW-MEDIUM**

**Mitigating Factors:**
1. `SameSite=Lax` cookies (prevents most CSRF)
2. Login required (`@require_login`)
3. JSON APIs less attractive to attackers
4. Same-origin policy enforced

**Residual Risk:**
- Subdomain attacks (if attacker controls subdomain)
- Compromised browser extensions

**Recommendation:** Current approach acceptable for internal business tool.

---

## 🔄 Future Improvements (Optional)

### Option 1: Add CSRF to JSON APIs

**Effort:** Medium (2-3 hours)

**Steps:**
1. Implement correct CSRF wrapper (preserve headers)
2. Update all fetch calls to include `X-CSRFToken`
3. Test thoroughly
4. Remove `@csrf.exempt` decorators

**Benefits:**
- Full CSRF protection
- Security best practice

**Drawbacks:**
- Risk of breaking existing functionality
- More code to maintain

### Option 2: Implement Double-Submit Cookie

**Effort:** Low (1 hour)

**Steps:**
1. Set `csrf_token` cookie on login
2. Frontend reads cookie and sends as header
3. Backend validates cookie matches header

**Benefits:**
- No template changes needed
- Works with JSON APIs

**Drawbacks:**
- Less secure than synchronized tokens

---

## 📝 Change Log

| Date | Change | Author | Reason |
|------|--------|--------|--------|
| 2025-12-02 | Rollback to 76b9eb0 | System | Phase 0 broke booking system |
| 2025-12-08 | Created documentation | Claude Code | Post-incident documentation |

---

## 📚 References

- **Flask-WTF CSRF Docs:** https://flask-wtf.readthedocs.io/en/stable/csrf.html
- **OWASP CSRF Guide:** https://owasp.org/www-community/attacks/csrf
- **SameSite Cookie Spec:** https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite
- **Post-Mortem:** `docs/POST_MORTEM_CSRF_BOOKING_2025-12-02.md`

---

## ✅ Summary

**Current Strategy:** Selective CSRF protection

- **Forms:** Protected with CSRF tokens
- **JSON APIs:** Exempt, rely on session auth
- **Risk:** Low-Medium, acceptable for internal tool
- **Testing:** Mandatory before any CSRF changes

**Lessons Learned:**
1. NEVER remove `@csrf.exempt` without testing
2. Always verify frontend actually sends tokens
3. Document why routes are exempt
4. Test thoroughly before production deploy

---

**Approved by:** Luke Hoppe
**Review Date:** 2025-12-08
**Next Review:** 2026-01-08 (or before major CSRF changes)
