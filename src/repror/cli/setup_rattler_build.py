import os
from enum import StrEnum
from pathlib import Path
from rich import print

from repror.internals.git import (
    check_rev_is_present,
    clone_repo,
    checkout_branch_or_commit,
    pull,
    fetch_changes,
)
from repror.internals.rattler_build import build_rattler
from rich.panel import Panel


class SetupRattlerBuild(StrEnum):
    """Return type for setup_rattler_build function."""

    Pixi = "From pixi env"
    Cached = "Cached version"
    Built = "Built version"


def setup_rattler_build(
    rattler_build_config: dict, root_folder: Path
) -> SetupRattlerBuild:
    """
    Setup a local rattler-build environment
    this is used when using a custom rattler-build version
    """

    # read the rattler-build configuration from the configuration file
    rattler_build_config = rattler_build_config.get("rattler-build", {})
    if not rattler_build_config:
        print(
            Panel(
                "No rattler-build configuration found, using pixi env",
                title="Rattler build",
            )
        )
        # using rattler-build defined in pixi.toml
        # will skip setting up rattler-build
        return SetupRattlerBuild.Pixi

    # Branch and url of the rattler-build repository
    url = rattler_build_config["url"]
    revision = rattler_build_config["rev"]

    # Check the hash of rattler_build_hash if it is the same skip the
    # clone and build
    clone_dir = root_folder / ".rb-clone"
    hash_file = clone_dir / "rattler_build_hash"
    if hash_file.exists():
        with open(hash_file, "r") as f:
            if f.read() == revision:
                return SetupRattlerBuild.Cached

    # Clone the repository
    if not clone_dir.exists():
        clone_repo(url, clone_dir)
    else:
        # Check if revision is present and fetch latest updates if missing
        rev_present = check_rev_is_present(clone_dir, revision)
        if not rev_present:
            fetch_changes(clone_dir)

    # Set to correct version
    print(f"Using git revision {revision}")
    checkout_branch_or_commit(clone_dir, revision)
    pull(clone_dir)

    # Build rattler
    build_rattler(clone_dir)

    # Write a file with the hash so that we know what we've built
    with open(clone_dir / "rattler_build_hash", "w") as f:
        f.write(revision)

    # Set to release binary
    bin_path = Path(clone_dir) / "target" / "release" / "rattler-build"
    os.environ["RATTLER_BUILD_BIN"] = str(bin_path)
    print(Panel(f"{bin_path}", title="Rattler build binary path"))
    return SetupRattlerBuild.Built
