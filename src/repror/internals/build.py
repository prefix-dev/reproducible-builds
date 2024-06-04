from pathlib import Path
import shutil
from typing import Optional, TypedDict

from repror.internals.conf import Recipe
from repror.internals.rattler_build import get_rattler_build
from repror.internals.commands import (
    calculate_hash,
    find_conda_file,
    move_file,
    run_command,
)


class BuildInfo(TypedDict):
    recipe_path: str
    pkg_hash: str
    output_dir: str
    conda_loc: str


def build_conda_package(recipe_path: Path, output_dir: Path):
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


def rebuild_conda_package(conda_file: Path, output_dir: Path):
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


def build_recipe(recipe_path: Path, output_dir: Path) -> Optional[BuildInfo]:
    # bypass exception on top
    build_conda_package(recipe_path, output_dir)

    # let's record first hash
    conda_file = find_conda_file(output_dir)

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
    conda_file = find_conda_file(output_dir)
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
    recipe: Recipe, build_dir: Path, cloned_prefix_dir: Path
) -> dict[str, Optional[BuildInfo]]:
    _, recipe_location = recipe.load_remote_recipe_config(Path(cloned_prefix_dir))

    build_infos: dict[str, Optional[BuildInfo]] = {}

    build_dir = build_dir / f"{recipe.name}_build"
    build_dir.mkdir(parents=True, exist_ok=True)

    build_info = build_recipe(recipe_location, build_dir)

    build_infos[recipe.name] = build_info

    return build_infos


def build_local_recipe(recipe: Recipe, build_dir):
    print(f"Building recipe: {recipe.name}")
    build_infos = {}

    build_info = build_recipe(recipe.path, build_dir)

    build_infos[recipe.name] = build_info

    return build_infos
