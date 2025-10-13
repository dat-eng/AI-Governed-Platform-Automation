import argparse
import datetime
import json
import ssl
import time
import uuid
from dataclasses import dataclass, fields
from typing import Any, Generator, Mapping, Optional, Union
from urllib.parse import urljoin

import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase, HTTPBasicAuth
from requests.exceptions import HTTPError
from urllib3.util.retry import Retry

from ...utils.logger import get_logger

# Disable Insecure Request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)


class APIClientException(Exception):
    """
    Exception raised for errors occurring in APIClient operations.

    Attributes:
        code (str): Categorized error code (e.g., 'timeout', 'auth_error')
        original_exception (Exception, optional): Underlying caught exception
        Additional attributes are dynamically added based on keyword arguments.
    """

    def __init__(self, message: str, code: str = "unknown_error", **kwargs):
        super().__init__(message)
        self.code = code
        for k, v in kwargs.items():
            setattr(self, k, v)


class TokenAuth(AuthBase):
    """
    Requests-compatible Bearer Token authenticator.

    Attributes:
        token (str): Bearer token value
        header_name (str): Header key for auth, default 'Authorization'
        scheme (str): Scheme prefix, default 'Bearer'
    """

    def __init__(self, token: str, header_name="Authorization", scheme="Bearer"):
        self.token = token
        self.header_name = header_name
        self.scheme = scheme

    def __call__(self, request):
        request.headers[self.header_name] = (
            f"{self.scheme} {self.token}" if self.scheme else self.token
        )
        return request


class APIKeyAuth(AuthBase):
    """
    Simple API key authenticator.

    Attributes:
        api_key (str): The API key value
        header_name (str): The header in which to send the key (default 'X-API-Key')
    """

    def __init__(self, api_key: str, header_name: str = "X-API-Key"):
        self.api_key = api_key
        self.header_name = header_name

    def __call__(self, request):
        request.headers[self.header_name] = self.api_key
        return request


@dataclass
class APIClientConfig:
    """
    Configuration container for initializing APIClient.

    Attributes:
        base_url (str): Base URL of the API
        token_url (str): Endpoint for token auth (optional)
        token_field (str): JSON field containing the token
        token_params (dict): Additional form parameters for token request
        token (str): Pre-obtained token (used if token_url is not provided)
        username (str): Basic auth username
        password (str): Basic auth password
        verify (bool | str): SSL verification or CA bundle path
        retry_strategy (Retry): Custom retry strategy (optional)
        auth_type (str): 'bearer', 'basic', or 'api_key'
        api_key (str): API key for authentication
        api_key_header (str): Header used to send the API key
        connect_timeout (float): Connection timeout (default: 10s)
        read_timeout (float): Read timeout (default: 10s)
    """

    # ── Core connection ──────────────────────────────────────────────────────────
    base_url: str
    connect_timeout: float = 10.0
    read_timeout: float = 10.0
    verify: Union[bool, str] = True
    retry_strategy: Optional[Retry] = None

    # ── Auth ─────────────────────────────────────────────────────────────────────
    auth_type: str = "bearer"  # bearer · basic · api_key
    # bearer-style
    token_url: Optional[str] = None
    token_field: str = "access_token"
    token_params: Optional[Mapping[str, Any]] = None
    token: Optional[str] = None
    # basic-auth
    username: Optional[str] = None
    password: Optional[str] = None
    # api-key
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"

    # ── Helpers ──────────────────────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, config: Mapping[str, Any]) -> "APIClientConfig":
        """
        Build a new ``APIClientConfig`` from a mapping, dropping any
        unknown keys.

        Example
        -------
        >>> raw = {
        ...     "base_url": "...",
        ...     "auth_type": "basic",
        ...     "username": "alice",
        ...     "password": "secret",
        ...     "connect_timeout": 5,
        ... }
        >>> config = APIClientConfig.from_dict(raw)
        """
        valid_keys = {f.name for f in fields(cls)}
        init_args = {k: v for k, v in config.items() if k in valid_keys}
        return cls(**init_args)

    def update(self, config: Mapping[str, Any]) -> None:
        """
        Overwrite attributes in-place from a mapping, silently skipping
        unknown keys.

        Example
        -------
        >>> config.update({"read_timeout": 30, "token": "new-token"})
        """
        for k, v in config.items():
            if hasattr(self, k):
                setattr(self, k, v)


