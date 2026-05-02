"""Chanakya full application package."""

from __future__ import annotations

import importlib
import sys

_CORE_MODULES = (
    "config",
    "db",
    "debug",
    "domain",
    "history_provider",
    "model",
    "maf_workflows",
    "mcp_runtime",
    "store",
    "seed",
    "heartbeat",
    "subagents",
    "conversation_layer_support",
    "agent_manager",
    "chat_service",
    "app",
)

for _module_name in _CORE_MODULES:
    _module = importlib.import_module(
        f"{__name__}.core.{_module_name}"
    )
    sys.modules[f"{__name__}.{_module_name}"] = _module
    globals()[_module_name] = _module
