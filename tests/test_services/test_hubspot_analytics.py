# -*- coding: utf-8 -*-
"""
Service Layer Tests - HubSpot Analytics (Phase G.3)
Tests for the 6 analytics methods in hubspot_service.py
and their integration in analytics_service.py.
"""

import sys
import pytest
import time
from unittest.mock import patch, MagicMock, PropertyMock


# ========== MOCK HUBSPOT MODULES ==========
# hubspot-api-client is not installed locally, so we mock the module tree

def _ensure_hubspot_mocks():
    """Ensure hubspot module tree exists in sys.modules for inline imports."""
    modules = [
        'hubspot',
        'hubspot.crm',
        'hubspot.crm.deals',
        'hubspot.crm.contacts',
        'hubspot.crm.pipelines',
        'hubspot.crm.objects',
        'hubspot.crm.objects.notes',
        'hubspot.crm.associations',
        'hubspot.crm.associations.v4',
    ]
    for mod in modules:
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()


_ensure_hubspot_mocks()


# ========== FIXTURES ==========

@pytest.fixture
def hs_service():
    """HubSpotService instance with mocked client."""
    _ensure_hubspot_mocks()
    from app.services.hubspot_service import HubSpotService
    svc = HubSpotService()
    svc.client = MagicMock()
    svc._initialized = True
    return svc


@pytest.fixture
def hs_service_unavailable():
    """HubSpotService that is not available."""
    from app.services.hubspot_service import HubSpotService
    svc = HubSpotService()
    svc.client = None
    svc._initialized = False
    return svc


# ========== CACHE ==========

class TestCache:

    def test_cache_set_and_get(self, hs_service):
        hs_service._cache_set('test_key', 42)
        assert hs_service._cache_get('test_key') == 42

    def test_cache_expired(self, hs_service):
        hs_service._cache_set('old_key', 99)
        # Manually expire
        hs_service._cache_ts['old_key'] = time.time() - 9999
        assert hs_service._cache_get('old_key') is None

    def test_cache_miss(self, hs_service):
        assert hs_service._cache_get('nonexistent') is None


# ========== GET TOTAL DEALS COUNT ==========

class TestGetTotalDealsCount:

    def test_returns_none_when_unavailable(self, hs_service_unavailable):
        assert hs_service_unavailable.get_total_deals_count() is None

    def test_returns_count_all(self, hs_service):
        mock_resp = MagicMock()
        mock_resp.total = 125
        hs_service.client.crm.deals.search_api.do_search.return_value = mock_resp

        result = hs_service.get_total_deals_count()
        assert result == 125

    def test_returns_count_filtered(self, hs_service):
        mock_resp = MagicMock()
        mock_resp.total = 30
        hs_service.client.crm.deals.search_api.do_search.return_value = mock_resp

        result = hs_service.get_total_deals_count(stage='rueckholung')
        assert result == 30

    def test_uses_cache(self, hs_service):
        mock_resp = MagicMock()
        mock_resp.total = 50
        hs_service.client.crm.deals.search_api.do_search.return_value = mock_resp

        # First call fetches
        hs_service.get_total_deals_count()
        # Second call uses cache
        result = hs_service.get_total_deals_count()
        assert result == 50
        assert hs_service.client.crm.deals.search_api.do_search.call_count == 1

    def test_handles_exception(self, hs_service):
        hs_service.client.crm.deals.search_api.do_search.side_effect = Exception("API error")
        assert hs_service.get_total_deals_count() is None


# ========== GET AVG DEAL VALUE ==========

class TestGetAvgDealValue:

    def test_returns_none_when_unavailable(self, hs_service_unavailable):
        assert hs_service_unavailable.get_avg_deal_value() is None

    def test_calculates_average(self, hs_service):
        deal1 = MagicMock()
        deal1.properties = {'amount': '1000'}
        deal2 = MagicMock()
        deal2.properties = {'amount': '2000'}
        deal3 = MagicMock()
        deal3.properties = {'amount': '3000'}

        mock_resp = MagicMock()
        mock_resp.results = [deal1, deal2, deal3]
        mock_resp.paging = None
        hs_service.client.crm.deals.search_api.do_search.return_value = mock_resp

        result = hs_service.get_avg_deal_value()
        assert result == 2000.0

    def test_skips_invalid_amounts(self, hs_service):
        deal1 = MagicMock()
        deal1.properties = {'amount': '1500'}
        deal2 = MagicMock()
        deal2.properties = {'amount': 'invalid'}
        deal3 = MagicMock()
        deal3.properties = {'amount': None}

        mock_resp = MagicMock()
        mock_resp.results = [deal1, deal2, deal3]
        mock_resp.paging = None
        hs_service.client.crm.deals.search_api.do_search.return_value = mock_resp

        result = hs_service.get_avg_deal_value()
        assert result == 1500.0

    def test_returns_none_no_deals(self, hs_service):
        mock_resp = MagicMock()
        mock_resp.results = []
        mock_resp.paging = None
        hs_service.client.crm.deals.search_api.do_search.return_value = mock_resp

        assert hs_service.get_avg_deal_value() is None

    def test_handles_exception(self, hs_service):
        hs_service.client.crm.deals.search_api.do_search.side_effect = Exception("fail")
        assert hs_service.get_avg_deal_value() is None


