# Threat Model & Zero-Trust Enforcement

> This system is designed according to **Zero-Trust principles**, ensuring that **no entity (human, CI pipeline, or AI agent)** can provision infrastructure without a **scoped identity, policy-bound approval, and audit trace**.

---

## 🎯 Security Design Objective

> **"Provisioning automation must remain self-service while still satisfying FedRAMP/FISMA Zero-Trust mandates — no persistent credentials, no unlogged infra changes, and no bypass of policy via automation or AI agent requests."**

This threat model explains how Vault, Sentinel, API gateway enforcement, network segmentation, and audit logging work together to enforce that principle.

---

## 🧭 Trust Boundary Overview

1. User / AI Agent / CI Job
   - Must provide Vault-issued ephemeral token
▼
2. FastAPI Gateway (sas_server)
	-	First trust boundary
	-	Validates token, environment scope, and policy bundle
▼
3. sas_client Orchestration Layer
	-	Secondary boundary
	-	Requests short-lived Vault secrets for downstream systems
▼
4. Terraform / Calm / Infoblox APIs
	-	Executes only with scoped token + policy bundle context
▼
5. Audit + Tagging Layer
	-	Final boundary — logs every action with policy + identity context

---

## 🔐 Vault Token Lifecycle

	1.	Request arrives with Vault token (no static credentials accepted)
	2.	FastAPI verifies token validity + policy binding
	3.	On approval, sas_client requests ephemeral sub-token
	4.	Terraform/Calm/Infoblox calls use sub-token ONLY, expiring after execution
	5.	Token is revoked or expires — no long-lived credentials remain

**Result:** Even **AI-triggered provisioning** remains **within Zero-Trust credential boundaries.**

---

## 🚨 Attack Surface & Mitigations

| Threat Vector | Risk | Mitigation in Architecture |
|--------------|------|----------------------------|
| **Static credentials compromised** | High risk in legacy setups | ✅ No static credentials — Vault-only ephemeral token model |
| **Agent generates malformed provisioning request** | Could bypass policy | ✅ All requests validated against **policy_bundle** enforced by Sentinel before execution |
| **Bypass through direct Terraform/Calm API call** | Rogue provisioning | ✅ Systems NOT exposed directly — only callable via FastAPI gateway with Vault token |
| **Audit evasion** | Untracked infra change | ✅ All API triggers log `owner`, `policy_bundle`, `request_id`, `timestamp` |
| **Privilege escalation (Dev→Prod)** | Unauthorized environment access | ✅ Policy bundling — e.g., `fedramp_sbx_default` only allows SBX-level blueprints |
| **AI hallucination leading to dangerous infra request** | Potential overreach | ✅ FastAPI enforces strict schema & policy validation — agent cannot "guess" infrastructure actions beyond allowed scope |

---

## 🎭 Compliance Language Mapped to Architecture

| Compliance Control Requirement | Fulfillment |
|-------------------------------|------------|
| **FedRAMP AC-2 / AC-3 (Access Enforcement)** | Vault token scoping + Sentinel policy bundles |
| **FISMA AU-2 (Audit Events)** | Request ID + policy context persisted per call |
| **Zero-Trust (M-22-09)** | No infra call bypasses auth gateway; no static privileges |
| **HIPAA Least Privilege Principle** | Token lifetime + environment scoping per request |
| **SOC2 - Change Management** | Every provisioning action is logged as a **traceable change event** |

---

## ✅ Summary Statement (Use This in Interviews)

> *“Even though the system supports AI-triggered provisioning, we never allow the AI layer to act outside Zero-Trust boundaries — every request still requires a Vault-issued token, policy bundle mapping, and goes through a FastAPI gateway that enforces Sentinel guardrails before Terraform or Calm are executed.”*

---

> ➡ **Next file:** `roadmap.md` — defines platform evolution direction (agent remediation, self-explaining policies, drift auto-correction).
