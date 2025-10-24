import click
from sas_client.api.github import GitHubApi
from sas_client.config.github_config import build_github_base_config, build_github_user_config
from sas_client.agent.rag_sources import build_context_from_github_files, compose_prompt_with_context
from sas_client.agent.agent import answer  # the function you just added

@click.command()
@click.argument("question", nargs=-1, required=True)
@click.option("--file", "files", multiple=True, required=True,
              help="Format owner/repo:path@ref (ref optional)")
def main(question, files):
    q = " ".join(question)
    parsed = []
    for f in files:
        # dat-eng/AI-Governed-Platform-Automation:README.md@main
        left, *ref = f.split("@", 1)
        owner_repo, path = left.split(":", 1)
        owner, repo = owner_repo.split("/", 1)
        parsed.append({"owner": owner, "repo": repo, "path": path, "ref": ref[0] if ref else "main"})

    # cfg = {**build_github_base_config(), **build_github_user_config()}
    gh = GitHubApi()
    contexts = build_context_from_github_files(gh, parsed)
    system, user = compose_prompt_with_context(q, contexts)
    out = answer(user, system=system)
    print(out)

if __name__ == "__main__":
    main()
