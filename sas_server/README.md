
# sas_server — FastAPI Gateway for AI-Governed Platform Automation
> **API gateway that exposes Terraform, Calm, Vault, and Infoblox provisioning workflows as secure, agent-triggerable service endpoints.**
>
> Designed for **GovCloud, enterprise platform teams, and AI/ChatOps orchestration**, where developers or AI agents can request infrastructure via **natural language → API → Terraform/Vault pipeline**, all under **Zero-Trust, policy-controlled execution**.

---

## 🎯 Purpose

`sas_server` turns orchestration logic from `sas_client` into a **service layer** — making platform provisioning:
- **Discoverable** by developers via `/docs` (OpenAPI + Red Hat Developer Hub integration)
- **Callable by CI/CD** workflows safely (no Vault credentials exposed)
- **Triggerable by AI Agents** that convert natural language into JSON payloads
- **Compliant by default**, thanks to Vault-token requirement and Sentinel policy enforcement

> 💡 Think of this as the **“Platform Gateway”** — the endpoint an AI agent, ChatOps bot, or self-service portal talks to, instead of hitting Terraform or Calm directly.

---

## 🔐 Zero-Trust API Model

- Every request **requires a Vault-issued Bearer token** — no static credentials ever stored in server config.
- Policies applied via **Sentinel / Terraform** bundles control **who can provision what, in which environment**.
- All requests are **audited with user, policy_bundle, infra scope, and tags**.

## 🚀 Example API Call
#### Terraform onboarding:

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


