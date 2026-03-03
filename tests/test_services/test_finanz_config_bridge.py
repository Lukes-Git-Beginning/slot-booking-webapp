# -*- coding: utf-8 -*-
"""
Finanzberatung Config Bridge Tests

Verifies that:
1. FinanzConfig path helpers produce correct paths (no 'persistent' segment)
2. Path alignment: get_file_path() matches the formula used in store_file()
3. Regression guard: zero current_app.config.get() calls in all finanz services
4. All 5 previously-broken services import from app.config.base at module level
5. FINANZ_LLM_ENABLED reads actual environment variable

These tests intentionally run WITHOUT a Flask app context to prove
the config bridge works outside request context.
"""

import glob
import os
import unittest
from unittest.mock import patch


class TestFinanzConfigPathHelpers(unittest.TestCase):
    """Tests for FinanzConfig path helper classmethods."""

    def setUp(self):
        from app.config.base import Config, FinanzConfig
        self.Config = Config
        self.FinanzConfig = FinanzConfig

    def test_get_upload_dir_contains_persist_base(self):
        """get_upload_dir() must include PERSIST_BASE in the path."""
        result = self.FinanzConfig.get_upload_dir(42)
        assert self.Config.PERSIST_BASE in result, (
            f"Expected PERSIST_BASE '{self.Config.PERSIST_BASE}' in path '{result}'"
        )

    def test_get_upload_dir_contains_upload_dir_name(self):
        """get_upload_dir() must include FINANZ_UPLOAD_DIR in the path."""
        result = self.FinanzConfig.get_upload_dir(42)
        assert self.FinanzConfig.FINANZ_UPLOAD_DIR in result, (
            f"Expected FINANZ_UPLOAD_DIR '{self.FinanzConfig.FINANZ_UPLOAD_DIR}' in path '{result}'"
        )

    def test_get_upload_dir_contains_session_id_as_string(self):
        """get_upload_dir() must include session_id converted to string."""
        result = self.FinanzConfig.get_upload_dir(42)
        assert "42" in result, f"Expected '42' in path '{result}'"

    def test_get_upload_dir_no_persistent_segment(self):
        """get_upload_dir() must NOT contain the old erroneous 'persistent' path segment."""
        result = self.FinanzConfig.get_upload_dir(42)
        # Split path to check for exact segment 'persistent'
        parts = result.replace("\\", "/").split("/")
        assert "persistent" not in parts, (
            f"Path must not contain 'persistent' segment. Got: '{result}'"
        )

    def test_get_upload_dir_accepts_int_session_id(self):
        """get_upload_dir() accepts int session_id and produces string in path."""
        result = self.FinanzConfig.get_upload_dir(99)
        assert "99" in result

    def test_get_file_path_ends_with_session_and_filename(self):
        """get_file_path(42, 'doc.pdf') must produce path ending in 42/doc.pdf."""
        result = self.FinanzConfig.get_file_path(42, "doc.pdf")
        normalized = result.replace("\\", "/")
        assert normalized.endswith("42/doc.pdf"), (
            f"Expected path ending in '42/doc.pdf', got: '{result}'"
        )

    def test_get_file_path_no_persistent_segment(self):
        """get_file_path() must NOT contain the old erroneous 'persistent' path segment."""
        result = self.FinanzConfig.get_file_path(42, "test.pdf")
        parts = result.replace("\\", "/").split("/")
        assert "persistent" not in parts, (
            f"Path must not contain 'persistent' segment. Got: '{result}'"
        )

    def test_get_chromadb_path_contains_persist_base(self):
        """get_chromadb_path() must include PERSIST_BASE."""
        result = self.FinanzConfig.get_chromadb_path()
        assert self.Config.PERSIST_BASE in result, (
            f"Expected PERSIST_BASE in chroma path '{result}'"
        )

    def test_get_chromadb_path_contains_chroma_db(self):
        """get_chromadb_path() must contain 'chroma_db'."""
        result = self.FinanzConfig.get_chromadb_path()
        assert "chroma_db" in result, f"Expected 'chroma_db' in path '{result}'"

    def test_get_chromadb_path_no_persistent_segment(self):
        """get_chromadb_path() must NOT contain the 'persistent' segment."""
        result = self.FinanzConfig.get_chromadb_path()
        parts = result.replace("\\", "/").split("/")
        assert "persistent" not in parts, (
            f"Path must not contain 'persistent' segment. Got: '{result}'"
        )


class TestPathAlignment(unittest.TestCase):
    """
    Verify that the path produced by get_file_path() matches the
    manually constructed expected path — proving DSGVO deletion
    and upload storage use the same path formula.
    """

    def test_get_file_path_matches_manual_construction(self):
        """
        Path from get_file_path() must exactly match:
        os.path.join(Config.PERSIST_BASE, FinanzConfig.FINANZ_UPLOAD_DIR, str(session_id), filename)
        """
        from app.config.base import Config, FinanzConfig

        session_id = 42
        filename = "abc123.pdf"

        expected = os.path.join(
            Config.PERSIST_BASE,
            FinanzConfig.FINANZ_UPLOAD_DIR,
            str(session_id),
            filename,
        )
        actual = FinanzConfig.get_file_path(session_id, filename)

        assert actual == expected, (
            f"Path mismatch!\n"
            f"  Expected (manual): {expected}\n"
            f"  Actual (helper):   {actual}"
        )

    def test_get_upload_dir_matches_manual_construction(self):
        """
        Path from get_upload_dir() must exactly match:
        os.path.join(Config.PERSIST_BASE, FinanzConfig.FINANZ_UPLOAD_DIR, str(session_id))
        """
        from app.config.base import Config, FinanzConfig

        session_id = 7

        expected = os.path.join(
            Config.PERSIST_BASE,
            FinanzConfig.FINANZ_UPLOAD_DIR,
            str(session_id),
        )
        actual = FinanzConfig.get_upload_dir(session_id)

        assert actual == expected, (
            f"Upload dir mismatch!\n"
            f"  Expected: {expected}\n"
            f"  Actual:   {actual}"
        )


