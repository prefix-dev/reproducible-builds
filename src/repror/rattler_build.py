import os
from pathlib import Path
import shutil

from repror.util import run_command
from repror.git import clone_repo, checkout_branch_or_commit


def get_rattler_build():
    if 'RATTLER_BUILD_BIN' in os.environ:
        return os.environ['RATTLER_BUILD_BIN']
    else:
        return 'rattler-build'


def setup_rattler_build(rattler_build_config: dict, clone_dir):
    url = rattler_build_config["url"]
    branch = rattler_build_config["branch"]

    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    clone_repo(url, clone_dir)

    print(f"Checking out {branch}")
    checkout_branch_or_commit(clone_dir, branch)

    build_rattler(clone_dir)

    # set binary path to it

    bin_path = Path(clone_dir) / "target" / "release" / "rattler-build"
    os.environ['RATTLER_BUILD_BIN'] = str(bin_path)


def build_rattler(clone_dir):
    build_command = ["cargo", "build", "--release"]
    
    run_command(build_command, cwd=clone_dir)

def rattler_build_version(cwd):
    rattler_bin = get_rattler_build()

    command = [rattler_bin, "-V"]

    run_command(command, cwd=str(cwd))