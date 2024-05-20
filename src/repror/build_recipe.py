import datetime
import glob
import os
import json
from typing import Optional
import conf
from pathlib import Path
import subprocess
import hashlib
import shutil
import tempfile
from repror.build import (
    BuildInfo,
    build_conda_package,
    build_local_recipe,
    build_remote_recipes,
    rebuild_conda_package,
    rebuild_package,
)
from repror.rattler_build import setup_rattler_build

from repror.conf import load_config
from repror.git import checkout_branch_or_commit, clone_repo
from util import calculate_hash, find_conda_build, get_recipe_name, move_file


def build_recipes(repositories, local_recipes, tmp_dir, build_dir):
    rattler_clone_dir = Path(tmp_dir) / "rattler-clone"
    rattler_config = config["rattler-build"]

    # setup_rattler_build(rattler_config, rattler_clone_dir)

    cloned_prefix_dir = Path(tmp_dir) / "cloned"
    remote_build_info, local_build_info = {}, {}

    for repo in repositories:
        remote_build_info = build_remote_recipes(repo, build_dir, cloned_prefix_dir)

    for local in local_recipes:
        local_build_info = build_local_recipe(local, build_dir)

    return remote_build_info, local_build_info



if __name__ == "__main__":
    config = conf.load_config()

    build_info = {}

    with tempfile.TemporaryDirectory() as tmp_dir:
        # rattler_clone_dir = Path(tmp_dir) / "rattler-clone"
        # rattler_config = config["rattler-build"]

        # setup_rattler_build(rattler_config, rattler_clone_dir)

        # cloned_prefix_dir = Path(tmp_dir) / "cloned"

        build_dir = Path("/tmp")
        # build_dir.mkdir(exist_ok=True)
        os.makedirs("/tmp/rattler_build/build", exist_ok=True)

        build_results = {}

        remote_build_info, local_build_info = build_recipes(
            config.get("repositories", []), config.get("local", []), tmp_dir, build_dir
        )

        remote_build_info.update(local_build_info)

        os.makedirs('build_info', exist_ok=True)

        with open('build_info/build_info.json', 'w') as f:
            json.dump(remote_build_info, f)

        # rebuild_dir = Path("rebuild_outputs")
        # rebuild_dir.mkdir(exist_ok=True)

        # rebuild_info = rebuild_packages(remote_build_info, rebuild_dir, tmp_dir)
        # rebuild_info.update(rebuild_packages(local_build_info, rebuild_dir, tmp_dir))

        # import pdb; pdb.set_trace()

    # total_packages = len(build_results)
    # reproducible = sum(value for value in build_results.values() if value)
    # not_reproducible = sum(value for value in build_results.values() if not value)

    # today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    # with open(f"data/chart_data_{today_date}.txt", "w") as f:
    #     f.write(f"{total_packages} {reproducible} {not_reproducible}\n")

    # with open(f"data/packages_info_{today_date}.json", "w") as pkg_info:
    #     json.dump(build_results, pkg_info)
