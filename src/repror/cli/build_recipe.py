import os
import json
from typing import Optional
import platform
from pathlib import Path
from repror.internals.build import (
    build_local_recipe,
    build_remote_recipes,
)
from repror.internals.conf import Recipe, load_all_recipes


def filter_recipes(
    recipe_names: Optional[list[str]], json_recipe: Optional[str], tmp_dir: str
) -> list[Recipe]:
    if not json_recipe:
        all_recipes = load_all_recipes(tmp_dir)
        if recipe_names:
            recipes_to_build = [
                recipe for recipe in all_recipes if recipe.name in recipe_names
            ]
        else:
            recipes_to_build = all_recipes
    else:
        recipes_to_build = [Recipe(**json.loads(json_recipe))]

    return recipes_to_build


def _build_recipe(recipe: Recipe, tmp_dir: Path, build_dir: Path):
    cloned_prefix_dir = Path(tmp_dir) / "cloned"
    build_info = {}

    if recipe.is_local():
        build_info.update(build_local_recipe(recipe, build_dir))
    else:
        build_info.update(build_remote_recipes(recipe, build_dir, cloned_prefix_dir))

    return build_info


def build_recipe(recipes: list[Recipe], tmp_dir: Path):
    platform_name, platform_version = platform.system().lower(), platform.release()

    build_info = {}

    build_dir = Path("build_outputs")
    build_dir.mkdir(exist_ok=True)

    os.makedirs("build_info", exist_ok=True)

    for recipe in recipes:
        build_info = _build_recipe(recipe, tmp_dir, build_dir)

        with open(
            f"build_info/{platform_name}_{platform_version}_{recipe.build_id}_build_info.json",
            "w",
        ) as f:
            json.dump(build_info, f)
