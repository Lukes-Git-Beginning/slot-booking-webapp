# -*- coding: utf-8 -*-
"""
HubSpot Scope Test — Prüft welche API-Berechtigungen verfügbar sind.

Usage:
    python scripts/hubspot_test_scopes.py
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv(project_root / '.env')
except ImportError:
    pass

TOKEN = os.getenv('HUBSPOT_ACCESS_TOKEN', '')
if not TOKEN:
    print("ERROR: HUBSPOT_ACCESS_TOKEN not set.")
    sys.exit(1)

try:
    from hubspot import HubSpot
except ImportError:
    print("ERROR: hubspot-api-client not installed.")
    sys.exit(1)

import requests

client = HubSpot(access_token=TOKEN)
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
BASE = "https://api.hubapi.com"

results = {}


def test_scope(name, fn):
    """Run a scope test and record result."""
    try:
        data = fn()
        results[name] = True
        print(f"  ✅ {name}")
        if data:
            print(f"     → {data}")
    except Exception as e:
        err = str(e)
        if '403' in err or 'Forbidden' in err:
            results[name] = False
            print(f"  ❌ {name} — 403 Forbidden (Scope fehlt)")
        elif '401' in err or 'Unauthorized' in err:
            results[name] = False
            print(f"  ❌ {name} — 401 Unauthorized (Token ungültig?)")
        else:
            results[name] = 'error'
            print(f"  ⚠️  {name} — {err[:120]}")


print(f"\nHubSpot Scope Test")
print(f"Token: {TOKEN[:8]}...{TOKEN[-4:]}")
print(f"{'=' * 60}")

# ── Bisher aktive Scopes (Regression) ──────────────────────

print("\n── Bisher aktive Scopes ──")

test_scope("crm.objects.deals.read", lambda: (
    client.crm.deals.basic_api.get_page(limit=1),
    "Deals abrufbar"
)[1])

test_scope("crm.objects.contacts.read", lambda: (
    client.crm.contacts.basic_api.get_page(limit=1),
    "Kontakte abrufbar"
)[1])

test_scope("crm.pipelines", lambda: (
    client.crm.pipelines.pipelines_api.get_all(object_type="deals"),
    "Pipelines abrufbar"
)[1])


def test_associations():
    deals = client.crm.deals.basic_api.get_page(limit=1)
    if deals.results:
        deal_id = deals.results[0].id
        client.crm.deals.associations_api.get_all(
            deal_id=deal_id, to_object_type="contacts"
        )
        return "Associations abrufbar"
    return "Keine Deals zum Testen"


test_scope("crm.objects.associations", test_associations)

# ── Bisher fehlend (403) ───────────────────────────────────

print("\n── Bisher fehlend (David sollte aktiviert haben) ──")


def test_owners():
    resp = client.crm.owners.owners_api.get_page(limit=5)
    owners = resp.results or []
    if owners:
        names = [f"{o.first_name} {o.last_name}".strip() for o in owners[:5]]
        return f"{len(resp.results)} Owners gefunden: {', '.join(names)}"
    return "Owners API erreichbar, aber keine Owners"


test_scope("crm.objects.owners.read", test_owners)

# ── Zukunfts-Scopes ───────────────────────────────────────

print("\n── Zukunfts-Scopes ──")

test_scope("crm.objects.companies.read", lambda: (
    client.crm.companies.basic_api.get_page(limit=1),
    f"Companies abrufbar ({len(client.crm.companies.basic_api.get_page(limit=1).results)} gefunden)"
)[1])


def test_line_items():
    resp = client.crm.line_items.basic_api.get_page(limit=1)
    count = len(resp.results) if resp.results else 0
    return f"Line Items abrufbar ({count} gefunden)"


test_scope("crm.objects.line_items.read", test_line_items)


def test_marketing_events():
    resp = requests.get(
        f"{BASE}/marketing/v3/marketing-events/events",
        headers=HEADERS, timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        count = len(data.get('results', []))
        return f"Marketing Events abrufbar ({count} Events)"
    raise Exception(f"Status {resp.status_code}: {resp.text[:100]}")


test_scope("crm.objects.marketing_events.read", test_marketing_events)


def test_analytics():
    resp = requests.get(
        f"{BASE}/analytics/v2/reports/deals/total",
        headers=HEADERS,
        params={"start": "20260101", "end": "20260312"},
        timeout=10,
    )
    if resp.status_code == 200:
        return "Analytics API erreichbar"
    raise Exception(f"Status {resp.status_code}: {resp.text[:100]}")


test_scope("analytics.read", test_analytics)


def test_deals_write():
    """Check if we can access the deals update endpoint (without actually writing)."""
    resp = requests.get(
        f"{BASE}/crm/v3/objects/deals?limit=1",
        headers=HEADERS, timeout=10
    )
    # We can't truly test write without writing — just check token info
    resp2 = requests.get(
        f"{BASE}/oauth/v1/access-tokens/{TOKEN}",
        headers=HEADERS, timeout=10
    )
    if resp2.status_code == 200:
        scopes = resp2.json().get('scopes', [])
        has_write = any('deals' in s and 'write' in s for s in scopes)
        if has_write:
            return f"Write-Scope vorhanden (Scopes: {[s for s in scopes if 'deal' in s]})"
        return f"Kein deals.write in Scopes. Vorhandene Deal-Scopes: {[s for s in scopes if 'deal' in s]}"
    raise Exception(f"Token-Info nicht abrufbar: {resp2.status_code}")


test_scope("crm.objects.deals.write (check only)", test_deals_write)

# ── Token-Info (alle Scopes auflisten) ─────────────────────

print(f"\n── Alle Token-Scopes ──")
try:
    resp = requests.get(
        f"{BASE}/oauth/v1/access-tokens/{TOKEN}",
        headers=HEADERS, timeout=10
    )
    if resp.status_code == 200:
        info = resp.json()
        scopes = sorted(info.get('scopes', []))
        print(f"  Token User: {info.get('user', 'N/A')}")
        print(f"  Hub ID: {info.get('hub_id', 'N/A')}")
        print(f"  App ID: {info.get('app_id', 'N/A')}")
        print(f"  Scopes ({len(scopes)}):")
        for s in scopes:
            print(f"    - {s}")
    else:
        print(f"  Token-Info nicht abrufbar (Status {resp.status_code})")
        print(f"  (Private App Tokens unterstützen diesen Endpoint evtl. nicht)")
except Exception as e:
    print(f"  Fehler: {e}")

# ── Zusammenfassung ────────────────────────────────────────

print(f"\n{'=' * 60}")
print("ZUSAMMENFASSUNG")
print(f"{'=' * 60}")

ok = [k for k, v in results.items() if v is True]
fail = [k for k, v in results.items() if v is False]
err = [k for k, v in results.items() if v == 'error']

print(f"\n  ✅ Funktioniert ({len(ok)}): {', '.join(ok) if ok else '-'}")
print(f"  ❌ Fehlt ({len(fail)}): {', '.join(fail) if fail else '-'}")
if err:
    print(f"  ⚠️  Fehler ({len(err)}): {', '.join(err)}")

if 'crm.objects.owners.read' in ok:
    print("\n  → Telefonist-Namensauflösung funktioniert jetzt automatisch!")
    print("    Kein Code-Change nötig — _resolve_telefonist_name() nutzt den Scope direkt.")