class TestConfigBridgeRegression(unittest.TestCase):
    """
    Regression guard: verify that no finanz service file contains
    'current_app.config.get' and all previously-broken services
    use direct FinanzConfig class imports.
    """

    def _get_finanz_service_files(self):
        """Return list of absolute paths to all app/services/finanz_*.py files."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        pattern = os.path.join(project_root, "app", "services", "finanz_*.py")
        files = glob.glob(pattern)
        assert len(files) > 0, "No finanz_*.py files found — check project structure"
        return files

    def test_no_current_app_config_get_in_any_finanz_service(self):
        """
        REGRESSION GUARD: Zero finanz service files must contain
        'current_app.config.get'. This prevents re-introducing the
        broken Flask config access pattern.
        """
        offending_files = []
        for fpath in self._get_finanz_service_files():
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            if "current_app.config.get" in content:
                offending_files.append(os.path.basename(fpath))

        assert offending_files == [], (
            f"Found 'current_app.config.get' in these finanz service files "
            f"(must be zero): {offending_files}"
        )

    def test_previously_broken_services_have_config_import(self):
        """
        All 5 previously-broken services must import from app.config.base
        at module level (not inside method bodies).
        """
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        services_dir = os.path.join(project_root, "app", "services")

        # These 5 were previously reading config via current_app
        previously_broken = [
            "finanz_dsgvo_service.py",
            "finanz_extraction_service.py",
            "finanz_classification_service.py",
            "finanz_field_extraction_service.py",
            "finanz_embedding_service.py",
        ]

        missing_import = []
        for fname in previously_broken:
            fpath = os.path.join(services_dir, fname)
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            if "from app.config.base import" not in content:
                missing_import.append(fname)

        assert missing_import == [], (
            f"These services are missing 'from app.config.base import': {missing_import}"
        )

    def test_dsgvo_service_uses_finanz_config_get_file_path(self):
        """
        finanz_dsgvo_service.py must call finanz_config.get_file_path
        (the DSGVO path bug fix).
        """
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        fpath = os.path.join(
            project_root, "app", "services", "finanz_dsgvo_service.py"
        )
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        assert "finanz_config.get_file_path" in content, (
            "finanz_dsgvo_service.py must use finanz_config.get_file_path() "
            "for correct DSGVO file deletion paths"
        )

    def test_upload_service_uses_finanz_config_get_upload_dir(self):
        """
        finanz_upload_service.py must call finanz_config.get_upload_dir
        (migrated to use path helper).
        """
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        fpath = os.path.join(
            project_root, "app", "services", "finanz_upload_service.py"
        )
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        assert "finanz_config.get_upload_dir" in content, (
            "finanz_upload_service.py must use finanz_config.get_upload_dir() "
            "as the path helper"
        )


class TestLLMEnabledEnvVar(unittest.TestCase):
    """Verify FINANZ_LLM_ENABLED reads from actual environment variable."""

    def test_finanz_llm_enabled_default_is_false(self):
        """Default value of FINANZ_LLM_ENABLED is False when env var not set."""
        from app.config.base import FinanzConfig
        with patch.dict(os.environ, {}, clear=False):
            # Without FINANZ_LLM_ENABLED set, default should be False
            # (FinanzConfig is a class with class-level attributes evaluated at import,
            #  so we test the default value directly)
            assert FinanzConfig.FINANZ_LLM_ENABLED is False or \
                   FinanzConfig.FINANZ_LLM_ENABLED == 0, \
                   f"Expected False, got {FinanzConfig.FINANZ_LLM_ENABLED}"

    def test_finanz_llm_enabled_reads_env_at_class_definition(self):
        """
        FINANZ_LLM_ENABLED is a class attribute read at import time from env.
        Verify get_env_bool() correctly parses the env var.
        """
        from app.config.base import get_env_bool

        with patch.dict(os.environ, {"FINANZ_LLM_ENABLED": "true"}):
            assert get_env_bool("FINANZ_LLM_ENABLED", False) is True

        with patch.dict(os.environ, {"FINANZ_LLM_ENABLED": "false"}):
            assert get_env_bool("FINANZ_LLM_ENABLED", False) is False

        with patch.dict(os.environ, {"FINANZ_LLM_ENABLED": "1"}):
            assert get_env_bool("FINANZ_LLM_ENABLED", False) is True

    def test_get_env_bool_false_variants(self):
        """get_env_bool returns False for '0', 'no', 'false'."""
        from app.config.base import get_env_bool

        for val in ("0", "no", "false", "False", "NO"):
            with patch.dict(os.environ, {"FINANZ_LLM_ENABLED": val}):
                result = get_env_bool("FINANZ_LLM_ENABLED", True)
                assert result is False, f"Expected False for env value '{val}', got {result}"


if __name__ == "__main__":
    unittest.main()
