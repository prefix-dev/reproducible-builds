from collections import defaultdict
import glob
import json
import os
from pathlib import Path
from typing import Any, Literal


from repror.internals.db import Build, Rebuild, RemoteRecipe, get_session


def find_patches(folder_path: str) -> list[Path]:
    """
    Use glob to find all .json files in the folder
    """
    json_files = glob.glob(os.path.join(folder_path, "**/*.json"))
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


def aggregate_recipe_patches(
    folder_path: str,
) -> list[RemoteRecipe]:
    """
    Aggregate all found patches, and return list of what should be saved
    """
    recipes_patches = list()
    json_files = find_patches(folder_path)

    for file_path in json_files:
        recipes_patches.append(RemoteRecipe.model_validate_json(file_path.read_bytes()))

    return recipes_patches


def save_patch(model: Build | Rebuild):
    """
    Save the patch to a file
    """
    patch_file = f"build_info/{model.platform_name}/{model.recipe_name}/{model.__class__.__name__.lower()}.json"
    os.makedirs(os.path.dirname(patch_file), exist_ok=True)

    with open(patch_file, "w") as file:
        file.write(model.model_dump_json())


def save_recipe_patch(recipe: RemoteRecipe):
    """
    Save the patch to a file
    """
    patch_file = f"recipe_info/{recipe.name}/{recipe.__class__.__name__.lower()}.json"
    os.makedirs(os.path.dirname(patch_file), exist_ok=True)

    with open(patch_file, "w") as file:
        file.write(recipe.model_dump_json())


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
