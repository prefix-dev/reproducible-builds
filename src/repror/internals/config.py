from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import tempfile
from typing import Optional
import yaml
from pydantic import BaseModel, Field

from multiprocessing.pool import ThreadPool
from repror.internals.db import Recipe as RecipeDB, RemoteRecipe, get_recipe, save
from repror.internals.recipe import (
    get_recipe_name,
    load_recipe_config,
    load_remote_recipe_config,
    recipe_files_hash,
)

import logging

logger = logging.getLogger(__name__)


class LocalRecipe(BaseModel):
    path: str


class RemoteRepository(BaseModel):
    url: str
    rev: str
    recipes: list[LocalRecipe]

    def __hash__(self):
        return hash((self.url, self.rev))


class RattlerBuildConfig(BaseModel):
    rev: str
    url: str


class ConfigYaml(BaseModel):
    repositories: list[RemoteRepository] = Field(default_factory=list)
    rattler_build: Optional[RattlerBuildConfig] = Field(
        default=None, alias="rattler-build", serialization_alias="rattler-build"
    )
    local: list[LocalRecipe]


@lru_cache
def load_config(config_path: str = "config.yaml") -> ConfigYaml:
    with open(config_path, "r", encoding="utf8") as file:
        return ConfigYaml.model_validate(yaml.safe_load(file))


def save_config(data: ConfigYaml, config_path: str = "config.yaml"):
    with open(config_path, "w", encoding="utf8") as file:
        data_as_dict = data.model_dump(by_alias=True)
        yaml.safe_dump(data_as_dict, file)


def load_remote_recipes(
    repo: RemoteRepository, recipes: list[LocalRecipe], clone_dir: Path
) -> list[RemoteRecipe]:
    remote_recipes = []
    for recipe in recipes:
        logger.debug(f"Recipe {recipe.path} not found in the database, adding it")
        remote_config, raw_config = load_remote_recipe_config(
            repo.url, repo.rev, recipe.path, Path(clone_dir)
        )
        recipe_name = get_recipe_name(remote_config)
        recipe_content_hash = recipe_files_hash(Path(recipe.path).parent)
        stored_recipe = RemoteRecipe(
            name=recipe_name,
            url=repo.url,
            path=str(recipe.path),
            raw_config=raw_config,
            rev=repo.rev,
            content_hash=recipe_content_hash,
        )
        remote_recipes.append(stored_recipe)
    return remote_recipes


class LoadedRecipes(BaseModel):
    all_recipes: list[RecipeDB | RemoteRecipe]
    saved_recipes: int


def load_all_recipes(config_path: str = "config.yaml") -> LoadedRecipes:
    config = load_config(config_path)
    recipes = []
    saved_recipes = 0
    with tempfile.TemporaryDirectory() as clone_dir:
        # iterate over existing recipes
        # this is done to avoid not-so-intuitive setup of the :memory: database
        # with the StaticPool for the Session
        # it also seems to throw flush errors when same session is used for multiple threads
        # so I thought that it would be better to separate fetching and saving
        recipes_to_fetch = defaultdict(list)
        for repo in config.repositories:
            for recipe in repo.recipes:
                stored_recipe = get_recipe(repo.url, recipe.path, repo.rev)
                if stored_recipe:
                    logger.debug(f"Recipe {recipe.path} found in the database")
                    recipes.append(stored_recipe)
                else:
                    recipes_to_fetch[repo].append(recipe)

        with ThreadPool() as pool:
            remote_recipes = pool.starmap(
                load_remote_recipes,
                [
                    (repo, recipes, clone_dir)
                    for repo, recipes in recipes_to_fetch.items()
                ],
            )
            saved_recipes = len(
                [
                    save(recipe)
                    for repo_recipes in remote_recipes
                    for recipe in repo_recipes
                ]
            )
            [recipes.extend(recipe_list) for recipe_list in remote_recipes]

    for local in config.local:
        local_config = load_recipe_config(local.path)
        local_path = Path(local.path)
        recipe_name = get_recipe_name(local_config)
        recipe_content_hash = recipe_files_hash(local_path.parent)
        recipe = RecipeDB(
            name=recipe_name,
            path=local.path,
            raw_config=local_path.read_text(encoding="utf8"),
            content_hash=recipe_content_hash,
        )
        recipes.append(recipe)

    return LoadedRecipes(all_recipes=recipes, saved_recipes=saved_recipes)
