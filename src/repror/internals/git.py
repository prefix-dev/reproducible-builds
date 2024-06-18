from pathlib import Path
from subprocess import CompletedProcess

import base64
import os
import re
import subprocess
from typing import Optional

import requests
from .commands import run_command

from dotenv import load_dotenv

load_dotenv()


class GithubAPI:
    """
    Class to interact with the GitHub API.
    It is used to update files in a GitHub repository.
    """

    owner: str
    repo: str
    branch: str

    def __init__(self):
        self.owner = self.extract_repo_owner()
        self.branch = self.get_git_branch()

    @property
    def token(self):
        token = os.getenv("REPROR_UPDATE_TOKEN")
        if not token:
            raise ValueError(
                "REPROR_UPDATE_TOKEN is not set. Please set it in .env file or as an environment variable."
            )
        return token

    def _get_git_remote_url(self):
        """Get the remote URL of the git repository."""
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"], stdout=subprocess.PIPE, text=True
        )
        return result.stdout.strip()

    def extract_repo_owner(self):
        """Return the owner of the repository in owner/repo format"""
        remote_url = self._get_git_remote_url()

        https_pattern = r"^https://github.com/([^/]+)/([^/]+?)(?:\.git)?$"
        ssh_pattern = r"^git@github.com:([^/]+)/([^/]+?)(?:\.git)?$"

        if re.match(https_pattern, remote_url):
            return "/".join(re.findall(https_pattern, remote_url)[0])
        elif re.match(ssh_pattern, remote_url):
            return "/".join(re.findall(ssh_pattern, remote_url)[0])
        else:
            raise ValueError(
                f"Remote URL does not match expected GitHub patterns {remote_url}"
            )

    def get_git_branch(self):
        """Return the current branch name"""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def update_obj(
        self,
        content: str | bytes,
        file_path: str,
        message: str,
        remote_branch: Optional[str] = None,
    ):
        """Update a file in a GitHub repository and commit the changes."""
        url = f"https://api.github.com/repos/{self.owner}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        response = requests.get(
            url, headers=headers, params={"ref": remote_branch or self.branch}
        )
        response.raise_for_status()
        data = response.json()
        sha = data["sha"]

        # Update the file
        message = f"{message} at {file_path}"
        if isinstance(content, str):
            content_encoded = base64.b64encode(content.encode()).decode()
        else:
            content_encoded = base64.b64encode(content).decode()

        payload = {
            "message": message,
            "committer": {"name": "repror_bot", "email": "repror_bot@prefix.dev"},
            "branch": self.branch,
            "content": content_encoded,
            "sha": sha,
        }

        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()


github_api = GithubAPI()


def clone_repo(repo_url, clone_dir) -> CompletedProcess:
    """Simple git clone command."""
    return run_command(["git", "clone", repo_url, str(clone_dir)], silent=True)


def fetch_changes(clone_dir: Path) -> CompletedProcess:
    """Fetch latest changes from remote."""
    return run_command(["git", "fetch"], cwd=str(clone_dir))


def check_rev_is_present(clone_dir: Path, rev: str) -> bool:
    """
    Verify if revision is present in .git repository
    Usually it is used to check if an update is needed
    """
    try:
        output = run_command(
            ["git", "cat-file", "-t", rev], cwd=str(clone_dir), silent=True
        )
        return b"commit" in output.stdout
    except subprocess.CalledProcessError:
        return False



def checkout_branch_or_commit(clone_dir, ref) -> CompletedProcess:
    """Checkout a branch or commit."""
    return run_command(["git", "checkout", ref], cwd=str(clone_dir), silent=True)


def pull(clone_dir) -> CompletedProcess:
    """Pull the latest changes from the remote."""
    return run_command(["git", "checkout", clone_dir], cwd=str(clone_dir), silent=True)
