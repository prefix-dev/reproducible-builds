import os
from pathlib import Path
import shutil
import subprocess
from typing import NamedTuple, Optional, TypedDict

from repror.conf import load_config
from repror.rattler_build import get_rattler_build
from repror.util import (
    calculate_hash,
    find_conda_build,
    get_recipe_name,
    move_file,
    run_command,
)
from repror.git import clone_repo, checkout_branch_or_commit


class BuildInfo(TypedDict):
    recipe_path: str
    pkg_hash: str
    output_dir: str
    conda_loc: str


def build_conda_package(recipe_path, output_dir):
    rattler_bin = get_rattler_build()
    build_command = [
        rattler_bin,
        "build",
        "-r",
        recipe_path,
        "--output-dir",
        output_dir,
    ]

    run_command(build_command)


def rebuild_conda_package(conda_file, output_dir):
    rattler_bin = get_rattler_build()

    re_build_command = [
        rattler_bin,
        "rebuild",
        "--package-file",
        conda_file,
        "--output-dir",
        output_dir,
    ]

    run_command(re_build_command)


def build_recipe(recipe_path, output_dir) -> Optional[BuildInfo]:
    try:
        build_conda_package(recipe_path, output_dir)
    except subprocess.CalledProcessError:
        # something went wrong with building it
        # for now we record it as not rebuildable
        # and skip to next recipe
        # build_results[str(recipe_path)] = False
        return None

    # let's record first hash
    conda_file = find_conda_build(output_dir)
    print(conda_file)

    # move to artifacts
    # so we could upload it in github action

    new_file_loc = move_file(conda_file, "artifacts")

    first_build_hash = calculate_hash(new_file_loc)

    return BuildInfo(
        recipe_path=str(recipe_path),
        pkg_hash=first_build_hash,
        output_dir=str(output_dir),
        conda_loc=str(new_file_loc),
    )


def rebuild_package(conda_file, output_dir) -> Optional[BuildInfo]:
    try:
        rebuild_conda_package(conda_file, output_dir)
    except subprocess.CalledProcessError:
        # something went wrong with building it
        # for now we record it as not rebuildable
        # and skip to next recipe
        # build_results[str(recipe_path)] = False
        return None

    # let's record first hash
    conda_file = find_conda_build(output_dir)
    print(conda_file)
    first_build_hash = calculate_hash(conda_file)

    return BuildInfo(
        recipe_path=str(conda_file),
        pkg_hash=first_build_hash,
        output_dir=str(output_dir),
        conda_loc=str(conda_file),
    )


def build_remote_recipes(
    repo, build_dir, cloned_prefix_dir
) -> dict[str, Optional[BuildInfo]]:
    repo_url = repo["url"]
    ref = repo.get("branch") or repo.get("commit")
    clone_dir = cloned_prefix_dir.joinpath(repo_url.split("/")[-1].replace(".git", ""))

    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    print(f"Cloning repository: {repo_url}")
    clone_repo(repo_url, clone_dir)

    build_infos: dict[str, Optional[BuildInfo]] = {}

    if ref:
        print(f"Checking out {ref}")
        checkout_branch_or_commit(clone_dir, ref)

    for recipe in repo["recipes"]:
        recipe_path = clone_dir / recipe["path"]
        # recipe_name = recipe_path.name

        recipe_config = load_config(recipe_path)

        recipe_name = get_recipe_name(recipe_path)

        is_noarch = recipe_config.get("build", {}).get("noarch", False)

        print(f"Building recipe: {recipe_name}")

        build_dir = build_dir / f"{recipe_name}_build"
        build_dir.mkdir(parents=True, exist_ok=True)

        build_info = build_recipe(recipe_path, build_dir)

        build_infos[recipe_name] = build_info

    return build_infos


def build_local_recipe(local, build_dir):
    recipe_path = Path(local["path"])

    recipe_path = Path(local["path"])

    recipe_config = load_config(recipe_path)

    recipe_name = get_recipe_name(recipe_path)

    is_noarch = recipe_config.get("build", {}).get("noarch", False)

    print(f"Building recipe: {recipe_name}")
    build_infos = {}

    # build_dir = build_dir / f"{recipe_name}_build"
    # build_dir.mkdir(parents=True, exist_ok=True)

    build_info = build_recipe(recipe_path, build_dir)

    build_infos[recipe_name] = build_info

    return build_infos
