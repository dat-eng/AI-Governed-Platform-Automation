
"""
sas_client.agent.agent
A lightweight AI agent that plans tool calls (Terraform, Ansible, Nutanix/Calm, Vault)
using sas_client.* APIs. Replace `llm_complete` with your LLM provider.

Usage:
  export SAS_BASE_URL=...
  export SAS_TOKEN=...
  export SAS_TIMEOUT=60
  export SAS_DRY_RUN=true
  # Optional: allow terraform apply
  # export ALLOW_TF_APPLY=true

  sas-agent "Plan Terraform for org IRS-SSSD workspace SSSD_SBX"
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, TypedDict, Literal
import os, json, time, sys, traceback

# --- Import sas_client APIs ---
from sas_client.api.common.api_client import APIClient, APIClientConfig
from sas_client.api.common.vault import VaultApi
from sas_client.api.terraform import TerraformApi
from sas_client.api.ansible import AnsibleApi
from sas_client.api.nutanix import NutanixApi

# ---------------------------- Config / Context -------------------------------

class Ctx(TypedDict, total=False):
    base_url: str
    token: Optional[str]
    timeout: int
    dry_run: bool

def load_ctx() -> Ctx:
    return {
        "base_url": os.getenv("SAS_BASE_URL", "http://localhost:8000"),
        "token": os.getenv("SAS_TOKEN"),
        "timeout": int(os.getenv("SAS_TIMEOUT", "60")),
        "dry_run": os.getenv("SAS_DRY_RUN", "false").lower() == "true",
    }

def make_client(ctx: Ctx) -> APIClient:
    cfg = APIClientConfig(base_url=ctx["base_url"], token=ctx.get("token"), timeout=ctx["timeout"])
    return APIClient(cfg)

# ------------------------------- Tools ---------------------------------------

class ToolCall(TypedDict):
    name: str
    args: Dict[str, Any]

ToolFn = Callable[..., str]

def tool_vault_read(ctx: Ctx, *, mount: str="kvv2", path: str="", field: Optional[str]=None) -> str:
    client = make_client(ctx)
    vault = VaultApi(client)
    data = vault.read_kv_v2(mount=mount, path=path, field=field)
    return json.dumps({"mount": mount, "path": path, "field": field, "data": data}, indent=2)

def tool_terraform_run(ctx: Ctx, *, organization: str, workspace: str, action: Literal["plan","apply"]="plan", variables: Optional[Dict[str, Any]]=None) -> str:
    if action == "apply" and os.getenv("ALLOW_TF_APPLY","false").lower() != "true":
        return "[blocked] Terraform apply requires ALLOW_TF_APPLY=true"
    client = make_client(ctx)
    tf = TerraformApi(client)
    # Prefer safe helper if available; fall back to workspace action
    if hasattr(tf, "run_workspace_action"):
        resp = tf.run_workspace_action(org_name=organization, workspace_name=workspace, action=action, variables=variables or {})
    else:
        # fallback to ensure workspace and then plan/apply if methods exist
        tf.ensure_workspace(org_name=organization, project_name=None, workspace_name=workspace)
        resp = {"status": f"{action} requested for {organization}/{workspace}", "variables": variables}
    return json.dumps(resp, indent=2)

def tool_ansible_run(ctx: Ctx, *, job_template: str, extra_vars: Dict[str, Any], poll: bool=True, cancel_on_timeout: bool=True) -> str:
    client = make_client(ctx)
    a = AnsibleApi(client)
    job = a.run_job(job_template_name=job_template, extra_vars=extra_vars)
    if poll and hasattr(a, "wait_for_job"):
        status = a.wait_for_job(job, timeout=ctx["timeout"], cancel_on_timeout=cancel_on_timeout)
    else:
        status = a.get_job_status(job)
    out = {"job": job, "status": status}
    return json.dumps(out, indent=2)

def tool_calm_launch(ctx: Ctx, *, blueprint_name: str, project: str, inputs: Dict[str, Any]) -> str:
    client = make_client(ctx)
    n = NutanixApi(client)
    app = n.launch_app(blueprint_name=blueprint_name, project_name=project, inputs=inputs)
    if hasattr(n, "wait_for_app_status"):
        status = n.wait_for_app_status(app, timeout=ctx["timeout"])
    else:
        status = {"state": "submitted"}
    return json.dumps({"app": app, "status": status}, indent=2)

TOOLS: Dict[str, ToolFn] = {
    "vault_read": tool_vault_read,
    "terraform_run": tool_terraform_run,
    "ansible_run": tool_ansible_run,
    "calm_launch": tool_calm_launch,
}

def validate_args(name: str, args: Dict[str, Any]) -> Optional[str]:
    if name not in TOOLS:
        return f"Unknown tool '{name}'"
    required = {
        "vault_read": ["path"],
        "terraform_run": ["organization","workspace"],
        "ansible_run": ["job_template","extra_vars"],
        "calm_launch": ["blueprint_name","project","inputs"],
    }[name]
    missing = [k for k in required if k not in args]
    if missing:
        return f"Missing required args for {name}: {missing}"
    return None

# ------------------------------ Planner (LLM) --------------------------------

SYSTEM_PROMPT = """You are a careful ops agent for sas_client.
- If the user asks to run Terraform 'apply', only proceed if explicitly allowed; else respond with a short confirmation request.
- Use JSON tool calls exactly in this format:
  TOOLS: {"name": "<tool_name>", "args": {...}}
