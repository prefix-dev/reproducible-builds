from rich.table import Table
from ..internals.db import Build, Rebuild
from ..internals.commands import pixi_root
from pathlib import Path


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


def build_to_table(build: Build) -> Table:
    """Converts a Build instance to a rich table"""
    cols = [
        "Build Status",
        "Build Hash",
        "Build Location",
        "Failure Reason",
        "Timestamp",
        "Actions URL",
    ]
    table = Table(*cols, title=f"Build Details ({build.recipe_name})")
    table.add_row(
        build.state.value,
        build.build_hash,
        build.build_loc,
        build.reason,
        str(build.timestamp),
        build.actions_url,
    )
    return table


def rebuild_to_table(rebuild: Rebuild) -> Table:
    """Converts a Rebuild instance to a rich table"""
    cols = [
        "Build Status",
        "Failure Reason",
        "Timestamp",
        "Actions URL",
    ]
    table = Table(*cols, title=f"Re-build Details ({rebuild.recipe_name})")
    table.add_row(
        rebuild.state.value,
        rebuild.reason,
        str(rebuild.timestamp),
        rebuild.actions_url,
    )
    return table
