



import os
from pathlib import Path

from repror.build import rattler_build_version, setup_rattler_build


def test_setup_rattler_build():
    config = {
        "url": "https://github.com/nichmor/rattler-build.git",
        "branch": "fix/conda-timestamp-affect-reproducibility"
    }

    clone_dir = os.getcwd()

    clone_dir = Path(clone_dir) / "rattler"
    
    setup_rattler_build(config, clone_dir)


    rattler_build_version(clone_dir)
