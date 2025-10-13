from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from ..api.common.vault import VaultApi
from ..utils.logger import get_logger
from .config_mixer import _deep_merge, _env, _shallow_merge, _to_bool

logger = get_logger(__name__)


# ---------- dataclasses (BASE defaults) ----------
@dataclass
class WorkspaceConfig:
    attributes: Dict[str, Any] = field(
        default_factory=lambda: {"queue_all_runs": _to_bool(_env("TFE_QUEUE_ALL_RUNS", "true"))}
    )
    variable_set: str = _env("TFE_VARIABLE_SET", "vRA Prod Set")


@dataclass
class ProjectConfig:
    access: str = _env("TFE_PROJECT_ACCESS", "admin")
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)


@dataclass
class TerraformBaseConfig:
    token: str
    base_url: str = _env("TERRAFORM_BASE_URL", "https://terraform.enterprise.com")
    verify: bool = _to_bool(_env("TERRAFORM_VERIFY_SSL", "true"))
    project: ProjectConfig = field(default_factory=ProjectConfig)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TerraformVaultConfig:
    mount: str = _env("TERRAFORM_VAULT_MOUNT", "kv2")
    path: str = _env("TERRAFORM_VAULT_PATH", "sssd-sas/endpoints/terraform")
    field: str = _env("TERRAFORM_VAULT_FIELD", "secret")


# ---------- public builder API ----------
def build_terraform_base_config() -> Dict[str, Any]:
    """
    Compose final Terraform configuration in this order (lowest -> highest precedence):
      1. Package BASE defaults (dataclasses above)
      2. base_overrides (dict you pass programmatically, optional)
      3. user_yaml (terraform.yaml supplied by user)
      4. Environment variables (already applied in dataclass defaults for base fields)

    Returns a plain dict suitable for TerraformApi(config=...)
    """
    # 1. Try to get token from environment variable
    terraform_token = _env("TERRAFORM_TOKEN")

    # 2. If not present, fetch from Vault
    if not terraform_token:
        logger.info("Getting credentials from Vault")
        vault_config = TerraformVaultConfig()
        terraform_token = VaultApi().read_kv_v2(
            vault_config.mount, vault_config.path, vault_config.field
        )

    # start with base dataclass defaults (already env-aware for base fields)
    base_config = TerraformBaseConfig(token=terraform_token)
    base = base_config.as_dict()

    return base


def build_terraform_user_config(
    base: Dict, user_config: Optional[Dict] = None, overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Compose final Terraform configuration in this order (lowest -> highest precedence):
      1. Package BASE defaults (dataclasses above)
      2. base_overrides (dict you pass programmatically, optional)
      3. user_yaml (terraform.yaml supplied by user)
      4. Environment variables (already applied in dataclass defaults for base fields)

    Returns a plain dict suitable for TerraformApi(config=...)
    """
    # overlay user YAML
    if user_config:
        _deep_merge(base, user_config)

    # apply base_overrides programmatically (optional)
    if overrides:
        _shallow_merge(base, overrides)

    return base
