import hashlib
from pathlib import Path
import tempfile
from typing import Optional

import yaml
from repror.internals import git


def load_remote_recipe_config(
    url: str, rev: str, path: str, clone_dir: Optional[Path] = None
) -> tuple[dict, str]:
    if not clone_dir:
        with tempfile.TemporaryDirectory() as tmp_dir:
            clone_dir = Path(tmp_dir)

    clone_dir = clone_dir.joinpath(
        url.replace(".git", "").replace("/", "").replace("https:", "")
    )

    if not clone_dir.exists():
        git.clone_repo(url, clone_dir)

    git.checkout_branch_or_commit(clone_dir, rev)

    recipe_path = clone_dir / path
    config = load_recipe_config(recipe_path)

    raw_config = recipe_path.read_text(encoding="utf8")

    return config, raw_config


def load_recipe_config(recipe_path: Path) -> dict:
    raw_config = recipe_path.read_text(encoding="utf8")
    return yaml.safe_load(raw_config)


def get_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def get_recipe_name(config: dict) -> str:
    if "context" in config:
        if "name" in config["context"]:
            return config["context"]["name"]

    if "package" in config:
        return config["package"]["name"]

    if "recipe" in config:
        return config["recipe"]["name"]

    raise ValueError("Recipe name not found in the configuration file")
