import os
import re
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from pydantic import BaseModel
from rich.panel import Panel

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from repror.internals.db import (
    BuildState,
    get_rebuild_data,
    get_total_successful_builds_and_rebuilds,
)
from repror.internals.git import github_api
from repror.internals.print import print
from repror.internals.config import load_all_recipes


class StatisticData(BaseModel):
    build_state: BuildState
    rebuild_state: Optional[BuildState] = None
    recipe_name: str
    equal_hash: Optional[bool] = None
    reason: Optional[str] = None
    time: str
    actions_url: Optional[str] = None

    @property
    def is_success(self):
        return (
            self.build_state == BuildState.SUCCESS
            and self.rebuild_state
            and self.rebuild_state == BuildState.SUCCESS
            and self.equal_hash
        )


def get_platform_fa(platform):
    if platform == "windows":
        return "fa-brands fa-windows"  # Emoji for Windows
    elif platform == "darwin":
        return "fa-brands fa-apple"  # Emoji for macOS
    elif platform == "linux":
        return "fa-brands fa-linux"  # Emoji for Linux
    else:
        return "fa-solid fa-question"  # Default emoji if platform is unknown


reproducible = "fa-solid fa-thumbs-up text-green-600"
failure = "fa-solid fa-times text-red-600"
non_reproducible = "fa-solid fa-thumbs-down text-red-300"


def get_build_state_fa(
    build_state: BuildState, rebuild_state: Optional[BuildState] = None
):
    if build_state == BuildState.SUCCESS and (
        rebuild_state is None or rebuild_state == BuildState.SUCCESS
    ):
        return reproducible
    elif build_state == BuildState.FAIL:
        return failure
    elif build_state == BuildState.SUCCESS and rebuild_state == BuildState.FAIL:
        return non_reproducible
    else:
        return "fa-solid fa-question"


def platform_fa(platform):
    return get_platform_fa(platform)


def build_state_fa(build, rebuild):
    return get_build_state_fa(build, rebuild)


def interpolate_color(percentage: float):
    """Interpolate between red and green based on a percentage.
    Linear interpolation is used to calculate the color.
    """
    if percentage < 0 or percentage > 100:
        raise ValueError("Percentage must be between 0 and 100")

    # Normalize percentage to a range of 0 to 1
    normalized = percentage / 100

    # Calculate the red, green, and blue components
    r = round(255 * (1 - normalized))
    g = round(128 * normalized)
    b = 0

    # Return the color in RGB format
    return (r, g, b)


def get_docs_dir(root_folder: Path):
    """Get the docs directory path. By default get the local docs directory."""
    docs = os.getenv("REPRO_DOCS_DIR", "docs.local")
    return Path(root_folder) / Path(docs)


def remove_ansi_codes(text: str) -> str:
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def rerender_html(
    root_folder: Path,
    update_remote: bool = False,
    config_path: Path = Path("config.yaml"),
):
    docs_folder = get_docs_dir(root_folder)
    print(f"Generating into : {docs_folder}")

    env = Environment(
        loader=FileSystemLoader(searchpath=Path(__file__).parent / "templates")
    )
    env.filters["platform_fa"] = platform_fa

    builds = get_rebuild_data()

    total_recipes = len(load_all_recipes(str(config_path)).all_recipes)

    # Statistics for graph
    counts_per_platform = {}
    # Get the last 10 days
    start = datetime.now() - timedelta(days=9)
    end_of_day = datetime(start.year, start.month, start.day, 23, 59, 59)
    timestamps = [end_of_day + timedelta(days=i) for i in range(0, 10)]
    by_platform = defaultdict(list)
    for build in builds:
        # Do it in the loop so that we do this only once per platform
        # and we dont have to hardcode the platforms
        if build.platform_name not in counts_per_platform:
            counts = [
                get_total_successful_builds_and_rebuilds(
                    build.platform_name, before_time=time
                )
                for time in timestamps
            ]
            counts_per_platform[build.platform_name] = {
                # Total successful builds
                "builds": [count.builds for count in counts],
                # Total reproducible builds
                "rebuilds": [count.rebuilds for count in counts],
                # Total builds = builds + failed builds
                "total_builds": [count.total_builds for count in counts],
                # Total recipes
                "total_recipes": total_recipes,
            }

        if build.state == BuildState.FAIL:
            by_platform[build.platform_name].append(
                StatisticData(
                    build_state=build.state,
                    recipe_name=build.recipe_name,
                    time=str(build.timestamp),
                    reason=remove_ansi_codes(build.reason) if build.reason else None,
                    actions_url=build.actions_url,
                )
            )
            continue
        rebuild = build.rebuilds[-1] if build.rebuilds else None
        by_platform[build.platform_name].append(
            StatisticData(
                recipe_name=build.recipe_name,
                build_state=build.state,
                rebuild_state=rebuild.state if rebuild else None,
                reason=remove_ansi_codes(rebuild.reason)
                if rebuild and rebuild.reason
                else None,
                time=str(rebuild.timestamp) if rebuild else str(build.timestamp),
                equal_hash=build.build_hash == rebuild.rebuild_hash
                if rebuild
                else None,
                actions_url=build.actions_url,
            )
        )

    template = env.get_template("index.html.jinja")

    html_content = template.render(
        by_platform=by_platform,
        dates=[time.strftime("%Y-%m-%d") for time in timestamps],
        counts_per_platform=counts_per_platform,
        build_state_fa=build_state_fa,
        reproducible=reproducible,
        failure=failure,
        non_reproducible=non_reproducible,
        interpolate_color=interpolate_color,
    )
    # Save the table to README.md
    index_html_path = docs_folder / Path("index.html")
    index_html_path.parent.mkdir(exist_ok=True)
    index_html_path.write_text(html_content, encoding="utf-8")

    panel = Panel(
        f"Generated {index_html_path}.\n Run [bold]pixi r serve-html[/bold] to view",
        title="Success",
        style="green",
    )
    print(panel)
    if update_remote:
        # Update the index.html using GitHub API
        print(":running: Updating index.html with new data")
        github_api.update_obj(
            html_content,
            # Always update the index.html in the docs folder
            "docs/index.html",
            "Update statistics",
        )
