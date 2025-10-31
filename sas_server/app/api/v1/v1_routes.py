"""
FastAPI wrapper around your existing CLI modules.

How to run locally:
  pip install -r requirements.txt
  uvicorn server:app --host 0.0.0.0 --port 8000 --reload

Each endpoint accepts a `config_path` (path to your YAML config on disk),
then forwards to the corresponding API class and method.
"""

from fastapi import APIRouter
from .ansible import ansible_router
from .github import github_router
from .infoblox import infoblox_router
from .nutanix import nutanix_router
from .terraform import terraform_router


v1_router = APIRouter(prefix="/v1")

v1_router.include_router(ansible_router)
v1_router.include_router(github_router)
v1_router.include_router(infoblox_router)
v1_router.include_router(nutanix_router)
v1_router.include_router(terraform_router)
