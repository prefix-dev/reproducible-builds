import os
from sqlite3 import Connection
from subprocess import CalledProcessError
from typing import Optional
import platform
from pathlib import Path
from repror.internals.build import (
    BuildInfo,
    build_local_recipe,
    build_remote_recipes,
)
from repror.internals.conf import Recipe, load_all_recipes
from repror.internals.db import get_latest_build, save_build, save_failed_build
from repror.internals.rattler_build import rattler_build_hash


def filter_recipes(recipe_names: Optional[list[str]]) -> list[Recipe]:
    all_recipes = load_all_recipes()
    if recipe_names:
        recipes_to_build = []
        all_recipes_names = [recipe.name for recipe in all_recipes]
        for recipe_to_filter in recipe_names:
            if recipe_to_filter not in all_recipes_names:
                raise ValueError(
                    f"Recipe {recipe_to_filter} not found in the configuration file"
                )
            recipes_to_build.append(
                all_recipes[all_recipes_names.index(recipe_to_filter)]
            )

    else:
        recipes_to_build = all_recipes

    return recipes_to_build


def _build_recipe(
    recipe: Recipe, tmp_dir: Path, build_dir: Path
) -> dict[str, Optional[BuildInfo]]:
    cloned_prefix_dir = Path(tmp_dir) / "cloned"
    build_info = {}

    if recipe.is_local():
        build_info.update(build_local_recipe(recipe, build_dir))
    else:
        build_info.update(build_remote_recipes(recipe, build_dir, cloned_prefix_dir))

    return build_info


def build_recipe(
    connection: Connection,
    recipes: list[Recipe],
    tmp_dir: Path,
    force_build: bool = False,
):
    platform_name, platform_version = platform.system().lower(), platform.release()

    build_info = {}

    build_dir = Path("build_outputs")
    build_dir.mkdir(exist_ok=True)

    os.makedirs("build_info", exist_ok=True)

    for recipe in recipes:
        rattler_hash = rattler_build_hash()
        recipe_hash = recipe.content_hash

        latest_build = get_latest_build(
            connection,
            recipe.name,
            rattler_hash,
            recipe_hash,
            platform_name,
            platform_version,
        )
        if latest_build and not force_build:
            print("Found latest build. Skipping build")
            continue

        try:
            build_info = _build_recipe(recipe, tmp_dir, build_dir)
        except CalledProcessError as e:
            last_failed_logs = e.stderr[1000:].decode("utf-8")
            import pdb

            pdb.set_trace()
            save_failed_build(
                connection, recipe.name, rattler_hash, recipe_hash, last_failed_logs
            )
            return None

        save_build(
            connection,
            recipe.name,
            rattler_hash,
            recipe_hash,
            build_info[recipe.name]["pkg_hash"],
            build_info[recipe.name]["conda_loc"],
        )
