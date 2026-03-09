# -*- coding: utf-8 -*-
"""
HubSpot Discovery Script - Kampagnen-Properties + Pipeline-Stages

Zweck:
  1. Kontakt-Properties nach "campaign"/"kampagne" durchsuchen
  2. Marketing Campaigns API abfragen
  3. Contact Lists abfragen
  4. Beispiel-Kontakt mit allen Properties laden
  5. Pipeline-Stages auslesen und dokumentieren

Usage:
    python scripts/hubspot_discover_campaigns.py

Benötigt: HUBSPOT_ACCESS_TOKEN als ENV-Variable oder in .env
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / '.env')
except ImportError:
    pass

TOKEN = os.getenv('HUBSPOT_ACCESS_TOKEN', '')
PIPELINE_ID = os.getenv('HUBSPOT_PIPELINE_ID', 'default')

if not TOKEN:
    print("ERROR: HUBSPOT_ACCESS_TOKEN not set. Set it in .env or as environment variable.")
    sys.exit(1)

try:
    from hubspot import HubSpot
except ImportError:
    print("ERROR: hubspot-api-client not installed. Run: pip install hubspot-api-client>=8.0.0")
    sys.exit(1)

client = HubSpot(access_token=TOKEN)


def discover_campaign_properties():
    """Search contact properties for campaign-related fields."""
    print("\n" + "=" * 60)
    print("1. KONTAKT-PROPERTIES (campaign/kampagne)")
    print("=" * 60)

    try:
        all_props = client.crm.properties.core_api.get_all(object_type="contacts")
        campaign_props = []
        for prop in all_props.results:
            name_lower = prop.name.lower()
            label_lower = (prop.label or '').lower()
            if any(kw in name_lower or kw in label_lower for kw in
                   ['campaign', 'kampagne', 'source', 'quelle', 'kanal', 'channel', 'utm']):
                campaign_props.append({
                    'name': prop.name,
                    'label': prop.label,
                    'type': prop.type,
                    'field_type': prop.field_type,
                    'group': prop.group_name,
                    'options': [o.label for o in (prop.options or [])][:10],
                })

        if campaign_props:
            for p in campaign_props:
                print(f"\n  Property: {p['name']}")
                print(f"  Label:    {p['label']}")
                print(f"  Type:     {p['type']} / {p['field_type']}")
                print(f"  Group:    {p['group']}")
                if p['options']:
                    print(f"  Options:  {', '.join(p['options'])}")
        else:
            print("  Keine campaign-bezogenen Properties gefunden.")

        print(f"\n  Total contact properties: {len(all_props.results)}")
        return campaign_props

    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def discover_deal_properties():
    """Search deal properties for campaign-related fields."""
    print("\n" + "=" * 60)
    print("2. DEAL-PROPERTIES (campaign/kampagne)")
    print("=" * 60)

    try:
        all_props = client.crm.properties.core_api.get_all(object_type="deals")
        campaign_props = []
        for prop in all_props.results:
            name_lower = prop.name.lower()
            label_lower = (prop.label or '').lower()
            if any(kw in name_lower or kw in label_lower for kw in
                   ['campaign', 'kampagne', 'source', 'quelle', 'kanal', 'channel',
                    'utm', 'lead', 'foerder', 'förder', 'meta']):
                campaign_props.append({
                    'name': prop.name,
                    'label': prop.label,
                    'type': prop.type,
                    'field_type': prop.field_type,
                    'group': prop.group_name,
                    'options': [o.label for o in (prop.options or [])][:10],
                })

        if campaign_props:
            for p in campaign_props:
                print(f"\n  Property: {p['name']}")
                print(f"  Label:    {p['label']}")
                print(f"  Type:     {p['type']} / {p['field_type']}")
                print(f"  Group:    {p['group']}")
                if p['options']:
                    print(f"  Options:  {', '.join(p['options'])}")
        else:
            print("  Keine campaign-bezogenen Deal-Properties gefunden.")

        print(f"\n  Total deal properties: {len(all_props.results)}")
        return campaign_props

    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def discover_pipeline_stages():
    """List all pipeline stages with IDs."""
    print("\n" + "=" * 60)
    print("3. PIPELINE-STAGES")
    print("=" * 60)

    try:
        # List all pipelines first
        pipelines = client.crm.pipelines.pipelines_api.get_all(object_type="deals")
        for pipeline in pipelines.results:
            print(f"\n  Pipeline: {pipeline.label} (ID: {pipeline.id})")

            stages = client.crm.pipelines.pipeline_stages_api.get_all(
                object_type="deals",
                pipeline_id=pipeline.id,
            )
            sorted_stages = sorted(stages.results, key=lambda s: s.display_order)
            for stage in sorted_stages:
                print(f"    [{stage.display_order:2d}] {stage.label:<30} ID: {stage.id}")

            # Generate STAGE_MAPPING snippet
            print(f"\n  --- Python STAGE_MAPPING for pipeline '{pipeline.label}' ---")
            print("  STAGE_MAPPING = {")
            for stage in sorted_stages:
                safe_key = stage.label.lower().replace(' ', '_').replace('-', '_')
                safe_key = ''.join(c for c in safe_key if c.isalnum() or c == '_')
                print(f'      "{safe_key}": "{stage.id}",  # {stage.label}')
            print("  }")

    except Exception as e:
        print(f"  ERROR: {e}")


def discover_sample_contact():
    """Load a sample contact with all properties."""
    print("\n" + "=" * 60)
    print("4. BEISPIEL-KONTAKT (alle Properties)")
    print("=" * 60)

    try:
        from hubspot.crm.contacts import PublicObjectSearchRequest
        req = PublicObjectSearchRequest(limit=1)
        resp = client.crm.contacts.search_api.do_search(
            public_object_search_request=req
        )
        if not resp.results:
            print("  Keine Kontakte gefunden.")
            return

        contact_id = resp.results[0].id
        # Fetch with ALL properties
        contact = client.crm.contacts.basic_api.get_by_id(
            contact_id=contact_id,
            properties_with_history=None,
            archived=False,
        )

        props = contact.properties or {}
        print(f"  Contact ID: {contact_id}")
        print(f"  Total properties: {len(props)}")
        print(f"\n  Non-null properties:")
        for key, val in sorted(props.items()):
            if val and val.strip():
                print(f"    {key}: {val[:80]}")

    except Exception as e:
        print(f"  ERROR: {e}")


def discover_sample_deal():
    """Load a sample deal with all properties."""
    print("\n" + "=" * 60)
    print("5. BEISPIEL-DEAL (alle Properties)")
    print("=" * 60)

    try:
        from hubspot.crm.deals import PublicObjectSearchRequest
        req = PublicObjectSearchRequest(
            limit=1,
            filter_groups=[{"filters": [{
                "propertyName": "pipeline",
                "operator": "EQ",
                "value": PIPELINE_ID,
            }]}],
        )
        resp = client.crm.deals.search_api.do_search(
            public_object_search_request=req
        )
        if not resp.results:
            print("  Keine Deals gefunden.")
            return

        deal_id = resp.results[0].id
        deal = client.crm.deals.basic_api.get_by_id(deal_id=deal_id)

        props = deal.properties or {}
        print(f"  Deal ID: {deal_id}")
        print(f"  Total properties: {len(props)}")
        print(f"\n  Non-null properties:")
        for key, val in sorted(props.items()):
            if val and val.strip():
                print(f"    {key}: {val[:80]}")

    except Exception as e:
        print(f"  ERROR: {e}")


def discover_marketing_campaigns():
    """Try to fetch marketing campaigns (requires Marketing Hub)."""
    print("\n" + "=" * 60)
    print("6. MARKETING CAMPAIGNS API")
    print("=" * 60)

    try:
        import requests
        headers = {"Authorization": f"Bearer {TOKEN}"}

        # Marketing Campaigns API
        resp = requests.get(
            "https://api.hubapi.com/marketing/v3/campaigns",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            campaigns = data.get('results', [])
            print(f"  Found {len(campaigns)} campaigns:")
            for c in campaigns[:20]:
                print(f"    - {c.get('name', 'N/A')} (ID: {c.get('id', 'N/A')})")
        else:
            print(f"  Status {resp.status_code}: {resp.text[:200]}")
            print("  (Marketing Campaigns API might require Marketing Hub Professional+)")

    except Exception as e:
        print(f"  ERROR: {e}")


def discover_contact_lists():
    """List contact lists."""
    print("\n" + "=" * 60)
    print("7. CONTACT LISTS")
    print("=" * 60)

    try:
        import requests
        headers = {"Authorization": f"Bearer {TOKEN}"}

        resp = requests.get(
            "https://api.hubapi.com/contacts/v1/lists",
            headers=headers,
            params={"count": 20},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            lists = data.get('lists', [])
            print(f"  Found {len(lists)} lists:")
            for l in lists:
                print(f"    - {l.get('name', 'N/A')} (ID: {l.get('listId')}, "
                      f"count: {l.get('metaData', {}).get('size', 'N/A')})")
        else:
            print(f"  Status {resp.status_code}: {resp.text[:200]}")

    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == '__main__':
    print("HubSpot Discovery Script")
    print(f"Token: {TOKEN[:8]}...{TOKEN[-4:]}")
    print(f"Pipeline ID: {PIPELINE_ID}")

    discover_campaign_properties()
    discover_deal_properties()
    discover_pipeline_stages()
    discover_sample_contact()
    discover_sample_deal()
    discover_marketing_campaigns()
    discover_contact_lists()

    print("\n" + "=" * 60)
    print("DISCOVERY COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Identify the campaign property name from the results above")
    print("  2. Update STAGE_MAPPING in app/config/base.py with the stage IDs")
    print("  3. Use the campaign property in hubspot_service.get_campaign_stats()")
