from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Literal, Optional, Tuple
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
    _name: Optional[str] = None
    _config: Optional[dict] = None

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

    def load_recipe_config(self, clone_dir: Optional[Path] = None) -> dict:
        if self.is_local():
            return self.load_local_recipe_config()
        else:
            conf, _ = self.load_remote_recipe_config(clone_dir)
            return conf

    def load_local_recipe_config(self, recipe_path: Optional[str] = None) -> dict:
        path = Path(recipe_path) if recipe_path else Path(self.path)
        with path.open("r", encoding="utf8") as file:
            return yaml.safe_load(file)

    def load_remote_recipe_config(
        self, clone_dir: Optional[Path] = None
    ) -> Tuple[dict, Path]:
        repo_url = self.url
        ref = self.branch
        if not clone_dir:
            with tempfile.TemporaryDirectory() as tmp_dir:
                clone_dir = Path(tmp_dir)

        clone_dir = clone_dir.joinpath(repo_url.split("/")[-1].replace(".git", ""))

        if not clone_dir.exists():
            clone_repo(repo_url, clone_dir)

        if ref:
            checkout_branch_or_commit(clone_dir, ref)

        recipe_path = clone_dir / self.path
        conf = self.load_local_recipe_config(recipe_path)
        return (conf, recipe_path)

    @property
    def name(self) -> str:
        if self._name:
            return self._name

        config = self.config

        if "name" in config.get("context", {}):
            self._name = config["context"]["name"]
        else:
            self._name = (
                config["package"]["name"]
                if "package" in self.config
                else self.config["recipe"]["name"]
            )

        return self._name

    @property
    def config(self) -> dict:
        if self._config:
            return self._config

        config = self.load_recipe_config()
        self._config = config
        return self._config


def load_all_recipes(config: str = "config.yaml") -> list[Recipe]:
    config = load_config(config)
    recipes = []
    for repo in config.get("repositories", []):
        url = repo["url"]
        branch = repo["branch"]
        for recipe in repo.get("recipes", []):
            path = recipe["path"]
            recipe = Recipe(url=url, branch=branch, path=path, recipe_type="remote")
            recipes.append(recipe)

    for local in config.get("local", []):
        path = local["path"]
        recipe = Recipe(url=None, branch=None, path=path, recipe_type="local")
        recipes.append(recipe)

    return recipes
