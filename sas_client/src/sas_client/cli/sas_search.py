import json, click
from sas_client.vectorstores.simple import SimpleVectorStore
from sas_client.rag.index_github import retrieve

@click.command()
@click.argument("query", nargs=-1, required=True)
@click.option("--index-dir", default=".rag_index", show_default=True)
@click.option("--k", default=6, show_default=True)
def main(query, index_dir, k):
    q = " ".join(query)
    store = SimpleVectorStore(index_dir)
    hits = retrieve(store, q, k=k)
    click.echo(json.dumps(hits, indent=2, ensure_ascii=False))

if __name__ == "__main__": main()