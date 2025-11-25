# Security Policy - Business Tool Hub

## Version
**v3.3.7** - Last Updated: 2025-11-14

## 🔒 Security Enhancements Implemented

This document summarizes all security measures implemented in the Business Tool Hub (Slot-Booking, T2-Closer, Analytics).

---

## ✅ IMPLEMENTED SECURITY CONTROLS

### 1. CSRF Protection (CRITICAL) ✅
- **Implementation:** Flask-WTF mit automatischer CSRF-Token-Injection
- **Coverage:** Alle POST/PUT/PATCH/DELETE-Requests
- **Files:**
  - `app/core/extensions.py` - CSRFProtect initialization
  - `templates/hub/base.html` - Meta-Tag + JavaScript Auto-Injection
  - `templates/slots/base.html` - Meta-Tag + JavaScript Auto-Injection
  - `templates/t2/base.html` - Meta-Tag + JavaScript Auto-Injection
  - `templates/login.html` - CSRF-Token in Login-Form
- **Impact:** Prevents Cross-Site Request Forgery attacks

### 2. Bcrypt Password Hashing (CRITICAL) ✅
- **Implementation:** Hybrid System (bcrypt + legacy plaintext fallback)
- **Hash Rounds:** 12 (secure default)
- **Files:**
  - `app/services/security_service.py` - Bcrypt hashing & verification
  - `scripts/migrate_passwords_to_bcrypt.py` - Migration script for 17 users
- **Next Steps:** Run migration on server to hash all USERLIST passwords
- **Impact:** Protects passwords even if `.env` is compromised

### 3. Session Fixation Prevention (HIGH) ✅
- **Implementation:** Session regeneration after successful login
- **Files:** `app/routes/auth.py:87-89`
- **Code:**
  ```python
  session.clear()  # Destroy old session ID
  session.permanent = True  # Use 8-hour lifetime
  session.update({"logged_in": True, "user": username})
  ```
- **Impact:** Prevents session hijacking attacks

### 4. Content Security Policy (HIGH) ✅
- **Implementation:** CSP headers in Flask `after_request` hook
- **Files:** `app/__init__.py:373-387`
- **Directives:**
  - `script-src 'self' 'unsafe-inline' 'unsafe-eval'` - Required for Tailwind/Alpine
  - `style-src 'self' 'unsafe-inline'` - Inline styles
  - `img-src 'self' data: https:` - Base64 + external images
  - `connect-src 'self'` - AJAX to same origin only
  - `frame-ancestors 'none'` - Clickjacking protection
  - `form-action 'self'` - Forms submit to same origin only
- **TODO:** Refactor to nonce-based CSP for stricter security
- **Impact:** Mitigates XSS attacks

### 5. Account Lockout System (MEDIUM) ✅
- **Implementation:** 3-Tier progressive lockout
- **Files:**
  - `app/services/account_lockout.py` - Lockout logic
  - `app/routes/auth.py:74-79, 119-125` - Integration
- **Policy:**
  - Tier 1: 5 failed attempts → 15 minutes lockout
  - Tier 2: 10 failed attempts → 1 hour lockout
  - Tier 3: 15 failed attempts → 24 hours lockout
- **Data:** `data/persistent/account_lockouts.json`
- **Impact:** Prevents brute force attacks

### 6. Path Traversal Protection (MEDIUM) ✅
- **Implementation:** `os.path.basename()` sanitization
- **Files:** `app/services/data_persistence.py:515, 543`
- **Code:**
  ```python
  filename = os.path.basename(filename)  # Strips '../' attacks
  ```
- **Impact:** Prevents directory traversal attacks on JSON file operations

### 7. HSTS Header (MEDIUM) ✅ PREPARED
- **Implementation:** Nginx header (commented, ready for HTTPS)
- **Files:** `deployment/nginx-business-hub-enhanced.conf:36-38`
- **Configuration:**
  ```nginx
  # Uncomment after HTTPS/SSL is configured:
  # add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
  ```
