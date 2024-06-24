import os
from collections import defaultdict
from typing import Optional

from pydantic import BaseModel
from rich.panel import Panel

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from repror.internals.db import BuildState, get_rebuild_data
from repror.internals.git import github_api
from repror.internals.print import print


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


def get_docs_dir(root_folder: Path):
    """Get the docs directory path. By default get the local docs directory."""
    docs = os.getenv("REPRO_DOCS_DIR", "docs.local")
    return Path(root_folder) / Path(docs)


def rerender_html(root_folder: Path, update_remote: bool = False):
    docs_folder = get_docs_dir(root_folder)
    print(f"Generating into : {docs_folder}")

    env = Environment(
        loader=FileSystemLoader(searchpath=Path(__file__).parent / "templates")
    )

    builds = get_rebuild_data()

    by_platform = defaultdict(list)

    for build in builds:
        if build.state == BuildState.FAIL:
            by_platform[build.platform_name].append(
                StatisticData(
                    build_state=build.state,
                    recipe_name=build.recipe_name,
                    time=str(build.timestamp),
                    reason=build.reason,
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
                reason=rebuild.reason if rebuild else None,
                time=str(rebuild.timestamp) if rebuild else str(build.timestamp),
                equal_hash=build.build_hash == rebuild.rebuild_hash
                if rebuild
                else None,
                actions_url=build.actions_url,
            )
        )

    template = env.get_template("index.html")

    html_content = template.render(by_platform=by_platform)
    # Save the table to README.md
    index_html_path = docs_folder / Path("index.html")
    index_html_path.parent.mkdir(exist_ok=True)
    index_html_path.write_text(html_content)

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
