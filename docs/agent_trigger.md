# AI / ChatOps Agent Trigger Workflow

> This document explains how **AI agents or ChatOps bots** can safely trigger infrastructure provisioning actions through the platform — using **natural language intent**, mapped to **policy-bound API calls**.

---

## 🎯 Goal

Allow a developer or AI agent to request:

> _“Provision a Snowflake SBX environment for Alice under PROD policy with DNS registration.”_

…and have the platform convert that into a **secured, policy-governed API call** without exposing Terraform, Vault, or Calm directly.

---

## 🧠 Natural Language to API Translation (Conceptual Flow)

 > _“Provision a Snowflake SBX environment for Alice with SBX policy”_

1. AI Agent/ LLM Layer
- Extracts key parameters: service=snowflake, env=SBX, owner=alice
- Maps intent to known policy bundle: sbx_default
- Generates JSON payload for API

2. FastAPI Gateway (sas_server)
- Validates Vault token
- Verifies policy bundle
- Logs intent for audit lineage
- Routes call to sas_client

3. sas_client Execution Layer
- Requests Vault ephemeral token
- Calls Terraform/Calm/Infoblox/Ansible modules
- Registers DNS, applies tags, enforces Sentinel policy

4. Response JSON to Agent or CLI
- Includes resource ID, DNS name, policy used, and audit reference

---

## 📬 Example — Agent-Generated Payload

Agent converts natural language to this JSON (or YAML for CLI):

```json
{
  "environment": "SBX",
  "service": "snowflake",
  "owner": "alice",
  "policy_bundle": "fedramp_sbx_default",
  "dns": true,
  "tags": {
    "business_unit": "data-platform",
    "compliance": "fedramp"
  }
}
```

---

## 🌐 Equivalent API Call (Agent or ChatOps Trigger)

```bash
curl -X POST https://platform.company.local/api/v1/provision \
  -H "Authorization: Bearer $VAULT_TOKEN" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

---

## 📦 Example JSON Response (Agent-Friendly)
```json
{
  "status": "provisioning_started",
  "request_id": "REQ-2025-02-19-12345",
  "environment": "SBX",
  "service": "snowflake",
  "dns_registered": "alice.sbx.govcloud.local",
  "policy_bundle_applied": "fedramp_sbx_default",
  "next_actions": [
    "Query /status/REQ-2025-02-19-12345 for completion",
    "Review Sentinel enforcement summary via /explain/REQ-2025-02-19-12345"
  ],
  "audit_trace_id": "AUD-1740-IRS-FEDRAMP-LOG"
}
```

---

## 📌 Why This Matters 

I architect platforms in a way that CI pipelines and AI agents can safely trigger provisioning under Zero-Trust — every action is policy-bound, token-scoped, and audit-referenced. That’s how you scale platform automation in regulated environments without losing compliance control.

## 🚀 Future Capability: Agent Governance Loop

Planned (documented in roadmap.md):
- Agent examines Terraform plan via /explain route before provisioning
- Agent cross-checks tags & Vault policies against org compliance rules
- Agent responds back with “Approved to apply” or “Request requires policy elevation”
- Moves toward LLM-driven policy recommendation (“Based on request, apply hipaa_dev_bundle”)
