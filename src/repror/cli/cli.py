import os
import platform
import tempfile
import logging
from pathlib import Path
from typing import Annotated, Optional

import typer

from rich.spinner import Spinner
from rich.live import Live

from repror.internals.config import load_config
from repror.internals.print import print
from repror.internals import build_metadata_to_sql


# Different CLI commands
from . import build_recipe as build
from . import generate_recipes as generate
from . import generate_html as html
from . import setup_rattler_build as setup
from . import rebuild_recipe as rebuild
from . import check_recipe
from .utils import pixi_root_cli

from ..internals.options import global_options


app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)

# Set up logging by reading the LOG_LEVEL environment variable
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())


@app.callback()
def main(
    skip_setup_rattler_build: bool = False,
    in_memory_sql: bool = False,
    no_output: bool = False,
):
    """
    \bRepror is a tool to:
    - Build/rebuild packages using conda build
    - Manage a local rattler-build environment for custom builds
    - Rewrite the reproducible-builds README.md file with update statistics
    """
    global_options.no_output = no_output
    if skip_setup_rattler_build:
        print("[dim yellow]Will skip setting up rattler-build[/dim yellow]")
        global_options.skip_setup_rattler_build = True
    if in_memory_sql:
        print("[yellow]Will use in-memory SQLite database[/yellow]")
        global_options.in_memory_sql = True


@app.command()
def generate_recipes():
    """Generate list of recipes from the configuration file."""
    generate.generate_recipes()


def _check_local_rattler_build():
    """Setup rattler build if set in yaml"""
    if global_options.skip_setup_rattler_build:
        return

    spinner_type = "simpleDots" if platform.system() == "Windows" else "dots"
    live_update_message = (
        "Rattler build setup complete ({outcome})"
        if platform.system() == "Windows"
        else ":white_check_mark: Rattler build setup complete ({outcome})"
    )

    spinner = Spinner(spinner_type, "Setting up rattler build...")
    with Live(spinner) as live:
        config = load_config()
        outcome = setup.setup_rattler_build(config=config, root_folder=pixi_root_cli())
        live.update(live_update_message.format(outcome=outcome))


@app.command()
def build_recipe(
    recipe_names: Annotated[Optional[list[str]], typer.Argument()] = None,
    rattler_build_exe: Annotated[Optional[Path], typer.Option()] = None,
    force: Annotated[bool, typer.Option()] = False,
    patch: Annotated[bool, typer.Option()] = False,
    run_rebuild: Annotated[bool, typer.Option("--rebuild")] = False,
    actions_url: Annotated[Optional[str], typer.Option()] = None,
):
    """Build recipe for specified recipe name."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        if not rattler_build_exe:
            _check_local_rattler_build()
        else:
            os.environ["RATTLER_BUILD_BIN"] = str(rattler_build_exe)
        recipes_to_build = build.recipes_for_names(recipe_names)

        build.build_recipes(recipes_to_build, Path(tmp_dir), force, patch, actions_url)
        if run_rebuild:
            print("Rebuilding recipes...")
            rebuild.rebuild_recipe(
                recipes_to_build, Path(tmp_dir), force, patch, actions_url
            )
            print("Verifying if rebuilds are reproducible...")
            check_recipe.check(recipes_to_build)


@app.command()
def rebuild_recipe(
    recipe_names: Annotated[Optional[list[str]], typer.Argument()] = None,
    rattler_build_exe: Annotated[Optional[Path], typer.Option()] = None,
    force: Annotated[bool, typer.Option()] = False,
    patch: Annotated[bool, typer.Option()] = False,
    actions_url: Annotated[Optional[str], typer.Option()] = None,
):
    """Rebuild recipe from a string in the form of url::branch::path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        if not rattler_build_exe:
            _check_local_rattler_build()
        else:
            os.environ["RATTLER_BUILD_BIN"] = str(rattler_build_exe)
        recipes_to_rebuild = build.recipes_for_names(recipe_names)
        rebuild.rebuild_recipe(
            recipes_to_rebuild, Path(tmp_dir), force, patch, actions_url
        )


@app.command()
def merge_patches(update_remote: Annotated[bool, typer.Option()] = False):
    """Merge database patches after CI jobs run to the database."""
    build_metadata_to_sql.metadata_to_db(update_remote=update_remote)


@app.command()
def generate_html(
    update_remote: Annotated[Optional[bool], typer.Option()] = None,
    remote_branch: Annotated[Optional[str], typer.Option()] = None,
):
    """Generate the HTML file with the statistics of the reproducible builds."""
    html.rerender_html(
        root_folder=pixi_root_cli(), update_remote=update_remote or False
    )


@app.command()
def setup_rattler_build():
    """Setup a source build environment for rattler. (currently for testing if this works)"""
    _check_local_rattler_build()


@app.command()
def check(recipe_names: Annotated[Optional[list[str]], typer.Argument()] = None):
    """Check if recipe name[s] is reproducible, by verifying it's build and rebuild hash."""
    recipes_to_check = build.recipes_for_names(recipe_names)
    check_recipe.check(recipes_to_check)
