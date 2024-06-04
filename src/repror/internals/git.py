from subprocess import CompletedProcess

import base64
import os
import re
import subprocess

import requests
from .commands import run_command

from dotenv import load_dotenv

load_dotenv()


class GithubAPI:
    token: str
    owner: str
    repo: str
    branch: str

    def __init__(self):
        token = os.getenv("REPROR_UPDATE_TOKEN")
        if not token:
            raise ValueError(
                "REPROR_UPDATE_TOKEN is not set. Please set it in .env file or as an environment variable."
            )
        self.token = token
        self.owner = self.extract_repo_owner()
        self.branch = self.get_git_branch()

    def _get_git_remote_url(self):
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"], stdout=subprocess.PIPE, text=True
        )
        return result.stdout.strip()

    def extract_repo_owner(self):
        # Return the owner of the repository in owner/repo format
        remote_url = self._get_git_remote_url()

        https_pattern = r"^https://github.com/([^/]+)/([^/]+)\.git$"
        ssh_pattern = r"^git@github.com:([^/]+)/([^/]+)\.git$"

        if re.match(https_pattern, remote_url):
            return "/".join(re.findall(https_pattern, remote_url)[0])
        elif re.match(ssh_pattern, remote_url):
            return "/".join(re.findall(ssh_pattern, remote_url)[0])
        else:
            raise ValueError("Remote URL does not match expected GitHub patterns")

    def get_git_branch(self):
        # Return the current branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def update_obj(self, content: str | bytes, file_path: str, message: str):
        # Get the SHA of the existing file at file_path
        url = f"https://api.github.com/repos/{self.owner}/contents/{file_path}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        response = requests.get(url, headers=headers, params={"ref": self.branch})
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


def checkout_branch_or_commit(clone_dir, ref) -> CompletedProcess:
    """Checkout a branch or commit."""
    return run_command(["git", "checkout", ref], cwd=str(clone_dir), silent=True)
