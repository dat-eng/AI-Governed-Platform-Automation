from sas_client.api.infoblox import InfobloxApi
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from sas_client.utils.utils import load_config


infoblox_router = APIRouter(prefix="/infoblox")


# ---- Infoblox ----
class InfobloxRunInput(BaseModel):
    config_path: Optional[str] = None
    network_cidr: Optional[str] = None
    network_cidr_v6: Optional[str] = None
    mac: Optional[str] = None
    fqdn: Optional[str] = None


@infoblox_router.post("/host_record_exists")
def infoblox_host_exists(body: InfobloxRunInput):
    try:
        user_config = {}
        if body.config_path:
            user_config = load_config(body.config_path)
        api = InfobloxApi()
        result = api.host_record_exists(body.fqdn, user_config=user_config)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@infoblox_router.post("/get_next_available_ip_v4")
def infoblox_get_next_available_ip_v4(body: InfobloxRunInput):
    try:
        user_config = {}
        if body.config_path:
            user_config = load_config(body.config_path)
        api = InfobloxApi()
        result = api.get_next_available_ip(
            "v4", body.network_cidr, user_config=user_config
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@infoblox_router.post("/get_next_available_ip_v6")
def infoblox_get_next_available_ip_v6(body: InfobloxRunInput):
    try:
        user_config = {}
        if body.config_path:
            user_config = load_config(body.config_path)
        api = InfobloxApi()
        result = api.get_next_available_ip(
            "v6", body.network_cidr_v6, user_config=user_config
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
