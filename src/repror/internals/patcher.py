from collections import defaultdict
import glob
import json
import os
from pathlib import Path
from typing import Any, Literal


from repror.internals.db import Build, Rebuild, V1Rebuild, get_session


def find_patches(folder_path: str) -> list[Path]:
    """
    Use glob to find all .json files in the folder
    """
    json_files = glob.glob(os.path.join(folder_path, "**/*.json"), recursive=True)
    return [Path(file) for file in json_files]


def aggregate_build_patches(
    folder_path: str,
) -> dict[str, dict[Literal["build", "rebuild"], dict]]:
    """
    Aggregate all found patches, and return list of what should be saved
    """
    patches: dict[str, Any] = defaultdict(lambda: defaultdict(dict))
    json_files = find_patches(folder_path)

    for file_path in json_files:
        with open(file_path, "r") as file:
            data = json.load(file)
            patch_type = file_path.stem
            platform_type = file_path.parent.parent
            assert patch_type in {
                "build",
                "rebuild",
            }, f"Invalid patch type {patch_type}"
            patches[str(file_path.parent)][platform_type][patch_type] = data

    return patches


def save_patch(model: Build | Rebuild):
    """
    Save the patch to a file
    """
    patch_file = f"build_info/{model.platform_name}/{model.recipe_name}/{model.__class__.__name__.lower()}.json"
    os.makedirs(os.path.dirname(patch_file), exist_ok=True)

    with open(patch_file, "w") as file:
        file.write(model.model_dump_json())


def save_v1_patch(model: V1Rebuild):
    """
    Save a V1 rebuild patch to a file.
    """
    patch_file = f"build_info/v1/{model.platform_name}/{model.package_name}.json"
    os.makedirs(os.path.dirname(patch_file), exist_ok=True)

    with open(patch_file, "w") as file:
        file.write(model.model_dump_json())


# Load the patch data
def load_patch(patch_data: dict[Literal["build", "rebuild"], Any]):
    build = patch_data["build"]
    build = Build.model_validate(build)
    build.id = None

    with get_session() as session:
        session.add(build)

        if "rebuild" in patch_data:
            rebuild = patch_data["rebuild"]
            rebuild = Rebuild.model_validate(rebuild)
            rebuild.id = None
            rebuild.build_id = None
            rebuild.build = build
            session.add(rebuild)

        session.commit()


def find_v1_patches(folder_path: str = "build_info/v1") -> list[Path]:
    """
    Find all V1 rebuild patch files.
    """
    if not os.path.exists(folder_path):
        return []
    json_files = glob.glob(os.path.join(folder_path, "**/*.json"), recursive=True)
    return [Path(file) for file in json_files]


def load_v1_patches(folder_path: str = "build_info/v1") -> int:
    """
    Load all V1 rebuild patches into the database.
    Returns the number of patches loaded.
    """
    patch_files = find_v1_patches(folder_path)
    count = 0

    for file_path in patch_files:
        with open(file_path, "r") as file:
            data = json.load(file)
            v1_rebuild = V1Rebuild.model_validate(data)
            v1_rebuild.id = None  # Reset ID for new insert

            with get_session() as session:
                session.add(v1_rebuild)
                session.commit()
                count += 1

    return count
