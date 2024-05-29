import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
from repror import conf

def checkout_feedstock(package_name, dest_recipe_dir):
    """
    Check out the feedstock repository for the given package name.
    """
    repo_url = f"https://github.com/conda-forge/{package_name}-feedstock"
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            subprocess.run(["git", "clone", repo_url, temp_dir], check=True)
            recipe_dir = os.path.join(temp_dir, "recipe")
            # os.makedirs(dest_recipe_dir, exist_ok=True)
            shutil.copytree(recipe_dir, dest_recipe_dir, dirs_exist_ok=True)
            return dest_recipe_dir
        except subprocess.CalledProcessError:
            print(f"Failed to clone repository: {repo_url}")
            return None

def apply_crm_convert(dest_recipe_dir, meta_yaml_path):
    """
    Apply the crm convert tool to the given meta.yaml file.
    """
    dest_file = os.path.join(dest_recipe_dir, "recipe.yaml")
    subprocess.run(["crm", "convert", meta_yaml_path, "--output", dest_file], check=False)

def save_new_recipe(dest_recipe_dir):
    """
    Save the new recipe in the specified directory.
    """
    meta_yaml_path = os.path.join(dest_recipe_dir, "meta.yaml")
    apply_crm_convert(dest_recipe_dir, meta_yaml_path)

def process_packages(package_names):
    """
    Process each package: check out feedstock, apply crm convert, and save new recipe.
    """
    base_dest_dir = os.getcwd()
    config = conf.load_config()
    all_existing_paths = {recipe['path'] for recipe in config['local']}
    for package_name in package_names:
        print(f"Processing package: {package_name}")
        dest_recipe_dir = os.path.join(base_dest_dir, "recipes", package_name)
        recipe_path = Path(os.path.join(dest_recipe_dir, "recipe.yaml"))
        if recipe_path.exists():
            continue
        dest_recipe_dir = checkout_feedstock(package_name, dest_recipe_dir)
        if dest_recipe_dir:
            save_new_recipe(dest_recipe_dir)
        else:
            print(f"Skipping package: {package_name} due to checkout failure")
            continue

        rel_path = os.path.relpath(recipe_path, base_dest_dir)
        if rel_path not in all_existing_paths:
            config['local'].append({'path': rel_path})

    conf.save_config(config)

if __name__ == "__main__":
    some_names = sys.argv[1:]

    example_names = ["boltons"]

    package_names = some_names or example_names


    process_packages(package_names)
