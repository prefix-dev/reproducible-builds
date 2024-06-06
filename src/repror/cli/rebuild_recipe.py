import json
import os
from pathlib import Path
import platform
from sqlite3 import Connection
from subprocess import CalledProcessError
from typing import Optional

from repror.internals.build import BuildInfo, Recipe, _rebuild_package
from repror.internals.db import (
    get_latest_build,
    get_latest_rebuild,
    save_failed_rebuild,
    save_rebuild,
)
from repror.internals.rattler_build import rattler_build_hash


def rebuild_package(
    previous_build_info: Optional[tuple],
    recipe: Recipe,
    rebuild_dir: Path,
    platform: str,
) -> Optional[BuildInfo]:
    rebuild_infos: dict[str, Optional[BuildInfo]] = {}

    if not previous_build_info:
        return None

    rebuild_directory = Path(rebuild_dir) / f"{recipe.name}_rebuild"

    output_dir = rebuild_directory / "output"

    rebuild_info = _rebuild_package(previous_build_info[-3], output_dir, platform)

    rebuild_infos[recipe.name] = rebuild_info

    return rebuild_infos


def rebuild_recipe(connection: Connection, recipes: list[Recipe], tmp_dir: Path):
    platform_name, platform_version = platform.system().lower(), platform.release()

    Path(f"ci_artifacts/{platform_name}/build").mkdir(exist_ok=True, parents=True)
    Path(f"ci_artifacts/{platform_name}/rebuild").mkdir(exist_ok=True, parents=True)

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

        latest_rebuild = (
            get_latest_rebuild(connection, latest_build[-3]) if latest_build else None
        )
        # if latest_rebuild:
        #     print("Found latest rebuild. Skipping rebuilding it again")
        #     continue

        try:
            rebuild_info = rebuild_package(latest_build, recipe, tmp_dir, platform_name)
        except CalledProcessError as e:
            last_failed_logs = e.stderr[2500:].decode("utf-8")
            save_failed_rebuild(
                connection, recipe.name, latest_build[-3], last_failed_logs
            )
            return None

        latest_rebuild = save_rebuild(
            connection,
            recipe.name,
            latest_build[0],
            rebuild_info[recipe.name]["pkg_hash"],
        )

        os.makedirs(f"build_info/{platform_name}", exist_ok=True)

        import pdb

        pdb.set_trace()
        with open(
            f"build_info/{platform_name}/{recipe.build_id}_platform_{platform_name}_{platform_version}_info.json",
            "w",
        ) as f:
            patch_info = {
                "build": latest_build,
                "rebuild": latest_rebuild[0],
            }

            json.dump(patch_info, f)

        # with open(
        #     f"build_info/{platform_name}/{recipe.build_id}_platform_{platform_name}_{platform_version}_build_info.json",
        #     "w",
        # ) as f:
        #     json.dump(previous_build_info, f)
