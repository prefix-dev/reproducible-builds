from enum import Enum
from pathlib import Path
import shutil
from subprocess import CalledProcessError
from typing import Optional

from pydantic import BaseModel, ConfigDict

from repror.internals.db import Build, BuildState, Rebuild, Recipe, RemoteRecipe
from repror.internals.rattler_build import get_rattler_build
from repror.internals.commands import (
    calculate_hash,
    find_conda_file,
    move_file,
    run_streaming_command,
    StreamingCmdOutput,
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


def build_conda_package(
    recipe: Recipe | RemoteRecipe, output_dir: Path
) -> StreamingCmdOutput:
    rattler_bin = get_rattler_build()
    with recipe.local_path as path:
        build_command = [
            rattler_bin,
            "build",
            "-r",
            path,
            "--output-dir",
            output_dir,
        ]
        return run_streaming_command(command=build_command)


def rebuild_conda_package(conda_file: Path, output_dir: Path) -> StreamingCmdOutput:
    rattler_bin = get_rattler_build()

    re_build_command = [
        rattler_bin,
        "rebuild",
        "--package-file",
        conda_file,
        "--output-dir",
        output_dir,
    ]

    return run_streaming_command(command=re_build_command)


def build_recipe(
    recipe: Recipe | RemoteRecipe, output_dir: Path, build_info: BuildInfo
) -> BuildResult:
    """Build a single recipe"""
    print(f"Building recipe: {recipe.name}")

    if isinstance(recipe, RemoteRecipe):
        output_dir = output_dir / f"{recipe.name}_build"
        output_dir.mkdir(parents=True, exist_ok=True)

    # bypass exception on top
    output = build_conda_package(recipe, output_dir)
    if output.return_code != 0:
        print(f"Failed to build recipe: {recipe.path}")
        failed_build = Build(
            recipe_name=recipe.name,
            state=BuildState.FAIL,
            build_tool_hash=build_info.rattler_build_hash,
            recipe_hash=recipe.content_hash,
            platform_name=build_info.platform,
            platform_version=build_info.platform_version,
            # TODO: capture reason later
            reason=output.stderr[-1000:],
        )
        return BuildResult(
            build=failed_build,
            exception=None,
        )

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
        recipe_hash=recipe.content_hash,
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

    output = rebuild_conda_package(Path(build.build_loc), output_dir)
    if output.return_code != 0:
        print(f"Failed to build recipe: {recipe.name}")
        failed_build = Rebuild(
            build_id=build.id,
            state=BuildState.FAIL,
            # Catch this later
            reason=output.stdout[-1000:],
            build=build,
        )
        return RebuildResult(rebuild=failed_build, exception=None)

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
