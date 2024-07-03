import json
from repror.cli.utils import platform_name, platform_version
from repror.internals import config
from repror.internals.db import get_latest_build_with_rebuild
from pathlib import Path


def _generate_recipes(
    rattler_build_hash: str,
    all_: bool = False,
    only_failed: bool = False,
    config_path: Path = Path("config.yaml"),
):
    # Prepare the matrix
    all_recipes = config.load_all_recipes(config_path=str(config_path))

    if all_ and only_failed:
        raise ValueError("Cannot use both --all and --only-failed")

    if only_failed:
        # Get the name and hash of all the recipes
        name_and_hash = [(recipe.name, recipe.content_hash) for recipe in all_recipes]

        # Current rattler hash
        # Latest build with rebuild, a.k.a. finished recipes
        finished_recipes = get_latest_build_with_rebuild(
            name_and_hash,
            build_tool_hash=rattler_build_hash,
            platform_name=platform_name(),
            # platform_version=platform_version(),
        )
        to_run = []

        for recipe_name, (build, rebuild) in finished_recipes.items():
            if not rebuild or not build:
                to_run.append(recipe_name)
            elif build.state == "failed" or rebuild.state == "failed":
                to_run.append(recipe_name)
            elif build.build_hash != rebuild.rebuild_hash:
                to_run.append(recipe_name)

        for name, hash in name_and_hash:
            if name not in finished_recipes:
                to_run.append(name)

        # Get the recipes that are failed, non-repro, or didn't run yet
        import pdb; pdb.set_trace()
        return list(set(to_run))

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
    rattler_build_hash: str,
    all_: bool = False,
    only_failed: bool = False,
    config_path: Path = Path("config.yaml"),
):
    """Generate list of recipes from the configuration file."""
    recipe_list = _generate_recipes(rattler_build_hash, all_, only_failed, config_path)
    # Convert the matrix to JSON
    print(json.dumps(recipe_list))