# ========== GET PIPELINE STATS ==========

class TestGetPipelineStats:

    def test_returns_none_when_unavailable(self, hs_service_unavailable):
        assert hs_service_unavailable.get_pipeline_stats() is None

    def test_returns_stage_counts(self, hs_service):
        stage1 = MagicMock()
        stage1.id = '100'
        stage1.label = 'Neu'
        stage2 = MagicMock()
        stage2.id = '200'
        stage2.label = 'Qualifiziert'

        pipeline_resp = MagicMock()
        pipeline_resp.results = [stage1, stage2]
        hs_service.client.crm.pipelines.pipeline_stages_api.get_all.return_value = pipeline_resp

        # Mock deal search for each stage count
        count_resp1 = MagicMock()
        count_resp1.total = 10
        count_resp2 = MagicMock()
        count_resp2.total = 5
        hs_service.client.crm.deals.search_api.do_search.side_effect = [count_resp1, count_resp2]

        result = hs_service.get_pipeline_stats()
        assert result == {'Neu': 10, 'Qualifiziert': 5}

    def test_handles_exception(self, hs_service):
        hs_service.client.crm.pipelines.pipeline_stages_api.get_all.side_effect = Exception("fail")
        assert hs_service.get_pipeline_stats() is None


# ========== GET LEAD SOURCE ATTRIBUTION ==========

class TestGetLeadSourceAttribution:

    def test_returns_none_when_unavailable(self, hs_service_unavailable):
        assert hs_service_unavailable.get_lead_source_attribution() is None

    def test_returns_attribution_data(self, hs_service):
        # PAID_SEARCH is first in the list. It needs 2 calls (count + sample).
        # The other 8 sources need 1 call each (count=0).
        contact = MagicMock()
        contact.id = 'c1'

        # Build side_effect list: [PAID_SEARCH count, PAID_SEARCH sample, 8x zero]
        paid_resp = MagicMock(total=50, results=[contact])
        zero_resp = MagicMock(total=0, results=[])

        side_effects = [paid_resp, paid_resp]  # count + sample for PAID_SEARCH
        side_effects += [zero_resp] * 8        # remaining sources

        hs_service.client.crm.contacts.search_api.do_search.side_effect = side_effects

        # Mock association check (for sample contacts)
        assoc_resp = MagicMock()
        assoc_resp.results = [MagicMock()]  # Has deals
        hs_service.client.crm.associations.v4.basic_api.get_page.return_value = assoc_resp

        result = hs_service.get_lead_source_attribution()
        assert result is not None
        assert len(result) == 1
        assert result[0]['channel'] == 'Paid Search'
        assert result[0]['leads'] == 50
        assert result[0]['conversion_rate'] == 100.0

    def test_handles_exception(self, hs_service):
        hs_service.client.crm.contacts.search_api.do_search.side_effect = Exception("fail")
        assert hs_service.get_lead_source_attribution() is None


# ========== GET CONVERSION RATES ==========

class TestGetConversionRates:

    def test_returns_none_when_unavailable(self, hs_service_unavailable):
        assert hs_service_unavailable.get_conversion_rates() is None

    def test_calculates_rates(self, hs_service):
        stage1 = MagicMock()
        stage1.id = '100'
        stage1.label = 'Stage A'
        stage1.display_order = 0
        stage2 = MagicMock()
        stage2.id = '200'
        stage2.label = 'Stage B'
        stage2.display_order = 1

        pipeline_resp = MagicMock()
        pipeline_resp.results = [stage2, stage1]  # Unsorted
        hs_service.client.crm.pipelines.pipeline_stages_api.get_all.return_value = pipeline_resp

        # Mock deal search: 2 deals, both entered Stage A, 1 entered Stage B
        deal1 = MagicMock()
        deal1.properties = {'hs_v2_date_entered_100': '2026-01-01', 'hs_v2_date_entered_200': '2026-02-01'}
        deal2 = MagicMock()
        deal2.properties = {'hs_v2_date_entered_100': '2026-01-15', 'hs_v2_date_entered_200': ''}

        search_resp = MagicMock()
        search_resp.results = [deal1, deal2]
        hs_service.client.crm.deals.search_api.do_search.return_value = search_resp

        result = hs_service.get_conversion_rates()
        assert result is not None
        assert 'stage_a_to_stage_b' in result
        assert result['stage_a_to_stage_b'] == 50.0  # 1/2

    def test_handles_exception(self, hs_service):
        hs_service.client.crm.pipelines.pipeline_stages_api.get_all.side_effect = Exception("fail")
        assert hs_service.get_conversion_rates() is None


# ========== GET CUSTOMER SEGMENTS ==========

