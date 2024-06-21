from rich.progress import track
import os
from pathlib import Path
import subprocess
import tempfile
import shutil
from typing import Optional, Annotated

from repror.internals import conf
from repror.internals import git


from rich.syntax import Syntax

import typer
from rich import print

app = typer.Typer()


def checkout_feedstock(
    package_name: str, dest_recipe_dir: Path, clone_dir: str | bytes, copy: bool
):
    """
    Check out the feedstock repository for the given package name.
    """
    repo_url = f"https://github.com/conda-forge/{package_name}-feedstock"
    try:
        git.clone_repo(repo_url, clone_dir)
        recipe_dir = os.path.join(clone_dir, "recipe")
        if copy:
            print(f"Saving to: {dest_recipe_dir}")
            shutil.copytree(recipe_dir, dest_recipe_dir, dirs_exist_ok=True)

        return recipe_dir if not copy else dest_recipe_dir

    except subprocess.CalledProcessError:
        print(f"[red bold]Failed to clone repository: {repo_url}[/red bold]")
        return None


def apply_crm_convert(
    dest_recipe_dir: Path, meta_yaml_path: Path, save: bool = False
) -> bytes:
    """
    Apply the crm convert tool to the given meta.yaml file.
    """
    if save:
        dest_file = os.path.join(dest_recipe_dir, "recipe.yaml")
        captured = subprocess.run(
            ["crm", "convert", meta_yaml_path, "--output", dest_file], check=False
        )
        return captured.stdout
    # Don't save the output just use stdout
    else:
        captured = subprocess.run(
            ["crm", "convert", meta_yaml_path], check=False, capture_output=True
        )
        return captured.stdout


def generate_and_save_new_recipe(
    dest_recipe_dir: Optional[Path], save: bool = False
) -> bytes:
    """
    Save the new recipe in the specified directory.
    """
    meta_yaml_path = os.path.join(dest_recipe_dir, "meta.yaml")
    return apply_crm_convert(dest_recipe_dir, meta_yaml_path, save)


def process_packages(package_names: list[str], save: bool) -> int:
    """
    Process each package: check out feedstock, apply crm convert, and save new recipe.
    """

    saved = 0
    base_dest_dir = os.getcwd()
    config = conf.load_config()
    all_existing_paths = {recipe["path"] for recipe in config["local"]}
    for package_name in track(package_names, description="Converting packages"):
        print(f"[green bold]Processing package: {package_name}[/green bold]")

        # Create the destination director
        # If there is no destination directory, we don't save the recipe
        dest_recipe_dir = os.path.join(base_dest_dir, "recipes", package_name)
        # And output file
        recipe_path = Path(os.path.join(dest_recipe_dir, "recipe.yaml"))

        if save and recipe_path.exists():
            print(f":boom: Recipe already exists for {package_name}")
            continue

        print("Checking out feedstock")
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_recipe_dir = checkout_feedstock(
                package_name, dest_recipe_dir, clone_dir=temp_dir, copy=save
            )
            # None means error in this case
            if dest_recipe_dir is not None:
                stdout = generate_and_save_new_recipe(dest_recipe_dir, save)
                if not stdout:
                    print(
                        f"[red]Skipping package: {package_name} due to converter failure[/red]"
                    )
                    continue

                stdout = Syntax(f"\n{stdout.decode()}", "yaml")
                print(stdout)
                if save:
                    saved += 1
            else:
                print(
                    f"[yellow bold]Skipping package: {package_name} due to checkout failure[/yellow bold]"
                )
                continue

        # Append to the configuration file
        if save:
            # Get the relative path
            rel_path = os.path.relpath(recipe_path, base_dest_dir)
            if rel_path not in all_existing_paths:
                config["local"].append({"path": rel_path})

    # Update the configuration file
    if save:
        conf.save_config(config)

    return saved


@app.command()
def run(
    package_names: Annotated[
        Optional[list[str]],
        typer.Option(
            "-p",
            "--package-name",
            help="packages you would like to convert e.g `flask`",
        ),
    ] = None,
    save: Annotated[
        bool, typer.Option(help="Add feedstock to recipes, update `config.yaml`")
    ] = False,
):
    """
    Convert the feedstock meta.yaml to recipe.yaml using conda-recipe-manager (crm) convert.
    """
    package_names = package_names or [
        "libblas",
        "liblapack",
        "libcblas",
        "libsqlite",
        "libopenblas",
        "libcxx",
        "libssh2",
        "ncurses",
        "readline",
        "tk",
        "bzip2",
        "brotlipy",
        "pyyaml",
        "tornado",
        "icu",
        "libiconv",
        "psutil",
        "libedit",
        "c-ares",
        "libwebp-base",
        "numpy",
        "libev",
        "ruamel.yaml",
        "fonttools",
        "libjpeg-turbo",
        "libxml2",
        "gettext",
        "libbrotlienc",
        "libbrotlicommon",
        "libbrotlidec",
        "brotli-bin",
        "unicodedata2",
        "grpcio",
        "libsodium",
        "h5py",
        "argon2-cffi-bindings",
        "expat",
        "zeromq",
        "pandoc",
        "libxcb",
        "xorg-libxau",
        "xorg-libxdmcp",
        "markupsafe",
        "hdf5",
        "zstd",
        "python",
        "libglib",
        "fontconfig",
        "matplotlib-base",
        "yaml",
        "gmp",
        "libprotobuf",
        "snappy",
        "liblapacke",
        "protobuf",
        "giflib",
        "libdeflate",
        "aiohttp",
        "cairo",
        "frozenlist",
        "pyzmq",
        "lz4-c",
        "lame",
        "matplotlib",
        "openblas",
        "wrapt",
        "arrow-cpp",
        "pycosat",
        "pyarrow",
        "libopus",
        "aom",
        "libidn2",
        "blas",
        "blas-devel",
        "scipy",
        "libxslt",
        "libtasn1",
        "openh264",
        "gnutls",
        "libunistring",
        "statsmodels",
        "boost-cpp",
        "nettle",
        "contourpy",
        "mpfr",
        "libllvm14",
        "x264",
    ]
    saved = process_packages(package_names, save)
    if saved > 0:
        print(f"[green]Successfully saved {saved} new[/green] :scroll:")
