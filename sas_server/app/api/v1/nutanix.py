from sas_client.api.nutanix import NutanixApi
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from sas_client.utils.utils import load_config


nutanix_router = APIRouter(prefix="/nutanix")


# ---- Nutanix ----
class NutanixRunInput(BaseModel):
    config_path: Optional[str] = None
    project: Optional[str] = None
    owner_seid: Optional[str] = None
    owner_email: Optional[str] = None
    server_data: Optional[str] = None


@nutanix_router.post("/launch_app")
def nutanix_launch_app(body: NutanixRunInput):
    try:
        user_config = {}
        if body.config_path:
            user_config = load_config(body.config_path)
        api = NutanixApi()
        result = api.launch_app(
            body.project,
            body.owner_email,
            body.owner_seid,
            body.server_data,
            user_config=user_config,
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
