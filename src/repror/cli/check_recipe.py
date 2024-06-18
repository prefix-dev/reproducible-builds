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

    recipes_to_find = []
    for recipe in recipes:
        recipe_name = recipe.name
        recipe_hash = recipe.content_hash()
        recipes_to_find.append((recipe_name, recipe_hash))

    latest_build_and_rebuild = get_latest_build_with_rebuild(
        recipes_to_find,
        rattler_hash,
        platform_name,
        platform_version,
    )
    for recipe in recipes:
        latest_build, latest_rebuild = latest_build_and_rebuild.get(
            recipe.name, (None, None)
        )

        if not latest_build and not latest_rebuild:
            status[recipe.name] = "No (not built yet)"
            continue

        rebuild_hash = latest_rebuild.rebuild_hash if latest_rebuild else ""
        status[recipe.name] = "Yes" if latest_build and latest_build.build_hash == rebuild_hash else "No"

    title = "Is the Recipe Repro?" if  len(recipes) == 1 else "Are Recipes Repro?"
    table = Table("Name", "Is Repro?", title=title)
    for recipe, is_repro in status.items():
        table.add_row(recipe, is_repro)

    print(table)
