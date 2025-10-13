# __init__.py
# The toplevel SAS Client package.

# Set default logging handler to avoid "No handler found" warnings.
from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import PackageNotFoundError, metadata
from importlib.metadata import version as _v
from logging import NullHandler
from typing import TYPE_CHECKING

# ---- Runtime metadata (no duplication; reads what's installed) ----------------
DIST_NAME = "sas_client"  # must match [project.name] in pyproject.toml

try:
    _md = metadata(DIST_NAME)
    __version__ = _v(DIST_NAME)
    __title__ = _md["Name"]
    __summary__ = _md.get("Summary", "")
    __author__ = _md.get("Author", "") or _md.get("Author-email", "")
except PackageNotFoundError:
    # Running from a checkout without install
    __version__ = "0.0.0"
    __title__ = "sas_client"
    __summary__ = __url__ = __author__ = __license__ = ""


@dataclass(frozen=True)
class PackageInfo:
    name: str
    version: str
    summary: str
    author: str


def package_info() -> PackageInfo:
    """Return runtime package metadata from the installed distribution."""
    return PackageInfo(
        name=__title__,
        version=__version__,
        summary=__summary__,
        author=__author__,
    )


logging.getLogger(__name__).addHandler(NullHandler())

# ---- Public API (lazy-loaded re-exports) -------------------------------------
__all__ = [
    # API surface
    "AnsibleApi",
    "GitHubApi",
    "InfobloxApi",
    "NexusApi",
    "NutanixApi",
    "NutanixSDK",
    "NutanixClient",
    "NutanixConfig",
    "TerraformApi",
    # Metadata helpers
    "package_info",
    "PackageInfo",
    "__version__",
]

# Top-level name -> (module path, attribute)
_LAZY_MAP = {
    "AnsibleApi": ("sas_client.api.ansible", "AnsibleApi"),
    "GitHubApi": ("sas_client.api.github", "GitHubApi"),
    "InfobloxApi": ("sas_client.api.infoblox", "InfobloxApi"),
    "NexusApi": ("sas_client.api.nexus", "NexusApi"),
    "NutanixApi": ("sas_client.api.nutanix", "NutanixApi"),
    "NutanixSDK": ("sas_client.api.nutanix_sdk", "NutanixSDK"),
    "NutanixClient": ("sas_client.api.nutanix_client", "NutanixClient"),
    "NutanixConfig": ("sas_client.api.nutanix_client", "NutanixConfig"),
    "TerraformApi": ("sas_client.api.terraform", "TerraformApi"),
}


def __getattr__(name: str):
    if name not in _LAZY_MAP:
        raise AttributeError(name)
    mod_name, attr = _LAZY_MAP[name]
    try:
        mod = import_module(mod_name)
    except Exception as exc:
        raise ImportError(f"{name} unavailable: failed to import {mod_name}") from exc
    obj = getattr(mod, attr)
    globals()[name] = obj  # cache after first lookup
    return obj


def __dir__():
    return sorted(set(globals()) | set(__all__))


# Help type checkers/IDEs without importing at runtime
if TYPE_CHECKING:
    from sas_client.api.ansible import AnsibleApi
    from sas_client.api.github import GitHubApi
    from sas_client.api.infoblox import InfobloxApi
    from sas_client.api.nexus import NexusApi
    from sas_client.api.nutanix import NutanixApi
    from sas_client.api.nutanix_client import NutanixClient, NutanixConfig
    from sas_client.api.nutanix_sdk import NutanixSDK
    from sas_client.api.terraform import TerraformApi
