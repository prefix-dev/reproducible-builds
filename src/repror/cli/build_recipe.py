import os
from typing import Optional
import platform
from pathlib import Path
from repror.internals.build import (
    BuildInfo,
    BuildResult,
    build_local_recipe,
    build_remote_recipes,
)
from repror.internals.conf import Recipe, load_all_recipes
from repror.internals.db import get_latest_build, save
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
    recipe: Recipe, tmp_dir: Path, build_dir: Path, build_info: BuildInfo
) -> BuildResult:
    cloned_prefix_dir = Path(tmp_dir) / "cloned"

    if recipe.is_local():
        return build_local_recipe(recipe, build_dir, build_info)
    else:
        return build_remote_recipes(recipe, build_dir, cloned_prefix_dir, build_info)


def build_recipe(
    recipes: list[Recipe],
    tmp_dir: Path,
    force_build: bool = False,
):
    platform_name, platform_version = platform.system().lower(), platform.release()

    build_dir = Path("build_outputs")
    build_dir.mkdir(exist_ok=True)

    os.makedirs("build_info", exist_ok=True)

    for recipe in recipes:
        rattler_hash = rattler_build_hash()
        recipe_hash = recipe.content_hash

        build_info = BuildInfo(
            build_tool_hash=rattler_hash,
            platform=platform_name,
            platform_version=platform_version,
        )

        latest_build = get_latest_build(
            recipe.name,
            rattler_hash,
            recipe_hash,
            platform_name,
            platform_version,
        )
        if latest_build and not force_build:
            print("Found latest build. Skipping build")
            continue

        build_result = _build_recipe(recipe, tmp_dir, build_dir, build_info)
        save(build_result.build)
        if build_result.exception:
            raise build_result.exception
