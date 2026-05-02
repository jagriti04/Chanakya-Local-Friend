"""Chanakya full application package."""

from __future__ import annotations

from pathlib import Path

_CORE_DIR = Path(__file__).resolve().parent / "core"
if _CORE_DIR.exists():
    __path__.append(str(_CORE_DIR))
