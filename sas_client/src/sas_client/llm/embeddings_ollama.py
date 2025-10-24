import os, requests
from typing import List

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")  # ollama pull nomic-embed-text

def embed_texts(texts: List[str], model: str = EMBED_MODEL) -> List[List[float]]:
    r = requests.post(f"{OLLAMA_BASE}/api/embeddings", json={"model": model, "input": texts}, timeout=120)
    r.raise_for_status()
    data = r.json()
    # Ollama returns {"embedding": [...]} for single input or {"embeddings":[...]} for batched.
    if "embeddings" in data: return data["embeddings"]
    if "embedding"  in data: return [data["embedding"]]
    raise RuntimeError(f"Unexpected embedding payload: {data}")