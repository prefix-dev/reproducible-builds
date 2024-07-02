import json
from repror.cli.utils import platform_name, platform_version
from repror.internals import config
from repror.internals.db import get_latest_build_with_rebuild
from typing import Optional
from pathlib import Path


def _generate_recipes(
    rattler_build_hash: str, all_: bool = False, config_path: Optional[Path] = None
):
    if not config_path:
        config_path = Path("config.yaml")

    # Prepare the matrix
    all_recipes = config.load_all_recipes(config_path=str(config_path))

    if not all_:
        # Get the name and hash of all the recipes
        name_and_hash = [(recipe.name, recipe.content_hash) for recipe in all_recipes]
        # Current rattler hash
        # Latest build with rebuild, a.k.a. finished recipes
        finished_recipes = get_latest_build_with_rebuild(
            name_and_hash,
            build_tool_hash=rattler_build_hash,
            platform_name=platform_name(),
            platform_version=platform_version(),
        ).keys()

        # Get the recipes that are not finished yet
        return [
            recipe.name for recipe in all_recipes if recipe.name not in finished_recipes
        ]
    else:
        return [recipe.name for recipe in all_recipes]


def generate_recipes(
    rattler_build_hash: str, all_: bool = False, config_path: Optional[Path] = None
):
    """Generate list of recipes from the configuration file."""
    recipe_list = _generate_recipes(rattler_build_hash, all_, config_path)
    # Convert the matrix to JSON
    print(json.dumps(recipe_list))
