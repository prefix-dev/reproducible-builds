import os
import platform
import tempfile
from pathlib import Path
from typing import Annotated, Optional

import typer

from repror.internals.conf import load_config
from repror.internals.print import print
from repror.internals import db
from repror.internals import build_metadata_to_sql


# Different CLI commands
from . import build_recipe as build
from . import generate_recipes as generate
from . import rewrite_readme as rewrite
from . import setup_rattler_build as setup
from . import rebuild_recipe as rebuild

from ..internals.commands import pixi_root
from rich.spinner import Spinner
from rich.live import Live

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


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
    in_memory_sql: bool = False


global_options = GlobalOptions()


@app.callback()
def main(skip_setup_rattler_build: bool = False, in_memory_sql: bool = False):
    """
    \bRepror is a tool to:
    - Build/rebuild packages using conda build
    - Manage a local rattler-build environment for custom builds
    - Rewrite the reproducible-builds README.md file with update statistics
    """
    if skip_setup_rattler_build:
        print("[dim yellow]Will skip setting up rattler-build[/dim yellow]")
        global_options.skip_setup_rattler_build = True
    if in_memory_sql:
        print("[yellow]Will use in-memory SQLite database[/yellow]")
        global_options.in_memory_sql = True


def setup_db():
    """Setup the engine using the global options."""
    db.setup_engine(global_options.in_memory_sql)


@app.command()
def generate_recipes():
    """Generate list of recipes from the configuration file."""
    generate.generate_recipes()


def _check_local_rattler_build(live: Optional[Live] = None):
    """Setup rattler build if local_rattler_build is set"""
    print("[dim green]Checking for local rattler build[/dim green]")
    if not global_options.skip_setup_rattler_build:
        config = load_config()
        setup.setup_rattler_build(
            rattler_build_config=config, root_folder=pixi_root_cli(), live=live
        )
    print("[dim green]Local rattler build check complete[/dim green]")


@app.command()
def build_recipe(
    recipe_names: Annotated[Optional[list[str]], typer.Argument()] = None,
    rattler_build_exe: Annotated[Optional[Path], typer.Option()] = None,
    force_build: Annotated[bool, typer.Option()] = False,
):
    """Build recipe from a string in the form of url::branch::path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        setup_db()
        if not rattler_build_exe:
            _check_local_rattler_build()
        else:
            os.environ["RATTLER_BUILD_BIN"] = str(rattler_build_exe)
        recipes_to_build = build.recipes_for_names(recipe_names)

        build.build_recipes(recipes_to_build, tmp_dir, force_build)


@app.command()
def rebuild_recipe(
    recipe_names: Annotated[Optional[list[str]], typer.Argument()] = None,
    rattler_build_exe: Annotated[Optional[Path], typer.Option()] = None,
    force_rebuild: Annotated[bool, typer.Option()] = False,
):
    """Rebuild recipe from a string in the form of url::branch::path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        setup_db()
        if not rattler_build_exe:
            _check_local_rattler_build()
        else:
            os.environ["RATTLER_BUILD_BIN"] = str(rattler_build_exe)
        recipes_to_rebuild = build.recipes_for_names(recipe_names)
        rebuild.rebuild_recipe(recipes_to_rebuild, tmp_dir, force_rebuild)


@app.command()
def merge_patches(update_remote: Annotated[Optional[bool], typer.Option()] = False):
    """Merge database patches after CI jobs run to the database."""
    setup_db()
    build_metadata_to_sql.metadata_to_db(update_remote=update_remote)


@app.command()
def generate_html(
    update_remote: Annotated[Optional[bool], typer.Option()] = False,
    remote_branch: Annotated[Optional[str], typer.Option()] = None,
):
    """Rewrite the README.md file with updated statistics"""
    setup_db()
    rewrite.rerender_html(update_remote)


@app.command()
def setup_rattler_build():
    """Setup a source build environment for rattler. (currently for testing if this works)"""
    spinner_type = "simpleDots" if platform.system() == "Windows" else "dots"

    spinner = Spinner(spinner_type, "Setting up rattler build...")
    with Live(spinner) as live:
        print(":dancer: Rattler build setup starting :dancer:")
        _check_local_rattler_build(live)
        print(":dancer: Rattler build setup complete :dancer:")
