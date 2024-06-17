import platform
from repror.internals.conf import Recipe
from repror.internals.rattler_build import rattler_build_hash
from repror.internals.db import get_latest_build_with_rebuild
from rich.table import Table
from repror.internals.print import print


def check(
    recipes: list[Recipe],
):
    """
    Build recipes using rattler-build
    """
    platform_name, platform_version = platform.system().lower(), platform.release()
    rattler_hash = rattler_build_hash()

    status = {}

    for recipe in recipes:
        recipe_hash = recipe.content_hash

        latest_build, latest_rebuild = get_latest_build_with_rebuild(
            recipe.name,
            rattler_hash,
            recipe_hash,
            platform_name,
            platform_version,
        )
        if not latest_build and not latest_rebuild:
            raise ValueError(f"No build and rebuild found for recipe {recipe.name}")

        status[recipe.name] = (
            "Yes" if latest_build.build_hash == latest_rebuild.rebuild_hash else "No"
        )

    table = Table("Name", "Is Repro?", title="Are Recipe Repro?")
    for recipe, is_repro in status.items():
        table.add_row(recipe, is_repro)

    print(table)
