from __future__ import annotations

import copy
import os
from typing import Any, List, Mapping, MutableMapping, Optional

"""
Shared helpers for classes that have `self.config` (a dict-like).
"""
_MISSING = object()


def _require(cfg: Mapping[str, Any], key: str, default: Any = _MISSING) -> Any:
    """
    Get cfg[key]; if missing and default provided, return default; else raise KeyError.
    """
    if key in cfg:
        return cfg[key]
    if default is not _MISSING:
        return default
    raise KeyError(key)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None else default


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    val = str(v).strip().lower()
    if val in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"Cannot interpret boolean value from: {v!r}")


def _deep_merge(
    base: MutableMapping[str, Any], override: Mapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    Recursively merge 'override' into 'base' (in place). Dicts merge, lists replace.
    """
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def _shallow_merge(
    base: MutableMapping[str, Any], override: Mapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    Shallow-merge self.config with provided non-None overrides.
    """
    for k, v in override.items():
        if v is not None:
            base[k] = v
    return base


def _list_from_arg(maybe: Optional[str | List[str]]) -> Optional[List[str]]:
    """
    Supports:
      --members alice,bob,charlie
      --members alice --members bob --members charlie
    """
    if maybe is None:
        return None
    if isinstance(maybe, list):
        out: List[str] = []
        for item in maybe:
            out.extend([s.strip() for s in item.split(",") if s.strip()])
        return out or None
    # string
    return [s.strip() for s in str(maybe).split(",") if s.strip()] or None
