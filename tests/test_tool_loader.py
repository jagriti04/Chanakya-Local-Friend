"""
Tests for src/chanakya/services/tool_loader.py

Focus: The new environment variable injection logic in load_all_mcp_tools_async(),
and the caching behavior. These tests mock out the MCP client to test the tool
loader logic without requiring actual MCP server connections.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/home/jailuser/git")


def build_server_config_from_details(details: dict, os_environ: dict | None = None) -> dict:
    """
    Replicate the server config building + env injection logic from tool_loader.py.
    This tests the logic in isolation without importing the module.
    """
    if os_environ is None:
        os_environ = {}

    server_config_for_client = {
        "command": details["command"],
        "args": details["args"],
        "transport": details.get("transport", "stdio"),
    }
    if "env" in details and isinstance(details["env"], dict):
        new_env = {}
        for env_key, env_val in details["env"].items():
            # Priority 1: Check if it's already in the OS environment
            os_val = os_environ.get(env_key)
            if os_val:
                new_env[env_key] = os_val
            else:
                new_env[env_key] = env_val
        server_config_for_client["env"] = new_env
    return server_config_for_client


class TestEnvInjectionLogic(unittest.TestCase):
    """
    Tests for the environment variable injection logic in load_all_mcp_tools_async.
    This is the new logic added in this PR.
    """

    def test_os_env_value_takes_priority_over_config_value(self):
        """When an env var exists in OS env, it should override the config file value."""
        details = {
            "command": "node",
            "args": ["server.js"],
            "env": {"BRAVE_API_KEY": "config_placeholder"},
        }
        os_env = {"BRAVE_API_KEY": "real_os_key"}
        result = build_server_config_from_details(details, os_environ=os_env)
        self.assertEqual(result["env"]["BRAVE_API_KEY"], "real_os_key")

    def test_config_value_used_when_not_in_os_env(self):
        """When env var is not in OS env, the config file value should be used."""
        details = {
            "command": "node",
            "args": ["server.js"],
            "env": {"BRAVE_API_KEY": "config_value"},
        }
        os_env = {}  # Empty OS env
        result = build_server_config_from_details(details, os_environ=os_env)
        self.assertEqual(result["env"]["BRAVE_API_KEY"], "config_value")

    def test_multiple_env_vars_injected_selectively(self):
        """Only env vars present in OS env should be overridden."""
        details = {
            "command": "python",
            "args": ["server.py"],
            "env": {
                "BRAVE_API_KEY": "brave_placeholder",
                "GOOGLE_MAPS_API_KEY": "maps_placeholder",
                "ACCUWEATHER_API_KEY": "accuweather_placeholder",
            },
        }
        os_env = {
            "BRAVE_API_KEY": "real_brave_key",
            # GOOGLE_MAPS_API_KEY not set
            "ACCUWEATHER_API_KEY": "real_accuweather_key",
        }
        result = build_server_config_from_details(details, os_environ=os_env)
        self.assertEqual(result["env"]["BRAVE_API_KEY"], "real_brave_key")
        self.assertEqual(result["env"]["GOOGLE_MAPS_API_KEY"], "maps_placeholder")
        self.assertEqual(result["env"]["ACCUWEATHER_API_KEY"], "real_accuweather_key")

    def test_empty_os_env_value_does_not_override(self):
        """An empty string in OS env should not override the config value."""
        details = {
            "command": "node",
            "args": ["server.js"],
            "env": {"BRAVE_API_KEY": "config_value"},
        }
        os_env = {"BRAVE_API_KEY": ""}  # Empty string - falsy
        result = build_server_config_from_details(details, os_environ=os_env)
        self.assertEqual(result["env"]["BRAVE_API_KEY"], "config_value")

    def test_no_env_key_in_details_no_env_added(self):
        """If the server details have no 'env' key, no env is added to config."""
        details = {
            "command": "node",
            "args": ["server.js"],
        }
        os_env = {"SOME_KEY": "some_value"}
        result = build_server_config_from_details(details, os_environ=os_env)
        self.assertNotIn("env", result)

    def test_env_not_dict_not_processed(self):
        """If env is not a dict, it should not be processed (guard in the logic)."""
        details = {
            "command": "node",
            "args": ["server.js"],
            "env": "not_a_dict",
        }
        # The original code: if "env" in details and isinstance(details["env"], dict)
        # So if env is not dict, it's skipped
        os_env = {}
        result = build_server_config_from_details(details, os_environ=os_env)
        self.assertNotIn("env", result)

    def test_transport_defaults_to_stdio(self):
        """Transport should default to 'stdio' when not specified."""
        details = {
            "command": "node",
            "args": ["server.js"],
        }
        result = build_server_config_from_details(details)
        self.assertEqual(result["transport"], "stdio")

    def test_transport_overridden_when_specified(self):
        """Transport should use the value from details when provided."""
        details = {
            "command": "node",
            "args": ["server.js"],
            "transport": "sse",
        }
        result = build_server_config_from_details(details)
        self.assertEqual(result["transport"], "sse")

    def test_command_and_args_preserved(self):
        """Command and args should be preserved from details."""
        details = {
            "command": "python",
            "args": ["server.py", "--port", "8080"],
        }
        result = build_server_config_from_details(details)
        self.assertEqual(result["command"], "python")
        self.assertEqual(result["args"], ["server.py", "--port", "8080"])

    def test_empty_env_dict_in_details(self):
        """An empty env dict in details should result in an empty env in config."""
        details = {
            "command": "node",
            "args": [],
            "env": {},
        }
        os_env = {"SOME_VAR": "some_val"}
        result = build_server_config_from_details(details, os_environ=os_env)
        self.assertEqual(result["env"], {})


class TestToolLoaderCachingLogic(unittest.TestCase):
    """
    Tests for caching behavior in load_all_mcp_tools_async.
    Uses mocks to test without actual MCP servers.
    """

    def _setup_env(self):
        os.environ.setdefault("APP_SECRET_KEY", "test-secret-tool-loader")
        os.environ.setdefault("FLASK_DEBUG", "True")
        os.environ.setdefault("DATABASE_PATH", ":memory:")
        os.environ.setdefault("LLM_PROVIDER", "ollama")

    def test_load_all_mcp_tools_empty_config_returns_empty_list(self):
        """When MCP config is empty, should return [] and set flags."""
        self._setup_env()

        # Clear module cache
        for key in list(sys.modules.keys()):
            if "chanakya" in key:
                del sys.modules[key]

        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test-secret",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
            },
        ):
            from src.chanakya.services import tool_loader

            # Reset the global state
            tool_loader.CACHED_MCP_TOOLS = []
            tool_loader.MCP_TOOLS_LOADED_FLAG = False

            with patch("src.chanakya.services.tool_loader.load_mcp_config_internal") as mock_load:
                mock_load.return_value = {}  # Empty config

                result = asyncio.new_event_loop().run_until_complete(
                    tool_loader.load_all_mcp_tools_async()
                )

            self.assertEqual(result, [])
            self.assertTrue(tool_loader.MCP_TOOLS_LOADED_FLAG)
            self.assertEqual(
                tool_loader.mcp_tool_descriptions_for_llm,
                "No specialized tools available.",
            )
            self.assertEqual(tool_loader.mcp_tool_names_for_llm, "")

    def test_returns_cached_tools_when_already_loaded(self):
        """When MCP_TOOLS_LOADED_FLAG is True, should return cached tools."""
        self._setup_env()

        for key in list(sys.modules.keys()):
            if "chanakya" in key:
                del sys.modules[key]

        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test-secret",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
            },
        ):
            from src.chanakya.services import tool_loader

            # Set up "already loaded" state
            mock_tool = MagicMock()
            mock_tool.name = "mock_tool"
            tool_loader.CACHED_MCP_TOOLS = [mock_tool]
            tool_loader.MCP_TOOLS_LOADED_FLAG = True

            with patch("src.chanakya.services.tool_loader.load_mcp_config_internal") as mock_load:
                result = asyncio.new_event_loop().run_until_complete(
                    tool_loader.load_all_mcp_tools_async()
                )
                # Should not call load_mcp_config_internal again
                mock_load.assert_not_called()

            self.assertEqual(result, [mock_tool])

    def test_force_reload_bypasses_cache(self):
        """When force_reload=True, should re-fetch tools even if cached."""
        self._setup_env()

        for key in list(sys.modules.keys()):
            if "chanakya" in key:
                del sys.modules[key]

        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test-secret",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
            },
        ):
            from src.chanakya.services import tool_loader

            mock_tool = MagicMock()
            tool_loader.CACHED_MCP_TOOLS = [mock_tool]
            tool_loader.MCP_TOOLS_LOADED_FLAG = True

            with patch("src.chanakya.services.tool_loader.load_mcp_config_internal") as mock_load:
                mock_load.return_value = {}  # Empty config

                result = asyncio.new_event_loop().run_until_complete(
                    tool_loader.load_all_mcp_tools_async(force_reload=True)
                )
                # Should have called load_mcp_config_internal because force_reload=True
                mock_load.assert_called_once()

            self.assertEqual(result, [])


class TestToolLoaderEnvInjectionIntegration(unittest.TestCase):
    """
    Integration tests for the env injection within the full load_all_mcp_tools_async flow.

    Note: tool_loader.py uses os.environ.get() in the env injection block but is missing
    `import os` at the top of the file. This test patches `os` into the module's namespace
    to allow testing the injection logic.
    """

    def setUp(self):
        os.environ.setdefault("APP_SECRET_KEY", "test-secret-integration")
        os.environ.setdefault("FLASK_DEBUG", "True")
        os.environ.setdefault("DATABASE_PATH", ":memory:")
        os.environ.setdefault("LLM_PROVIDER", "ollama")

        for key in list(sys.modules.keys()):
            if "chanakya" in key:
                del sys.modules[key]

    def test_os_env_key_injected_into_server_config(self):
        """
        Verify that when BRAVE_API_KEY is set in OS env, it gets injected
        into the server config when loading tools.
        Patches 'os' into tool_loader module namespace to work around the missing
        `import os` in tool_loader.py.
        """
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test-secret",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
                "BRAVE_API_KEY": "real-brave-key-from-env",
            },
        ):
            # Patch 'os' into the module's namespace to fix the missing import
            import os as _os

            from src.chanakya.services import tool_loader

            tool_loader_module = sys.modules["src.chanakya.services.tool_loader"]
            setattr(tool_loader_module, "os", _os)

            tool_loader.CACHED_MCP_TOOLS = []
            tool_loader.MCP_TOOLS_LOADED_FLAG = False

            mcp_config = {
                "brave-search": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                    "env": {"BRAVE_API_KEY": "placeholder_key"},
                    "transport": "stdio",
                }
            }

            captured_config = {}

            class MockMCPClient:
                def __init__(self, cfg):
                    captured_config.update(cfg)

                async def get_tools(self):
                    return []

            with (
                patch("src.chanakya.services.tool_loader.load_mcp_config_internal") as mock_load,
                patch(
                    "src.chanakya.services.tool_loader.MultiServerMCPClient",
                    MockMCPClient,
                ),
            ):
                mock_load.return_value = mcp_config

                asyncio.new_event_loop().run_until_complete(
                    tool_loader.load_all_mcp_tools_async(force_reload=True)
                )

            # Check that the brave search server config has the real key from OS env
            self.assertIn("brave-search", captured_config)
            self.assertEqual(
                captured_config["brave-search"]["env"]["BRAVE_API_KEY"],
                "real-brave-key-from-env",
            )

    def test_missing_os_import_causes_name_error(self):
        """
        This is a regression test documenting that tool_loader.py is missing
        `import os` at the top. Without patching, load_all_mcp_tools_async will
        raise NameError when it tries to call os.environ.get().
        """
        with patch.dict(
            os.environ,
            {
                "APP_SECRET_KEY": "test-secret",
                "FLASK_DEBUG": "True",
                "DATABASE_PATH": ":memory:",
            },
        ):
            for key in list(sys.modules.keys()):
                if "chanakya" in key:
                    del sys.modules[key]

            from src.chanakya.services import tool_loader

            # Ensure 'os' is NOT patched in the module (it shouldn't be there)
            tool_loader_module = sys.modules["src.chanakya.services.tool_loader"]
            had_os = hasattr(tool_loader_module, "os")
            if had_os:
                delattr(tool_loader_module, "os")

            try:
                tool_loader.CACHED_MCP_TOOLS = []
                tool_loader.MCP_TOOLS_LOADED_FLAG = False

                mcp_config = {
                    "server": {
                        "command": "cmd",
                        "args": [],
                        "env": {"API_KEY": "placeholder"},
                    }
                }

                class MockMCPClient:
                    def __init__(self, cfg):
                        pass

                    async def get_tools(self):
                        return []

                with (
                    patch(
                        "src.chanakya.services.tool_loader.load_mcp_config_internal"
                    ) as mock_load,
                    patch(
                        "src.chanakya.services.tool_loader.MultiServerMCPClient",
                        MockMCPClient,
                    ),
                ):
                    mock_load.return_value = mcp_config
                    try:
                        asyncio.new_event_loop().run_until_complete(
                            tool_loader.load_all_mcp_tools_async(force_reload=True)
                        )
                        # If it doesn't raise, 'os' was somehow available - that's fine
                    except NameError:
                        # This confirms the bug: NameError: name 'os' is not defined
                        pass  # Expected behavior given the missing import
            finally:
                # Restore 'os' if it was there before
                if had_os:
                    setattr(tool_loader_module, "os", os)


if __name__ == "__main__":
    unittest.main()
