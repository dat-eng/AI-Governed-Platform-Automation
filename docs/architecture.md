# Platform Architecture — AI-Governed Zero-Trust Provisioning Framework


## 🎯 Architectural Goal

The core principle behind this system is:

> **"No engineer or agent should manually request infrastructure. Every platform action should be a self-service, policy-governed workflow that is safe for both CI pipelines and AI agents to execute — without violating Zero-Trust compliance boundaries."**

This system abstracts Terraform, Nutanix Calm, Vault, Sentinel, Infoblox, and Ansible under a single orchestration layer that can be triggered through **CLI, REST API, CI/CD, or AI agents**.

---

## 🧠 High-Level System Flow

1. Developer / AI Agent / CLI Trigger  (natural language or JSON intent)
2. FastAPI Gateway (sas_server)
   - Receives intent or API call
   - Validates request and Vault token
   - Associates request with policy bundle (e.g. SBX/FedRamp)│
3. Orchestration Client (sas_client)
   - Calls Nutanix Calm for baseline infra provisioning
   - Runs Terraform with Sentinel policy enforcement
   - Requests Vault secrets / tokens (short-lived)
   - Registers DNS/IP via Infoblox
   - Optionally triggers Ansible / post-setup automation
4. Provisioned Infrastructure (Cloud / On-Prem / Hybrid)
   - Tagged + logged for audit
   - Returns structured response for agents / dashboards

---

## 📦 Major Components and Their Roles

| Component | Role in Architecture |
|-----------|---------------------|
| **FastAPI (`sas_server`)** | Acts as the **secure API gateway**. This is the surface that **developers, CI jobs, or AI agents** interact with. |
| **Python Client (`sas_client`)** | Central orchestration engine. Abstracts multiple provisioning tools behind a clean API. Prevents direct access to Terraform/Calm. |
| **Vault** | Issues **ephemeral tokens** and enforces Zero-Trust. No static credentials are embedded in scripts or YAML. |
| **Terraform + Sentinel** | Enforces **policy-as-code** — ensures environment rules (SBX vs DEV vs PROD) cannot be bypassed. |
| **Nutanix Calm** | Handles base VM / environment orchestration. This forms the **first layer of infrastructure provisioning**. |
| **Infoblox** | Provides network identity (IP allocation + DNS). Integrated automatically for auditability. |
| **Developer Hub (Backstage/Red Hat)** | Provides **UI discovery and catalog** experience. Maps technical workflows to human-accessible components. |
| **AI Agent (Optional Layer)** | Not required to run the system, but the platform is designed to support natural language → policy bundle → provisioning pipeline mapping. |

---

## 🔁 Provisioning Lifecycle — Step-by-Step

 - User or AI requests provisioning (CLI, API, or ChatOps).
 - FastAPI validates Vault token + attaches policy bundle context.
 - Orchestrator (sas_client) pulls relevant Terraform/Calm module.
 - Vault issues short-lived token → injected only at execution time.
 - Terraform applies infrastructure with Sentinel policy enforcement.
 - Calm completes orchestration → Infoblox registers DNS/IP.
 - Audit event is logged (owner, policy, timestamp, infra outputs).
 - JSON response returned — safe for AI parsing or CI dashboards.

---

## 🎙 Architecture Explained

I designed the platform so that no engineer directly interacts with Terraform, Calm, or Vault. Instead, we expose a secure orchestration surface — FastAPI for agent/API calls and a CLI wrapper for CI pipelines. Every provisioning request is associated with a policy bundle like `sbx_default`, which determines what Terraform modules and Vault roles can be invoked. This architecture allows the same workflows to be triggered by developers, GitHub Actions, or even AI agents without compromising compliance or exposing credentials.

---

## 📊 Design Philosophy

| Principle | Applied as |
|----------|-----------|
| **Zero-Trust Access** | Vault enforces identity-per-run; no long-lived creds. |
| **Policy-as-Code First** | Terraform modules wrapped with Sentinel rules. |
| **Agent-Safe Outputs** | JSON responses with explicit state + audit metadata. |
| **Self-Service by Default** | All workflows are callable via endpoint or CLI — no tickets. |
| **AI-Ready Architecture** | Human intent → policy → API → provisioning flow. |

---

## 📌 Next: See `agent_trigger.md` for how natural language AI calls map into this architecture.
