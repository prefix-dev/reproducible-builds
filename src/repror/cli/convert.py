import os
from pathlib import Path
import subprocess
import tempfile
import shutil
from typing import Optional

from repror.internals import conf
from repror.internals import git

import typer
from rich import print

app = typer.Typer()


def checkout_feedstock(package_name: str, dest_recipe_dir: Path, clone_dir: str | bytes, dont_copy: bool):
    """
    Check out the feedstock repository for the given package name.
    """
    repo_url = f"https://github.com/conda-forge/{package_name}-feedstock"
    try:
        git.clone_repo(repo_url, clone_dir)
        recipe_dir = os.path.join(clone_dir, "recipe")
        if not dont_copy:
            print(f"Saving to: {dest_recipe_dir}")
            shutil.copytree(recipe_dir, dest_recipe_dir, dirs_exist_ok=True)

        return recipe_dir if dont_copy else dest_recipe_dir

    except subprocess.CalledProcessError:
        print(f"[red bold]Failed to clone repository: {repo_url}[/red bold]")
        return None


def apply_crm_convert(dest_recipe_dir: Path, meta_yaml_path: Path, dont_save: bool = False):
    """
    Apply the crm convert tool to the given meta.yaml file.
    """
    if not dont_save:
        dest_file = os.path.join(dest_recipe_dir, "recipe.yaml")
        subprocess.run(
            ["crm", "convert", meta_yaml_path, "--output", dest_file], check=False
        )
    # Don't save the output just use stdout
    else:
        subprocess.run(
            ["crm", "convert", meta_yaml_path], check=False
        )


def generate_and_save_new_recipe(dest_recipe_dir: Optional[Path], dont_save: bool = False):
    """
    Save the new recipe in the specified directory.
    """
    meta_yaml_path = os.path.join(dest_recipe_dir, "meta.yaml")
    apply_crm_convert(dest_recipe_dir, meta_yaml_path, dont_save)


def process_packages(package_names: list[str], dont_save: bool):
    """
    Process each package: check out feedstock, apply crm convert, and save new recipe.
    """
    base_dest_dir = os.getcwd()
    config = conf.load_config()
    all_existing_paths = {recipe["path"] for recipe in config["local"]}
    for package_name in package_names:
        print(f"[green bold]Processing package: {package_name}[/green bold]")

        # Create the destination director
        # If there is no destination directory, we don't save the recipe
        dest_recipe_dir = os.path.join(base_dest_dir, "recipes", package_name)
        # And output file
        recipe_path = Path(os.path.join(dest_recipe_dir, "recipe.yaml"))

        if not dont_save and recipe_path.exists():
            print(f":boom: Recipe already exists for {package_name}")
            continue

        print("Checking out feedstock")
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_recipe_dir = checkout_feedstock(package_name, dest_recipe_dir, clone_dir=temp_dir, dont_copy=dont_save)
            # None means error in this case
            if dest_recipe_dir is not None:
                generate_and_save_new_recipe(dest_recipe_dir, dont_save)
            else:
                print(f"[yellow bold]Skipping package: {package_name} due to checkout failure[/yellow bold]")
                continue

        # Append to the configuration file
        if not dont_save:
            # Get the relative path
            rel_path = os.path.relpath(recipe_path, base_dest_dir)
            if rel_path not in all_existing_paths:
                config["local"].append({"path": rel_path})

    # Update the configuration file
    if not dont_save:
        conf.save_config(config)


@app.command()
def run(package_names: Optional[list[str]] = None, dont_save: bool = False):
    package_names = package_names or ["boltons"]
    process_packages(package_names, dont_save)
