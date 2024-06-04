import os
from pathlib import Path
from rich import print

from repror.internals.git import clone_repo, checkout_branch_or_commit, pull
from repror.internals.rattler_build import build_rattler


def setup_rattler_build(rattler_build_config: dict, root_folder: Path):
    """
    Setup a local rattler-build environment
    this is used when using a custom rattler-build version
    """

    # read the rattler-build configuration from the configuration file
    rattler_build_config = rattler_build_config.get("rattler-build", {})
    if not rattler_build_config:
        # using rattler-build defined in pixi.toml
        # will skip setting up rattler-build
        return

    # Branch and url of the rattler-build repository
    url = rattler_build_config["url"]
    branch = rattler_build_config["branch"]

    clone_dir = root_folder / ".rb-clone"

    if not clone_dir.exists():
        clone_repo(url, clone_dir)

    # Set to correct version
    print(f"Checking out {branch}")
    checkout_branch_or_commit(clone_dir, branch)
    print("Pulling")
    pull(clone_dir)

    print("Building rattler")

    # Build rattler
    build_rattler(clone_dir)

    # Set to release binary
    bin_path = Path(clone_dir) / "target" / "release" / "rattler-build"
    os.environ["RATTLER_BUILD_BIN"] = str(bin_path)
