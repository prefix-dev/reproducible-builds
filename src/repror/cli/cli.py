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
from repror.internals.db import get_rebuild_data, setup_engine
from repror.internals.print import print
from repror.internals import patch_database
from repror.internals.rattler_build import rattler_build_hash

# Different CLI commands
from . import build_recipe as build
from . import generate_recipes as generate
from . import generate_html as html
from . import setup_rattler_build as setup
from . import rebuild_recipe as rebuild
from . import v1_sampler
from .utils import pixi_root_cli, platform_name, reproducible_table

from ..internals.options import global_options
from ..internals.config import load_all_recipes


def _print_status(msg: str) -> None:
    """Print status message to stderr to avoid interfering with stdout capture."""
    import sys
    from rich.console import Console

    console = Console(file=sys.stderr)
    console.print(msg)


app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)

# Set up logging by reading the LOG_LEVEL environment variable
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())


@app.callback()
def main(
    skip_setup_rattler_build: bool = False,
    in_memory_sql: bool = False,
    no_output: bool = False,
    config_path: str = "config.yaml",
):
    """
    \bRepror is a tool to:
    - Build/rebuild packages using conda build
    - Manage a local rattler-build environment for custom builds
    - Rewrite the reproducible-builds README.md file with update statistics
    """
    global_options.no_output = no_output
    global_options.config_path = config_path
    if skip_setup_rattler_build:
        _print_status("[dim yellow]Will skip setting up rattler-build[/dim yellow]")
        global_options.skip_setup_rattler_build = True
    if in_memory_sql:
        _print_status("[yellow]Will use in-memory SQLite database[/yellow]")
        global_options.in_memory_sql = True
    setup_engine(in_memory_sql)


@app.command()
def generate_recipes(
    all_: Annotated[
        bool, typer.Option("--all", help="Generate all recipe names")
    ] = False,
):
    """Generate list of recipes from the configuration file. By default it will print only the ones that are not built yet."""
    generate.generate_recipes(rattler_build_hash=rattler_build_hash(), all_=all_)


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
        recipes_to_build = build.recipes_for_names(
            recipe_names, global_options.config_path
        )

        build.build_recipes(recipes_to_build, Path(tmp_dir), force, patch, actions_url)
        if run_rebuild:
            print("Rebuilding recipes...")
            rebuild.rebuild_recipe(
                recipes_to_build, Path(tmp_dir), force, patch, actions_url
            )
            print("Verifying if rebuilds are reproducible...")
            builds = get_rebuild_data(recipe_names, platform_name())
            print(
                reproducible_table(
                    [recipe.name for recipe in recipes_to_build],
                    builds,
                    platform_name(),
                )
            )


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
        recipes_to_rebuild = build.recipes_for_names(
            recipe_names, global_options.config_path
        )
        rebuild.rebuild_recipe(
            recipes_to_rebuild, Path(tmp_dir), force, patch, actions_url
        )


@app.command()
def merge_patches(update_remote: Annotated[bool, typer.Option()] = False):
    """Merge database patches after CI jobs run to the database."""
    num_builds_patches = patch_database.patch_builds_to_db()

    if num_builds_patches > 0:
        print(
            f":red_car: Database patched. {num_builds_patches} build patches applied."
        )
    else:
        print(":man_shrugging: No build patches to merge.")

    all_recipes = load_all_recipes()

    if update_remote and (num_builds_patches > 0 or all_recipes.saved_recipes > 0):
        print(":globe_with_meridians: Database patches merged to remote database.")
        patch_database.write_database_to_remote()


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
def status(
    recipe_names: Annotated[Optional[list[str]], typer.Argument()] = None,
    platform: Annotated[str, typer.Option()] = platform.system().lower(),
):
    """Check if recipe name[s] is reproducible for your platform, by verifying it's build and rebuild hash."""
    recipe_names = [recipe.name for recipe in build.recipes_for_names(recipe_names)]
    builds = get_rebuild_data(recipe_names, platform)
    print(reproducible_table(recipe_names, builds, platform))


# Add v1 sampler subcommands
app.add_typer(
    v1_sampler.app,
    name="v1",
    help="Commands for V1 recipe package sampling and rebuilding",
)
