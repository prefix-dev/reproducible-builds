import glob
import hashlib
import os
import shutil
import subprocess
import yaml


def run_command(command, cwd=None, env=None):
    subprocess.run(command, cwd=cwd, env=env, check=True)


def calculate_hash(conda_file):
    with open(conda_file, "rb") as f:
        # Read the entire file
        data = f.read()
        # Calculate the SHA-256 hash
        build_hash = hashlib.sha256(data).hexdigest()

    return build_hash


def find_conda_build(build_folder):
    # for now, we return only one
    conda_file = glob.glob(str(build_folder) + "/**/*.conda", recursive=True)[0]

    return conda_file

def find_all_conda_build(build_folder):
    # for now, we return all
    return glob.glob(str(build_folder) + "/**/*.conda", recursive=True)



def move_file(conda_file, destination_directory):
    os.makedirs(destination_directory, exist_ok=True)
    filename = os.path.basename(conda_file)

    file_loc = f"{destination_directory}/{filename}"

    shutil.move(conda_file, file_loc)

    return file_loc


def get_recipe_name(recipe_file):
    with open(recipe_file, "r") as file:
        recipe = yaml.safe_load(file)

    if "name" in recipe.get("context", {}):
        return recipe["context"]["name"]

    return recipe["package"]["name"]
