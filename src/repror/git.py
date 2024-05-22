from repror.util import run_command


def clone_repo(repo_url, clone_dir):
    run_command(["git", "clone", repo_url, str(clone_dir)])


def checkout_branch_or_commit(clone_dir, ref):
    run_command(["git", "checkout", ref], cwd=str(clone_dir))
