from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from ..api.common.vault import VaultApi
from ..utils.logger import get_logger
from .config_mixer import _deep_merge, _env, _shallow_merge, _to_bool

logger = get_logger(__name__)

# ---------- dataclasses (BASE defaults) ----------


@dataclass
class InfobloxBaseConfig:
    password: str
    base_url: str = _env("INFOBLOX_BASE_URL", "https://internal-grid.enterprise.com")
    verify: bool = _to_bool(_env("INFOBLOX_VERIFY_SSL", "true"))
    username: str = _env("INFOBLOX_USER_NAME", "myuser")
    auth_type: str = _env("INFOBLOX_AUTH_TYPE", "basic")

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InfobloxVaultConfig:
    mount: str = _env("ANSIBLE_VAULT_MOUNT", "kv2")
    path: str = _env("ANSIBLE_VAULT_PATH", "sssd-sas/endpoints/infoblox")
    field: str = _env("ANSIBLE_VAULT_FIELD", "secret")


# ---------- public builder API ----------
def build_infoblox_base_config() -> Dict[str, Any]:
    """
    Compose final configuration in this order (lowest -> highest precedence):
      1. Package BASE defaults (dataclasses above)
      2. base_overrides (dict you pass programmatically, optional)
      3. user_yaml (terraform.yaml supplied by user)
      4. Environment variables (already applied in dataclass defaults for base fields)

    Returns a plain dict suitable for InfobloxApi(config=...)
    """
    # 1. Try to get token from environment variable
    infoblox_secret = _env("INFOBLOX_SECRET")

    # 2. If not present, fetch from Vault
    if not infoblox_secret:
        logger.info("Getting credentials from Vault")
        vault_config = InfobloxVaultConfig()
        infoblox_secret = VaultApi().read_kv_v2(
            vault_config.mount, vault_config.path, vault_config.field
        )

    # Base dataclass defaults (already env-aware for base fields)
    base_config = InfobloxBaseConfig(password=infoblox_secret)
    base = base_config.as_dict()

    return base


def build_infoblox_user_config(
    base: Dict, user_config: Optional[Dict] = None, overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compose final Infoblox configuration in this order (lowest -> highest precedence):
      1. Package BASE defaults (dataclasses above)
      2. base_overrides (dict you pass programmatically, optional)
      3. user_yaml (terraform.yaml supplied by user)
      4. Environment variables (already applied in dataclass defaults for base fields)

    Returns a plain dict suitable for InfobloxApi
    """
    # overlay user YAML
    if user_config:
        _deep_merge(base, user_config)

    # apply base_overrides programmatically (optional)
    if overrides:
        _shallow_merge(base, overrides)

    return base
