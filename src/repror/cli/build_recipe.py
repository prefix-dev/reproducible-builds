import os
import json
from repror.internals import conf
import platform
from pathlib import Path
from repror.internals.build import (
    Recipe,
    build_local_recipe,
    build_remote_recipes,
)


def build_recipes(recipe: Recipe, tmp_dir: Path, build_dir: Path):
    cloned_prefix_dir = Path(tmp_dir) / "cloned"
    build_info = {}

    url = recipe["url"]
    if url == "local":
        build_info.update(build_local_recipe(recipe, build_dir))
    else:
        build_info.update(
            build_remote_recipes(recipe, build_dir, cloned_prefix_dir)
        )

    return build_info


def build_recipe_from_str(recipe_string: str, tmp_dir: Path):
    platform_name, platform_version = platform.system().lower(), platform.release()

    url, branch, path = recipe_string.split("::")

    recipe_obj: Recipe = Recipe(url=url, branch=branch, path=path)

    config = conf.load_config()

    build_info = {}

    build_dir = Path("build_outputs")
    build_dir.mkdir(exist_ok=True)

    build_info = build_recipes(recipe_obj, tmp_dir, build_dir)

    os.makedirs("build_info", exist_ok=True)

    with open(
            f"build_info/{platform_name}_{platform_version}_{recipe_string.replace("/", "_").replace("::", "_").replace(":", "_")}_build_info.json",
            "w",
    ) as f:
        json.dump(build_info, f)
