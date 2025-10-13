rom fastapi import APIRouter
from .v1.v1_routes import v1_router
 
api_router = APIRouter(prefix="/api")
 
api_router.include_router(v1_router)