import os
from pathlib import Path
import shutil

from repror.internals.git import clone_repo, checkout_branch_or_commit
from repror.internals.rattler_build import build_rattler


def setup_rattler_build(rattler_build_config: dict, tmp_dir: Path):
    rattler_build_config = rattler_build_config.get("rattler-build", {})
    if not rattler_build_config:
        # using rattler-build defined in pixi.toml
        return

    url = rattler_build_config["url"]
    branch = rattler_build_config["branch"]

    clone_dir = Path(tmp_dir) / "rattler-clone"

    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    clone_repo(url, clone_dir)

    print(f"Checking out {branch}")
    checkout_branch_or_commit(clone_dir, branch)

    build_rattler(clone_dir)

    # set binary path to it

    bin_path = Path(clone_dir) / "target" / "release" / "rattler-build"
    os.environ["RATTLER_BUILD_BIN"] = str(bin_path)
