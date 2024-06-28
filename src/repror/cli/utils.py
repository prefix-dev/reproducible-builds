import platform
from rich.table import Table
from rich.text import Text
from ..internals.db import Build, Rebuild
from ..internals.commands import pixi_root
from pathlib import Path


def pixi_root_cli():
    """Get the pixi root otherwise use the current directory."""
    root_folder = pixi_root()
    if not root_folder:
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
        Text.from_ansi(build.reason or ""),
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
        Text.from_ansi(rebuild.reason or ""),
        str(rebuild.timestamp),
        rebuild.actions_url,
    )
    return table


def reproducible_table(
    recipe_names: list[str], builds: list[Build], platform: str
) -> Table:
    """Converts a a list of Build instance to a rich table that shows the reproducibility of the builds"""
    cols = [
        "Name",
        "Platform",
        "Is Repro",
    ]
    table = Table(
        *cols, title=f"Are we repro ? Total recipes in our queue: {len(recipe_names)}"
    )

    build_map = {build.recipe_name: build for build in builds}

    for name in recipe_names:
        build_by_name = build_map.get(name)
        if not build_by_name:
            table.add_row(name, platform, "Not build yet")
            continue

        if not build_by_name.rebuilds:
            table.add_row(
                build_by_name.recipe_name,
                build_by_name.platform_name,
                "Not rebuild yet",
            )
            continue

        rebuild_hash = (
            build_by_name.rebuilds[-1].rebuild_hash if build_by_name.rebuilds else None
        )
        is_same = build_by_name.build_hash == rebuild_hash if rebuild_hash else False
        table.add_row(
            build_by_name.recipe_name,
            build_by_name.platform_name,
            "Yes" if is_same else "No",
        )

    return table


def platform_name() -> str:
    """Get the platform name."""
    return platform.system().lower()


def platform_version() -> str:
    """Get the platform version."""
    return platform.release()
