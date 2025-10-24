# AI-Governed Platform Automation
> **Intelligent, Zero-Trust provisioning framework for data platforms using Terraform, Nutanix Calm, Vault, FastAPI, and agent-triggerable APIs.**
>
> Designed for **GovCloud, financial, and regulated enterprise environments** where **self-service automation must still enforce compliance (HIPAA, SOC2)**.

---

## 🚀 Mission

Modern platform engineering isn’t just about IaC — it’s about **governed, policy-aware orchestration** that can be safely triggered via **CLI, CI/CD, or AI agents** without sacrificing **auditability or Zero-Trust enforcement**.

This framework turns platform actions like *“Provision Snowflake SBX with Vault-approved credentials and Infoblox DNS registration”* into **secure, API-exposed, agent-ready automation flows**.

---

## 🧠 High-Level Architecture

### AI Agent / ChatOps / Developer CLI UI ###    
- Natural Language
- CLI Command


### FastAPI Service Layer (sas_server) ###                    
- Receives intent or API calls                                           
- Validates policy context (SBX/DEV/PROD, ownership, tags)               
- Authenticates via Vault-issued token                                   


### Python Orchestration Client (sas_client) ###                   
- Wraps Nutanix Calm, Terraform, Infoblox, Vault, Ansible APIs           
- Encapsulates provisioning logic into reusable modules                  
- Enforces Zero-Trust — no static credentials ever stored                


### Provisioning Layer: Nutanix Calm • Terraform + Sentinel • Infoblox • Vault ###
- Calm builds infrastructure                                             
- Terraform applies policy-as-code and tags                              
- Vault issues short-lived tokens                                        
- Infoblox registers IP/DNS securely                                     

---

## 🔐 Compliance Positioning

| Control Area                     | How This Framework Enforces It                                              |
|--------------------------------|----------------------------------------------------------------------------|
| **Zero-Trust Access**          | Vault-issued ephemeral tokens replace static credentials                   |
| **FedRAMP/FISMA Alignment**    | Sentinel policies + audit logs on every Terraform/Calm call                |
| **Auditability**               | All requests logged via FastAPI layer with user + policy context           |
| **Separation of Duties**       | API gateway separates intent submission from provisioning execution        |
| **Agent-Safe Execution**       | Every action exposed via scoped endpoints safe for AI/ChatOps triggering  |

---

## ✅ Current Capabilities

| Capability                                                            | Status |
|---------------------------------------------------------------------|:------:|
| Terraform scaffold provisioning with Sentinel guardrails            | ✅     |
| Nutanix Calm blueprint orchestration via Python API                 | ✅     |
| Infoblox IP/hostname registration + tagging                         | ✅     |
| Vault token authentication & secret injection                       | ✅     |
| FastAPI endpoint layer (agent-triggerable)                          | ✅     |
| GitHub/GitLab CI pipeline packaging for Python modules              | ✅     |
| Red Hat Developer Hub integration for discovery & onboarding        | ✅     |
| Drift detection hooks                                               | 🔄 Planned |
| Remediation via agent feedback loop                                 | 🔄 Planned |
| AI Prompt → Policy Bundle selection (LLM-driven routing)            | 🚀 Roadmap |

---

## 🎯 Example — Agent or CLI Trigger

**Natural language (future AI agent prompt):**
> _“Provision Snowflake SBX environment for user `alice`, apply `fedramp_sbx_default` policy, and register DNS with Infoblox.”_

**Equivalent FastAPI Call:**
```bash
curl -X POST https://platform.company.local/api/v1/provision \
  -H "Authorization: Bearer $VAULT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "environment": "SBX",
        "service": "snowflake",
        "owner": "alice",
        "policy_bundle": "fedramp_sbx_default",
        "dns": true,
        "tags": {
            "business_unit": "platform",
            "compliance": "fedramp"
        }
      }'


⸻

📦 Repo Structure 

ai-governed-platform-automation/
├─ docs/
│  ├─ architecture.md              # Expanded diagrams + sequence flow for interviews
│  ├─ threat-model.md              # Zero-Trust and credential handling notes
│  └─ roadmap.md                   # Agent routing, drift remediation, policy extension
├─ modules/
│  ├─ sas-client/                  # (Linked or submodule) Python orchestration client
│  ├─ sas-server/                  # FastAPI agent gateway layer
│  ├─ terraform-templates/         # Policy-enforced starter modules (Sentinel included)
│  ├─ calm-blueprints/             # Sanitized blueprint structure
│  ├─ vault-patterns/              # Example approles, policies (placeholders)
│  └─ infoblox/                    # DNS registration workflow examples
├─ examples/
│  ├─ provision_sbx_env.md         # End-to-end sample flow with logs
│  └─ agent_trigger.md             # AI/ChatOps invocation concept
├─ ci/
│  └─ github-actions.yaml          # Packaging/validation workflow
└─ README.md                       # (this file)

🔭 Roadmap Highlights
	•	✅ Current: Unified platform automation with Vault + Calm + Terraform + FastAPI
	•	🚀 Next: Agent intent → auto-map to policy bundles (fedramp_sbx, hipaa_dev, etc.)
	•	🎯 Future: Drift detection + automatic Terraform plan review via AI agent
	•	🧠 Stretch Goal: “Explain this provisioning plan” — agent explains the compliance posture of a requested build

⸻

📄 License

Apache-2.0 (recommended for platform tooling repositories exposed publicly)

⸻

🎯 Suggested GitHub Topics

platform-automation • zero-trust • vault • terraform • nutanix-calm • govcloud • fastapi • sas • sentinel • ai-ops • devex • backstage • red-hat-developer-hub
