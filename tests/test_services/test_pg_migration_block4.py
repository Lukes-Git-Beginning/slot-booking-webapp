# -*- coding: utf-8 -*-
"""
Tests fuer PG-Migration Block 4 — Cosmetics + Avatar + Lootbox Dual-Write

Testet:
- CosmeticsShop.load_purchases: PG-first read
- CosmeticsShop.save_purchases: Dual-Write
- LootboxService._load_data / _save_data: PG Dual-Write
- AvatarService._load_avatars: PG-first read
"""

import pytest
import json
from unittest.mock import MagicMock, patch, mock_open

# Import service modules at module level so pytz is loaded before any mock_open patches
from app.services.cosmetics_shop import CosmeticsShop
from app.services.lootbox_service import LootboxService
from app.services.avatar_service import AvatarService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_shop():
    """Return a CosmeticsShop instance without touching real files."""
    shop = CosmeticsShop.__new__(CosmeticsShop)
    shop.purchases_file = "fake/purchases.json"
    shop.active_cosmetics_file = "fake/active.json"
    return shop


def _make_lootbox():
    """Return a LootboxService instance without touching real files."""
    svc = LootboxService.__new__(LootboxService)
    svc.lootbox_file = "fake/lootboxes.json"
    return svc


def _make_avatar():
    """Return an AvatarService instance without touching real files."""
    svc = AvatarService.__new__(AvatarService)
    svc.upload_dir = "fake/uploads"
    svc.shop_avatars_dir = "fake/avatars"
    svc.avatars_file = "fake/user_avatars.json"
    return svc


def _make_ctx(session):
    """Create a context manager mock wrapping session."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _make_error_ctx():
    """Create a context manager that raises on enter."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(side_effect=Exception("PG down"))
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# CosmeticsShop — load_purchases (PG-first)
# ---------------------------------------------------------------------------

class TestCosmeticsShopLoadPurchases:
    """Tests fuer load_purchases mit PG-first Logik."""

    def test_load_purchases_returns_pg_data_when_available(self):
        """Wenn PG verfuegbar ist, werden Daten aus PG gelesen."""
        shop = _make_shop()

        mock_row = MagicMock()
        mock_row.username = "alice"
        mock_row.item_id = "booking_rookie"
        mock_row.item_type = "title"

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_row]

        with patch('app.services.cosmetics_shop.USE_POSTGRES', True), \
             patch('app.services.cosmetics_shop.POSTGRES_AVAILABLE', True), \
             patch('app.services.cosmetics_shop.db_session_scope', return_value=_make_ctx(mock_session)):
            result = shop.load_purchases()

        assert "alice" in result
        assert "booking_rookie" in result["alice"]["titles"]

    def test_load_purchases_falls_back_to_json_on_pg_error(self):
        """Bei PG-Fehler wird JSON-Fallback benutzt."""
        shop = _make_shop()

        json_data = json.dumps({
            "bob": {"titles": ["coffee_addict"], "themes": [], "avatars": [],
                    "effects": [], "frames": [], "purchase_history": []}
        })

        with patch('app.services.cosmetics_shop.USE_POSTGRES', True), \
             patch('app.services.cosmetics_shop.POSTGRES_AVAILABLE', True), \
             patch('app.services.cosmetics_shop.db_session_scope', return_value=_make_error_ctx()), \
             patch('builtins.open', mock_open(read_data=json_data)):
            result = shop.load_purchases()

        assert "bob" in result
        assert "coffee_addict" in result["bob"]["titles"]

    def test_load_purchases_uses_json_when_postgres_disabled(self):
        """Mit USE_POSTGRES=False wird direkt JSON gelesen."""
        shop = _make_shop()

        json_data = json.dumps({
            "charlie": {"titles": ["early_bird"], "themes": [], "avatars": [],
                        "effects": [], "frames": [], "purchase_history": []}
        })

        with patch('app.services.cosmetics_shop.USE_POSTGRES', False), \
             patch('builtins.open', mock_open(read_data=json_data)):
            result = shop.load_purchases()

        assert "charlie" in result


# ---------------------------------------------------------------------------
# CosmeticsShop — save_purchases (Dual-Write)
# ---------------------------------------------------------------------------

