import json
from base64 import b64decode
from typing import Any, Dict, Final, Optional

import yaml

from ..config.github_config import build_github_base_config, build_github_user_config
from ..utils.logger import get_logger
from ..utils.utils import build_overrides, validate_inputs_with_config
from .common.api_client import APIClient, APIClientConfig


class GitHubApi:
    """
    Client for interacting with the GitHub API to retrieve and parse project metadata files.

    This class provides methods to fetch YAML-based project metadata from a GitHub repository,
    decode and parse the data, and extract OS-specific project details.
    """

    PATH_VERSION: Final[str] = "/api/v3"
    PATH_GITHUB_PROJECTS_TEMPLATE: Final[str] = (
        f"{PATH_VERSION}/repos/{{owner}}/{{repo}}/contents"
    )

    def __init__(self):
        """
        Initialize the GitHub API client.

        Args:
            config (dict): A dictionary containing:
                - project_name (str): Default project file name
                - owner (str): GitHub repo owner
                - repo (str): GitHub repo name
        """
        self.logger = get_logger(__name__)
        self.config = build_github_base_config()
        self.client = APIClient(APIClientConfig.from_dict(self.config))

    def extract_and_log_metadata(self, parsed_yaml: dict, os_type: str) -> dict:
        """
        Extracts and logs relevant project metadata fields based on the OS type.

        Args:
            parsed_yaml (dict): Parsed YAML content from the project file.
            os_type (str): Operating system type ('linux' or 'windows').

        Returns:
            dict: Dictionary of extracted metadata fields.
        """
        os_type = os_type.lower()

        # Select OS-specific keys
        if os_type == "linux":
            keys_to_extract = ["server_support_group_rhel", "responsible_org_rhel"]
        elif os_type == "windows":
            keys_to_extract = ["server_support_group_win", "responsible_org_win"]
        else:
            raise ValueError(f"Unsupported OS type: {os_type}")

        # Add common metadata fields
        keys_to_extract += [
            "project_id",
            "project_poc",
            "project_frontline_mgr_seid",
            "project_branch_mgr_seid",
        ]

        # Extract fields, defaulting to 'N/A' if not found
        metadata = {k: parsed_yaml.get(k, "N/A") for k in keys_to_extract}

        # Log the metadata for visibility/debugging
        log_message = "\n".join(f"{k}: {v}" for k, v in metadata.items())
        self.logger.info(f"Project Metadata:\n{log_message}")

        return metadata

    # -------------------------
    # Small helpers
    # -------------------------
    def _validate_keys(self) -> Dict:
        validation = validate_inputs_with_config(
            args={
                "owner": self.config.get("owner"),
                "repo": self.config.get("repo"),
                "project_name": self.config.get("project_name"),
                "os_type": self.config.get("os_type"),
            },
            config=self.config,
            required_mappings={
                "owner": ["owner"],
                "repo": ["repo"],
                "project_name": ["project_name"],
                "os_type": ["os_type"],
            },
        )

        return validation

    from base64 import b64decode

    def get_file_text(
       self,
       owner: str,
       repo: str,
       path: str,
       ref: str = "main",
       user_config: dict = None,
    )  ->  str:
        """
        Return the decoded text content of a file from GitHub.
        Uses the GitHub 'contents' API and decodes base64 payload.
        """
       
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        # APIClient already carries base_url=https://api.github.com and Bearer token
        data = self.client.get(
           endpoint,
           params={"ref": ref}
        )
        if data.get("type") != "file":
            raise ValueError(f"{path} is not a file")
        content = data.get("content", "")
        if data.get("encoding") == "base64":
            return b64decode(content).decode("utf-8", errors="ignore")
        return content or ""

    def get_project_data(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        project_name: Optional[str] = None,
        os_type: Optional[str] = None,
        user_config: dict = None,
    ) -> Dict[str, Any]:
        """
        Download and parse a project YAML file from the GitHub repository.

        Args:
            owner (str, optional): GitHub organization or user. Defaults to config value.
            repo (str, optional): Repository name. Defaults to config value.
            project_name (str, optional): Name of the project file (without extension). Defaults to config value.
            os_type (str, optional): Operating system type for metadata filtering. Defaults to "Linux" through the caller.

        Returns:
            dict: Extracted metadata from the project file.

        Raises:
            RuntimeError: If the file content could not be retrieved from GitHub.
        """
        overrides = build_overrides(
            owner=owner, repo=repo, project_name=project_name, os_type=os_type
        )

        self.config = build_github_user_config(
            self.config, user_config=user_config, overrides=overrides
        )
        self.logger.debug(f"Resolved job config: {json.dumps(self.config, indent=2)}")

        # Validate keys
        validation = self._validate_keys()
        if validation["status"] == "error":
            self.logger.error(f"Missing Keys: {validation}")
            return f"Missing Keys: {validation}"

        self.logger.info(
            f"🚀 Getting project data from GitHub for project: {self.config.get('project_name')}"
        )

        try:
            # Build the full API endpoint for the YAML file
            endpoint = self.PATH_GITHUB_PROJECTS_TEMPLATE.format(
                owner=self.config.get("owner"), repo=self.config.get("repo")
            )
            endpoint += f"/{self.config.get('project_name').lower()}.yml"

            response = self.client.get(endpoint)

            # GitHub returns file content base64-encoded
            if "content" not in response:
                raise RuntimeError(f"Unable to retrieve YAML content from {endpoint}")

            content_str = b64decode(response["content"]).decode("utf-8")
            parsed_yaml = yaml.safe_load(content_str)

            self.logger.debug(
                f"Parsed YAML content from '{self.config.get('project_name')}.yml':\n"
                f"{json.dumps(parsed_yaml, indent=2)}"
            )

            metadata = self.extract_and_log_metadata(parsed_yaml, self.config.get("os_type"))
            return metadata
        except Exception as e:
            self.logger.exception(f"❌ Unexpected error: {e}")
