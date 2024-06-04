from subprocess import CompletedProcess

from .commands import run_command


def clone_repo(repo_url, clone_dir) -> CompletedProcess:
    """Simple git clone command."""
    return run_command(["git", "clone", repo_url, str(clone_dir)], silent=True)


def checkout_branch_or_commit(clone_dir, ref) -> CompletedProcess:
    """Checkout a branch or commit."""
    return run_command(["git", "checkout", ref], cwd=str(clone_dir), silent=True)
