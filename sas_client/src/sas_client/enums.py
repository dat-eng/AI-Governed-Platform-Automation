from __future__ import annotations

from enum import Enum
from typing import Any, Optional, Type, TypeVar

T = TypeVar("T")


def _norm_name(name: str) -> str:
    return str(name).strip().replace("-", "_").upper()


def _norm_code(code: str) -> str:
    s = str(code).strip()
    return s.upper()


class CodeEnumMixin:
    """
    Mixin with helpers for enums that store a short 'code' in .value.
    NOTE: Use with Enum: class OS(CodeEnumMixin, Enum): ...
    """

    # NOTE: Do NOT declare _ALIASES/_DESCRIPTIONS defaults here.
    # Define them ONLY in concrete enums (if needed).

    # NOTE: define _ALIASES / _DESCRIPTIONS on subclasses (either as dicts,
    # or, if Enum wraps them, they may appear as Enum members whose .value is a dict).

    @classmethod
    def _get_attr_unwrapped(cls, attr: str, expected_type: Type[T]) -> Optional[T]:
        """
        Return an attribute from the subclass as `expected_type`, handling both:
          - direct attributes of that type (e.g., dict or set)
          - Enum members whose `.value` is of that type
        """
        obj: Any = getattr(cls, attr, None)
        if isinstance(obj, expected_type):
            return obj  # type: ignore[return-value]
        # If Enum wrapped it into a member, unwrap .value
        val = getattr(obj, "value", None)
        if isinstance(val, expected_type):
            return val  # type: ignore[return-value]
        return None

    @classmethod
    def from_str(cls, name: str):
        """Strict: parse by symbolic name (supports aliases); raises KeyError."""
        if name is None:
            raise KeyError(f"{cls.__name__}.from_str: name is None")
        norm = _norm_name(name)

        # Safely resolve aliases if provided on the subclass
        alias_map = cls._get_attr_unwrapped("_ALIASES", dict)
        if alias_map:
            norm = alias_map.get(norm, norm)
        return cls[norm]  # type: ignore[index]

    @classmethod
    def try_from_str(cls, name: Optional[str]):
        """Lenient: like from_str but returns None on bad/empty input."""
        if not name:
            return None
        try:
            return cls.from_str(name)
        except KeyError:
            return None

    @classmethod
    def from_code(cls, code: str):
        """Strict: parse by code/value; raises ValueError."""
        norm = _norm_code(code)
        return cls(norm)  # type: ignore[call-arg]

    @classmethod
    def try_from_code(cls, code: Optional[str]):
        """Lenient: like from_code but returns None on bad/empty input."""
        if code is None or str(code).strip() == "":
            return None
        try:
            return cls.from_code(code)
        except ValueError:
            return None

    @property
    def code(self) -> str:
        """The value used in hostnames."""
        return self.value  # type: ignore[return-value]

    @property
    def description(self) -> str:
        """
        Human-friendly description if provided in _DESCRIPTIONS,
        else title-cased enum name.
        """
        desc_map = self.__class__._get_attr_unwrapped("_DESCRIPTIONS", dict)
        return desc_map.get(self.name, self.name.title()) if desc_map else self.name.title()

    def __str__(self) -> str:
        return self.name  # type: ignore[return-value]


class OS(CodeEnumMixin, Enum):
    LINUX = "2"
    WINDOWS = "0"

    _ALIASES = {
        "LINUX": "LINUX",
        "RHEL": "LINUX",
        "REDHAT": "LINUX",
        "WIN": "WINDOWS",
        "MSWIN": "WINDOWS",
        "WINNT": "WINDOWS",
    }
    _DESCRIPTIONS = {
        "LINUX": "Linux Operating System",
        "WINDOWS": "Microsoft Windows Operating System",
    }