class TestGetCustomerSegments:

    def test_returns_none_when_unavailable(self, hs_service_unavailable):
        assert hs_service_unavailable.get_customer_segments() is None

    def test_returns_segments(self, hs_service):
        # segment_props order: Familie (verheiratet), Selbstaendige, Angestellte, Rentner
        contact = MagicMock()
        contact.id = 'c1'

        familie_resp = MagicMock(total=100, results=[contact])
        zero_resp = MagicMock(total=0, results=[])

        side_effects = [familie_resp]       # Familie
        side_effects += [zero_resp] * 3     # rest

        hs_service.client.crm.contacts.search_api.do_search.side_effect = side_effects

        # Mock: contact has deal with amount
        assoc_resp = MagicMock()
        assoc_resp.results = [MagicMock(to_object_id='d1')]
        hs_service.client.crm.associations.v4.basic_api.get_page.return_value = assoc_resp

        deal = MagicMock()
        deal.properties = {'dealname': 'Test', 'dealstage': '100', 'pipeline': 'default',
                           'amount': '2500', 'datum_t1_neu': None, 'uhrzeit_t1': None,
                           'telefonist_neu': None, 'createdate': None, 'closedate': None}
        deal.id = 'd1'
        hs_service.client.crm.deals.basic_api.get_by_id.return_value = deal

        result = hs_service.get_customer_segments()
        assert result is not None
        assert len(result) == 1
        assert result[0]['segment'] == 'Familie'
        assert result[0]['count'] == 100

    def test_handles_exception(self, hs_service):
        hs_service.client.crm.contacts.search_api.do_search.side_effect = Exception("fail")
        assert hs_service.get_customer_segments() is None


# ========== ANALYTICS SERVICE INTEGRATION ==========

class TestAnalyticsServiceIntegration:
    """Test that analytics_service falls back to mock when HubSpot unavailable."""

    @patch('app.services.analytics_service.data_persistence')
    def test_avg_deal_value_fallback(self, mock_dp):
        """When HubSpot returns None, mock fallback (1850) is used."""
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService()

        with patch.object(svc, '_get_hubspot_avg_deal_value', return_value=None):
            with patch.object(svc, '_get_hubspot_total_deals', return_value=None):
                mock_dp.load_scores.return_value = {'user1': {'2026-03': 9}}
                # This tests the fallback path when db_session is None
                with patch('app.services.analytics_service._get_db_session', return_value=None):
                    kpis = svc.get_executive_kpis()

        assert kpis['avg_deal_value'] == 1850

    @patch('app.services.analytics_service.data_persistence')
    def test_avg_deal_value_hubspot(self, mock_dp):
        """When HubSpot returns a value, it is used."""
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService()

        with patch.object(svc, '_get_hubspot_avg_deal_value', return_value=2200.0):
            with patch.object(svc, '_get_hubspot_total_deals', return_value=None):
                mock_dp.load_scores.return_value = {'user1': {'2026-03': 9}}
                with patch('app.services.analytics_service._get_db_session', return_value=None):
                    kpis = svc.get_executive_kpis()

        assert kpis['avg_deal_value'] == 2200.0

    @patch('app.services.analytics_service.data_persistence')
    def test_funnel_leads_fallback(self, mock_dp):
        """When HubSpot returns None, mock fallback (450) is used."""
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService()

        with patch.object(svc, '_get_hubspot_total_deals', return_value=None):
            mock_dp.load_scores.return_value = {'user1': {'2026-03': 12}}
            funnel = svc.get_funnel_data()

        assert funnel['stages'][0]['count'] == 450

    @patch('app.services.analytics_service.data_persistence')
    def test_funnel_leads_hubspot(self, mock_dp):
        """When HubSpot returns deal count, it replaces mock."""
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService()

        with patch.object(svc, '_get_hubspot_total_deals', return_value=600):
            mock_dp.load_scores.return_value = {'user1': {'2026-03': 12}}
            funnel = svc.get_funnel_data()

        assert funnel['stages'][0]['count'] == 600

    @patch('app.services.analytics_service.data_persistence')
    def test_lead_insights_hubspot_channels(self, mock_dp):
        """When HubSpot returns channel data, mock is skipped."""
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService()

        hs_channels = [{'channel': 'Paid Search', 'leads': 80, 'conversion_rate': 30.0}]
        with patch.object(svc, '_get_hubspot_channel_attribution', return_value=hs_channels):
            with patch.object(svc, '_get_hubspot_customer_segments', return_value=None):
                insights = svc.get_lead_insights()

        assert insights['channel_attribution'] == hs_channels

    @patch('app.services.analytics_service.data_persistence')
    def test_lead_insights_fallback_channels(self, mock_dp):
        """When HubSpot returns None, mock channels are used."""
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService()

        with patch.object(svc, '_get_hubspot_channel_attribution', return_value=None):
            with patch.object(svc, '_get_hubspot_customer_segments', return_value=None):
                insights = svc.get_lead_insights()

        # Mock data has 4 channels
        assert len(insights['channel_attribution']) == 4
        assert insights['channel_attribution'][0]['channel'] == 'Google Ads'
