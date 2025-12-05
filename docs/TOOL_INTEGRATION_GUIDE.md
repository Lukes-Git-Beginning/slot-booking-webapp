# Tool Integration Guide - Central Business Tool Hub

**Version:** 1.0
**Letzte Aktualisierung:** 2025-12-05
**Für:** Neue Developer die Tools in den Hub integrieren wollen

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Erforderliche Dateien](#erforderliche-dateien)
3. [Integration Steps (1-7)](#integration-steps)
4. [Code-Beispiele](#code-beispiele)
5. [Best Practices & Patterns](#best-practices--patterns)
6. [Checkliste](#checkliste)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

---

## Übersicht

Der **Central Business Tool Hub** ist eine Multi-Tool-Plattform mit Flask-Backend, Tailwind CSS + DaisyUI Frontend, und PostgreSQL-Datenbank (optional).

### Bestehende Tools

| Tool | Routes | Service | Status | Beschreibung |
|------|--------|---------|--------|--------------|
| **Slot-Booking** | `app/routes/main.py` (multi-blueprint) | `app/services/booking_service.py` | ✅ Active | Terminbuchungs-System mit Gamification |
| **T2-Closer** | `app/routes/t2.py` (1,947 Zeilen) | `app/services/t2_*.py` | ✅ Active | T2-Termin-Management mit Würfelsystem |
| **Analytics** | `app/routes/analytics.py` (150 Zeilen) | `app/services/analytics_service.py` | ✅ Active | Business Intelligence Dashboard |

### Architektur-Patterns

```
app/
├── routes/              # HTTP-Handler (Blueprints)
│   ├── hub.py           # Central Navigation
│   ├── t2.py            # T2-Tool (Komplex-Beispiel)
│   └── [dein_tool].py   ← HIER anfangen
├── services/            # Business-Logic
│   └── [dein_tool]_service.py  ← Business-Layer
├── models/              # SQLAlchemy Models (optional)
│   └── [dein_tool].py
└── core/                # Shared Infrastructure
    ├── extensions.py
    ├── google_calendar.py
    └── cache_manager.py

templates/
└── [dein_tool]/         # HTML-Templates
    ├── base.html
    └── dashboard.html
```

---

## Erforderliche Dateien

### Minimum (3 Dateien für Basic Tool)

1. **`app/routes/[tool].py`** - Blueprint mit HTTP-Routes
2. **`app/services/[tool]_service.py`** - Business-Logic
3. **`templates/[tool]/dashboard.html`** - UI Template

### Optional (für komplexere Tools)

4. **`app/models/[tool].py`** - SQLAlchemy Models (wenn PostgreSQL genutzt wird)
5. **`app/utils/[tool]_helpers.py`** - Tool-spezifische Utilities
6. **`static/[tool]/`** - Tool-spezifische CSS/JS Assets
7. **`tests/test_[tool]_*.py`** - Unit/Integration Tests

**Gesamt:** 3-8 Dateien je nach Komplexität

---

## Integration Steps

### Step 1: Blueprint erstellen

**File:** `app/routes/[tool].py`

```python
# -*- coding: utf-8 -*-
"""
[Tool Name] Blueprint
[Kurze Beschreibung was das Tool macht]
"""

from flask import Blueprint, render_template, session, jsonify, request, redirect, url_for, flash
from app.utils.decorators import require_login
from app.utils.helpers import is_admin

# Blueprint mit url_prefix erstellen
mytool_bp = Blueprint('mytool', __name__, url_prefix='/mytool')

# Optional: Permission-Check für alle Routes
@mytool_bp.before_request
def require_access():
    """Check if user has access to this tool"""
    user = session.get('user')
    if not user:
        from flask import abort
        abort(401)

    # Optional: Weitere Permission-Checks
    # if not is_admin(user):
    #     abort(403)

# Haupt-Dashboard Route
@mytool_bp.route("/")
@require_login
def dashboard():
    """Main dashboard view for the tool"""
    user = session.get('user')

    # Load data from service
    from app.services.mytool_service import mytool_service
    dashboard_data = mytool_service.get_dashboard_data(user)

    return render_template('mytool/dashboard.html',
                           user=user,
                           **dashboard_data)

# API Endpoint (für AJAX calls)
@mytool_bp.route("/api/fetch-data", methods=['GET'])
@require_login
def api_fetch_data():
    """API endpoint for AJAX calls"""
    user = session.get('user')

    try:
        from app.services.mytool_service import mytool_service
        data = mytool_service.get_data(user)

        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        from app.utils.logging import logger
        logger.error(f"API error in mytool: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# POST Route (z.B. für Form-Submissions)
@mytool_bp.route("/action", methods=['POST'])
@require_login
def action():
    """Handle user action"""
    user = session.get('user')

    # Get form data
    data = request.get_json() or request.form

    # Validate input
    if not data.get('required_field'):
        flash('Pflichtfeld fehlt', 'danger')
        return redirect(url_for('mytool.dashboard'))

    # Process via service
    from app.services.mytool_service import mytool_service
    success = mytool_service.process_action(user, data)

    if success:
        flash('Aktion erfolgreich!', 'success')
    else:
        flash('Fehler bei der Verarbeitung', 'danger')

    return redirect(url_for('mytool.dashboard'))
```

**Key Patterns:**
- Blueprint-Name = URL-Prefix (meist)
- `@require_login` für alle authenticated Routes
- Service-Layer für Business-Logic (nicht in Route!)
- `flash()` für User-Feedback
- `redirect()` nach POST-Requests

---

### Step 2: Blueprint registrieren

**File:** `app/__init__.py` (Funktion `register_blueprints`, ca. Zeile 220-265)

**Hinzufügen:**

```python
# MyTool Blueprint
try:
    from app.routes.mytool import mytool_bp
    app.register_blueprint(mytool_bp, url_prefix='/mytool')
    app.logger.info("MyTool blueprint registered")
except ImportError as e:
    app.logger.warning(f"MyTool blueprint error: {e}")
```

**Position:** Nach ähnlichen Tool-Blueprints (z.B. nach Analytics ~Zeile 262)

**Pattern:** Immer `try/except` für graceful degradation!

---

### Step 3: Navigation hinzufügen

**File:** `app/__init__.py` (Funktion `get_available_tools`, Zeile 443-520)

**Hinzufügen zur `tools` Liste:**

```python
{
    'id': 'mytool',
    'name': 'My Tool Name',
    'description': 'Brief description of what tool does',
    'icon': '🎯',  # Emoji-Fallback (wird nicht in Logs angezeigt!)
    'lucide_icon': 'target',  # Lucide icon name (bevorzugt)
    'url': '/mytool/',
    'status': 'active',  # oder 'coming_soon'
    'users': get_tool_user_count('mytool'),
    'color': '#d4af6a'  # ZFA Gold (oder #207487 Blau, #294c5d Dunkelblau)
},
```

**Lucide Icons:** https://lucide.dev/icons/
**ZFA Color Scheme:**
- `#d4af6a` - Gold (Primary)
- `#207487` - Blau (Secondary)
- `#294c5d` - Dunkelblau (Accent)

---

### Step 4: Service Layer erstellen

**File:** `app/services/mytool_service.py`

```python
# -*- coding: utf-8 -*-
"""
MyTool Service - Business logic for MyTool
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.core.extensions import data_persistence, cache_manager

logger = logging.getLogger(__name__)

class MyToolService:
    """Business logic for MyTool"""

    def __init__(self):
        """Initialize service with dependencies"""
        self.data_persistence = data_persistence
        self.cache_manager = cache_manager
        self.cache_ttl = 600  # 10 minutes

    def get_dashboard_data(self, user: str) -> Dict:
        """
        Load dashboard data for user

        Args:
            user: Username

        Returns:
            Dict with dashboard metrics
        """
        # Check cache first
        cache_key = f"mytool_dashboard_{user}"
        cached = self.cache_manager.get("mytool", cache_key)

        if cached:
            logger.debug(f"Cache hit for {cache_key}")
            return cached

        # Load from persistent storage
        data = self.data_persistence.load_data('mytool_data', {})
        user_data = data.get(user, {})

        # Compute metrics
        metrics = {
            'total_items': len(user_data),
            'active_items': sum(1 for item in user_data.values() if item.get('active')),
            'last_activity': user_data.get('last_activity', 'Nie'),
        }

        # Cache for 10 minutes
        self.cache_manager.set("mytool", cache_key, metrics, ttl=self.cache_ttl)

        return metrics

    def get_data(self, user: str) -> List[Dict]:
        """Get all data for user"""
        data = self.data_persistence.load_data('mytool_data', {})
        return list(data.get(user, {}).values())

    def process_action(self, user: str, action_data: Dict) -> bool:
        """
        Process user action

        Args:
            user: Username
            action_data: Action parameters

        Returns:
            bool: Success status
        """
        try:
            # Load current data
            data = self.data_persistence.load_data('mytool_data', {})

            if user not in data:
                data[user] = {}

            # Process action
            item_id = action_data.get('item_id', str(datetime.now().timestamp()))
            data[user][item_id] = {
                'id': item_id,
                'name': action_data.get('name'),
                'created_at': datetime.now().isoformat(),
                'active': True
            }

            # Save
            self.data_persistence.save_data('mytool_data', data)

            # Invalidate cache
            self.cache_manager.invalidate("mytool", f"mytool_dashboard_{user}")

            logger.info(f"Action processed for user {user}: {item_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing action for {user}: {e}")
            return False

# Singleton instance
mytool_service = MyToolService()
```

**Service Pattern:**
- Klasse mit `__init__` für Dependencies
- `data_persistence` für File-Storage
- `cache_manager` für Caching (10-60 min TTL)
- Try-Except um alle File-Operationen
- Logging für Errors
- Singleton-Instance am Ende

---

### Step 5: Templates erstellen

**Directory:** `templates/mytool/`

#### **Base Template:** `templates/mytool/base.html`

```html
{% extends "hub/base.html" %}

{% block title %}MyTool - Beraterwelt{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-4xl font-bold text-primary mb-6">My Tool</h1>

    <!-- Content Block for Child Templates -->
    {% block mytool_content %}{% endblock %}
</div>
{% endblock %}
```

#### **Dashboard Template:** `templates/mytool/dashboard.html`

```html
{% extends "mytool/base.html" %}

{% block mytool_content %}
<!-- Stats Grid -->
<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
    <!-- Stat Card 1 -->
    <div class="card bg-base-200 shadow-xl">
        <div class="card-body">
            <h2 class="card-title text-primary">
                <i data-lucide="list" class="w-6 h-6"></i>
                Total Items
            </h2>
            <p class="text-3xl font-bold">{{ total_items }}</p>
        </div>
    </div>

    <!-- Stat Card 2 -->
    <div class="card bg-base-200 shadow-xl">
        <div class="card-body">
            <h2 class="card-title text-secondary">
                <i data-lucide="check-circle" class="w-6 h-6"></i>
                Active
            </h2>
            <p class="text-3xl font-bold">{{ active_items }}</p>
        </div>
    </div>

    <!-- Stat Card 3 -->
    <div class="card bg-base-200 shadow-xl">
        <div class="card-body">
            <h2 class="card-title text-accent">
                <i data-lucide="clock" class="w-6 h-6"></i>
                Last Activity
            </h2>
            <p class="text-xl font-semibold">{{ last_activity }}</p>
        </div>
    </div>
</div>

<!-- Main Content Area -->
<div class="card bg-base-200 shadow-xl">
    <div class="card-body">
        <h2 class="card-title text-2xl mb-4">Dashboard</h2>

        <!-- Action Buttons -->
        <div class="flex gap-4 mb-6">
            <button class="btn btn-primary" onclick="addItem()">
                <i data-lucide="plus" class="w-5 h-5 mr-2"></i>
                Add New Item
            </button>
            <button class="btn btn-secondary" onclick="refreshData()">
                <i data-lucide="refresh-cw" class="w-5 h-5 mr-2"></i>
                Refresh
            </button>
        </div>

        <!-- Content goes here -->
        <div id="content-area">
            <p class="text-gray-500">Your content here...</p>
        </div>
    </div>
</div>

<!-- JavaScript for AJAX calls -->
<script>
    // Initialize Lucide icons
    lucide.createIcons();

    async function refreshData() {
        try {
            const response = await fetch('/mytool/api/fetch-data');
            const result = await response.json();

            if (result.success) {
                console.log('Data refreshed:', result.data);
                // Update UI with result.data
            } else {
                console.error('Error:', result.error);
            }
        } catch (error) {
            console.error('Network error:', error);
        }
    }

    async function addItem() {
        // Show modal or form
        alert('Add Item functionality - implement as needed');
    }
</script>
{% endblock %}
```

**Template Pattern:**
- Extend `hub/base.html` (hat bereits Tailwind + DaisyUI)
- DaisyUI Components: `card`, `btn`, `badge`, `modal`
- Tailwind Classes: `grid`, `flex`, `gap-6`, `text-primary`
- Lucide Icons: `<i data-lucide="icon-name"></i>` + `lucide.createIcons()`
- Responsive: `md:grid-cols-3`, `lg:flex-row`

---

### Step 6: Access Control (Optional)

**File:** `app/__init__.py` (Funktion `user_has_tool_access`, Zeile 536-555)

**Hinzufügen:**

```python
def user_has_tool_access(username: str, tool_id: str) -> bool:
    """Check if user has access to tool"""
    admin_users = get_admin_users()

    # Admins have access to all tools
    if username in admin_users:
        return True

    # Add tool-specific access rules
    if tool_id == 'mytool':
        # Option 1: Everyone has access
        return True

        # Option 2: Only certain roles
        # from app.config.base import Config
        # return username in Config.get_mytool_users()

        # Option 3: Admin only
        # return False

    # ... rest of function
```

---

### Step 7: Deployment

#### Lokal testen

```bash
# 1. Server starten
python run.py

# 2. Browser öffnen
# http://localhost:5000/mytool/

# 3. Funktionalität testen
```

#### Deployment auf Hetzner VPS

```bash
# 1. Backup erstellen (IMMER!)
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && tar -czf /tmp/backup_$(date +%Y%m%d_%H%M).tar.gz data/persistent/"

# 2. Dateien deployen
scp -i ~/.ssh/server_key app/routes/mytool.py root@91.98.192.233:/opt/business-hub/app/routes/
scp -i ~/.ssh/server_key app/services/mytool_service.py root@91.98.192.233:/opt/business-hub/app/services/
scp -i ~/.ssh/server_key -r templates/mytool/ root@91.98.192.233:/opt/business-hub/templates/

# 3. __init__.py deployen (Blueprint-Registrierung)
scp -i ~/.ssh/server_key app/__init__.py root@91.98.192.233:/opt/business-hub/app/

# 4. Service neu starten
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"

# 5. Logs prüfen
ssh -i ~/.ssh/server_key root@91.98.192.233 "journalctl -u business-hub -n 50 --no-pager"

# 6. Health-Check
curl -I https://berater.zfa.gmbh/health
# Sollte: 200 OK

# 7. Browser-Test
# https://berater.zfa.gmbh/mytool/
```

#### Git Commit (nur nach erfolgreichen Server-Tests!)

```bash
git add app/routes/mytool.py app/services/mytool_service.py templates/mytool/
git commit -m "feat: Add MyTool integration"
git push origin main
```

---

## Code-Beispiele

### Vollständiges Beispiel: "LeadTracker" Tool

#### **File 1:** `app/routes/leadtracker.py`

```python
# -*- coding: utf-8 -*-
"""LeadTracker Routes - CRM Lead Management"""

from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for, flash
from app.utils.decorators import require_login
from app.services.leadtracker_service import leadtracker_service

leadtracker_bp = Blueprint('leadtracker', __name__, url_prefix='/leadtracker')

@leadtracker_bp.route("/")
@require_login
def dashboard():
    """Main dashboard"""
    user = session.get('user')
    dashboard_data = leadtracker_service.get_dashboard_data(user)
    return render_template('leadtracker/dashboard.html', user=user, **dashboard_data)

@leadtracker_bp.route("/leads")
@require_login
def leads_view():
    """All leads view"""
    user = session.get('user')
    leads = leadtracker_service.get_user_leads(user)
    return render_template('leadtracker/leads.html', user=user, leads=leads)

@leadtracker_bp.route("/api/add-lead", methods=['POST'])
@require_login
def api_add_lead():
    """Add new lead via API"""
    user = session.get('user')
    data = request.get_json()

    # Validate
    if not data.get('name') or not data.get('email'):
        return jsonify({'success': False, 'error': 'Name and email required'}), 400

    # Process
    success = leadtracker_service.add_lead(user, data)

    if success:
        return jsonify({'success': True, 'message': 'Lead added'})
    else:
        return jsonify({'success': False, 'error': 'Failed to add lead'}), 500

@leadtracker_bp.route("/api/update-lead/<lead_id>", methods=['PUT'])
@require_login
def api_update_lead(lead_id):
    """Update lead status"""
    user = session.get('user')
    data = request.get_json()

    success = leadtracker_service.update_lead(user, lead_id, data)
    return jsonify({'success': success})
```

#### **File 2:** `app/services/leadtracker_service.py`

```python
# -*- coding: utf-8 -*-
"""LeadTracker Service - CRM Business Logic"""

import logging
from typing import Dict, List
from datetime import datetime
from app.core.extensions import data_persistence, cache_manager

logger = logging.getLogger(__name__)

class LeadTrackerService:
    """CRM lead management logic"""

    def __init__(self):
        self.data_file = 'leadtracker_leads'
        self.cache_ttl = 600

    def get_dashboard_data(self, user: str) -> Dict:
        """Get dashboard metrics"""
        cache_key = f"leadtracker_dashboard_{user}"
        cached = cache_manager.get("leadtracker", cache_key)

        if cached:
            return cached

        leads = self.get_user_leads(user)

        result = {
            'total_leads': len(leads),
            'active_leads': sum(1 for l in leads if l.get('status') == 'active'),
            'converted': sum(1 for l in leads if l.get('status') == 'converted'),
            'lost': sum(1 for l in leads if l.get('status') == 'lost'),
        }

        cache_manager.set("leadtracker", cache_key, result, ttl=self.cache_ttl)
        return result

    def get_user_leads(self, user: str) -> List[Dict]:
        """Get all leads for user"""
        data = data_persistence.load_data(self.data_file, {})
        return data.get(user, [])

    def add_lead(self, user: str, lead_data: Dict) -> bool:
        """Add new lead"""
        try:
            data = data_persistence.load_data(self.data_file, {})

            if user not in data:
                data[user] = []

            # Create lead
            lead = {
                'id': f"lead_{int(datetime.now().timestamp())}",
                'name': lead_data.get('name'),
                'email': lead_data.get('email'),
                'phone': lead_data.get('phone', ''),
                'status': 'new',
                'source': lead_data.get('source', 'manual'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }

            data[user].append(lead)
            data_persistence.save_data(self.data_file, data)

            # Invalidate cache
            cache_manager.invalidate("leadtracker", f"leadtracker_dashboard_{user}")

            logger.info(f"Lead added for {user}: {lead['id']}")
            return True

        except Exception as e:
            logger.error(f"Error adding lead for {user}: {e}")
            return False

    def update_lead(self, user: str, lead_id: str, update_data: Dict) -> bool:
        """Update existing lead"""
        try:
            data = data_persistence.load_data(self.data_file, {})

            if user not in data:
                return False

            # Find lead
            for lead in data[user]:
                if lead.get('id') == lead_id:
                    # Update fields
                    lead['status'] = update_data.get('status', lead.get('status'))
                    lead['notes'] = update_data.get('notes', lead.get('notes', ''))
                    lead['updated_at'] = datetime.now().isoformat()

                    data_persistence.save_data(self.data_file, data)
                    cache_manager.invalidate("leadtracker", f"leadtracker_dashboard_{user}")

                    logger.info(f"Lead updated for {user}: {lead_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error updating lead {lead_id} for {user}: {e}")
            return False

# Singleton
leadtracker_service = LeadTrackerService()
```

#### **File 3:** `templates/leadtracker/dashboard.html`

```html
{% extends "hub/base.html" %}

{% block title %}Lead Tracker - CRM{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-4xl font-bold text-primary mb-6">
        <i data-lucide="users" class="inline-block w-10 h-10 mr-2"></i>
        Lead Tracker
    </h1>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="card bg-base-200 shadow-xl">
            <div class="card-body">
                <h2 class="card-title text-sm">Total Leads</h2>
                <p class="text-3xl font-bold text-primary">{{ total_leads }}</p>
            </div>
        </div>
        <div class="card bg-base-200 shadow-xl">
            <div class="card-body">
                <h2 class="card-title text-sm">Active</h2>
                <p class="text-3xl font-bold text-secondary">{{ active_leads }}</p>
            </div>
        </div>
        <div class="card bg-base-200 shadow-xl">
            <div class="card-body">
                <h2 class="card-title text-sm">Converted</h2>
                <p class="text-3xl font-bold text-accent">{{ converted }}</p>
            </div>
        </div>
        <div class="card bg-base-200 shadow-xl">
            <div class="card-body">
                <h2 class="card-title text-sm">Lost</h2>
                <p class="text-3xl font-bold text-error">{{ lost }}</p>
            </div>
        </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex gap-4 mb-6">
        <button class="btn btn-primary" onclick="document.getElementById('add_modal').showModal()">
            <i data-lucide="plus" class="w-5 h-5 mr-2"></i>
            Add Lead
        </button>
        <a href="{{ url_for('leadtracker.leads_view') }}" class="btn btn-secondary">
            <i data-lucide="list" class="w-5 h-5 mr-2"></i>
            View All Leads
        </a>
    </div>
</div>

<!-- Add Lead Modal -->
<dialog id="add_modal" class="modal">
    <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Add New Lead</h3>
        <form id="addLeadForm">
            <div class="form-control mb-4">
                <label class="label"><span class="label-text">Name *</span></label>
                <input type="text" name="name" class="input input-bordered" required>
            </div>
            <div class="form-control mb-4">
                <label class="label"><span class="label-text">Email *</span></label>
                <input type="email" name="email" class="input input-bordered" required>
            </div>
            <div class="form-control mb-4">
                <label class="label"><span class="label-text">Phone</span></label>
                <input type="tel" name="phone" class="input input-bordered">
            </div>
            <div class="modal-action">
                <button type="submit" class="btn btn-primary">Save</button>
                <button type="button" class="btn" onclick="document.getElementById('add_modal').close()">Cancel</button>
            </div>
        </form>
    </div>
</dialog>

<script>
    lucide.createIcons();

    document.getElementById('addLeadForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            email: formData.get('email'),
            phone: formData.get('phone')
        };

        try {
            const response = await fetch('/leadtracker/api/add-lead', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                document.getElementById('add_modal').close();
                location.reload();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Network error:', error);
            alert('Network error occurred');
        }
    });
</script>
{% endblock %}
```

---

## Best Practices & Patterns

### Pattern 1: Service Layer für Business-Logic

```python
# ❌ FALSCH: Logic in Route
@mytool_bp.route("/action", methods=['POST'])
def action():
    data = data_persistence.load_data('mytool', {})
    data[user]['value'] = request.form.get('value')
    data_persistence.save_data('mytool', data)
    return redirect('/')

# ✅ RICHTIG: Logic in Service
@mytool_bp.route("/action", methods=['POST'])
def action():
    from app.services.mytool_service import mytool_service
    success = mytool_service.update_value(user, request.form.get('value'))
    return redirect('/')
```

### Pattern 2: Caching-Strategie

```python
def get_data(self, user: str):
    # 1. Check cache
    cache_key = f"mytool_{user}_data"
    cached = cache_manager.get("mytool", cache_key)
    if cached:
        return cached

    # 2. Load from storage
    data = data_persistence.load_data('mytool', {})
    result = data.get(user, {})

    # 3. Process/compute
    result['computed_value'] = len(result)

    # 4. Cache with TTL
    cache_manager.set("mytool", cache_key, result, ttl=600)

    # 5. Return
    return result
```

**Cache TTLs by use case:**
- Dashboard data: `600s` (10 min) - frequently accessed
- User profiles: `300s` (5 min) - moderate refresh
- Analytics: `1800s` (30 min) - rarely changes
- Static config: `3600s` (1 hour) - very stable

### Pattern 3: Error Handling

```python
def process_action(self, user: str, data: Dict) -> bool:
    try:
        # Validate
        if not data.get('required_field'):
            logger.warning(f"Missing required_field for {user}")
            return False

        # Process
        result = self._do_something(data)

        # Save
        self.data_persistence.save_data('mytool', result)

        logger.info(f"Action processed successfully for {user}")
        return True

    except ValueError as e:
        logger.warning(f"Validation error for {user}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error for {user}: {e}", exc_info=True)
        return False
```

### Pattern 4: Route Handler

```python
@mytool_bp.route("/endpoint", methods=['POST'])
@require_login
def endpoint():
    user = session.get('user')

    # 1. Get request data
    data = request.get_json() or request.form

    # 2. Validate input
    if not validate_input(data):
        flash('Validation error', 'danger')
        return redirect(url_for('mytool.dashboard'))

    # 3. Process (use service layer)
    from app.services.mytool_service import mytool_service
    success = mytool_service.process(user, data)

    # 4. Return response
    if success:
        flash('Success!', 'success')
    else:
        flash('Error occurred', 'danger')

    return redirect(url_for('mytool.dashboard'))
```

### Pattern 5: API Endpoints (für AJAX)

```python
@mytool_bp.route("/api/fetch-data", methods=['GET'])
@require_login
def api_fetch_data():
    user = session.get('user')

    try:
        from app.services.mytool_service import mytool_service
        data = mytool_service.get_data(user)

        return jsonify({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### Pattern 6: Data Persistence

```python
# Load data
data = data_persistence.load_data('key_name', default={})

# Modify data
data[user] = {'value': 123}

# Save data
data_persistence.save_data('key_name', data)

# Backup (optional but recommended)
data_persistence.create_backup()
```

### Pattern 7: PostgreSQL Models (Optional)

```python
# In app/models/mytool.py
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base

class MyToolItem(Base):
    __tablename__ = 'mytool_items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_mytool_username', 'username'),
    )

# In service:
from app.models.base import get_db_session
from app.models.mytool import MyToolItem

def get_user_items(user: str):
    session = get_db_session()
    items = session.query(MyToolItem).filter_by(username=user).all()
    session.close()
    return items
```

---

## Checkliste

### Pre-Integration

- [ ] Tool-Konzept klar definiert
- [ ] Bestehende Tools analysiert (T2, Analytics als Referenz)
- [ ] Entscheidung: JSON-Storage oder PostgreSQL?
- [ ] `CLAUDE.md` gelesen (Deployment-Workflow!)

### Development

- [ ] Blueprint erstellt (`app/routes/[tool].py`)
- [ ] Service-Layer erstellt (`app/services/[tool]_service.py`)
- [ ] Templates erstellt (`templates/[tool]/dashboard.html`)
- [ ] Blueprint registriert (`app/__init__.py` register_blueprints)
- [ ] Navigation hinzugefügt (`app/__init__.py` get_available_tools)
- [ ] Access-Control konfiguriert (falls nötig)
- [ ] Lokale Tests durchgeführt (`python run.py`)

### Testing

- [ ] Server startet ohne Fehler
- [ ] Tool ist in Navigation sichtbar
- [ ] Dashboard lädt korrekt
- [ ] API-Endpoints funktionieren
- [ ] Daten werden korrekt gespeichert
- [ ] Cache funktioniert (TTL beachten!)

### Deployment

- [ ] Backup erstellt (`tar -czf backup...`)
- [ ] Dateien auf VPS hochgeladen (`scp`)
- [ ] Service neu gestartet (`systemctl restart business-hub`)
- [ ] Logs geprüft (keine Errors)
- [ ] Health-Check durchgeführt (`curl /health`)
- [ ] Browser-Test auf Production-URL
- [ ] Funktionalität getestet

### Git

- [ ] Änderungen staged (`git add`)
- [ ] Commit erstellt (klare Message: `feat: Add [Tool]`)
- [ ] Auf GitHub gepusht (`git push origin main`)
- [ ] `.env` / Credentials NICHT committed!

---

## Deployment

### Hetzner VPS Details

- **Server:** `91.98.192.233`
- **SSH-Key:** `~/.ssh/server_key`
- **App-Pfad:** `/opt/business-hub/`
- **Service:** `business-hub.service`
- **URL:** https://berater.zfa.gmbh/
- **Logs:** `/var/log/business-hub/error.log`

### Deployment-Commands

```bash
# 1. Backup (IMMER ZUERST!)
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "cd /opt/business-hub && tar -czf /tmp/backup_$(date +%Y%m%d_%H%M).tar.gz data/persistent/"

# 2. Deploy Routes
scp -i ~/.ssh/server_key app/routes/[tool].py \
  root@91.98.192.233:/opt/business-hub/app/routes/

# 3. Deploy Services
scp -i ~/.ssh/server_key app/services/[tool]_service.py \
  root@91.98.192.233:/opt/business-hub/app/services/

# 4. Deploy Templates
scp -i ~/.ssh/server_key -r templates/[tool]/ \
  root@91.98.192.233:/opt/business-hub/templates/

# 5. Deploy __init__.py (Blueprint-Registrierung)
scp -i ~/.ssh/server_key app/__init__.py \
  root@91.98.192.233:/opt/business-hub/app/

# 6. Restart Service
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "systemctl restart business-hub"

# 7. Check Status
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "systemctl status business-hub --no-pager | head -20"

# 8. View Logs
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "tail -100 /var/log/business-hub/error.log | grep -i error"

# 9. Health Check
curl -I https://berater.zfa.gmbh/health
# Expected: HTTP/2 200
```

### Rollback (bei Problemen)

```bash
# 1. Restore Backup
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "cd /opt/business-hub && tar -xzf /tmp/backup_YYYYMMDD_HHMM.tar.gz"

# 2. Restart Service
ssh -i ~/.ssh/server_key root@91.98.192.233 \
  "systemctl restart business-hub"

# 3. Verify
curl -I https://berater.zfa.gmbh/health
```

---

## Troubleshooting

### Problem: Blueprint wird nicht gefunden

**Symptom:** `ImportError: cannot import name 'mytool_bp'`

**Lösung:**
1. Prüfe Blueprint-Definition: `mytool_bp = Blueprint('mytool', __name__, url_prefix='/mytool')`
2. Prüfe `__init__.py`: `from app.routes.mytool import mytool_bp`
3. Prüfe Datei-Pfad: `app/routes/mytool.py` existiert?

### Problem: Service import fails

**Symptom:** `ModuleNotFoundError: No module named 'app.services.mytool_service'`

**Lösung:**
1. Prüfe Service-Datei existiert: `app/services/mytool_service.py`
2. Prüfe Singleton-Instance: `mytool_service = MyToolService()` am Ende
3. Import in Route prüfen: `from app.services.mytool_service import mytool_service`

### Problem: Template nicht gefunden

**Symptom:** `TemplateNotFoundError: mytool/dashboard.html`

**Lösung:**
1. Prüfe Template-Pfad: `templates/mytool/dashboard.html` existiert?
2. Prüfe render_template Call: `render_template('mytool/dashboard.html', ...)`
3. Keine führenden Slashes: `mytool/dashboard.html` NICHT `/mytool/dashboard.html`

### Problem: Tool erscheint nicht in Navigation

**Symptom:** Tool fehlt im Hub-Menu

**Lösung:**
1. Prüfe `get_available_tools()` in `app/__init__.py`
2. Tool zur `tools` Liste hinzugefügt?
3. `'status': 'active'` gesetzt?
4. `user_has_tool_access()` gibt `True` zurück?

### Problem: Cache funktioniert nicht

**Symptom:** Daten werden nicht cached/zu oft geladen

**Lösung:**
1. Cache-TTL prüfen: `cache_manager.set("namespace", "key", data, ttl=600)`
2. Namespace konsistent: Immer gleicher String (z.B. `"mytool"`)
3. Invalidierung prüfen: `cache_manager.invalidate("namespace", "key")` nach Updates
4. Redis konfiguriert? `REDIS_URL` in `.env`?

### Problem: 401 Unauthorized

**Symptom:** Redirect zu Login-Page

**Lösung:**
1. `@require_login` Decorator vorhanden?
2. User in Session: `session.get('user')` ist nicht `None`?
3. `@mytool_bp.before_request` blockiert nicht ungewollt?

### Problem: 500 Internal Server Error

**Symptom:** Server-Error beim Aufrufen des Tools

**Lösung:**
1. Logs prüfen: `tail -100 /var/log/business-hub/error.log`
2. Exception-Stacktrace lesen
3. Try-Except um kritische Operationen
4. Logger-Statements hinzufügen für Debugging

---

## FAQ

**Q: Wo fange ich an?**
A: Erstelle `app/routes/[tool].py` mit Blueprint → Siehe Step 1 oben

**Q: Wie registriere ich mein Tool?**
A: In `app/__init__.py` bei `register_blueprints()` hinzufügen → Step 2

**Q: Wie kommt mein Tool in die Navigation?**
A: In `app/__init__.py` bei `get_available_tools()` eintragen → Step 3

**Q: Welche Frameworks nutzen wir?**
A: Flask (Backend), Tailwind CSS + DaisyUI (Frontend), PostgreSQL (optional)

**Q: Wie deploye ich?**
A: `scp` Files auf VPS → `systemctl restart business-hub` → Siehe Deployment-Section

**Q: Brauche ich eine Datenbank?**
A: Optional - `data_persistence` (JSON-Files) reicht für kleine Tools

**Q: Gibt es Code-Beispiele?**
A: Ja! LeadTracker Beispiel-Tool oben (vollständig implementiert)

**Q: Was sind T2/Slot-Booking?**
A: Bestehende Tools als Referenz - siehe `app/routes/t2.py` (komplex) oder `app/routes/analytics.py` (einfach)

**Q: Wie teste ich lokal?**
A: `python run.py` → Browser: `http://localhost:5000/mytool/`

**Q: Wo sind die Server-Credentials?**
A: Siehe `CLAUDE.md` - SSH-Key: `~/.ssh/server_key`, Server: `91.98.192.233`

---

## Referenzen

### Wichtige Dateien

| Datei | Zweck | Zeilen |
|-------|-------|--------|
| `app/__init__.py` | Application Factory, Blueprint-Registrierung | 570 |
| `app/routes/t2.py` | Komplexes Tool-Beispiel | 1,947 |
| `app/routes/analytics.py` | Einfaches Tool-Beispiel | 150 |
| `app/core/extensions.py` | Shared Extensions (CSRF, Cache, etc.) | 180 |
| `CLAUDE.md` | Projekt-Dokumentation, Deployment-Workflow | 850+ |

### Externe Docs

- **Flask Blueprints:** https://flask.palletsprojects.com/en/stable/blueprints/
- **Tailwind CSS:** https://tailwindcss.com/docs
- **DaisyUI Components:** https://daisyui.com/components/
- **Lucide Icons:** https://lucide.dev/icons/
- **SQLAlchemy:** https://docs.sqlalchemy.org/

---

## Kontakt & Support

**Bei Problemen:**
1. Logs prüfen: `tail -100 /var/log/business-hub/error.log`
2. Health-Check: `curl https://berater.zfa.gmbh/health`
3. Dieses Guide nochmal lesen
4. `CLAUDE.md` konsultieren für Deployment-Details

**Erfolgreiche Integration?**
- Git commit erstellen
- Tool in Production testen
- Dokumentation aktualisieren

---

**Ende des Guides** - Viel Erfolg bei der Tool-Integration! 🚀
