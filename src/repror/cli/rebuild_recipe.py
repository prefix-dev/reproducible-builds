from pathlib import Path
import platform
from typing import Optional

from repror.internals.build import BuildInfo, RebuildResult, Recipe, _rebuild_package
from repror.internals.db import (
    Build,
    get_latest_build_with_rebuild,
    save,
)
from repror.internals.patcher import save_patch
from repror.internals.rattler_build import rattler_build_hash
from repror.internals.print import print


def rebuild_package(
    previous_build: Build,
    recipe: Recipe,
    rebuild_dir: Path,
    build_info: BuildInfo,
) -> RebuildResult:
    rebuild_directory = Path(rebuild_dir) / f"{recipe.name}_rebuild"

    output_dir = rebuild_directory / "output"

    return _rebuild_package(previous_build, recipe, output_dir, build_info)


def rebuild_recipe(
    recipes: list[Recipe],
    tmp_dir: Path,
    force_rebuild: bool = False,
    patch: bool = False,
    actions_url: Optional[str] = None,
):
    platform_name, platform_version = platform.system().lower(), platform.release()

    Path(f"ci_artifacts/{platform_name}/build").mkdir(exist_ok=True, parents=True)
    Path(f"ci_artifacts/{platform_name}/rebuild").mkdir(exist_ok=True, parents=True)

    for recipe in recipes:
        print(f"Rebuilding recipe: {recipe.name}")
        rattler_hash = rattler_build_hash()
        recipe_hash = recipe.content_hash

        build_info = BuildInfo(
            rattler_build_hash=rattler_hash,
            platform=platform_name,
            platform_version=platform_version,
        )

        try:
            latest_build, latest_rebuild = get_latest_build_with_rebuild(
                recipe.name,
                rattler_hash,
                recipe_hash,
                platform_name,
                platform_version,
            )
        except ValueError:
            print(f"Failed to get latest build for recipe: {recipe.name}. Skipping.")
            continue

        if latest_rebuild and not force_rebuild:
            print("Found latest rebuild. Skipping rebuilding it again")
            continue

        rebuild_result = rebuild_package(latest_build, recipe, tmp_dir, build_info)
        print(f"{rebuild_result.rebuild}")
        if actions_url:
            rebuild_result.rebuild.actions_url = actions_url
        if patch:
            save_patch(rebuild_result.rebuild)
        save(rebuild_result.rebuild)

        if rebuild_result.exception:
            raise rebuild_result.exception
        print(f"[bold green]Done: '{recipe.name}' [/bold green]")
