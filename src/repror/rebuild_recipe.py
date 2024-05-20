import json
from pathlib import Path
import tempfile
from typing import Optional, cast

from repror.build import BuildInfo, rebuild_package
from repror.util import move_file


def rebuild_packages(build_infos: dict[str, Optional[BuildInfo]], rebuild_dir: Path, tmp_dir: Path):
    rebuild_infos: dict[str, Optional[BuildInfo]] = {}
    
    # rattler_clone_dir = Path(tmp_dir) / "rattler-clone"
    # rattler_config = config["rattler-build"]
    # setup_rattler_build(rattler_config, rattler_clone_dir)

    for recipe_name, info in build_infos.items():
        # let's move the build
        if not info:
            rebuild_infos[recipe_name] = None
            continue

        rebuild_directory = rebuild_dir / f"{recipe_name}_rebuild"
        
        output_dir = rebuild_directory / "output"

        rebuild_info = rebuild_package(info["conda_loc"], output_dir)

        rebuild_infos[recipe_name] = rebuild_info

    return rebuild_infos


if __name__ == "__main__":

    build_info = {}

    with tempfile.TemporaryDirectory() as tmp_dir:
        # rattler_clone_dir = Path(tmp_dir) / "rattler-clone"
        # rattler_config = config["rattler-build"]

        # setup_rattler_build(rattler_config, rattler_clone_dir)

        # cloned_prefix_dir = Path(tmp_dir) / "cloned"


        rebuild_dir = Path("/opt/bld/rebuild_outputs")
        # rebuild_dir.mkdir(exist_ok=True)

        
        with open("build_info/build_info.json", "r") as f:
            previous_build_info = json.load(f)

        rebuild_info = rebuild_packages(previous_build_info, rebuild_dir, tmp_dir)

        with open("build_info/rebuild_info.json", "w") as f:
            json.dump(rebuild_info, f)

