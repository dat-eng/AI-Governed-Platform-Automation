from __future__ import annotations

import hashlib
import json
import os
import uuid
from typing import Any, Dict, Iterable, List, Optional, Set, Union

import yaml


def load_config(path: str) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def make_id(length: int) -> str:
    return str(uuid.uuid4().hex)[:length]


def build_overrides(**kwargs) -> dict:
    """Return a dict of overrides, excluding any keys with None values."""
    return {k: v for k, v in kwargs.items() if v is not None}


def nested_keys_exist(inputs: dict, keys: List[str]) -> bool:
    """
    Check if keys (nested) exists in `element` (dict).

    Args:
        inputs (dict): Dictionary to search
        keys (list[str]): Ordered key[s] to look for in `element`
    Returns:
        bool: True if key[s] exists, False if any are missing
    """
    if not isinstance(inputs, dict):
        raise AttributeError("nested_keys_exist() expects dict as first argument.")
    if len(keys) == 0:
        raise AttributeError("nested_keys_exist() expects at least two arguments, one given.")
    if not all(isinstance(key, str) for key in keys):
        raise AttributeError("nested_keys_exist() expects keys to all be strings")

    _element = inputs
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return True


def get_nested_values(inputs: dict, keys: List[str]) -> Any:
    """
    Check if keys (nested) exists in `element` (dict).

    Args:
        inputs (dict): Dictionary to search
        keys (list[str]): Ordered key[s] to look for in `element`
    Returns:
        Any: value stored at the key path
    """
    if not isinstance(inputs, dict):
        raise AttributeError("nested_keys_exist() expects dict as first argument.")
    if len(keys) == 0:
        raise AttributeError("nested_keys_exist() expects at least two arguments, one given.")
    if not all(isinstance(key, str) for key in keys):
        raise AttributeError("nested_keys_exist() expects keys to all be strings")

    _element = inputs
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return None
    return _element


def to_key_value(d: dict) -> dict[str, object] | None:
    """
    If *d* contains exactly one key/value pair, return
    {"key": <key>, "value": <value>}.
    Returns None for an empty dict.
    """
    if not d:  # guard against {}
        return None
    k, v = next(iter(d.items()))
    return dict(key=k, value=v)


def checksum(path: str, algo: str = "sha256", chunk_size: int = 65536) -> str:
    """Return the hex digest of *path* using *algo*. Large‑file friendly."""
    h = hashlib.new(algo)
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(chunk_size), b""):  # noqa: E731
            h.update(blk)
    return h.hexdigest()


def build_parts(*args: str) -> str:
    return "".join(args)


KeyPath = Union[List[str], str, None]


def _to_keypath(path: KeyPath) -> Optional[List[str]]:
    """Normalize key path to list[str] or None (if no fallback)."""
    if path is None:
        return None
    if isinstance(path, str):
        path = path.strip()
        return path.split(".") if path else None
    if isinstance(path, Iterable):
        return list(path)  # defensive copy
    return None


def _get_nested(d: Dict[str, Any], path: List[str]) -> Any:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def validate_inputs_with_config(
    args: Dict[str, Any],
    config: Dict[str, Any],
    required_mappings: Dict[str, KeyPath],
    *,
    json_decode_fields: Optional[Set[str]] = None,
    treat_empty_as_missing: bool = True,
) -> Dict[str, Any]:
    """
    Resolve required inputs from direct args or config.
    - required_mappings maps arg name -> config key path (list or 'dot.path' or None).
      If None/empty: the arg must be provided directly.
    - json_decode_fields: fields to json.loads if they resolve to a JSON string.
    """
    json_decode_fields = json_decode_fields or set()
    resolved: Dict[str, Any] = {}
    missing: List[str] = []

    for arg_name, path in required_mappings.items():
        value = args.get(arg_name, None)

        # If not provided directly, try config fallback (if a path is defined)
        if value is None:
            keypath = _to_keypath(path)
            if keypath:  # only try config if we have a valid path
                value = _get_nested(config, keypath)

        # Optionally decode JSON for specific fields
        if arg_name in json_decode_fields and isinstance(value, str):
            s = value.strip()
            if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
                try:
                    value = json.loads(s)
                except Exception:
                    # leave as-is if it doesn't parse cleanly
                    pass

        # Decide if it's missing
        if treat_empty_as_missing:
            is_missing = value in (None, "", [], {})
        else:
            is_missing = value is None

        if is_missing:
            missing.append(arg_name)
        else:
            resolved[arg_name] = value

    if missing:
        return {"status": "error", "message": f"Inputs required: {', '.join(missing)}"}

    return {"status": "ok", "values": resolved}


if __name__ == "__main__":
    print("Import as a module to use")
