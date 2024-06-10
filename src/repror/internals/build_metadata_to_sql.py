from repror.internals.git import github_api
from repror.internals.print import print
from repror.internals.patcher import aggregate_patches, load_patch


def metadata_to_db(metadata_dir: str = "build_info", update_remote: bool = False):
    patches = aggregate_patches(metadata_dir)
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

    if update_remote:
        _update_remote()


def _update_remote():
    """Update the remote repro.db file with the new data"""
    print(":running: Updating repro.db")
    with open("repro.db", "rb") as repro_db:
        db_data = repro_db.read()
        github_api.update_obj(db_data, "repro.db", "Update database")
