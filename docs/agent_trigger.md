# AI / ChatOps Agent Trigger Workflow

> This document explains how **AI agents or ChatOps bots** can safely trigger infrastructure provisioning actions through the platform — using **natural language intent**, mapped to **policy-bound API calls**.

---

## 🎯 Goal

Allow a developer or AI agent to request:

> _“Provision a Snowflake SBX environment for Alice under FedRamp policy with DNS registration.”_

…and have the platform convert that into a **secured, policy-governed API call** without exposing Terraform, Vault, or Calm directly.

---

## 🧠 Natural Language to API Translation (Conceptual Flow)

⟶ “Provision Snowflake SBX for Alice with FedRAMP policy”

1. AI Agent/ LLM Layer
- Extracts key parameters: service=snowflake, env=SBX, owner=alice
- Maps intent to known policy bundle: fedramp_sbx_default
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