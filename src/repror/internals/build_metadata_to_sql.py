import json
from typing import Literal

from repror.cli.rewrite_readme import find_infos

from repror.internals.db import Build, Rebuild, Session
from repror.internals.git import github_api
from repror.internals.print import print


def write_metadata(build_metadata: dict[Literal["build", "rebuild"]]):
    build = build_metadata["build"]
    rebuild = build_metadata["rebuild"]

    build = Build.model_validate(build)
    rebuild = Rebuild.model_validate(rebuild)

    build.id = None
    rebuild.id = None

    rebuild.build = build

    with Session() as session:
        session.add(build)
        session.add(rebuild)
        session.commit()


def metadata_to_db(metadata_dir: str = "build_info", update_remote: bool = False):
    build_infos = find_infos(metadata_dir, "info")

    for build_file in build_infos:
        with open(build_file, "r") as f:
            patch_data = json.load(f)
            write_metadata(patch_data)

    if update_remote:
        _update_remote()


def _update_remote():
    """Update the remote repro.db file with the new data"""
    print(":running: Updating repro.db")
    with open("repro.db", "rb") as repro_db:
        db_data = repro_db.read()
        github_api.update_obj(db_data, "repro.db", "Update database")
