from typing import List, Dict
from sas_client.api.github import GitHubApi

SYSTEM_DEFAULT = (
    "You are a precise platform automation assistant.\n"
    "Use ONLY the provided CONTEXT to answer. If the answer is not present, say you don't know.\n"
    "Always include a 'Sources' section citing [owner/repo:path@ref]."
)

def build_context_from_github_files(
    gh: GitHubApi,
    files: List[Dict[str, str]],  # [{"owner","repo","path","ref"}]
    max_chars_per_file: int = 80_000
) -> List[Dict]:
    ctx = []
    for f in files:
        text = gh.get_file_text(f["owner"], f["repo"], f["path"], f.get("ref","main"))
        if len(text) > max_chars_per_file:
            text = text[:max_chars_per_file] + "\n...[truncated]..."
        ctx.append({
            "source": f'{f["owner"]}/{f["repo"]}:{f["path"]}@{f.get("ref","main")}',
            "text": text
        })
    return ctx

def compose_prompt_with_context(question: str, contexts: List[Dict], system: str | None = None) -> tuple[str, str]:
    blocks = []
    for i, c in enumerate(contexts):
        blocks.append(f"[{i}] {c['source']}\n{c['text']}")
    ctx = "\n\n".join(blocks)
    sysmsg = system or SYSTEM_DEFAULT
    user = f"CONTEXT:\n{ctx}\n\nQUESTION:\n{question}\n\nAnswer:"
    return sysmsg, user