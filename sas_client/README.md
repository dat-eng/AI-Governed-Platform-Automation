# sas_client — Unified Platform Orchestration Client
> **Python-based orchestration client that abstracts Terraform, Nutanix Calm, Infoblox, Ansible, and Vault into a single automation interface — designed for Zero-Trust, policy-aware, AI-triggerable provisioning workflows.**

---

## 🎯 Purpose

`sas_client` consolidates multiple infrastructure automation tools behind a **clean, Python-based command and API surface**, allowing developers, CI pipelines, or AI agents to trigger compliant platform provisioning without direct access to Vault, Terraform Cloud, or Nutanix consoles.

This client abstracts low-level calls to:
| System            | Purpose |
|------------------|--------|
| **Nutanix Calm** | Provision base infrastructure (VMs, projects, blueprints) |
| **Terraform + Sentinel** | Apply policy-enforced provisioning templates |
| **Infoblox** | Reserve IP and register DNS/hostnames |
| **Vault (Zero-Trust Security)** | Issue short-lived tokens for secure execution |
| **Ansible Automation** | Bootstrap environment or perform post-provision steps |

---

## 🔐 Zero-Trust Security Model

✅ No static credentials are stored.  
✅ Every execution requests **ephemeral tokens from Vault**, using `approle` or `jwt` auth.  
✅ All downstream automation (Terraform, Calm, Infoblox) runs **with least-privilege scoped tokens**.  
✅ Designed so **AI agents or CI/CD pipelines** can call platform actions **safely without elevated credentials**.

---

## 🚀 Quick Usage (CLI Example)

Provision a Sandbox (SBX) environment with governance tags:

```bash
launcher provision env \
    --type SBX \
    --owner alice \
    --policy_bundle sbx_default \
    --vault-token $VAULT_TOKEN \
    --dns-register true \
    --tags business_unit=platform compliance=fedramp
```
Behind this single command, the client:
	1.	Authenticates with Vault for scoped credentials.
	2.	Triggers Nutanix Calm blueprint or Terraform plan selection.
	3.	Reserves IP in Infoblox, registers DNS (alice.sbx.company.local).
	4.	Applies tags + policy bundle.
	5.	Logs an auditable trace for compliance.
    
```bash
launcher nutanix -config <path to config/nutanix.yaml>
```

Use help to get all supported api's using launcher package:
```bash
launcher --help
```

---

🧠 AI + CI/CD Integration

sas_client is designed for agent-triggerable provisioning:
	•	Can be invoked via GitHub Actions / GitLab CI without exposing credentials.
	•	Can be called through FastAPI layer (sas_server) for ChatOps / AI agent consumption.
	•	Output is structured JSON, making it safe for LLM parsing and summarization.
    
---

## 🗂️ Project Structure for sas-client Package

```
├── examples
│   ├──config                              # Sample YAML config files
│      ├── nutanix.yaml
│      ├── ...
├── Makefile                               # Makefile for installing virtual env etc
├── README.md                              # Documentation
├── requirements.txt                       # Dependencies 
├── setup.py                               # Python package definition
└── src                                    # Core automation modules
    └── sas_client
        ├── api
        │   ├── common
        │   │   ├── api_client.py
        │   │   └── __init__.py
        │   ├── nutanix.py
        │   ├── ...
        ├── cli.py                         # CLI entry point
        ├── __init__.py
        ├── utils                          # Utility functions
        │   ├── __init__.py
        │   ├── logger.py
        │   └── ...
        └── __version__.py
```

---

📦 CI/CD Packaging

A GitHub/GitLab CI pipeline publishes sas_client as a Python package artifact, ready for:
	•	✅ Internal PIP registry install: pip install sas-client
	•	✅ Usage inside ephemeral agent containers
	•	✅ Discovery in Red Hat Developer Hub / Backstage

⸻

🔭 Roadmap
	•	Add policy-aware dry-run mode: return Terraform/Sentinel evaluation context only.
	•	Add explain flag: AI agent-friendly summary of what this provisioning action will do and which policies apply.
	•	Integrate drift detection + remediation hooks.

