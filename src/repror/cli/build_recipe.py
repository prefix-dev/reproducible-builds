import os
from typing import Optional
import platform
from pathlib import Path
from repror.internals.build import (
    BuildInfo,
    BuildResult,
    build_local_recipe,
    build_remote_recipe,
)
from repror.internals.conf import Recipe, load_all_recipes
from repror.internals.db import get_latest_build, save
from repror.internals.rattler_build import rattler_build_hash
from repror.internals.build import BuildStatus
from rich.table import Table
from rich import print


def recipes_for_names(recipe_names: Optional[list[str]]) -> list[Recipe]:
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
        return build_remote_recipe(recipe, build_dir, cloned_prefix_dir, build_info)


def build_recipes(
    recipes: list[Recipe],
    tmp_dir: Path,
    force_build: bool = False,
):
    """
    Build recipes using rattler-build
    """
    platform_name, platform_version = platform.system().lower(), platform.release()

    build_dir = Path("build_outputs")
    build_dir.mkdir(exist_ok=True)

    os.makedirs("build_info", exist_ok=True)
    rattler_hash = rattler_build_hash()

    to_build = []

    recipe_status: list[(str, BuildStatus)] = []
    for recipe in recipes:
        recipe_hash = recipe.content_hash
        build_info = BuildInfo(
            rattler_build_hash=rattler_hash,
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
            recipe_status.append((recipe.name, BuildStatus.AlreadyBuilt))
            continue
        recipe_status.append((recipe.name, BuildStatus.ToBuild))
        to_build.append((recipe, tmp_dir, build_dir, build_info))

    # Create rich table with recipes that are already built and need to be built
    sort = {BuildStatus.ToBuild: 0, BuildStatus.AlreadyBuilt: 1}
    recipe_status = sorted(recipe_status, key=lambda status: sort.get(status[1]))
    table = Table("Name", "Status", title="Recipes to build")
    for recipe, status in recipe_status:
        table.add_row(recipe, status)

    print(table)
    for recipe, tmp_dir, build_dir, build_info in to_build:
        build_result = _build_recipe(recipe, tmp_dir, build_dir, build_info)
        save(build_result.build)
        if build_result.exception:
            raise build_result.exception
