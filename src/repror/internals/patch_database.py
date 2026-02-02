import subprocess

from repror.internals.db import PROD_DB
from repror.internals.git import github_api
from repror.internals.print import print
from repror.internals.patcher import (
    aggregate_build_patches,
    load_patch,
    load_v1_patches,
)

# Release tag for storing the database
DB_RELEASE_TAG = "database"


def patch_builds_to_db(build_dir: str = "build_info") -> int:
    patches = aggregate_build_patches(build_dir)
    for recipe_name in patches:
        for platform in patches[recipe_name]:
            if (
                "rebuild" in patches[recipe_name][platform]
                and "build" not in patches[recipe_name][platform]
            ):
                raise ValueError(
                    f"Rebuild patch for {recipe_name} without build patch. Aborting"
                )

            print(f":running: Writing {recipe_name} to the database")

            patch_for_recipe = patches[recipe_name][platform]
            load_patch(patch_for_recipe)

    return len(patches)


def patch_v1_rebuilds_to_db(build_dir: str = "build_info/v1") -> int:
    """Patch V1 rebuild results to the database."""
    count = load_v1_patches(build_dir)
    if count > 0:
        print(f":package: Loaded {count} V1 rebuild patches to the database")
    return count


def write_database_to_release():
    """Upload the database to a GitHub Release asset.

    This avoids polluting the git history with binary database updates.
    Uses the 'database' release tag to store the latest database file.
    """
    print(":package: Uploading database to GitHub Release")

    # Check if release exists, create if not
    check_result = subprocess.run(
        ["gh", "release", "view", DB_RELEASE_TAG],
        capture_output=True,
        text=True,
    )

    if check_result.returncode != 0:
        # Create the release
        print(f":sparkles: Creating release '{DB_RELEASE_TAG}'")
        subprocess.run(
            [
                "gh",
                "release",
                "create",
                DB_RELEASE_TAG,
                "--title",
                "Database",
                "--notes",
                "Auto-updated reproducibility database. Download repro.db to use locally.",
            ],
            check=True,
        )

    # Upload/replace the database file
    print(":arrow_up: Uploading repro.db to release")
    subprocess.run(
        ["gh", "release", "upload", DB_RELEASE_TAG, PROD_DB, "--clobber"],
        check=True,
    )
    print(":white_check_mark: Database uploaded successfully")


def download_database_from_release():
    """Download the database from the GitHub Release.

    Returns True if successful, False if release doesn't exist.
    """
    print(":arrow_down: Downloading database from GitHub Release")
    result = subprocess.run(
        ["gh", "release", "download", DB_RELEASE_TAG, "--pattern", PROD_DB, "--clobber"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(":white_check_mark: Database downloaded successfully")
        return True
    else:
        print(f":warning: Could not download database: {result.stderr}")
        return False


def write_database_to_remote():
    """Update the remote repro.db file.

    Uses GitHub Releases to avoid polluting git history with binary files.
    """
    write_database_to_release()