class TestCosmeticsShopSavePurchases:
    """Tests fuer save_purchases Dual-Write."""

    def test_save_purchases_writes_to_pg_and_json(self):
        """Dual-Write: sowohl PG als auch JSON werden beschrieben."""
        shop = _make_shop()

        data = {
            "alice": {"titles": ["booking_rookie"], "themes": [], "avatars": [],
                      "effects": [], "frames": [], "purchase_history": []}
        }

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        m = mock_open()
        with patch('app.services.cosmetics_shop.USE_POSTGRES', True), \
             patch('app.services.cosmetics_shop.POSTGRES_AVAILABLE', True), \
             patch('app.services.cosmetics_shop.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('builtins.open', m):
            shop.save_purchases(data)

        # PG: session.add called for new cosmetic row
        assert mock_session.add.called
        # JSON write happened
        assert m.called

    def test_save_purchases_json_write_always_happens_on_pg_error(self):
        """JSON-Write findet auch bei PG-Fehler statt."""
        shop = _make_shop()

        data = {
            "dave": {"titles": ["night_owl"], "themes": [], "avatars": [],
                     "effects": [], "frames": [], "purchase_history": []}
        }

        m = mock_open()
        with patch('app.services.cosmetics_shop.USE_POSTGRES', True), \
             patch('app.services.cosmetics_shop.POSTGRES_AVAILABLE', True), \
             patch('app.services.cosmetics_shop.db_session_scope', return_value=_make_error_ctx()), \
             patch('builtins.open', m):
            shop.save_purchases(data)

        # JSON must still be written despite PG failure
        assert m.called


# ---------------------------------------------------------------------------
# LootboxService — _load_data / _save_data (PG Dual-Write)
# ---------------------------------------------------------------------------

class TestLootboxServicePG:
    """Tests fuer LootboxService PG Dual-Write."""

    def test_load_data_returns_pg_data(self):
        """_load_data liest aus PG wenn verfuegbar."""
        svc = _make_lootbox()

        mock_row = MagicMock()
        mock_row.username = "eve"
        mock_row.crates = [{"id": "abc123", "type": "common"}]
        mock_row.history = []
        mock_row.pity_counter = 3

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [mock_row]

        with patch('app.services.lootbox_service.USE_POSTGRES', True), \
             patch('app.services.lootbox_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.lootbox_service.db_session_scope', return_value=_make_ctx(mock_session)):
            result = svc._load_data()

        assert "eve" in result
        assert result["eve"]["pity_counter"] == 3
        assert len(result["eve"]["crates"]) == 1

    def test_load_data_json_fallback_on_pg_error(self):
        """_load_data faellt auf JSON zurueck wenn PG fehlschlaegt."""
        svc = _make_lootbox()

        with patch('app.services.lootbox_service.USE_POSTGRES', True), \
             patch('app.services.lootbox_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.lootbox_service.db_session_scope', return_value=_make_error_ctx()), \
             patch('app.services.lootbox_service.atomic_read_json',
                   return_value={"frank": {"crates": [], "history": [], "pity_counter": 0}}):
            result = svc._load_data()

        assert "frank" in result

    def test_save_data_upserts_to_pg_and_json(self):
        """_save_data schreibt nach PG (upsert) und JSON."""
        svc = _make_lootbox()

        data = {"grace": {"crates": [], "history": [], "pity_counter": 5}}

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        mock_write = MagicMock()
        with patch('app.services.lootbox_service.USE_POSTGRES', True), \
             patch('app.services.lootbox_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.lootbox_service.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.lootbox_service.atomic_write_json', mock_write):
            svc._save_data(data)

        assert mock_session.add.called
        mock_write.assert_called_once()

    def test_save_data_updates_existing_pg_row(self):
        """_save_data aktualisiert bestehende PG-Zeile (kein add)."""
        svc = _make_lootbox()

        data = {"henry": {"crates": [{"id": "xyz"}], "history": [], "pity_counter": 2}}

        existing_row = MagicMock()
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = existing_row

        with patch('app.services.lootbox_service.USE_POSTGRES', True), \
             patch('app.services.lootbox_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.lootbox_service.db_session_scope', return_value=_make_ctx(mock_session)), \
             patch('app.services.lootbox_service.atomic_write_json', MagicMock()):
            svc._save_data(data)

        assert existing_row.crates == [{"id": "xyz"}]
        assert existing_row.pity_counter == 2
        # No new row inserted
        assert not mock_session.add.called


# ---------------------------------------------------------------------------
# AvatarService — _load_avatars (PG-first)
# ---------------------------------------------------------------------------

class TestAvatarServiceLoadAvatars:
    """Tests fuer AvatarService._load_avatars PG-first Logik."""

    def test_load_avatars_returns_pg_data(self):
        """_load_avatars liest aus PG wenn verfuegbar."""
        svc = _make_avatar()

        mock_row = MagicMock()
        mock_row.username = "ivan"
        mock_row.config = {"type": "upload", "url": "/static/uploads/avatars/ivan.webp"}
        mock_row.updated_at = None

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_row]

        with patch('app.services.avatar_service.USE_POSTGRES', True), \
             patch('app.services.avatar_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.avatar_service.db_session_scope', return_value=_make_ctx(mock_session)):
            result = svc._load_avatars()

        assert "ivan" in result
        assert result["ivan"]["type"] == "upload"
        assert result["ivan"]["path"] == "/static/uploads/avatars/ivan.webp"

    def test_load_avatars_falls_back_to_json_on_pg_error(self):
        """_load_avatars faellt auf JSON zurueck bei PG-Fehler."""
        svc = _make_avatar()

        json_data = json.dumps({
            "julia": {"type": "shop", "path": "/static/avatars/business_female.png", "updated_at": ""}
        })

        with patch('app.services.avatar_service.USE_POSTGRES', True), \
             patch('app.services.avatar_service.POSTGRES_AVAILABLE', True), \
             patch('app.services.avatar_service.db_session_scope', return_value=_make_error_ctx()), \
             patch('builtins.open', mock_open(read_data=json_data)):
            result = svc._load_avatars()

        assert "julia" in result
        assert result["julia"]["type"] == "shop"

    def test_load_avatars_uses_json_when_postgres_disabled(self):
        """_load_avatars liest direkt JSON wenn USE_POSTGRES=False."""
        svc = _make_avatar()

        json_data = json.dumps({
            "kim": {"type": "upload", "path": "/static/uploads/avatars/kim.webp", "updated_at": ""}
        })

        with patch('app.services.avatar_service.USE_POSTGRES', False), \
             patch('builtins.open', mock_open(read_data=json_data)):
            result = svc._load_avatars()

        assert "kim" in result
