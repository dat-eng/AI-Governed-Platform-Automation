import click
from sas_client.api.github import GitHubApi
from sas_client.rag.index_github import index_github_file
from sas_client.vectorstores.simple import SimpleVectorStore

@click.command()
@click.option("--owner", required=True)
@click.option("--repo", required=True)
@click.option("--path", required=True)
@click.option("--ref", default="main", show_default=True)
@click.option("--index-dir", default=".rag_index", show_default=True)
@click.option("--max-tokens", default=400, show_default=True)
def main(owner, repo, path, ref, index_dir, max_tokens):
    gh = GitHubApi()
    store = SimpleVectorStore(index_dir)
    n = index_github_file(gh, owner, repo, path, ref, store, max_tokens=max_tokens)
    click.echo(f"Indexed {n} chunks from {owner}/{repo}:{path}@{ref} → {index_dir}")

if __name__ == "__main__": main()