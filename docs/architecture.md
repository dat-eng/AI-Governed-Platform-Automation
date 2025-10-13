# Platform Architecture — AI-Governed Zero-Trust Provisioning Framework


## 🎯 Architectural Goal

The core principle behind this system is:

> **"No engineer or agent should manually request infrastructure. Every platform action should be a self-service, policy-governed workflow that is safe for both CI pipelines and AI agents to execute — without violating Zero-Trust compliance boundaries."**

This system abstracts Terraform, Nutanix Calm, Vault, Sentinel, Infoblox, and Ansible under a single orchestration layer that can be triggered through **CLI, REST API, CI/CD, or AI agents**.

---

## 🧠 High-Level System Flow

1. Developer / AI Agent / CLI Trigger  (natural language or JSON intent)
2. FastAPI Gateway (sas_server) 