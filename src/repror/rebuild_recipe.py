import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Optional

from repror.build import BuildInfo, Recipe, rebuild_package
from repror.conf import load_config
from repror.rattler_build import setup_rattler_build
from repror.util import find_all_conda_build


def rebuild_packages(
    build_infos: dict[str, Optional[BuildInfo]],
    rebuild_dir: Path,
    platform: str,
):
    rebuild_infos: dict[str, Optional[BuildInfo]] = {}

    for recipe_name, info in build_infos.items():
        if not info:
            rebuild_infos[recipe_name] = None
            continue

        rebuild_directory = rebuild_dir / f"{recipe_name}_rebuild"

        output_dir = rebuild_directory / "output"

        rebuild_info = rebuild_package(info["conda_loc"], output_dir, platform)

        rebuild_infos[recipe_name] = rebuild_info

    return rebuild_infos


if __name__ == "__main__":
    platform, previous_version, current_version = sys.argv[1], sys.argv[2], sys.argv[3]
    recipe_string = sys.argv[4]

    url, branch, path = recipe_string.split("::")
    recipe_obj: Recipe = Recipe(url=url, branch=branch, path=path)

    build_info = {}

    with tempfile.TemporaryDirectory() as tmp_dir:
        config = load_config()

        setup_rattler_build(config, Path(tmp_dir))

        rebuild_dir = Path("build_outputs")
        rebuild_dir.mkdir(exist_ok=True)

        Path(f"ci_artifacts/{platform}/build").mkdir(exist_ok=True, parents=True)
        Path(f"ci_artifacts/{platform}/rebuild").mkdir(exist_ok=True, parents=True)

        with open(
            f"build_info/{platform}_{previous_version}_{recipe_string.replace("/", "_").replace("::", "_").replace(":", "_")}_build_info.json",
            "r",
        ) as f:
            previous_build_info = json.load(f)

        rebuild_info = rebuild_packages(previous_build_info, rebuild_dir, platform)

        # get the diffoscope output
        all_builds = find_all_conda_build("artifacts")

        for recipe_name in rebuild_info:
            if not rebuild_info[recipe_name]:
                continue

            rebuilded_loc = rebuild_info[recipe_name]["conda_loc"]

            if Path(rebuilded_loc).name in all_builds:
                idx = all_builds.index(Path(rebuilded_loc).name)
                builded = all_builds[idx]
            else:
                continue

        os.makedirs(f"build_info/{platform}", exist_ok=True)

        with open(
            f"build_info/{platform}/{recipe_string.replace("/", "_").replace("::", "_").replace(":", "_")}_{platform}_{previous_version}_{current_version}_rebuild_info.json",
            "w",
        ) as f:
            json.dump(rebuild_info, f)

        with open(
            f"build_info/{platform}/{recipe_string.replace("/", "_").replace("::", "_").replace(":", "_")}_{platform}_{previous_version}_build_info.json",
            "w",
        ) as f:
            json.dump(previous_build_info, f)
