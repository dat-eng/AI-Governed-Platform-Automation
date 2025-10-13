from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from ..api.common.vault import VaultApi
from ..utils.logger import get_logger
from .config_mixer import _deep_merge, _env, _shallow_merge, _to_bool

logger = get_logger(__name__)

# ---------- dataclasses (BASE defaults) ----------


@dataclass
class NutanixBaseConfig:
    username: str
    password: str
    base_url: str = _env("NUTANIX_BASE_URL", "https://vl2smtbnut.com:9440")
    marketplace_blueprint_name: str = _env(
        "NUTANIX_MARKETPLACE_BP_NAME", "Red Hat Enterprise Linux 9 - DHCP"
    )
    verify: bool = _to_bool(_env("NUTANIX_VERIFY_SSL", "true"))
    provision_interval: int = _env("NUTANIX_WAIT_INTERVAL", 10)
    provision_max_wait: int = _env("NUTANIX_MAX_WAIT", 2400)
    wait_for_app: bool = _to_bool(_env("NUTANIX_WAIT_FOR_APP", "true"))
    delete_app_after_launch: bool = _to_bool(_env("NUTANIX_DELETE_APP_AFTER_LAUNCH", "false"))

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NutanixVaultConfig:
    mount: str = _env("NUTANIX_VAULT_MOUNT", "kv2")
    path: str = _env("NUTANIX_VAULT_PATH", "sssd-sas/endpoints/nutanix")
    secret_field: str = _env("NUTANIX_VAULT_FIELD", "secret")
    user_field: str = _env("NUTANIX_VAULT_FIELD", "username")


# ---------- public builder API ----------


def build_nutanix_base_config() -> Dict[str, Any]:
    """
    Compose final configuration in this order (lowest -> highest precedence):
      1. Package BASE defaults (dataclasses above)
      2. base_overrides (dict you pass programmatically, optional)
      3. user_yaml (nutanix.yaml supplied by user)
      4. Environment variables (already applied in dataclass defaults for base fields)

    Returns a plain dict suitable for NutanixApi(config=...)
    """
    # 1. Try to get token from environment variable
    nutanix_username = _env("NUTANIX_USERNAME")
    nutanix_password = _env("NUTANIX_SECRET")

    # 2. If not present, fetch from Vault
    if not (nutanix_username and nutanix_password):
        logger.info("Getting credentials from Vault")
        vault_config = NutanixVaultConfig()
        nutanix_username = VaultApi().read_kv_v2(
            vault_config.mount, vault_config.path, vault_config.user_field
        )
        nutanix_password = VaultApi().read_kv_v2(
            vault_config.mount, vault_config.path, vault_config.secret_field
        )

    # start with base dataclass defaults (already env-aware for base fields)
    base_config = NutanixBaseConfig(username=nutanix_username, password=nutanix_password)
    base = base_config.as_dict()

    return base


def build_nutanix_user_config(
    base: Dict, user_config: Optional[Dict] = None, overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compose final Nutanix configuration in this order (lowest -> highest precedence):
      1. Package BASE defaults (dataclasses above)
      2. base_overrides (dict you pass programmatically, optional)
      3. user_yaml (terraform.yaml supplied by user)
      4. Environment variables (already applied in dataclass defaults for base fields)

    Returns a plain dict suitable for NutanixApi(config=...)
    """
    # overlay user YAML
    if user_config:
        _deep_merge(base, user_config)

    # apply base_overrides programmatically (optional)
    if overrides:
        _shallow_merge(base, overrides)

    return base
