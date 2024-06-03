from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Self
import yaml

from repror.git import checkout_branch_or_commit, clone_repo


def load_config(config_path: str = "config.yaml"):
    with open(config_path, "r", encoding="utf8") as file:
        config = yaml.safe_load(file)
    return config


def save_config(data, config_path: str = "config.yaml"):
    with open(config_path, "w", encoding="utf8") as file:
        yaml.safe_dump(data, file)


@dataclass
class Recipe:
    recipe_type: Literal["local", "remote"]
    url: Optional[str]
    branch: Optional[str]
    recipe_path: str
    name: Optional[str] = None


class RecipeConfig:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def load_recipe(recipe_file) -> Self:
        with open(recipe_file, "r", encoding="utf8") as file:
            recipe = yaml.safe_load(file)
        return RecipeConfig(recipe)

    @staticmethod
    def load_remote_recipe(recipe: Recipe, clone_dir: Path) -> "RecipeConfig":
        repo_url = recipe.url
        ref = recipe.branch
        clone_dir = clone_dir.joinpath(repo_url.split("/")[-1].replace(".git", ""))

        if not clone_dir.exists():
            print(f"Cloning repository: {repo_url}")
            clone_repo(repo_url, clone_dir)

        if ref:
            print(f"Checking out {ref}")
            checkout_branch_or_commit(clone_dir, ref)

        recipe_path = clone_dir / recipe.recipe_path
        return RecipeConfig.load_recipe(recipe_path)

    @property
    def name(self) -> str:
        if "name" in self.config.get("context", {}):
            return self.config["context"]["name"]

        return (
            self.config["package"]["name"]
            if "package" in self.config
            else self.config["recipe"]["name"]
        )
