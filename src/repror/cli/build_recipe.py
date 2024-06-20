import os
import shutil
from typing import Optional
import platform
from pathlib import Path

from repror.cli.utils import build_to_table
from repror.internals.build import (
    BuildInfo,
    BuildResult,
    build_local_recipe,
    build_remote_recipe,
)
from repror.internals.conf import Recipe, load_all_recipes
from repror.internals.db import BuildState, get_latest_builds, save
from repror.internals.rattler_build import rattler_build_hash
from repror.internals.build import BuildStatus
from repror.internals.patcher import save_patch
from rich.table import Table
from rich import print


def recipes_for_names(recipe_names: Optional[list[str]]) -> list[Recipe]:
    """
    Get recipes objects for the given names. If no names are given, return all recipes
    """
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

    # make output dir per package
    package_output_dir = build_dir / recipe.name
    if package_output_dir.exists():
        shutil.rmtree(package_output_dir)

    if recipe.is_local():
        return build_local_recipe(recipe, package_output_dir, build_info)
    else:
        return build_remote_recipe(
            recipe, package_output_dir, cloned_prefix_dir, build_info
        )


def build_recipes(
    recipes: list[Recipe],
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
    recipes_to_find = []

    for recipe in recipes:
        recipe_name = recipe.name
        recipe_hash = recipe.content_hash()
        recipes_to_find.append((recipe_name, recipe_hash))

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

        if patch:
            print(f"Saving patch for {build_result.build}")
            save_patch(build_result.build)
        else:
            save(build_result.build)
        if build_result.build.state == BuildState.FAIL:
            raise ValueError(f"Build failed for {recipe.name}")