class Location(CodeEnumMixin, Enum):
    MEM = "T"
    MTB = "W"

    _ALIASES = {
        "MEMPHIS": "MEM",
        "MARTINSBURG": "MTB",
    }
    _DESCRIPTIONS = {
        "MEM": "Memphis Data Center",
        "MTB": "Martinsburg Data Center",
    }


class Environment(CodeEnumMixin, Enum):
    SBX = "X"
    DEV = "V"
    TEST = "T"
    PRE_PROD = "E"
    PROD = "P"
    ASPE = "A"

    _ALIASES = {
        "SANDBOX": "SBX",
        "DEVELOPMENT": "DEV",
        "PREPROD": "PRE_PROD",
        "PREPRODUCTION": "PRE_PROD",
        "PRODUCTION": "PROD",
        "DR": "ASPE",
    }
    _DESCRIPTIONS = {
        "SBX": "Sandbox Environment",
        "DEV": "Development Environment",
        "TEST": "Test Environment",
        "PRE_PROD": "Pre-Production Environment",
        "PROD": "Production Environment",
        "ASPE": "DR Environment",
    }

    _NONPROD_LIKE = {"SBX", "DEV", "TEST", "PRE_PROD"}
    _PROD_LIKE = {"PROD", "ASPE"}

    @classmethod
    def is_nonprod_like(cls, env: "Environment") -> bool:
        if not isinstance(env, cls):
            raise TypeError(f"is_nonprod_like expects {cls.__name__}, got {type(env)}")
        names = cls._get_attr_unwrapped("_NONPROD_LIKE", (set, frozenset)) or frozenset()
        # normalize to frozenset for consistent membership test
        names = frozenset(names)
        return env.name in names

    @classmethod
    def is_prod_like(cls, env: "Environment") -> bool:
        if not isinstance(env, cls):
            raise TypeError(f"is_prod_like expects {cls.__name__}, got {type(env)}")
        names = cls._get_attr_unwrapped("_PROD_LIKE", (set, frozenset)) or frozenset()
        # normalize to frozenset for consistent membership test
        names = frozenset(names)
        return env.name in names

    # instance shortcuts
    def is_nonprod(self) -> bool:
        names = self.__class__._get_attr_unwrapped("_NONPROD_LIKE", (set, frozenset)) or frozenset()
        return self.name in frozenset(names)

    def is_prod(self) -> bool:
        names = self.__class__._get_attr_unwrapped("_PROD_LIKE", (set, frozenset)) or frozenset()
        return self.name in frozenset(names)


class ServerType(CodeEnumMixin, Enum):
    APPLICATION = "AP"
    DB2 = "B2"
    BATCHSERVER = "BT"
    INFRASTRUCTURE = "IN"
    MONGODB = "MO"
    ORACLEDB = "OR"
    POSTGRESQL = "PS"
    RELATIONALDATABASE = "RD"
    SHAREDFOLDERS = "SH"
    SHAREPOINT = "SP"
    MICROSOFTSQL = "SQ"
    WEB = "WB"

    _ALIASES = {
        "APP": "APPLICATION",
        "POSTGRES": "POSTGRESQL",
        "PG": "POSTGRESQL",
        "SQLSERVER": "MICROSOFTSQL",
        "MSSQL": "MICROSOFTSQL",
        "IIS": "WEB",
    }
    _DESCRIPTIONS = {
        "APPLICATION": "Generic Application Server",
        "DB2": "IBM DB2 Database",
        "BATCHSERVER": "Batch Processing Server",
        "INFRASTRUCTURE": "Infrastructure Server",
        "MONGODB": "MongoDB Database",
        "ORACLEDB": "Oracle Database",
        "POSTGRESQL": "PostgreSQL Database",
        "RELATIONALDATABASE": "Relational Database",
        "SHAREDFOLDERS": "Shared Folders",
        "SHAREPOINT": "SharePoint Server",
        "MICROSOFTSQL": "Microsoft SQL Server",
        "WEB": "Web Server",
    }
