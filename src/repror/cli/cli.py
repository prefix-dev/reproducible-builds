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

app = typer.Typer(no_args_is_help=True)


class GlobalOptions:
    local_rattler_build: bool = False

    def __init__(self):
        self.local_rattler_build = False


global_options = GlobalOptions()


@app.callback()
def main(local_rattler_build: bool = False):
    """
    Manage users in the awesome CLI app.
    """
    if local_rattler_build:
        print("[bold yellow]Will use local rattler-build[/bold yellow]")
        global_options.local_rattler_build = True


@app.command()
def generate_recipes():
    """Generate list of recipes from the configuration file."""
    generate.generate_recipes()


def _check_local_rattler_build(tmp_dir: Path):
    """Setup rattler build if local_rattler_build is set"""
    if not global_options.local_rattler_build:
        config = load_config()
        setup.setup_rattler_build(rattler_build_config=config, tmp_dir=Path(tmp_dir))


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
    with tempfile.TemporaryDirectory() as tmp_dir:
        build_results_by_platform = rewrite.make_statistics(tmp_dir)
        rewrite.plot(build_results_by_platform)


@app.command()
def setup_rattler_build():
    """Setup a source build environment for rattler. (currently for testing if this works)"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = load_config()
        setup.setup_rattler_build(rattler_build_config=config, tmp_dir=Path(tmp_dir))
