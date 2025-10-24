
"""
sas_client.agent.agent
A lightweight AI agent that plans tool calls (Terraform, Ansible, Nutanix/Calm, Vault)
using sas_client.* APIs. Need to replace `llm_complete` with a LLM provider.

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
import logging
import requests

from openai import OpenAI

# --- Import sas_client APIs ---
from sas_client.api.common.api_client import APIClient, APIClientConfig
from sas_client.api.common.vault import VaultApi
from sas_client.api.terraform import TerraformApi
from sas_client.api.ansible import AnsibleApi
from sas_client.api.nutanix import NutanixApi

logger = logging.getLogger(__name__)
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
DEFAULT_MODEL = os.getenv("SAS_AGENT_MODEL", "gpt-4o-mini")  # used when backend=openai
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "llama3")          # default local model
OLLAMA_BASE   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

BACKEND = os.getenv("SAS_AGENT_BACKEND", "openai").lower()   # "openai" | "ollama"

def _answer_openai(
    prompt: str,
    system: Optional[str],
    *,
    model: Optional[str],
    temperature: float,
    max_tokens: int,
    timeout: Optional[float],
) -> str:
    # Reuse your existing OpenAI client path here
    from openai import OpenAI
    client = OpenAI(timeout=timeout)
    mdl = model or DEFAULT_MODEL

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=mdl,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()

def _answer_ollama(
    prompt: str,
    system: Optional[str],
    *,
    model: Optional[str],
    temperature: float,
    max_tokens: int,
    timeout: Optional[float],
) -> str:
    """
    Call local Ollama chat endpoint. No costs, no quotas.
    """
    mdl = model or OLLAMA_MODEL
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})

    payload = {
        "model": mdl,
        "messages": msgs,
        "stream": False,  # simplify
        "options": {"temperature": float(temperature)},
    }
    if max_tokens:
        # Ollama uses num_predict for max new tokens
        payload["options"]["num_predict"] = int(max_tokens)

    try:
        r = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=timeout or 60)
        r.raise_for_status()
        data = r.json()
        text = (data.get("message", {}).get("content") or "").strip()
        if not text:
            raise RuntimeError(f"Ollama returned no content: {data}")
        return text
    except requests.ConnectionError as e:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_BASE}. "
            f"Is it running? Try: `ollama pull {mdl}` then `ollama run {mdl} 'hi'`"
        ) from e

def answer(
    prompt: str,
    system: Optional[str] = None,
    *,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 800,
    timeout: Optional[float] = 60.0,
) -> str:
    """
    Unified entrypoint. Selects backend via SAS_AGENT_BACKEND.
    """
    print(f'AI Model: {BACKEND}')
    if BACKEND == "ollama":
        return _answer_ollama(prompt, system, model=model, temperature=temperature,
                              max_tokens=max_tokens, timeout=timeout)
    # default: openai
    return _answer_openai(prompt, system, model=model, temperature=temperature,
                          max_tokens=max_tokens, timeout=timeout)

# _client = OpenAI()  # uses OPENAI_API_KEY from env

def llm_complete(system: str, messages: list[dict[str, str]]) -> str:
    """
    Calls OpenAI's Responses API.
    The prompt instructs the model to return ONLY one of:
      - TOOLS: {"name":"...","args":{...}}
      - FINAL: "some concise answer"
    """
    # Harden the “contract” so the model sticks to your parser.
    guard = (
        "You MUST respond with exactly one line.\n"
        "Choose ONE of these formats ONLY:\n"
        "1) TOOLS: {\"name\":\"<tool>\",\"args\":{...}}\n"
        "2) FINAL: \"<concise answer>\"\n"
        "Never include extra text or markdown.\n"
        "Tools you may use: vault_read, terraform_run, ansible_run, calm_launch.\n"
        "If action is destructive (e.g., terraform apply) and not explicitly allowed, "
        "ask for confirmation using FINAL.\n"
    )

    # Build input for the Responses API
    inputs = [
        {"role": "system", "content": system + "\n\n" + guard},
        *messages  # e.g., {"role":"user","content":"..."} + any tool reflections you append
    ]

    # Choose a sensible default model (cheap + good at tool-planning)
    # You can bump to 'gpt-4o' if you want stronger planning.
    resp = _client.responses.create(
        model="gpt-4o-mini",
        input=inputs,
        temperature=0.2,
        max_output_tokens=400,
        # We want plain text we can parse (your agent expects strings)
        response_format={ "type": "text" },
    )

    # `output_text` is a convenience field with the concatenated text
    return resp.output_text.strip()
    
'''
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
'''

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
