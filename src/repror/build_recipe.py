import os
import json
import sys
import conf
from pathlib import Path
import tempfile
from repror.build import (
    build_local_recipe,
    build_remote_recipes,
)
from repror.rattler_build import setup_rattler_build


def build_recipes(repositories, local_recipes, tmp_dir, build_dir):
    cloned_prefix_dir = Path(tmp_dir) / "cloned"
    remote_build_info, local_build_info = {}, {}

    for repo in repositories:
        remote_build_info = build_remote_recipes(repo, build_dir, cloned_prefix_dir)

    for local in local_recipes:
        local_build_info = build_local_recipe(local, build_dir)

    return remote_build_info, local_build_info


if __name__ == "__main__":
    platform, version = sys.argv[1], sys.argv[2]

    if platform not in ["linux", "macos", "windows"]:
        print("Invalid platform ", platform)
        sys.exit(1)

    config = conf.load_config()

    build_info = {}

    with tempfile.TemporaryDirectory() as tmp_dir:
        setup_rattler_build(config, Path(tmp_dir))

        build_dir = Path("build_outputs")
        build_dir.mkdir(exist_ok=True)

        build_results = {}

        remote_build_info, local_build_info = build_recipes(
            config.get("repositories", []), config.get("local", []), tmp_dir, build_dir
        )

        remote_build_info.update(local_build_info)

        os.makedirs("build_info", exist_ok=True)

        with open(f"build_info/{platform}_{version}_build_info.json", "w") as f:
            json.dump(remote_build_info, f)
