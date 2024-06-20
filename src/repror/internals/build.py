from enum import Enum
from pathlib import Path
import shutil
from subprocess import CalledProcessError
from typing import Optional

from pydantic import BaseModel, ConfigDict

from repror.internals.conf import Recipe
from repror.internals.db import Build, BuildState, Rebuild
from repror.internals.rattler_build import get_rattler_build
from repror.internals.commands import (
    calculate_hash,
    find_conda_file,
    move_file,
    run_streaming_command,
)


class BuildStatus(str, Enum):
    ToBuild = "To Build"
    AlreadyBuilt = "Already Built"


class BuildInfo(BaseModel):
    """
    Contains information that was used to build a recipe
    """

    rattler_build_hash: str
    platform: str
    platform_version: str


class BuildResult(BaseModel):
    """
    Result of building a recipe
    """

    build: Build
    exception: Optional[CalledProcessError] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def failed(self):
        return self.build.state == BuildState.FAIL


class RebuildResult(BaseModel):
    rebuild: Rebuild
    exception: Optional[CalledProcessError] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def failed(self):
        return self.rebuild.state == BuildState.FAIL


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

    run_streaming_command(command=build_command)


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

    run_streaming_command(command=re_build_command)


def build_recipe(
    recipe: Recipe, output_dir: Path, build_info: BuildInfo
) -> BuildResult:
    """Build a single recipe"""

    # bypass exception on top
    try:
        build_conda_package(recipe.path, output_dir)
    except CalledProcessError as e:
        print(f"Failed to build recipe: {recipe.path}")
        failed_build = Build(
            recipe_name=recipe.name,
            state=BuildState.FAIL,
            build_tool_hash=build_info.rattler_build_hash,
            recipe_hash=recipe.content_hash(),
            platform_name=build_info.platform,
            platform_version=build_info.platform_version,
            reason=e.stderr[-1000:].decode("utf-8"),
        )
        return BuildResult(build=failed_build, exception=e)

    # let's record first hash
    conda_file = find_conda_file(output_dir)

    # move to artifacts
    # so we could upload it in github action
    new_file_loc = move_file(conda_file, Path("artifacts"))

    build = Build(
        recipe_name=recipe.name,
        state=BuildState.SUCCESS,
        build_hash=calculate_hash(new_file_loc),
        build_tool_hash=build_info.rattler_build_hash,
        recipe_hash=recipe.content_hash(),
        platform_name=build_info.platform,
        platform_version=build_info.platform_version,
        build_loc=str(new_file_loc),
    )

    return BuildResult(build=build, exception=None)


def _rebuild_package(
    build: Build, recipe: Recipe, output_dir, build_info: BuildInfo
) -> RebuildResult:
    # Validate build object
    if build.build_loc is None:
        raise ValueError("Build location is not set in the build object.")
    if build.id is None:
        raise ValueError("Build id is not set in the build object.")

    # copy to ci artifacts
    shutil.copyfile(
        build.build_loc,
        f"ci_artifacts/{build_info.platform}/build/{Path(build.build_loc).name}",
    )

    # raise exception to top
    try:
        rebuild_conda_package(Path(build.build_loc), output_dir)
    except CalledProcessError as e:
        print(f"Failed to build recipe: {recipe.name}")
        failed_build = Rebuild(
            build_id=build.id,
            state=BuildState.FAIL,
            reason=e.stderr[-1000:].decode("utf-8"),
            build=build,
        )
        return RebuildResult(rebuild=failed_build, exception=e)

    conda_file = find_conda_file(output_dir)
    shutil.copyfile(
        conda_file,
        f"ci_artifacts/{build_info.platform}/rebuild/{Path(conda_file).name}",
    )

    rebuild = Rebuild(
        build_id=build.id,
        state=BuildState.SUCCESS,
        rebuild_hash=calculate_hash(conda_file),
        build=build,
    )

    return RebuildResult(rebuild=rebuild)


def build_remote_recipe(
    recipe: Recipe, build_dir: Path, cloned_prefix_dir: Path, build_info: BuildInfo
) -> BuildResult:
    build_dir = build_dir / f"{recipe.name}_build"
    build_dir.mkdir(parents=True, exist_ok=True)

    return build_recipe(recipe, build_dir, build_info)


def build_local_recipe(recipe: Recipe, build_dir, build_info: BuildInfo) -> BuildResult:
    print(f"Building recipe: {recipe.name}")

    return build_recipe(recipe, build_dir, build_info)
