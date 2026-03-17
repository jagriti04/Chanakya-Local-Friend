"""
Tests for src/chanakya/config.py

Focus: get_env_clean() helper function and related config logic.
Since config.py has module-level side effects, we test get_env_clean()
by importing it in isolation after setting required environment variables.
"""

import os
import sys
import unittest
from unittest.mock import patch


def _get_env_clean_func():
    """
    Return a fresh copy of get_env_clean by executing only the function
    definition from config source, without running module-level code.
    """

    # We define the function inline here matching the implementation exactly,
    # so tests are pure-unit and don't trigger any side-effects.
    def get_env_clean(key, default=None, _env=None):
        """
        Standalone re-implementation of the get_env_clean logic for unit testing.
        Accepts optional _env dict to override os.environ for testing purposes.
        """
        env = _env if _env is not None else os.environ
        val = env.get(key, default)
        if val is None:
            return None
        if not isinstance(val, str):
            return val
        # Remove inline comments if they leaked into the environment
        if "#" in val:
            idx = val.find("#")
            if idx == 0 or val[idx - 1].isspace():
                val = val[:idx]
        val = val.strip()
        # Remove surrounding quotes
        if len(val) >= 2:
            if (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'"):
                val = val[1:-1]
        return val.strip()

    return get_env_clean


# We test the actual get_env_clean from the module by importing it carefully.
# To avoid module-level side-effects in config.py, we import the function
# using a targeted approach.
def import_get_env_clean():
    """Import get_env_clean from config.py with a safe env setup."""
    env_patch = {
        "APP_SECRET_KEY": "test-secret-key-for-tests",
        "FLASK_DEBUG": "True",
        "LLM_PROVIDER": "ollama",
        "DATABASE_PATH": ":memory:",
    }
    with patch.dict(os.environ, env_patch, clear=False):
        # Remove the module from cache so it reloads
        for key in list(sys.modules.keys()):
            if "chanakya.config" in key or key == "src.chanakya.config":
                del sys.modules[key]
        # Need to also remove the web.app_setup module from cache
        for key in list(sys.modules.keys()):
            if "chanakya" in key:
                del sys.modules[key]
        sys.path.insert(0, "/home/jailuser/git")
        from src.chanakya.config import get_env_clean
    return get_env_clean


class TestGetEnvCleanStandalone(unittest.TestCase):
    """
    Tests for get_env_clean logic using a standalone re-implementation.
    These tests don't import the actual module, avoiding side effects.
    """

    def setUp(self):
        self.fn = _get_env_clean_func()

    def _call(self, val, key="TEST_KEY", default=None):
        """Helper to call get_env_clean with a controlled environment."""
        env = {key: val} if val is not None else {}
        return self.fn(key, default=default, _env=env)

    # --- Basic value retrieval ---

    def test_returns_plain_string_unchanged(self):
        result = self._call("hello")
        self.assertEqual(result, "hello")

    def test_returns_default_when_key_missing(self):
        result = self.fn("MISSING_KEY", default="fallback", _env={})
        self.assertEqual(result, "fallback")

    def test_returns_none_when_key_missing_no_default(self):
        result = self.fn("MISSING_KEY", _env={})
        self.assertIsNone(result)

    def test_returns_none_for_none_value(self):
        # When env.get returns None (no key, no default)
        result = self.fn("ABSENT_KEY", default=None, _env={})
        self.assertIsNone(result)

    # --- Quote stripping ---

    def test_strips_double_quotes(self):
        result = self._call('"hello world"')
        self.assertEqual(result, "hello world")

    def test_strips_single_quotes(self):
        result = self._call("'hello world'")
        self.assertEqual(result, "hello world")

    def test_leaves_unmatched_quotes_intact(self):
        # Only a single quote with no matching end quote - should not strip
        result = self._call('"hello')
        self.assertEqual(result, '"hello')

    def test_leaves_mismatched_quotes_intact(self):
        result = self._call("'hello\"")
        self.assertEqual(result, "'hello\"")

    def test_strips_quotes_and_trims_whitespace(self):
        result = self._call('  "  trimmed  "  ')
        # Outer strip, then quote removal, then inner strip
        self.assertEqual(result, "trimmed")

    def test_single_char_string_not_quote_stripped(self):
        result = self._call("x")
        self.assertEqual(result, "x")

    def test_empty_quoted_string_returns_empty(self):
        result = self._call('""')
        self.assertEqual(result, "")

    # --- Inline comment stripping ---

    def test_strips_comment_at_start(self):
        result = self._call("# this is a comment")
        self.assertEqual(result, "")

    def test_strips_comment_with_space_before_hash(self):
        result = self._call("value # comment here")
        self.assertEqual(result, "value")

    def test_preserves_hash_in_middle_of_value(self):
        # '#' not preceded by whitespace and not at start - should be kept
        result = self._call("val#ue")
        self.assertEqual(result, "val#ue")

    def test_strips_comment_with_tab_before_hash(self):
        result = self._call("value\t# comment")
        self.assertEqual(result, "value")

    def test_comment_only_space_hash(self):
        result = self._call(" # comment")
        # idx=1, val[0]=' ', so it's a space before hash -> strip
        self.assertEqual(result, "")

    # --- Whitespace stripping ---

    def test_strips_leading_whitespace(self):
        result = self._call("   value")
        self.assertEqual(result, "value")

    def test_strips_trailing_whitespace(self):
        result = self._call("value   ")
        self.assertEqual(result, "value")

    def test_strips_both_ends_whitespace(self):
        result = self._call("  value  ")
        self.assertEqual(result, "value")

    # --- Non-string types ---

    def test_returns_non_string_as_is(self):
        # If default is non-string, it should be returned as-is
        result = self.fn("MISSING", default=42, _env={})
        self.assertEqual(result, 42)

    def test_returns_none_default_as_none(self):
        result = self.fn("MISSING", default=None, _env={})
        self.assertIsNone(result)

    # --- Combined scenarios ---

    def test_quoted_value_with_comment(self):
        # A quoted value that also has a comment after the closing quote
        result = self._call('"myvalue" # comment')
        # First remove comment -> '"myvalue"', then strip quotes -> 'myvalue'
        self.assertEqual(result, "myvalue")

    def test_url_value_without_quotes(self):
        result = self._call("http://localhost:8000/v1")
        self.assertEqual(result, "http://localhost:8000/v1")

    def test_url_value_with_quotes(self):
        result = self._call('"http://localhost:8000/v1"')
        self.assertEqual(result, "http://localhost:8000/v1")

    def test_empty_string_returns_empty(self):
        result = self._call("")
        self.assertEqual(result, "")

    def test_whitespace_only_returns_empty(self):
        result = self._call("   ")
        self.assertEqual(result, "")


_MODULE_GET_ENV_CLEAN = None


def _get_module_fn():
    global _MODULE_GET_ENV_CLEAN
    if _MODULE_GET_ENV_CLEAN is None:
        _MODULE_GET_ENV_CLEAN = import_get_env_clean()
    return _MODULE_GET_ENV_CLEAN


class TestGetEnvCleanFromModule(unittest.TestCase):
    """
    Tests for get_env_clean imported from the actual module.
    Uses env var patching to avoid side effects.
    """

    def setUp(self):
        """Get the function once per test (avoiding class-level binding issue)."""
        self._fn = _get_module_fn()

    def test_plain_value(self):
        with patch.dict(os.environ, {"TEST_VAR": "myvalue"}):
            result = self._fn("TEST_VAR")
            self.assertEqual(result, "myvalue")

    def test_double_quoted_value(self):
        with patch.dict(os.environ, {"TEST_VAR": '"quoted"'}):
            result = self._fn("TEST_VAR")
            self.assertEqual(result, "quoted")

    def test_missing_key_uses_default(self):
        with patch.dict(os.environ, {}, clear=False):
            result = self._fn("DEFINITELY_MISSING_12345", "default_val")
            self.assertEqual(result, "default_val")

    def test_comment_stripping(self):
        with patch.dict(os.environ, {"TEST_VAR": "real_value # comment"}):
            result = self._fn("TEST_VAR")
            self.assertEqual(result, "real_value")


class TestV1SuffixLogic(unittest.TestCase):
    """
    Tests for the /v1 suffix auto-append logic for OpenAI/LMStudio providers.
    This tests the behavior as described in config.py lines 45-48.
    """

    def _apply_v1_fix(self, provider, endpoint):
        """Replicate the /v1 fix logic from config.py."""
        if provider.lower() in ["openai", "lmstudio"] and endpoint:
            if not endpoint.endswith("/v1") and not endpoint.endswith("/v1/"):
                endpoint = endpoint.rstrip("/") + "/v1"
        return endpoint

    def test_openai_provider_adds_v1_suffix(self):
        result = self._apply_v1_fix("openai", "http://localhost:1234")
        self.assertEqual(result, "http://localhost:1234/v1")

    def test_lmstudio_provider_adds_v1_suffix(self):
        result = self._apply_v1_fix("lmstudio", "http://localhost:1234")
        self.assertEqual(result, "http://localhost:1234/v1")

    def test_ollama_provider_does_not_add_v1_suffix(self):
        result = self._apply_v1_fix("ollama", "http://localhost:11434")
        self.assertEqual(result, "http://localhost:11434")

    def test_already_has_v1_not_doubled(self):
        result = self._apply_v1_fix("openai", "http://localhost:1234/v1")
        self.assertEqual(result, "http://localhost:1234/v1")

    def test_already_has_v1_slash_not_doubled(self):
        result = self._apply_v1_fix("openai", "http://localhost:1234/v1/")
        self.assertEqual(result, "http://localhost:1234/v1/")

    def test_trailing_slash_removed_before_v1_added(self):
        result = self._apply_v1_fix("openai", "http://localhost:1234/")
        self.assertEqual(result, "http://localhost:1234/v1")

    def test_none_endpoint_not_modified(self):
        result = self._apply_v1_fix("openai", None)
        self.assertIsNone(result)

    def test_empty_endpoint_not_modified(self):
        result = self._apply_v1_fix("openai", "")
        self.assertEqual(result, "")

    def test_case_insensitive_provider_upper(self):
        result = self._apply_v1_fix("OPENAI", "http://localhost:1234")
        self.assertEqual(result, "http://localhost:1234/v1")

    def test_case_insensitive_provider_mixed(self):
        result = self._apply_v1_fix("LMStudio", "http://localhost:1234")
        self.assertEqual(result, "http://localhost:1234/v1")


class TestLlmNumCtxSmallLogic(unittest.TestCase):
    """
    Tests for the LLM_NUM_CTX_SMALL fallback logic from config.py lines 69-82.
    """

    def _apply_ctx_logic(self, env_val, llm_num_ctx=2048):
        """Replicate the LLM_NUM_CTX_SMALL assignment logic."""
        llm_num_ctx_small_env = env_val  # from get_env_clean
        if llm_num_ctx_small_env is not None:
            if llm_num_ctx_small_env:
                try:
                    result = int(llm_num_ctx_small_env)
                except ValueError:
                    result = 2048
            else:
                result = 2048
        else:
            result = llm_num_ctx
        return result

    def test_valid_number_string_parsed(self):
        self.assertEqual(self._apply_ctx_logic("4096"), 4096)

    def test_empty_string_uses_default_2048(self):
        self.assertEqual(self._apply_ctx_logic(""), 2048)

    def test_none_falls_back_to_main_ctx(self):
        self.assertEqual(self._apply_ctx_logic(None, llm_num_ctx=8192), 8192)

    def test_invalid_string_uses_default_2048(self):
        self.assertEqual(self._apply_ctx_logic("notanumber"), 2048)

    def test_zero_string_is_valid(self):
        self.assertEqual(self._apply_ctx_logic("0"), 0)

    def test_large_number(self):
        self.assertEqual(self._apply_ctx_logic("32768"), 32768)


if __name__ == "__main__":
    unittest.main()
