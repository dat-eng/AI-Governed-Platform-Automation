import click
from sas_client.vectorstores.simple import SimpleVectorStore
from sas_client.rag.index_github import retrieve
from sas_client.agent.agent import answer

SYSTEM = (
  "You are a precise platform automation assistant.\n"
  "Use ONLY the provided CONTEXT to answer. If not in CONTEXT, say you don't know.\n"
  "Always include a 'Sources' section citing [owner/repo:path#chunk@ref]."
)

def compose_prompt(question: str, contexts):
    blocks = []
    for i,h in enumerate(contexts):
        m=h["meta"]
        label=f"{m['owner']}/{m['repo']}:{m['path']}#chunk={m['chunk_id']}@{m['ref']}"
        blocks.append(f"[{i}] {label}\n{h['text']}")
    ctx="\n\n".join(blocks)
    return f"CONTEXT:\n{ctx}\n\nQUESTION:\n{question}\n\nAnswer:"

@click.command()
@click.argument("question", nargs=-1, required=True)
@click.option("--index-dir", default=".rag_index", show_default=True)
@click.option("--k", default=6, show_default=True)
def main(question, index_dir, k):
    q=" ".join(question)
    store=SimpleVectorStore(index_dir)
    hits=retrieve(store,q,k=k)
    user=compose_prompt(q,hits)
    print(answer(user, system=SYSTEM))

if __name__=="__main__": main()