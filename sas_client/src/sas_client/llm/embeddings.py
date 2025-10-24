import os
from typing import List
from openai import OpenAI

_MODEL_DEFAULT = os.getenv("SAS_EMBED_MODEL", "text-embedding-3-small")

def embed_texts(texts: List[str], model: str = _MODEL_DEFAULT) -> List[List[float]]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    # batching automatically supported by SDK
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]