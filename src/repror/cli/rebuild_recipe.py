import json
import os
from pathlib import Path
import platform

from repror.internals.build import BuildInfo, RebuildResult, Recipe, _rebuild_package
from repror.internals.db import (
    Build,
    get_latest_build_with_rebuild,
    save,
)
from repror.internals.rattler_build import rattler_build_hash


def rebuild_package(
    previous_build: Build,
    recipe: Recipe,
    rebuild_dir: Path,
    build_info: BuildInfo,
) -> RebuildResult:
    rebuild_directory = Path(rebuild_dir) / f"{recipe.name}_rebuild"

    output_dir = rebuild_directory / "output"

    return _rebuild_package(previous_build, recipe, output_dir, build_info)


def rebuild_recipe(recipes: list[Recipe], tmp_dir: Path, force_rebuild: bool = False):
    platform_name, platform_version = platform.system().lower(), platform.release()

    Path(f"ci_artifacts/{platform_name}/build").mkdir(exist_ok=True, parents=True)
    Path(f"ci_artifacts/{platform_name}/rebuild").mkdir(exist_ok=True, parents=True)

    for recipe in recipes:
        rattler_hash = rattler_build_hash()
        recipe_hash = recipe.content_hash

        build_info = BuildInfo(
            build_tool_hash=rattler_hash,
            platform=platform_name,
            platform_version=platform_version,
        )

        latest_build, latest_rebuild = get_latest_build_with_rebuild(
            recipe.name,
            rattler_hash,
            recipe_hash,
            platform_name,
            platform_version,
        )

        # latest_rebuild = (
        #     get_latest_rebuild(connection, latest_build[0]) if latest_build else None
        # )

        if latest_rebuild and not force_rebuild:
            print("Found latest rebuild. Skipping rebuilding it again")
            continue
        # if latest_build[2] == "fail":
        #     latest_rebuild = save_failed_rebuild(
        #         connection, recipe.name, latest_build[0], latest_build[-2]
        #     )

        #     with open(
        #         f"build_info/{platform_name}/{recipe.build_id}_platform_{platform_name}_{platform_version}_info.json",
        #         "w",
        #     ) as f:
        #         patch_info = {
        #             "build": latest_build,
        #             "rebuild": latest_rebuild[0],
        #         }

        #         json.dump(patch_info, f)

        #     return None

        rebuild_result = rebuild_package(latest_build, recipe, tmp_dir, build_info)

        os.makedirs(f"build_info/{platform_name}", exist_ok=True)
        with open(
            f"build_info/{platform_name}/{recipe.build_id}_platform_{platform_name}_{platform_version}_info.json",
            "w",
        ) as f:
            patch_info = {
                "build": latest_build.model_dump(mode="json", exclude={"timestamp"}),
                "rebuild": rebuild_result.rebuild.model_dump(
                    mode="json", exclude={"timestamp"}
                ),
            }

            json.dump(patch_info, f, default=str)

        import pdb

        pdb.set_trace()
        save(rebuild_result.rebuild)

        if rebuild_result.exception:
            raise rebuild_result.exception
