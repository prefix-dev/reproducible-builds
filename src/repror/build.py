from pathlib import Path
import shutil
from typing import Optional, TypedDict

from repror.conf import RecipeConfig
from repror.rattler_build import get_rattler_build
from repror.util import (
    calculate_hash,
    find_conda_build,
    move_file,
    run_command,
)
from repror.git import clone_repo, checkout_branch_or_commit


class Recipe(TypedDict):
    url: str
    branch: str
    recipe: str


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
    # bypass exception on top
    build_conda_package(recipe_path, output_dir)

    # let's record first hash
    conda_file = find_conda_build(output_dir)

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


def rebuild_package(conda_file, output_dir, platform) -> Optional[BuildInfo]:
    # copy to ci artifacts
    shutil.copyfile(
        conda_file, f"ci_artifacts/{platform}/build/{Path(conda_file).name}"
    )

    # raise exception to top
    rebuild_conda_package(conda_file, output_dir)

    # let's record first hash
    conda_file = find_conda_build(output_dir)
    shutil.copyfile(
        conda_file, f"ci_artifacts/{platform}/rebuild/{Path(conda_file).name}"
    )
    print(conda_file)
    first_build_hash = calculate_hash(conda_file)

    return BuildInfo(
        recipe_path=str(conda_file),
        pkg_hash=first_build_hash,
        output_dir=str(output_dir),
        conda_loc=str(conda_file),
    )


def build_remote_recipes(
    recipe: Recipe, build_dir, cloned_prefix_dir
) -> dict[str, Optional[BuildInfo]]:
    repo_url = recipe["url"]
    ref = recipe["branch"]  # or repo.get("commit")
    clone_dir = cloned_prefix_dir.joinpath(repo_url.split("/")[-1].replace(".git", ""))

    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    print(f"Cloning repository: {repo_url}")
    clone_repo(repo_url, clone_dir)

    build_infos: dict[str, Optional[BuildInfo]] = {}

    if ref:
        print(f"Checking out {ref}")
        checkout_branch_or_commit(clone_dir, ref)

    # for recipe in repo["recipes"]:
    recipe_path = clone_dir / recipe["path"]
    # recipe_name = recipe_path.name

    recipe_config = RecipeConfig.load_recipe(recipe_path)

    build_dir = build_dir / f"{recipe_config.name}_build"
    build_dir.mkdir(parents=True, exist_ok=True)

    build_info = build_recipe(recipe_path, build_dir)

    build_infos[recipe_config.name] = build_info

    return build_infos


def build_local_recipe(recipe: Recipe, build_dir):
    recipe_path = Path(recipe["path"])

    recipe_config: RecipeConfig = RecipeConfig.load_recipe(recipe_path)

    print(f"Building recipe: {recipe_config.name}")
    build_infos = {}

    build_info = build_recipe(recipe_path, build_dir)

    build_infos[recipe_config.name] = build_info

    return build_infos
