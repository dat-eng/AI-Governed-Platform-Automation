from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from ..api.common.vault import VaultApi
from ..utils.logger import get_logger
from .config_mixer import _deep_merge, _env, _shallow_merge, _to_bool

logger = get_logger(__name__)


# ---------- dataclasses (BASE defaults) ----------
@dataclass
class GitHubBaseConfig:
    token: str
    base_url: str = _env("GITHUB_BASE_URL", "https://github.enterprise.com")
    verify: bool = _to_bool(_env("GITHUB_VERIFY_SSL", "true"))

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GitHubVaultConfig:
    mount: str = _env("GITHUB_VAULT_MOUNT", "kv2")
    path: str = _env("GITHUB_VAULT_PATH", "sssd-sas/endpoints/github")
    field: str = _env("GITHUB_VAULT_FIELD", "secret")


# ---------- public builder API ----------
def build_github_base_config() -> Dict[str, Any]:
    """
    Compose final GitHub configuration in this order (lowest -> highest precedence):
      1. Package BASE defaults (dataclasses above)
      2. base_overrides (dict you pass programmatically, optional)
      3. user_yaml (terraform.yaml supplied by user)
      4. Environment variables (already applied in dataclass defaults for base fields)

    Returns a plain dict suitable for GitHubApi(config=...)
    """
    # 1. Try to get token from environment variable
    github_token = _env("GITHUB_TOKEN")

    # 2. If not present, fetch from Vault
    if not github_token:
        logger.info("Getting credentials from Vault")
        vault_config = GitHubVaultConfig()
        github_token = VaultApi().read_kv_v2(
            vault_config.mount, vault_config.path, vault_config.field
        )

    # start with base dataclass defaults (already env-aware for base fields)
    base_config = GitHubBaseConfig(token=github_token)
    base = base_config.as_dict()

    return base


def build_github_user_config(
    base: Dict, user_config: Optional[Dict] = None, overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compose final Ansible configuration in this order (lowest -> highest precedence):
      1. Package BASE defaults (dataclasses above)
      2. base_overrides (dict you pass programmatically, optional)
      3. user_yaml (terraform.yaml supplied by user)
      4. Environment variables (already applied in dataclass defaults for base fields)

    Returns a plain dict suitable for GitHubApi(config=...)
    """
    # overlay user YAML
    if user_config:
        _deep_merge(base, user_config)

    # apply base_overrides programmatically (optional)
    if overrides:
        _shallow_merge(base, overrides)

    return base
