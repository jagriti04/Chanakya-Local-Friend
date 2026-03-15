"""
Tests for src/chanakya/services/config_loader.py

Focus: load_mcp_config_internal() function.
Tests file existence checks, JSON parsing, mcpServers extraction, and error handling.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/home/jailuser/git")


def get_load_mcp_config_internal():
    """
    Import load_mcp_config_internal from the actual module,
    with Flask app mocked to avoid side effects.
    """
    # Set up required env vars before any import
    os.environ.setdefault("APP_SECRET_KEY", "test-secret-loader")
    os.environ.setdefault("FLASK_DEBUG", "True")
    os.environ.setdefault("DATABASE_PATH", ":memory:")
    os.environ.setdefault("LLM_PROVIDER", "ollama")

    # Clear chanakya modules from cache
    for key in list(sys.modules.keys()):
        if "chanakya" in key:
            del sys.modules[key]

    from src.chanakya.services.config_loader import load_mcp_config_internal
    return load_mcp_config_internal


# Standalone reimplementation to test the logic without module import issues
def load_mcp_config_standalone(filename: str) -> dict:
    """
    Standalone reimplementation of load_mcp_config_internal logic for isolated testing.
    """
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r") as f:
            config_data = json.load(f)
        return config_data.get("mcpServers", {})
    except Exception:
        return {}


class TestLoadMcpConfigStandalone(unittest.TestCase):
    """Tests of the config loading logic in isolation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_config(self, data: dict, filename: str = "mcp_config.json") -> str:
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, "w") as f:
            json.dump(data, f)
        return filepath

    # --- File not found ---

    def test_returns_empty_dict_when_file_not_found(self):
        result = load_mcp_config_standalone("/nonexistent/path/config.json")
        self.assertEqual(result, {})

    # --- Valid mcpServers ---

    def test_returns_mcp_servers_from_valid_config(self):
        data = {
            "mcpServers": {
                "brave-search": {
                    "command": "npx",
                    "args": ["@modelcontextprotocol/server-brave-search"],
                    "env": {"BRAVE_API_KEY": "test123"},
                }
            }
        }
        filepath = self._write_config(data)
        result = load_mcp_config_standalone(filepath)
        self.assertIn("brave-search", result)
        self.assertEqual(result["brave-search"]["command"], "npx")

    def test_returns_empty_dict_when_no_mcp_servers_key(self):
        data = {"otherKey": {"some": "data"}}
        filepath = self._write_config(data)
        result = load_mcp_config_standalone(filepath)
        self.assertEqual(result, {})

    def test_returns_empty_dict_when_mcp_servers_is_empty(self):
        data = {"mcpServers": {}}
        filepath = self._write_config(data)
        result = load_mcp_config_standalone(filepath)
        self.assertEqual(result, {})

    def test_multiple_servers_all_returned(self):
        data = {
            "mcpServers": {
                "server1": {"command": "cmd1", "args": []},
                "server2": {"command": "cmd2", "args": ["arg1"]},
            }
        }
        filepath = self._write_config(data)
        result = load_mcp_config_standalone(filepath)
        self.assertEqual(len(result), 2)
        self.assertIn("server1", result)
        self.assertIn("server2", result)

    # --- Invalid JSON ---

    def test_returns_empty_dict_for_invalid_json(self):
        filepath = os.path.join(self.temp_dir, "bad.json")
        with open(filepath, "w") as f:
            f.write("this is not valid JSON {{{")
        result = load_mcp_config_standalone(filepath)
        self.assertEqual(result, {})

    def test_returns_empty_dict_for_empty_file(self):
        filepath = os.path.join(self.temp_dir, "empty.json")
        with open(filepath, "w") as f:
            f.write("")
        result = load_mcp_config_standalone(filepath)
        self.assertEqual(result, {})

    # --- Server config details preserved ---

    def test_server_env_dict_preserved(self):
        data = {
            "mcpServers": {
                "weather": {
                    "command": "python",
                    "args": ["weather_server.py"],
                    "env": {"ACCUWEATHER_API_KEY": "key123", "OTHER_VAR": "val"},
                }
            }
        }
        filepath = self._write_config(data)
        result = load_mcp_config_standalone(filepath)
        self.assertEqual(result["weather"]["env"]["ACCUWEATHER_API_KEY"], "key123")

    def test_server_transport_field_preserved(self):
        data = {
            "mcpServers": {
                "maps": {
                    "command": "node",
                    "args": ["maps_server.js"],
                    "transport": "stdio",
                }
            }
        }
        filepath = self._write_config(data)
        result = load_mcp_config_standalone(filepath)
        self.assertEqual(result["maps"]["transport"], "stdio")


_MODULE_LOAD_FN = None
_MODULE_TEMP_DIR = None


def _get_module_load_fn():
    global _MODULE_LOAD_FN, _MODULE_TEMP_DIR
    if _MODULE_LOAD_FN is None:
        _MODULE_LOAD_FN = get_load_mcp_config_internal()
        _MODULE_TEMP_DIR = tempfile.mkdtemp()
    return _MODULE_LOAD_FN, _MODULE_TEMP_DIR


class TestLoadMcpConfigFromModule(unittest.TestCase):
    """
    Tests for load_mcp_config_internal imported from the actual module.
    """

    def setUp(self):
        self._fn, self.temp_dir = _get_module_load_fn()

    @classmethod
    def tearDownClass(cls):
        import shutil
        if _MODULE_TEMP_DIR:
            shutil.rmtree(_MODULE_TEMP_DIR, ignore_errors=True)

    def _write_config(self, data: dict, filename: str = "mcp_test.json") -> str:
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, "w") as f:
            json.dump(data, f)
        return filepath

    def test_returns_empty_for_nonexistent_file(self):
        result = self._fn("/nonexistent/path/config.json")
        self.assertEqual(result, {})

    def test_returns_mcp_servers_from_valid_config(self):
        data = {
            "mcpServers": {
                "test-server": {
                    "command": "python",
                    "args": ["test.py"],
                }
            }
        }
        filepath = self._write_config(data)
        result = self._fn(filepath)
        self.assertIn("test-server", result)

    def test_returns_empty_for_invalid_json(self):
        filepath = os.path.join(self.temp_dir, "invalid.json")
        with open(filepath, "w") as f:
            f.write("{ not json }")
        result = self._fn(filepath)
        self.assertEqual(result, {})

    def test_returns_empty_when_no_mcp_servers_key(self):
        data = {"other": "data"}
        filepath = self._write_config(data, "no_mcp.json")
        result = self._fn(filepath)
        self.assertEqual(result, {})

    def test_mcp_config_filename_constant_is_string(self):
        """MCP_CONFIG_FILENAME should be a string path."""
        # Clear cache and reimport to check the constant
        for key in list(sys.modules.keys()):
            if "chanakya" in key:
                del sys.modules[key]
        from src.chanakya.services.config_loader import MCP_CONFIG_FILENAME
        self.assertIsInstance(MCP_CONFIG_FILENAME, str)
        self.assertIn("mcp_config_file.json", MCP_CONFIG_FILENAME)


if __name__ == "__main__":
    unittest.main()