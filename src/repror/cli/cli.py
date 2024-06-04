import tempfile
from pathlib import Path
from typing import Annotated, Optional
from rich import print

import typer

from repror.internals.conf import load_config

# Different CLI commands
from . import build_recipe as build
from . import generate_recipes as generate
from . import rewrite_readme as rewrite
from . import setup_rattler_build as setup
from . import rebuild_recipe as rebuild
from ..internals.commands import pixi_root

app = typer.Typer(no_args_is_help=True)


def pixi_root_cli():
    """Get the pixi root otherwise use the current directory."""
    root_folder = pixi_root()
    if root_folder is None:
        root_folder = Path.cwd()
        print(
            "[bold yellow]No PIXI_PROJECT_ROOT found, using current directory, "
            "file operations might fail[/bold yellow]"
        )
    return root_folder


class GlobalOptions:
    """Global options for the CLI."""

    skip_setup_rattler_build: bool = False

    def __init__(self):
        self.skip_setup_rattler_build = False


global_options = GlobalOptions()


@app.callback()
def main(skip_setup_rattler_build: bool = False):
    """
    \bRepror is a tool to:
    - Build/rebuild packages using conda build
    - Manage a local rattler-build environment for custom builds
    - Rewrite the reproducible-builds README.md file with update statistics
    """
    if skip_setup_rattler_build:
        print("[bold yellow]Will skip setting up rattler-build[/bold yellow]")
        global_options.skip_setup_rattler_build = True


@app.command()
def generate_recipes():
    """Generate list of recipes from the configuration file."""
    generate.generate_recipes()


def _check_local_rattler_build(tmp_dir: Path):
    """Setup rattler build if local_rattler_build is set"""
    if not global_options.skip_setup_rattler_build:
        config = load_config()
        setup.setup_rattler_build(rattler_build_config=config)


@app.command()
def build_recipe(
    recipe_names: Annotated[Optional[list[str]], typer.Argument()] = None,
):
    """Build recipe from a string in the form of url::branch::path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        _check_local_rattler_build(tmp_dir)
        recipes_to_build = build.filter_recipes(recipe_names)

        build.build_recipe(recipes_to_build, tmp_dir)


@app.command()
def rebuild_recipe(
    recipe_names: Annotated[Optional[list[str]], typer.Argument()] = None,
):
    """Rebuild recipe from a string in the form of url::branch::path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        _check_local_rattler_build(tmp_dir)
        recipes_to_rebuild = build.filter_recipes(recipe_names)
        rebuild.rebuild_recipe(recipes_to_rebuild, tmp_dir)


@app.command()
def rewrite_readme():
    """Rewrite the README.md file with updated statistics"""
    build_results_by_platform = rewrite.make_statistics()
    rewrite.plot(build_results_by_platform)


@app.command()
def setup_rattler_build():
    """Setup a source build environment for rattler. (currently for testing if this works)"""
    config = load_config()
    setup.setup_rattler_build(rattler_build_config=config)
