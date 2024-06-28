from functools import lru_cache
from pathlib import Path
import tempfile
from typing import Optional
import yaml
from pydantic import BaseModel, Field

# from repror.internals.git import checkout_branch_or_commit, clone_repo
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


class RattlerBuildConfig(BaseModel):
    rev: str
    url: str


class ConfigYaml(BaseModel):
    repositories: list[RemoteRepository]
    rattler_build: Optional[RattlerBuildConfig] = Field(
        alias="rattler-build", serialization_alias="rattler-build"
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


def load_all_recipes(config_path: str = "config.yaml") -> list[RecipeDB | RemoteRecipe]:
    config = load_config(config_path)
    recipes = []
    with tempfile.TemporaryDirectory() as clone_dir:
        for repo in config.repositories:
            for recipe in repo.recipes:
                stored_recipe = get_recipe(repo.url, recipe.path, repo.rev)
                if not stored_recipe:
                    logger.debug(
                        f"Recipe {recipe.path} not found in the database, adding it"
                    )
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
                    save(stored_recipe)
                else:
                    logger.debug(f"Recipe {recipe.path} found in the database")
                recipes.append(stored_recipe)

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

    return recipes
