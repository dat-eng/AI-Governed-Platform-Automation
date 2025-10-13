import json
from string import Template
from typing import Any, Dict, Optional

from ..config.terraform_config import build_terraform_base_config, build_terraform_user_config
from ..utils.logger import get_logger
from ..utils.utils import build_overrides, validate_inputs_with_config
from .common.api_client import APIClient, APIClientConfig


class TerraformApi:
    """
    A class for interacting with Terraform via REST API.

    Orchestrates a full Terraform Enterprise onboarding flow.
    """

    PATH_TEAM_TEMPLATE = Template("api/v2/organizations/$organization/teams")
    PATH_ORGANIZATION_MEMBERSHIP_TEMPLATE = Template(
        "api/v2/organizations/$organization/organization-memberships"
    )
    PATH_PROJECT_TEMPLATE = Template("api/v2/organizations/$organization/projects")
    PATH_WORKSPACE_TEMPLATE = Template("api/v2/organizations/$organization/workspaces/$workspace")
    PATH_CREATE_WORKSPACE_TEMPLATE = Template("api/v2/organizations/$organization/workspaces")
    PATH_TEAM_MEMBERSHIP_USER_ID_TEMPLATE = Template("api/v2/teams/$team_id/relationships/users")
    PATH_TEAM_MEMBERSHIP_ORG_MEMBER_ID_TEMPLATE = Template(
        "api/v2/teams/$team_id/relationships/organization-memberships"
    )
    PATH_OAUTH_CLIENT_TEMPLATE = Template("api/v2/organizations/$organization/oauth-clients")
    PATH_OAUTH_TOKEN_TEMPLATE = Template("api/v2/oauth-clients/$oauth_client_id/oauth-tokens")
    PATH_VARIABLE_SET_TEMPLATE = Template("api/v2/organizations/$organization/varsets")
    PATH_WORKSPACE_VARIABLE_SET_TEMPLATE = Template(
        "api/v2/varsets/$variable_set_id/relationships/workspaces"
    )
    PATH_ORGANIZATION = "api/v2/organizations"
    PATH_PROJECTS = "api/v2/team-projects"
    PATH_TEAM_ACCESS = "api/v2/team-workspaces"
    PATH_PROJECT_TEAM_ACCESS = "api/v2/team-projects"
    PATH_GITHUB_APP_INSTALLATION = "api/v2/github-app/installations"

    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = build_terraform_base_config()
        self.client = APIClient(APIClientConfig.from_dict(self.config))
        self.client._session.headers.update(
            {
                "Content-Type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json",
            }
        )

    def check_team_access_to_project_by_name(
        self, organization: str, project_name: str, team_name: str
    ) -> bool:
        """Find team access to a project"""
        project_id = self.find_project(organization, project_name)
        team_id = self.find_team(organization, team_name)

        team_found = False

        if project_id is not None:
            path = self.PATH_PROJECT_TEAM_ACCESS + f"?filter[project][id]={project_id}"

            response = self.client.get(path)
            results = response.get("data", [])

            for data in results:
                if data["relationships"]["team"]["data"]["id"] == team_id:
                    team_found = True
                    break

        return team_found

    def add_team_access_to_project(
        self,
        organization: str,
        project_name: str,
        team_name: str,
        access: str,
        project_access: dict = None,
        workspace_access: dict = None,
    ) -> dict:
        """Add team access to a project"""
        project_id = self.find_project(organization, project_name)
        team_id = self.find_team(organization, team_name)

        team_project_access_exists = self.check_team_access_to_project_by_name(
            organization=organization, project_name=project_name, team_name=team_name
        )

        if team_project_access_exists:
            return

        if project_id is not None and team_id is not None:
            path = self.PATH_PROJECT_TEAM_ACCESS

            data = {
                "data": {
                    "type": "team-projects",
                    "attributes": {"access": access},
                    "relationships": {
                        "project": {"data": {"type": "projects", "id": project_id}},
                        "team": {"data": {"type": "teams", "id": team_id}},
                    },
                }
            }

            if project_access is not None:
                data["data"]["attributes"]["project-access"] = project_access

            if workspace_access is not None:
                data["data"]["attributes"]["workspace-access"] = workspace_access

            response = self.client.post(path, json=data)
            results = response.get("data", [])

            team_project_access = {
                "id": results["id"],
                "project_id": results["relationships"]["project"]["data"]["id"],
                "team_id": results["relationships"]["team"]["data"]["id"],
            }

            return team_project_access

    def add_user_to_team_by_org_member_id(
        self, organization: str, email: str, team_name: str
    ) -> dict:
        """Add user to a team with organization membership ID"""
        user = self.find_user_by_email(organization=organization, email=email)
        team_id = self.find_team(organization, team_name)

        if user is not None and team_id is not None:
            matches = list(filter(lambda x: x["id"] == team_id, user["teams"]))

            # No matches; user isn't already a member of the team
            if len(matches) < 1:
                path = self.PATH_TEAM_MEMBERSHIP_ORG_MEMBER_ID_TEMPLATE.substitute(
                    {"team_id": team_id}
                )

                data = {"data": {"type": "organization-memberships", "id": user["id"]}}

                self.client.post(path, json=data)

    def find_user_by_email(self, organization: str, email: str) -> dict:
        """Search for a user and return its ID"""
        path = self.PATH_ORGANIZATION_MEMBERSHIP_TEMPLATE.substitute({"organization": organization})
        params = {"email": email}
        response = self.client.get(path, params=params)
        results = response.get("data", [])

        if results:
            self.logger.info(f"User {email} exists")
            return {
                "email": email,
                "id": results[0].get("id"),
                "teams": results[0]["relationships"]["teams"]["data"],
            }

        return None

    def invite_user_to_organization(self, organization: str, email: str) -> dict:
        """Invite a new user to a organization"""
        # Check if user is already in organization
        user = self.find_user_by_email(organization=organization, email=email)

        if user is None:
            path = (
                self.PATH_ORGANIZATION_MEMBERSHIP_TEMPLATE.substitute(
                    {"organization": organization}
                )
                + f"?q={email}"
            )

            data = {"data": {"type": "organization-memberships", "attributes": {"email": email}}}

            response = self.client.post(path, json=data)
            response.get("data", [])

            self.logger.info("Invited user to org %s: %s", organization, email)

    def find_team(self, org: str, name: str) -> Optional[str]:
        # GET /api/v2/organizations/:organization/teams?search[name]=NAME (API supports filters/pagination)
        res = self.client.get(f"/api/v2/organizations/{org}/teams")
        for d in res.get("data", []):
            if d["attributes"]["name"] == name:
                return d["id"]
        return None

    def create_team(self, org: str, name: str) -> str:
        # POST /api/v2/organizations/:organization/teams
        payload = {"data": {"type": "teams", "attributes": {"name": name}}}
        res = self.client.post(f"/api/v2/organizations/{org}/teams", json=payload)
        return res["data"]["id"]

    def ensure_team(self, org: str, name: str) -> str:
        team_id = self.find_team(org, name)
        if team_id:
            self.logger.info("Team exists: %s (%s)", name, team_id)
            return team_id
        self.logger.info("Creating team: %s", name)
        return self.create_team(org, name)

    def find_project(self, org: str, name: str) -> Optional[str]:
        # GET /api/v2/organizations/:organization/projects
        res = self.client.get(f"/api/v2/organizations/{org}/projects")
        for d in res.get("data", []):
            if d["attributes"]["name"] == name:
                return d["id"]
        return None

    def create_project(self, org: str, name: str) -> str:
        # POST /api/v2/organizations/:organization/projects
        payload = {"data": {"type": "projects", "attributes": {"name": name}}}
        res = self.client.post(f"/api/v2/organizations/{org}/projects", json=payload)
        return res["data"]["id"]

    def ensure_project(self, org: str, name: str) -> str:
        pid = self.find_project(org, name)
        if pid:
            self.logger.info("Project exists: %s (%s)", name, pid)
            return pid
        self.logger.info("Creating project: %s", name)
        return self.create_project(org, name)

    def find_workspace(self, organization: str, workspace_name: str) -> Optional[str]:
        """Search for a workspace and return its ID"""
        resp = self.client.get(f"/api/v2/organizations/{organization}/workspaces")

        for d in resp.get("data", []):
            if d["attributes"]["name"] == workspace_name:
                return d["id"]

        return None

    def create_workspace(
        self, organization: str, project_id: str, workspace_name: str, attributes: Dict[str, Any]
    ) -> str:
        """
        POST /api/v2/organizations/:organization/workspaces
        associate with project via relationships.project
        """
        workspace_id = self.find_workspace(organization, workspace_name)
        if workspace_id:
            self.logger.info("Workspace exists: %s (%s)", workspace_name, workspace_id)
            return workspace_id

        endpoint = self.PATH_CREATE_WORKSPACE_TEMPLATE.substitute(
            {"organization": organization, "workspace": workspace_name}
        )
        payload = {
            "data": {
                "type": "workspaces",
                "attributes": {"name": workspace_name, **(attributes or {})},
                "relationships": {
                    "organization": {"data": {"type": "organizations", "id": organization}},
                    "project": {"data": {"type": "projects", "id": project_id}},
                },
            }
        }
        res = self.client.post(endpoint, json=payload)
        return res["data"]["id"]

    def find_variable_set(self, organization: str, variable_set_name: str) -> Optional[str]:
        """Search for a workspace and return its ID"""
        resp = self.client.get(f"/api/v2/organizations/{organization}/varsets")

        for d in resp.get("data", []):
            if d["attributes"]["name"] == variable_set_name:
                return d["id"]

        return None

    def attach_variable_set(
        self, organization: str, workspace_id: str, variable_set_name: str
    ) -> None:
        """
        Variable Sets API (attach to workspace)
        """

        # Check if variable set exists
        variable_set_id = self.find_variable_set(organization, variable_set_name)

        if variable_set_id is not None:
            path = self.PATH_WORKSPACE_VARIABLE_SET_TEMPLATE.substitute(
                {"variable_set_id": variable_set_id}
            )

            data = {"data": [{"type": "workspaces", "id": workspace_id}]}
            self.client.post(path, json=data)

    # -------------------------
    # Small helpers
    # -------------------------
    def _validate_keys(self) -> Dict:
        validation = validate_inputs_with_config(
            args={
                "organization": self.config.get("organization"),
                "team_name": self.config.get("team_name"),
                "project_name": self.config.get("project_name"),
                "members": self.config.get("members"),
            },
            config=self.config,
            required_mappings={
                "project_name": ["project", "name"],
                "team_name": ["team", "name"],
                "organization": ["organization"],
                "members": ["team", "members"],
            },
        )

        return validation

    def launch_onboard(
        self,
        organization: Optional[str] = None,
        team_name: Optional[str] = None,
        project_name: Optional[str] = None,
        members: Optional[list] = None,
        user_config: dict = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates a full Terraform Enterprise onboarding flow:
          - Ensure team
          - Invite members to org and team
          - Ensure project
          - Grant project access to team
          - Create workspace and attach variable sets
        """
        overrides = build_overrides(
            organization=organization,
            team_name=team_name,
            project_name=project_name,
            members=members,
        )

        self.config = build_terraform_user_config(
            self.config, user_config=user_config, overrides=overrides
        )
        self.logger.debug(f"Resolved job config: {json.dumps(self.config, indent=2)}")

        # Validate keys
        validation = self._validate_keys()
        if validation["status"] == "error":
            self.logger.error(f"Missing Keys: {validation}")
            return f"Missing Keys: {validation}"

        # Initialize params
        project_name = self.config["project_name"]
        team_name = self.config["team_name"]
        organization = self.config["organization"]
        members = self.config["members"]

        self.logger.info(
            f"🚀 Launching Terraform onboarding for team={self.config.get('team_name')}, project={self.config.get('project_name')}"
        )

        # Create team
        team_id = self.ensure_team(organization, team_name)

        # Invite + add members
        for email in members:
            self.invite_user_to_organization(organization, email)
            self.add_user_to_team_by_org_member_id(organization, email, team_name)

        # Ensure project
        project_id = self.ensure_project(organization, project_name)

        self.logger.info(f"Adding TFE {team_name} access to {project_name} project")
        self.add_team_access_to_project(
            organization=organization,
            project_name=project_name,
            team_name=team_name,
            access=self.config["project"]["access"],
            project_access=None,
            workspace_access=None,
        )

        # Create the workspace under project
        workspace_name = project_name
        workspace_attributes = self.config["project"]["workspace"]["attributes"]
        self.logger.info(f"Creating TFE {workspace_name} workspace")
        workspace_id = self.create_workspace(
            organization=organization,
            project_id=project_id,
            workspace_name=workspace_name,
            attributes=workspace_attributes,
        )

        # Attach var sets if any
        variable_set_name = self.config["project"]["workspace"]["variable_set"]
        if variable_set_name:
            self.attach_variable_set(organization, workspace_id, variable_set_name)
            self.logger.info(
                f"Attached variable set {variable_set_name} to workspace {workspace_name}"
            )

        result = {
            "organization": organization,
            "team": {"name": team_name, "id": team_id, "members": members},
            "project": {"name": project_name, "id": project_id},
            "workspace": {"name": workspace_name, "id": workspace_id},
        }
        self.logger.info(f"✅ Onboarding complete: {result}")
        return result
