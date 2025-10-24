import hashlib
from typing import Dict, List
from sas_client.api.github import GitHubApi
from sas_client.llm.embeddings_ollama import embed_texts
from sas_client.vectorstores.simple import SimpleVectorStore, Record
from sas_client.nlp.chunking import split_text

def index_github_file(gh: GitHubApi, owner: str, repo: str, path: str, ref: str, store: SimpleVectorStore, max_tokens=400):
    text = gh.get_file_text(owner, repo, path, ref)
    chunks = split_text(text, max_tokens=max_tokens)
    ids, metas, payloads = [], [], []
    for i, ch in enumerate(chunks):
        rid = hashlib.sha1(f"{owner}/{repo}:{path}:{ref}:{i}".encode()).hexdigest()
        meta = {"source":"github","owner":owner,"repo":repo,"path":path,"ref":ref,"chunk_id":i}
        ids.append(rid); metas.append(meta); payloads.append(ch)
    embs = embed_texts(payloads)
    store.add(embeddings=embs, records=[Record(id=i, text=t, meta=m) for i,t,m in zip(ids,payloads,metas)])
    return len(chunks)

def retrieve(store: SimpleVectorStore, query: str, k: int = 6) -> List[Dict]:
    qvec = embed_texts([query])[0]
    hits = store.search(qvec, k=k)
    return [{"score": s, "id": r.id, "text": r.text, "meta": r.meta} for s, r in hits]