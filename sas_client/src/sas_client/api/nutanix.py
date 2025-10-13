import json
import time
from typing import Dict, List, Optional, Tuple

from ..config.nutanix_config import build_nutanix_base_config, build_nutanix_user_config
from ..utils.logger import get_logger
from ..utils.utils import build_overrides, make_id, validate_inputs_with_config
from .common.api_client import APIClient, APIClientConfig


class NutanixApi:
    PATH_VERSION = "/api/nutanix/v3"

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = build_nutanix_base_config()
        self.client = APIClient(APIClientConfig.from_dict(self.config))

    def fetch_project(self) -> Dict:
        """
        Fetch Calm Project details.
        """
        self.logger.info("Fetching project details...")
        body = {"kind": "project", "filter": f"name=={self.config.get('project')}"}
        path_url = f"{self.PATH_VERSION}/projects/list"
        return self.client.post(path_url, json=body)["entities"][0]

    def fetch_marketplace_item(self) -> Dict:
        """
        Fetch Marketplace Item by name (type=blueprint).
        """
        self.logger.info("Fetching marketplace blueprint...")
        body = {
            "kind": "marketplace_item",
            "filter": f"name=={self.config.get('marketplace_blueprint_name')};type==blueprint",
        }
        marketplace_list = self.client.post(
            f"{self.PATH_VERSION}/calm_marketplace_items/list", json=body
        )
        uuid = marketplace_list["entities"][0]["metadata"]["uuid"]
        return self.client.get(f"{self.PATH_VERSION}/calm_marketplace_items/{uuid}")

    def prepare_template_spec(self, template_spec: dict, project: dict) -> dict:
        """
        Template Spec injection
        """
        template_spec.pop("name", None)
        template_spec["app_blueprint_name"] = (
            f"{self.config.get('marketplace_blueprint_name')}-{make_id(8)}"
        )
        template_spec["environment_uuid"] = project["spec"]["resources"][
            "environment_reference_list"
        ][0]["uuid"]
        return template_spec

    def launch_marketplace_blueprint(
        self, template_spec: Dict, project: Dict, marketplace_item: Dict
    ) -> str:
        self.logger.info("Launching marketplace blueprint...")
        payload = {
            "spec": template_spec,
            "metadata": {
                "kind": "blueprint",
                "project_reference": {"kind": "project", "uuid": project["metadata"]["uuid"]},
                "categories": marketplace_item["metadata"]["categories"],
            },
            "api_version": "3.1",
        }
        return self.client.post(f"{self.PATH_VERSION}/blueprints/marketplace_launch", json=payload)[
            "metadata"
        ]["uuid"]

    def get_runtime_variables(self, blueprint_uuid: str) -> Tuple[str, List[dict]]:
        """
        Build runtime variables.
        """
        self.logger.info("Fetching runtime editables...")
        response = self.client.get(
            f"{self.PATH_VERSION}/blueprints/{blueprint_uuid}/runtime_editables"
        )
        app_profile_uuid = response["resources"][0]["app_profile_reference"]["uuid"]

        wanted = {
            "hostname",
            "owner_email",
            "owner_seid",
            "location",
            "environment",
            "domain",
            "buildenv",
            "type",
            "os_type",
        }

        variables = []
        server_data = self.config.get("server_data", {})

        for profile in response["resources"]:
            variable_list = profile.get("runtime_editables", {}).get("variable_list", [])
            for var in variable_list:
                name = var.get("name")
                if name in wanted and (name in self.config or name in server_data):
                    value = server_data.get(name, self.config.get(name))
                    variables.append(
                        {
                            "name": name,
                            "uuid": var["uuid"],
                            "value": {
                                "value": value,
                                "context": "app_profile.Default.variable",
                            },
                        }
                    )

        return app_profile_uuid, variables

    def simple_launch_app(
        self, blueprint_uuid: str, app_profile_uuid: str, variables: list, app_name: str
    ) -> str:
        """
        Launching application from blueprint...
        """
        self.logger.info("Launching application from blueprint...")
        payload = {
            "spec": {
                "app_name": app_name,
                "app_description": self.config.get("app_description") or "Test launch from API",
                "app_profile_reference": {
                    "kind": "app_profile",
                    "name": "Default",
                    "uuid": app_profile_uuid,
                },
                "runtime_editables": {"variable_list": variables},
            }
        }
        response = self.client.post(
            f"{self.PATH_VERSION}/blueprints/{blueprint_uuid}/simple_launch", json=payload
        )
        return response["status"]["request_id"]

    def watch_launch_status(
        self, blueprint_uuid: str, request_id: str, timeout: int = 100, interval: int = 10
    ):
        url = f"{self.PATH_VERSION}/blueprints/{blueprint_uuid}/pending_launches/{request_id}"
        elapsed = 0
        app_uuid = None

        self.logger.info(f"request_id: {request_id}")
        while elapsed < timeout:
            response = self.client.get(url)
            status = response.get("status", {})
            app_uuid = status.get("application_uuid")
            state = status.get("state")

            self.logger.info(f"⏳ Elapsed: {elapsed}s | Status: {state}")
            if state in ["success", "failure"]:
                return state, app_uuid
            time.sleep(interval)
            elapsed += interval
        return "timed out", app_uuid

    def wait_for_app_provisioning(self, app_uuid: str, max_wait, interval) -> str:
        self.logger.info(f"Waiting for app {app_uuid} to be provisioned...")
        elapsed = 0
        final_state = "unknown"
        while elapsed < max_wait:
            try:
                response = self.client.get(f"{self.PATH_VERSION}/apps/{app_uuid}")
                final_state = response.get("status", {}).get("state", "").lower()
                self.logger.info(f"⏳ Elapsed: {elapsed}s | App state: {final_state}")
                if final_state in ["running", "provisioned", "stopped", "error", "failed"]:
                    break
            except Exception as e:
                self.logger.warning(f"Error checking app status: {e}")
            time.sleep(interval)
            elapsed += interval
        return final_state

    def delete_app(self, app_uuid: str, state: str):
        self.logger.info(f"App {app_uuid} reached state '{state}'. Proceeding to delete...")
        try:
            self.client.delete(f"{self.PATH_VERSION}/apps/{app_uuid}")
            self.logger.info("✅ Application deleted.")
            return "DELETED"
        except Exception as e:
            self.logger.error(f"❌ Failed to delete app: {e}")
            return "FAILED"

    # -------------------------
    # Small helpers
    # -------------------------
    def _validate_keys(self) -> Dict:
        validation = validate_inputs_with_config(
            args={
                "project": self.config.get("project"),
                "owner_email": self.config.get("owner_email"),
                "owner_seid": self.config.get("owner_seid"),
                "server_data": self.config.get("server_data"),
            },
            config=self.config,
            required_mappings={
                "project": ["project"],
                "owner_email": ["owner_email"],
                "owner_seid": ["owner_seid"],
                "server_data": ["server_data"],
                "os_type": ["server_data", "os_type"],
                "location": ["server_data", "location"],
                "environment": ["server_data", "environment"],
            },
            json_decode_fields={"server_data"},
        )

        return validation

    def _execute_launch_flow(self, app_name: str) -> Tuple[Optional[str], str]:
        """
        Perform the Calm launch sequence with optional per-call overrides.
        Returns: (app_uuid, status)
        """
        project = self.fetch_project()
        mkt_item = self.fetch_marketplace_item()
        template_spec = self.prepare_template_spec(
            mkt_item["spec"]["resources"]["app_blueprint_template"]["spec"], project
        )
        blueprint_uuid = self.launch_marketplace_blueprint(template_spec, project, mkt_item)
        app_profile_uuid, variables = self.get_runtime_variables(blueprint_uuid)
        request_id = self.simple_launch_app(blueprint_uuid, app_profile_uuid, variables, app_name)
        status, app_uuid = self.watch_launch_status(blueprint_uuid, request_id)

        return app_uuid, status

    def _log_launch_result(self, status: str, app_name: str) -> None:
        if status == "success":
            self.logger.info(f"✅ Launched app: {app_name} with status: {status}")
        else:
            self.logger.error(f"❌ Launch failed with status: {status}")

    def launch_app(
        self,
        project: Optional[str] = None,
        owner_email: Optional[str] = None,
        owner_seid: Optional[str] = None,
        server_data: Optional[str] = None,
        user_config: dict = None,
    ) -> str:
        """
        Main launcher: launches app, logs result.
        If wait_for_app is True (or config['wait_for_app'] is truthy), will block
        until the app reaches a terminal provisioning state (or times out).
        """
        overrides = build_overrides(
            project=project, owner_email=owner_email, owner_seid=owner_seid, server_data=server_data
        )

        self.config = build_nutanix_user_config(
            self.config, user_config=user_config, overrides=overrides
        )
        if isinstance(self.config.get("server_data"), str):
            self.config["server_data"] = json.loads(self.config.get("server_data"))
        self.logger.debug(f"Resolved job config: {json.dumps(self.config, indent=2)}")

        validation = self._validate_keys()
        if validation["status"] == "error":
            self.logger.error(f"Missing Keys: {validation}")
            return f"Missing Keys: {validation}"

        self.logger.info(
            f"🚀 Launching Nutanix Market Place Blueprint for project={self.config.get('project')}"
        )

        try:
            app_name = f"{self.config.get('project')}-{self.config['server_data']['os_type']}-{self.config['server_data']['location']}-{self.config['server_data']['environment']}-{make_id(6)}"

            app_uuid, status = self._execute_launch_flow(app_name)

            self._log_launch_result(status, app_name)

            final_state = status
            if self.config.get("wait_for_app") and status == "success" and app_uuid:
                final_state = self.wait_for_app_provisioning(
                    app_uuid,
                    max_wait=self.config.get("provision_max_wait"),
                    interval=self.config.get("provision_interval"),
                )

            delete_after = self.config.get("delete_app_after_launch")
            if delete_after and app_uuid:
                final_state = self.delete_app(app_uuid, final_state)

            self.logger.info(f"✅ App {app_name} provisioning finished with state: {final_state}")

            return final_state

        except Exception as e:
            self.logger.exception(f"❌ Unexpected error: {e}")
