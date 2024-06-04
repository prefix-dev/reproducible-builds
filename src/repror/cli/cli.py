import tempfile
from pathlib import Path

import typer

from repror.internals.conf import load_config

# Different CLI commands
from . import build_recipe as build
from . import generate_recipes as generate
from . import rewrite_readme as rewrite
from . import setup_rattler_build as setup
from . import rebuild_recipe as rebuild

app = typer.Typer(no_args_is_help=True)

from rich import print


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
def build_recipe(recipe_str: str):
    """Build recipe from a string in the form of url::branch::path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        _check_local_rattler_build(tmp_dir)
        build.build_recipe_from_str(recipe_str, tmp_dir)


@app.command()
def rebuild_recipe(recipe_str: str):
    """Rebuild recipe from a string in the form of url::branch::path."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        _check_local_rattler_build(tmp_dir)
        rebuild.rebuild_recipe(recipe_str, tmp_dir)


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
