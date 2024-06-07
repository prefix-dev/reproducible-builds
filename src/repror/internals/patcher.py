import json
from typing import Literal

from sqlmodel import Session
from repror.cli.rewrite_readme import find_infos

from repror.internals.db import engine, Build, Rebuild
from repror.internals.git import github_api



# Load the patch data
def patch(patch_data: dict[Literal["build", "rebuild"]]):
    build = patch_data["build"]
    rebuild = patch_data["rebuild"]

    build = Build.model_validate(build)
    rebuild = Rebuild.model_validate(rebuild)

    rebuild.build = build

    with Session(engine) as session:
        session.add(build)
        session.add(rebuild)
        session.commit()


def merge_patches(build_info_dir: str = "build_info", update_remote: bool = False) -> dict:
    build_infos = find_infos(build_info_dir, "info")

    for build_file in build_infos:
        with open(build_file, "r") as f:
            patch_data = json.load(f)
            patch(patch_data)



    if update_remote:
        # Update the README.md using GitHub API
        print(":running: Updating repro.db")
        with open('repro.db', 'rb') as repro_db:
            db_data = repro_db.read()
            github_api.update_obj(
                db_data,
                "repro.db",
                "Update database",
            )
