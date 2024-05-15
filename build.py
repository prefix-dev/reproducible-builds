import os

from util import run_command



def get_rattler_build():

    if 'RATTLER_BUILD_BIN' in os.environ:
        return os.environ['RATTLER_BUILD_BIN']
    else:
        return 'rattler-build'



def build_conda_recipe(recipe_path, output_dir):
    rattler_bin = get_rattler_build()
    build_command = [rattler_bin, 'build', "-r", recipe_path, "--output-dir", output_dir]
    
    run_command(build_command)



def rebuild_conda_package(conda_file, output_dir):
    rattler_bin = get_rattler_build()

    re_build_command = [rattler_bin, 'rebuild', "--package-file", conda_file, "--output-dir", output_dir]
    
    run_command(re_build_command)