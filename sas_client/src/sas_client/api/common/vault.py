import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import requests

from ...config.config_mixer import _env, _to_bool
from ...utils.logger import get_logger
from .api_client import APIClient, APIClientConfig


@dataclass
class VaultConfig:
    base_url: str = _env("VAULT_BASE_URL", "https://hcvault.enterprise.com")
    token: str = _env("VAULT_TOKEN")
    verify: bool = _to_bool(_env("VAULT_VERIFY_SSL", "true"))
    role_id: Optional[str] = _env("VAULT_ROLE_ID")
    secret_id: Optional[str] = _env("VAULT_SECRET_ID")
    namespace: Optional[str] = _env("VAULT_NAMESPACE")

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VaultApi:
    def __init__(self, role_id: Optional[str] = None, secret_id: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.config = VaultConfig().as_dict()

        if self.config.get("role_id") and self.config.get("secret_id"):
            # Use AppRole login to get a token
            self.logger.debug("Logging in with AppRole...")
            self.config["token"] = self._login_with_approle(
                self.config["role_id"], self.config["secret_id"]
            )

        if not self.config.get("token"):
            raise RuntimeError("Vault token is required (set VAULT_TOKEN or use AppRole)")

        self.logger.debug(f"Vault config: {json.dumps(self.config, indent=2)}")
        self.client = APIClient(APIClientConfig.from_dict(self.config))

        # Add headers
        self.client._session.headers.update(
            {
                "X-Vault-Token": self.config.get("token"),
                "X-Vault-Request": "true",
                "Accept": "application/json",
            }
        )
        if self.config.get("namespace"):
            self.client._session.headers.update("X-Vault-Namespace", self.config.get("namespace"))

    def _login_with_approle(self, role_id: str, secret_id: str) -> str:
        """
        Perform AppRole login to Vault and return a client token.
        """
        url = f"{self.config['base_url'].rstrip('/')}/v1/auth/approle/login"
        payload = {"role_id": role_id, "secret_id": secret_id}

        resp = requests.post(
            url,
            json=payload,
            verify=self.config.get("verify", True),
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()

        token = resp.json().get("auth", {}).get("client_token")
        if not token:
            raise RuntimeError("Failed to retrieve Vault token from AppRole login")

        return token

    def read_kv_v2(self, mount: str, path: str, field: Optional[str] = None) -> Any:
        """
        Read a secret from KV v2 engine.
        Example:
            mount="kv", path="terraform", field="token"
        """
        endpoint = f"/v1/{mount}/data/{path}"
        resp = self.client.get(endpoint)
        data = resp.get("data", {}).get("data", {})
        return data[field] if field else data

    def read_kv_v1(self, mount: str, path: str, field: Optional[str] = None) -> Any:
        """
        Read a secret from KV v1 engine.
        """
        endpoint = f"/v1/{mount}/{path}"
        resp = self.client.get(endpoint)
        data = resp.get("data", {})
        return data[field] if field else data
