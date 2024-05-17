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




def build_conda_recipe(recipe_path, output_dir):
    rattler_bin = get_rattler_build()
    build_command = [rattler_bin, 'build', "-r", recipe_path, "--output-dir", output_dir]
    
    run_command(build_command)



def rebuild_conda_package(conda_file, output_dir):
    rattler_bin = get_rattler_build()

    re_build_command = [rattler_bin, 'rebuild', "--package-file", conda_file, "--output-dir", output_dir]
    
    run_command(re_build_command)