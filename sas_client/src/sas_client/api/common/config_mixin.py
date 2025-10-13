from typing import Any, Dict, Mapping


class ConfigMixin:
    """
    Shared helpers for classes that have `self.config` (a dict-like).
    """

    _MISSING = object()

    def _merge_cfg(self, *overrides_dicts: Mapping[str, Any], **overrides: Any) -> Dict[str, Any]:
        """
        Shallow-merge self.config with provided non-None overrides.
        You can pass one or more dict-like objects plus keyword overrides.
        Later sources win.
        """
        base = dict(getattr(self, "config", {}) or {})
        merged = dict(base)
        for d in overrides_dicts:
            for k, v in d.items():
                if v is not None:
                    merged[k] = v
        for k, v in overrides.items():
            if v is not None:
                merged[k] = v
        return merged

    def _require(self, cfg: Mapping[str, Any], key: str, default: Any = _MISSING) -> Any:
        """
        Get cfg[key]; if missing and default provided, return default; else raise KeyError.
        """
        if key in cfg:
            return cfg[key]
        if default is not self._MISSING:
            return default
        raise KeyError(key)
