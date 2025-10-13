from fastapi import APIRouter, HTTPException
from sas_client.api.ansible import AnsibleApi
from pydantic import BaseModel
from typing import Optional
from sas_client.utils.utils import load_config


ansible_router = APIRouter(prefix="/ansible")


# ---- Ansible ----
class AnsibleRunInput(BaseModel):
    config_path: Optional[str] = None
    job_template_name: Optional[str] = None
    job_data: Optional[str] = None


@ansible_router.post("/run_job")
def ansible_run_job(body: AnsibleRunInput):
    try:
        user_config = {}
        if body.config_path:
            user_config = load_config(body.config_path)
        api = AnsibleApi()
        result = api.run_job(
            body.job_template_name, body.job_data, user_config=user_config
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
