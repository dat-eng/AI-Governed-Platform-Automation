from sas_client.api.github import GitHubApi
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from sas_client.utils.utils import load_config


github_router = APIRouter(prefix="/github")


# ---- GitHub ----
class GitHubRunInput(BaseModel):
    config_path: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    project_name: Optional[str] = None
    os_type: Optional[str] = None


@github_router.post("/get_project_data")
def github_get_project_data(body: GitHubRunInput):
    try:
        user_config = {}
        if body.config_path:
            user_config = load_config(body.config_path)
        api = GitHubApi()
        result = api.get_project_data(
            body.owner,
            body.repo,
            body.project_name,
            body.os_type,
            user_config=user_config,
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
