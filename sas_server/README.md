
# sas_server API wrapper

This adds a FastAPI layer over your existing CLI code.

## Layout
- `routes.py` — FastAPI app exposing endpoints for ansible, github, infoblox, nutanix, nexus, and terraform.
- `requirements.txt` — minimal deps.

## Run

1) Ensure Python 3.9+ and install deps:

```bash
pip install -r requirements.txt
```

2) Install the sas-client package.

```bash
pip install sas-client
```

3) Start the API server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4) Hit endpoints:

- Terraform onboarding:

```bash
curl -X POST http://localhost:8000/api/v1/terraform/onboard \
  -H "Content-Type: application/json" \
  -d '{
        "config_path": "/path/to/config/terraform.yaml",
      }'
```

```bash
curl -X POST http://localhost:8000/api/v1/terraform/onboard \
  -H "Content-Type: application/json" \
  -d '{
        "organization": "acme",
        "team_name": "platform",
        "project_name": "cloud-core",
        "members": ["alice@example.com", "bob@example.com"]
      }'
```