class APIClient:
    """
    A robust, flexible HTTP API client supporting advanced features such as:

    - Token-based, Basic, and API Key authentication
    - Automatic token refresh based on expiry
    - Custom retry strategies and request timeouts
    - Configurable via dataclass or dict
    - Structured error handling with categorized exceptions
    - Optional retry on JSON decode errors
    - Request timing metrics for observability
    - CLI interface for health check/testing
    - Exposed last_response for debugging

    Parameters:
    - config (APIClientConfig | dict): Configuration for the client including base URL, authentication, and retry settings
    """

    def __init__(self, config: Union[APIClientConfig, dict]):
        self.logger = get_logger(__name__)
        if isinstance(config, dict):
            config = APIClientConfig(**config)
        self.config = config
        self._session = requests.Session()
        self._session.verify = (
            config.verify
            if isinstance(config.verify, str)
            else (ssl.get_default_verify_paths().cafile if config.verify else False)
        )
        self._token_expiry: Optional[datetime.datetime] = None
        self.last_response: Optional[requests.Response] = None

        adapter = HTTPAdapter(
            max_retries=config.retry_strategy
            or Retry(
                total=3,
                backoff_factor=2.0,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(
                    ["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"]
                ),
            )
        )
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

        # Authentication
        if config.token_url:
            if not (config.username and config.password):
                raise ValueError("username and password required for token_url")
            self.refresh_token()
        elif config.token and config.auth_type == "bearer":
            self._session.auth = TokenAuth(token=config.token)
        elif config.auth_type == "api_key" and config.api_key:
            self._session.auth = APIKeyAuth(
                api_key=config.api_key, header_name=config.api_key_header
            )
        elif config.username and config.password:
            self._session.auth = HTTPBasicAuth(config.username, config.password)

        self._session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def _full_url(self, endpoint: str) -> str:
        """
        Resolves the full URL from a base URL and relative path.

        Parameters:
            endpoint (str): Relative path or full URL

        Returns:
            str: Fully-qualified URL
        """

        return endpoint if endpoint.startswith("http") else urljoin(self.config.base_url, endpoint)

    def refresh_token(self):
        """
        Refreshes the authentication token using Basic auth credentials.
        Stores the token and calculates expiry time if 'expires_in' is present in response.
        Raises:
            APIClientException: if the token refresh fails or token is missing.
        """

        url = self._full_url(self.config.token_url)
        try:
            resp = self._session.post(
                url=url,
                auth=HTTPBasicAuth(self.config.username, self.config.password),
                data=self.config.token_params,
                timeout=(self.config.connect_timeout, self.config.read_timeout),
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get(self.config.token_field)
            expires_in = data.get("expires_in", 3600)
            if not token:
                raise APIClientException("Token missing", code="token_missing")
            self._token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=expires_in - 60
            )
            self._session.auth = TokenAuth(token)
        except Exception as e:
            raise APIClientException(
                "Token refresh failed", code="auth_error", original_exception=e
            ) from e

    def _request_raw(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Executes a raw HTTP request with retries, timing, and automatic token handling.

        Parameters:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): URL path or full URL
            **kwargs: Additional request arguments (headers, json, timeout, etc.)

        Returns:
            requests.Response: Raw response object.

        Raises:
            APIClientException: Categorized error for timeout, connection, auth, or unknown.
        """
        url = self._full_url(endpoint)
        timeout = kwargs.pop("timeout", (self.config.connect_timeout, self.config.read_timeout))
        headers = self._session.headers.copy()
        headers.update(kwargs.pop("headers", {}))
        headers["X-Request-ID"] = str(uuid.uuid4())

        if "json" not in kwargs and "data" in kwargs and isinstance(kwargs["data"], (dict, list)):
            kwargs["json"] = kwargs.pop("data")

        if self._token_expiry and datetime.datetime.utcnow() >= self._token_expiry:
            self.refresh_token()

        try:
            start = time.time()
            response = self._session.request(
                method=method.upper(), url=url, timeout=timeout, headers=headers, **kwargs
            )
            self.last_response = response

            if response.status_code == 401 and self.config.token_url:
                logger.warning("401 Unauthorized: refreshing token")
                self.refresh_token()
                response = self._session.request(
                    method=method.upper(), url=url, timeout=timeout, headers=headers, **kwargs
                )
                self.last_response = response

            if response.status_code == 429 and "Retry-After" in response.headers:
                delay = int(response.headers["Retry-After"])
                logger.warning(f"429 Too Many Requests: retrying after {delay}s")
                time.sleep(delay)
                response = self._session.request(
                    method=method.upper(), url=url, timeout=timeout, headers=headers, **kwargs
                )
                self.last_response = response

            elapsed = time.time() - start
            logger.debug(f"{method.upper()} {url} completed in {elapsed:.3f}s")
            response.raise_for_status()
            return response
        except HTTPError as e:
            raise APIClientException(
                "HTTP error",
                code="http_error",
                status_code=e.response.status_code,
                original_exception=e,
            ) from e
        except requests.Timeout as e:
            raise APIClientException("Request timed out", code="timeout") from e
        except requests.ConnectionError as e:
            raise APIClientException("Connection error", code="connection_error") from e
        except Exception as e:
            raise APIClientException(
                "Unexpected error", code="unknown_error", original_exception=e
            ) from e

    def request(
        self, method: str, endpoint: str, retry_on_json_error: bool = False, **kwargs
    ) -> Any:
        """
        Executes a high-level HTTP request and attempts to parse the response as JSON.

        Parameters:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): API endpoint (relative or full URL)
            retry_on_json_error (bool): Whether to retry once on JSON decode errors
            **kwargs: Additional request options

        Returns:
            Parsed JSON object or plain text

        Raises:
            APIClientException: if the request or retry fails
        """

        response = self._request_raw(method, endpoint, **kwargs)
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except json.JSONDecodeError:
            if retry_on_json_error:
                logger.warning("JSON decode error, retrying once...")
                response = self._request_raw(method, endpoint, **kwargs)
                try:
                    return response.json()
                except Exception:
                    pass
            return response.text

    def get(self, endpoint: str, **kwargs):
        """
        Convenience method to perform a GET request.

        Parameters:
            endpoint (str): API endpoint
            **kwargs: Additional request parameters

        Returns:
            Parsed JSON or text
        """
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs):
        """
        Performs a POST request.

        Parameters:
            endpoint (str): API endpoint
            **kwargs: Additional request parameters

        Returns:
            Parsed JSON or text
        """
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs):
        """
        Performs a PUT request.

        Parameters:
            endpoint (str): API endpoint
            **kwargs: Additional request parameters

        Returns:
            Parsed JSON or text
        """
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs):
        """
        Performs a DELETE request.

        Parameters:
            endpoint (str): API endpoint
            **kwargs: Additional request parameters

        Returns:
            Parsed JSON or text
        """
        return self.request("DELETE", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs):
        """
        Performs a PATCH request.

        Parameters:
            endpoint (str): API endpoint
            **kwargs: Additional request parameters

        Returns:
            Parsed JSON or text
        """
        return self.request("PATCH", endpoint, **kwargs)

    def download(self, endpoint: str, dest_path: str, chunk_size: int = 8192, **kwargs) -> str:
        response = self._request_raw("GET", endpoint, stream=True, **kwargs)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
        return dest_path

    def upload(self, endpoint: str, file_path: str, field_name: str = "file", **kwargs) -> Any:
        with open(file_path, "rb") as f:
            files = {field_name: f}
            return self._session.post(self._full_url(endpoint), files=files, **kwargs)

    def stream(
        self, endpoint: str, chunk_size: int = 8192, **kwargs
    ) -> Generator[bytes, None, None]:
        response = self._request_raw("GET", endpoint, stream=True, **kwargs)
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk

    def set_header(self, key: str, value: str) -> None:
        """Set or overwrite a default header"""
        self._session.headers[key] = value

    def remove_header(self, key: str) -> None:
        """Remove a default header if present"""
        self._session.headers.pop(key, None)

    def close(self):
        """
        Closes the internal requests session.
        """
        self._session.close()

    def __enter__(self):
        """
        Enables context manager entry.

        Returns:
            APIClient: Self
        """
        return self

    def __exit__(self, *args):
        """
        Enables context manager exit and closes the session.
        """
        self.close()

    @classmethod
    def find_by_name(cls, name: str, results: list) -> list:
        """
        Lambda function to find by name
        """
        return list(filter(lambda x: x.get("name") == name, results))

    @classmethod
    def find_by_id(cls, id: int, results: list) -> list:
        """
        Lambda function to find by id
        """
        return list(filter(lambda x: x.get("id") == id, results))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple APIClient tester")
    parser.add_argument("base_url", help="API base URL")
    parser.add_argument("--endpoint", default="/health", help="Health check or test endpoint")
    args = parser.parse_args()

    cfg = APIClientConfig(base_url=args.base_url)
    client = APIClient(cfg)
    try:
        result = client.get(args.endpoint)
        print("Success:", result)
    except Exception as e:
        print("Error:", str(e))
