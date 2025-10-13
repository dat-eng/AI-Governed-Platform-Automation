from sas_client.api.terraform import TerraformApi
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sas_client.utils.utils import load_config


terraform_router = APIRouter(prefix="/terraform")


# ---- Terraform ----
class TerraformRunInput(BaseModel):
    config_path: Optional[str] = None
    organization: Optional[str] = None
    team_name: Optional[str] = None
    project_name: Optional[str] = None
    members: Optional[List[str]] = None


@terraform_router.post("/onboard")
def terraform_onboard(body: TerraformRunInput):
    try:
        user_config = {}
        if body.config_path:
            user_config = load_config(body.config_path)
        api = TerraformApi()
        result = api.launch_onboard(
            body.organization,
            body.team_name,
            body.project_name,
            body.members,
            user_config=user_config,
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