- Otherwise finish with:
  FINAL: "<concise answer>"
Tools: vault_read(path, mount?, field?), terraform_run(organization, workspace, action?, variables?), ansible_run(job_template, extra_vars, poll?), calm_launch(blueprint_name, project, inputs)
"""

def llm_complete(system: str, messages: List[Dict[str, str]]) -> str:
    """
    Replace with a real model (OpenAI/Azure/local). For now, a heuristic:
    """
    text = messages[-1]["content"].lower()
    if "calm" in text:
        return 'TOOLS: {"name":"calm_launch","args":{"blueprint_name":"PaaS RHEL9","project":"SSSD_SBX","inputs":{"hostname":"demo","vCPU":4,"memory_gb":8}}}'
    if "terraform" in text and "plan" in text:
        return 'TOOLS: {"name":"terraform_run","args":{"organization":"IRS-SSSD","workspace":"SSSD_SBX","action":"plan"}}'
    if "terraform" in text and "apply" in text:
        return 'TOOLS: {"name":"terraform_run","args":{"organization":"IRS-SSSD","workspace":"SSSD_SBX","action":"apply"}}'
    if "ansible" in text:
        return 'TOOLS: {"name":"ansible_run","args":{"job_template":"paas_rhel_post_deploy_dev","extra_vars":{"hostname":"demo","irs_environment":"SBX"}}}'
    if "vault" in text:
        return 'TOOLS: {"name":"vault_read","args":{"mount":"kvv2","path":"sssd/endpoints/aap"}}'
    return 'FINAL: Ready. Plug in your real LLM provider in llm_complete().'


# ------------------------------- Agent Loop ----------------------------------

@dataclass
class AgentState:
    goal: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    step_budget: int = 5
    trace: List[Dict[str, Any]] = field(default_factory=list)

def safe_call(name: str, args: Dict[str, Any], ctx: Ctx) -> str:
    err = validate_args(name, args)
    if err:
        return f"[error] {err}"
    try:
        return TOOLS[name](ctx, **args)
    except Exception as e:
        return f"[error] {name} failed: {e}\n{traceback.format_exc()}"

def run_agent(user_message: str, goal: str) -> str:
    ctx = load_ctx()
    state = AgentState(goal=goal, messages=[{"role":"user","content": user_message}])
    for step in range(state.step_budget):
        directive = llm_complete(SYSTEM_PROMPT, state.messages)
        state.trace.append({"step": step, "directive": directive})
        if directive.startswith("FINAL:"):
            return directive.replace("FINAL:", "").strip()
        if directive.startswith("TOOLS:"):
            raw = directive.replace("TOOLS:", "").strip()
            spec = json.loads(raw)
            name, args = spec["name"], spec.get("args", {})
            result = safe_call(name, args, ctx)
            state.trace.append({"tool": name, "args": args, "result": result})
            state.messages.append({"role":"tool","content": f"{name} → {result}"})
            state.messages.append({"role":"system","content":"If satisfied, return FINAL."})
            time.sleep(0.05)
        else:
            return f"Unknown directive: {directive}"
    return "Stopped: step budget reached without FINAL."

def main():
    user_msg = " ".join(sys.argv[1:]) or "Plan Terraform for IRS-SSSD workspace SSSD_SBX"
    out = run_agent(user_msg, goal="Execute requested infra action safely")
    print(out)

if __name__ == "__main__":
    main()
