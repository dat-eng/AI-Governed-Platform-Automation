"""
FastAPI wrapper around your existing CLI modules.
 
How to run locally:
  pip install -r requirements.txt
  uvicorn server:app --host 0.0.0.0 --port 8000 --reload
 
Each endpoint accepts a `config_path` (path to your YAML config on disk),
then forwards to the corresponding API class and method.
"""
 
from fastapi import FastAPI
from .api.api_routes import api_router
from fastapi.responses import RedirectResponse
 
app = FastAPI(title="SAS Server API", version="0.1.0")
 
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
 
@app.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(url="/docs", status_code=308)
 
# Mount versioned routers
app.include_router(api_router)