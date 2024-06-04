from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Literal, Optional
import yaml

from repror.internals.git import checkout_branch_or_commit, clone_repo


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
    path: str
    name: Optional[str] = None

    def is_local(self) -> bool:
        return self.recipe_type == "local"

    @property
    def build_id(self) -> str:
        if self.is_local():
            return self.path.replace("/", "_")
        else:
            return (
                self.url.replace("/", "_").replace(".git", "_").replace("https:", "")
                + "_"
                + self.branch.replace("/", "_")
                + "_"
                + self.path.replace("/", "_")
            )


def load_all_recipes(
    clone_dir: Optional[Path] = None, config: str = "config.yaml"
) -> list[Recipe]:
    config = load_config(config)
    recipes = []
    for repo in config.get("repositories", []):
        url = repo["url"]
        branch = repo["branch"]
        for recipe in repo.get("recipes", []):
            path = recipe["path"]

            recipe = Recipe(url=url, branch=branch, path=path, recipe_type="remote")
            if not clone_dir:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    recipe_conf = RecipeConfig.load_remote_recipe(recipe, Path(tmp_dir))
            else:
                recipe_conf = RecipeConfig.load_remote_recipe(recipe, Path(clone_dir))

            recipe.name = recipe_conf.name

            recipes.append(recipe)

    for local in config.get("local", []):
        path = local["path"]
        recipe = Recipe(url=None, branch=None, path=path, recipe_type="local")
        recipe_conf = RecipeConfig.load_local_recipe(recipe.path)
        recipe.name = recipe_conf.name
        recipes.append(recipe)

    return recipes


class RecipeConfig:
    def __init__(self, config, recipe_path: str = None):
        self.config = config
        self.recipe_path = recipe_path

    @staticmethod
    def load_local_recipe(recipe_file) -> "RecipeConfig":
        with open(recipe_file, "r", encoding="utf8") as file:
            recipe = yaml.safe_load(file)
        return RecipeConfig(recipe)

    @staticmethod
    def load_remote_recipe(recipe: Recipe, clone_dir: Path) -> "RecipeConfig":
        repo_url = recipe.url
        ref = recipe.branch
        clone_dir = clone_dir.joinpath(repo_url.split("/")[-1].replace(".git", ""))

        if not clone_dir.exists():
            clone_repo(repo_url, clone_dir)

        if ref:
            checkout_branch_or_commit(clone_dir, ref)

        recipe_path = clone_dir / recipe.path
        conf = RecipeConfig.load_local_recipe(recipe_path)
        conf.recipe_path = recipe_path
        return conf

    @property
    def name(self) -> str:
        if "name" in self.config.get("context", {}):
            return self.config["context"]["name"]

        return (
            self.config["package"]["name"]
            if "package" in self.config
            else self.config["recipe"]["name"]
        )
