from repror.internals.db import PROD_DB, get_recipe, get_session
from repror.internals.git import github_api
from repror.internals.print import print
from repror.internals.patcher import (
    aggregate_build_patches,
    load_patch,
    aggregate_recipe_patches,
)


def patch_builds_to_db(build_dir: str = "build_info") -> int:
    patches = aggregate_build_patches(build_dir)
    for recipe_name in patches:
        for platform in patches[recipe_name]:
            if (
                "rebuild" in patches[recipe_name][platform]
                and "build" not in patches[recipe_name][platform]
            ):
                raise ValueError(
                    f"Rebuild patch for {recipe_name} without build patch. Aborting"
                )

            print(f":running: Writing {recipe_name} to the database")

            patch_for_recipe = patches[recipe_name][platform]
            load_patch(patch_for_recipe)

    return len(patches)


def patch_recipes_to_db(recipes_dir: str = "recipe_info") -> int:
    patches = aggregate_recipe_patches(recipes_dir)
    with get_session() as session:
        for recipe_obj in patches:
            exisiting_recipe = get_recipe(
                recipe_obj.url, recipe_obj.path, recipe_obj.rev
            )
            if not exisiting_recipe:
                print(f":running: Writing {recipe_obj.name} to the database")
                session.add(recipe_obj)
            else:
                print(
                    f":running: Recipe {recipe_obj.name} already exists in the database. Skipping."
                )

        session.commit()
    return len(patches)


def write_database_to_remote():
    """Update the remote repro.db file with the new data"""
    print(":running: Updating repro.db")
    with open(PROD_DB, "rb") as repro_db:
        db_data = repro_db.read()
        github_api.update_obj(db_data, PROD_DB, "Update database")
