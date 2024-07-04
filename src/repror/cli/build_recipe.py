import os
import shutil
from typing import Optional
import platform
from pathlib import Path

from repror.cli.utils import build_to_table
from repror.internals.build import (
    BuildInfo,
    BuildResult,
    build_recipe,
)
from repror.internals.config import load_all_recipes
from repror.internals.db import get_latest_builds, save, Recipe, RemoteRecipe
from repror.internals.rattler_build import rattler_build_hash
from repror.internals.build import BuildStatus
from repror.internals.patcher import save_patch
from rich.table import Table
from rich import print


def recipes_for_names(
    recipe_names: Optional[list[str]], config_path: str = "config.yaml"
) -> list[Recipe | RemoteRecipe]:
    """
    Get recipes objects for the given names. If no names are given, return all recipes
    """
    all_recipes = load_all_recipes(config_path)
    if recipe_names:
        recipes_to_build = []
        all_recipes_names = [recipe.name for recipe in all_recipes.all_recipes]
        for recipe_to_filter in recipe_names:
            if recipe_to_filter not in all_recipes_names:
                raise ValueError(
                    f"Recipe {recipe_to_filter} not found in the configuration file"
                )
            recipes_to_build.append(
                all_recipes.all_recipes[all_recipes_names.index(recipe_to_filter)]
            )

    else:
        recipes_to_build = all_recipes.all_recipes

    return recipes_to_build


def _build_recipe(
    recipe: Recipe | RemoteRecipe, tmp_dir: Path, build_dir: Path, build_info: BuildInfo
) -> BuildResult:
    # make output dir per package
    package_output_dir = build_dir / recipe.name
    if package_output_dir.exists():
        shutil.rmtree(package_output_dir)

    return build_recipe(recipe, package_output_dir, build_info)


def build_recipes(
    recipes: list[Recipe | RemoteRecipe],
    tmp_dir: Path,
    force: bool = False,
    patch: bool = False,
    actions_url: Optional[str] = None,
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

    recipe_status: list[tuple[str, BuildStatus]] = []

    recipes_to_find = [(recipe.name, recipe.content_hash) for recipe in recipes]

    latest_builds = get_latest_builds(
        recipes_to_find,
        rattler_hash,
        platform_name,
        platform_version,
    )

    for recipe in recipes:
        build_info = BuildInfo(
            rattler_build_hash=rattler_hash,
            platform=platform_name,
            platform_version=platform_version,
        )
        recipe_build = latest_builds.get(recipe.name)

        if recipe_build and not force:
            recipe_status.append((recipe.name, BuildStatus.AlreadyBuilt))
            continue
        recipe_status.append((recipe.name, BuildStatus.ToBuild))
        to_build.append((recipe, tmp_dir, build_dir, build_info))

    # Create rich table with recipes that are already built and need to be built
    sort = {BuildStatus.ToBuild: 0, BuildStatus.AlreadyBuilt: 1}
    recipe_status = sorted(recipe_status, key=lambda status: sort.get(status[1]) or 1)
    table = Table("Name", "Status", title="Recipes to build")
    for recipe, status in recipe_status:
        table.add_row(recipe, status)

    print(table)
    for recipe, tmp_dir, build_dir, build_info in to_build:
        build_result = _build_recipe(recipe, tmp_dir, build_dir, build_info)
        print(build_to_table(build_result.build))

        if actions_url:
            build_result.build.actions_url = actions_url

        failure = build_result.failed
        if patch:
            print(f"Saving patch for {build_result.build.recipe_name}")
            save_patch(build_result.build)

        # We need to save the rebuild result to the database
        # even though we are using patches because we might invoke
        # the process again before the patch being applied
        save(build_result.build)
        if failure:
            raise ValueError(f"Build failed for {recipe.name}")