- **TODO:** Enable after SSL/TLS certificate is installed (Let's Encrypt)
- **Impact:** Forces HTTPS connections, prevents downgrade attacks

---

## 🛡️ EXISTING SECURITY CONTROLS

### 8. Two-Factor Authentication (2FA) ✅
- **Implementation:** TOTP-based 2FA with QR codes
- **Files:** `app/services/security_service.py:124-200`
- **Features:**
  - Google Authenticator compatible
  - 10 backup codes per user
  - Encrypted storage in `data/persistent/user_2fa.json`
- **Coverage:** Optional per-user, recommended for admins

### 9. Rate Limiting (Nginx + Flask) ✅
- **Implementation:** Zweischichtiges Rate Limiting
- **Nginx Layer:** `deployment/nginx-business-hub-enhanced.conf`
  - Login: 5/minute (Brute Force Protection)
  - Booking: 10/minute (DoS Protection)
  - API: 60/minute
  - Global: 100/minute
- **Flask Layer:** `app/utils/rate_limiting.py`
  - Flask-Limiter with in-memory storage
  - Granular limits per endpoint
- **TODO:** Consider Redis-backend for multi-worker deployments

### 10. Audit Logging ✅
- **Implementation:** Comprehensive security event logging
- **Files:** `app/services/audit_service.py`
- **Logged Events:**
  - Login success/failure (with IP & User-Agent)
  - Password changes
  - 2FA activation/deactivation
  - Admin actions
- **Retention:** 10,000 events with auto-rotation
- **Storage:** `data/persistent/audit_log.json`
- **Privacy:** Consider IP anonymization for GDPR compliance

### 11. Security Headers ✅
- **Implementation:** Nginx + Flask after_request
- **Headers:**
  - `X-Frame-Options: DENY` - Clickjacking protection
  - `X-Content-Type-Options: nosniff` - MIME-sniffing protection
  - `X-XSS-Protection: 1; mode=block` - Legacy XSS protection
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy: ...` - See #4
- **Files:** `deployment/nginx-business-hub-enhanced.conf:29-38`, `app/__init__.py:365-389`

### 12. Input Validation ✅
- **Implementation:** Strikte Validierung auf mehreren Ebenen
- **Examples:**
  - `app/routes/booking.py:123-150` - Name/description length limits
  - `app/routes/auth.py:69-72` - Username/password length limits
  - Datetime format validation with `strptime()`
  - Whitelist-based time slot validation
- **Pattern:** Validate early, reject invalid input before processing

---

## 🚨 KNOWN LIMITATIONS & ROADMAP

### Password Policy (TODO - MEDIUM Priority)
- **Current:** Minimum 6 characters, no complexity requirements
- **Recommendation:** Increase to 10-12 characters with complexity
- **File:** `app/services/security_service.py:105-106`
- **Suggested Implementation:**
  ```python
  import re

  def validate_password_strength(password):
      if len(password) < 10:
          return False, "Password must be at least 10 characters"
      if not re.search(r'[A-Z]', password):
          return False, "Password must contain uppercase letter"
      if not re.search(r'[a-z]', password):
          return False, "Password must contain lowercase letter"
      if not re.search(r'[0-9]', password):
          return False, "Password must contain digit"
      if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
          return False, "Password must contain special character"
      return True, "Password is strong"
  ```

### Session Rotation after Privilege Change (TODO - LOW Priority)
- **Issue:** Session is not invalidated after password change or 2FA activation
- **Risk:** Low (attacker needs existing session)
- **Recommendation:** Add `session.clear()` after security changes
- **Files:** `app/services/security_service.py:122`, `app/routes/security.py`

### Dependency Security Scanning (TODO - HIGH Priority)
- **Issue:** No automated CVE scanning for Python packages
- **Recommendation:** Add GitHub Actions workflow
- **Implementation:**
  ```yaml
  # .github/workflows/security.yml
  name: Security Scan
  on: [push, pull_request]
  jobs:
    security:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v3
        - name: Safety check
          run: |
            pip install safety
            safety check --json
  ```

### Nonce-based CSP (TODO - MEDIUM Priority)
- **Issue:** CSP currently allows `unsafe-inline` for scripts
- **Risk:** Reduces XSS protection effectiveness
- **Recommendation:** Implement nonce-based CSP
- **Effort:** High (requires refactoring all inline scripts in templates)

---

## 📊 SECURITY TESTING CHECKLIST

### Pre-Deployment Tests
- [ ] Test CSRF protection on all POST endpoints
- [ ] Verify bcrypt password migration (dry-run first)
- [ ] Test account lockout thresholds (5/10/15 attempts)
- [ ] Verify session fixation fix (inspect session cookie after login)
- [ ] Test path traversal protection (try `../etc/passwd` as filename)
- [ ] Check CSP headers with browser dev tools
- [ ] Verify rate limiting triggers (use curl loop)

### Post-Deployment Tests
- [ ] Monitor audit logs for anomalies
- [ ] Test 2FA with Google Authenticator
- [ ] Verify backup codes work
- [ ] Check failed login lockout in production
- [ ] Test password change flow
- [ ] Verify session timeout (8 hours)

---

## 🔐 DEPLOYMENT SECURITY CHECKLIST

### Server Configuration
- [ ] `.env` file has `chmod 600` (only owner can read)
- [ ] SECRET_KEY is cryptographically random (32+ bytes)
- [ ] `FLASK_DEBUG=False` in production
- [ ] Firewall: Only ports 80/443 open
- [ ] SSH: Only key-based authentication (disable password auth)
- [ ] Fail2ban configured for SSH brute force protection

### Application Security
- [ ] All dependencies up-to-date (`pip list --outdated`)
- [ ] Sentry DSN configured for error tracking
- [ ] Nginx rate limiting active
- [ ] Backup cronjob running (`deployment/vps_backup.sh`)
- [ ] Log rotation configured (systemd timer)
- [ ] Audit log retention policy enforced

### Data Protection
- [ ] Backups stored securely (off-server)
- [ ] JSON files have correct permissions (660)
- [ ] Service Account credentials not exposed
- [ ] GDPR compliance: User consent for data processing
- [ ] Data retention policy documented

---

## 📝 INCIDENT RESPONSE PROCEDURE

### If Security Breach Detected:
1. **Isolate:** Shut down affected service immediately
   ```bash
   systemctl stop business-hub
   ```

2. **Assess:** Check audit logs for compromise timeline
   ```bash
   cat /opt/business-hub/data/persistent/audit_log.json | jq '.[-100:]'
   ```

3. **Contain:** Rotate all secrets immediately
   - Regenerate SECRET_KEY
   - Force password reset for all users
   - Revoke all active sessions

4. **Recover:** Restore from last known-good backup
   ```bash
   rsync -av /opt/business-hub-backups/YYYY-MM-DD/ /opt/business-hub/data/
   ```

5. **Report:** Document incident, notify affected users

### Emergency Contacts
- **System Admin:** Luke (luke.hoppe@...)
- **Security Lead:** TBD
- **Hosting:** Hetzner Support

---

## 🔧 MAINTENANCE & UPDATES

### Weekly
- [ ] Check for security advisories (GitHub Dependabot)
- [ ] Review audit logs for suspicious activity
- [ ] Verify backup integrity

### Monthly
- [ ] Update dependencies (`pip install -U -r requirements.txt`)
- [ ] Review locked accounts (admin dashboard)
- [ ] Security scan with `safety check`

### Quarterly
- [ ] Penetration testing (internal or external)
- [ ] Security training for team
- [ ] Review and update this document

---

## 📚 REFERENCES

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [bcrypt Documentation](https://pypi.org/project/bcrypt/)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)

---

**Last Review:** 2025-11-14
**Next Review Due:** 2026-02-14
**Document Owner:** Luke Hoppe
