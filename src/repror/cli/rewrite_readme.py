from collections import defaultdict
import datetime
import glob
import json
import logging
import os

from rich import print
from rich.syntax import Syntax

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt

from repror.internals.conf import load_config
from repror.internals.git import github_api


README_PATH = "README.md"
DATA_CHART_PATH = "data/chart.png"


def find_infos(folder_path: str, suffix: str):
    """
    Use glob to find all .json files in the folder
    """
    json_files = glob.glob(os.path.join(folder_path, f"*/**{suffix}.json"))
    return json_files


def make_statistics(build_info_dir: str = "build_info") -> dict:
    build_info_by_platform = defaultdict(dict)
    rebuild_info_by_platform = defaultdict(dict)

    total_build_info = {}
    total_rebuild_info = {}

    build_infos = find_infos(build_info_dir, "build_info")

    for build_file in build_infos:
        platform_and_version = build_file.split("platform_")[1]
        platform, *_ = platform_and_version.split("_")

        with open(build_file, "r") as f:
            build_info_by_platform[platform].update(json.load(f))

    rebuild_infos = find_infos(build_info_dir, "rebuild_info")

    for rebuild_file in rebuild_infos:
        platform_and_version = rebuild_file.split("platform_")[1]
        platform, *_ = platform_and_version.split("_")

        with open(rebuild_file, "r") as f:
            rebuild_info_by_platform[platform].update(json.load(f))

        if platform == "linux":
            total_build_info.update(build_info_by_platform["linux"])
            total_rebuild_info.update(rebuild_info_by_platform["linux"])

    # calculate entire statistics that will be used to render main table
    assert len(total_build_info) == len(total_rebuild_info)

    build_results_by_platform = {}

    for platform in build_info_by_platform:
        build_results_by_platform[platform] = {}
        for recipe_name, info in build_info_by_platform[platform].items():
            if not info:
                build_results_by_platform[platform][recipe_name] = False
                continue

            re_info = rebuild_info_by_platform[platform][recipe_name]

            if not re_info:
                build_results_by_platform[platform][recipe_name] = False
                continue

            build_results_by_platform[platform][recipe_name] = (
                info["pkg_hash"] == re_info["pkg_hash"]
            )

    return build_results_by_platform


def plot(
    build_results_by_platform, update_remote: bool = False, remote_branch: str = None
):
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")

    with open("data/history.json", "r+") as history_file:
        previous_data = json.load(history_file)

        now_date = str(datetime.datetime.now().strftime("%Y-%m-%d"))

        now_platform = {}
        for platform in build_results_by_platform:
            total_packages = len(build_results_by_platform[platform])
            reproducible = sum(
                1 for value in build_results_by_platform[platform].values() if value
            )
            not_reproducible = sum(
                1 for value in build_results_by_platform[platform].values() if not value
            )
            now_platform[platform] = {
                "total_packages": total_packages,
                "repro": reproducible,
                "not_repro": not_reproducible,
            }

        previous_data[now_date] = now_platform

        history_file.seek(0)

        json.dump(previous_data, history_file)

        history_file.truncate()

    # Read the CSV file to plot the data
    dates = []
    total_packages = []
    reproducible = []
    not_reproducible = []

    # we take ubuntu as a base image
    for date in previous_data:
        if "linux" not in previous_data[date]:
            logging.warning(f"Skipping date {date} as linux is missing ")
            continue

        info = previous_data[date]["linux"]
        dates.append(date)
        total_packages.append(info["total_packages"])
        reproducible.append(info["repro"])
        not_reproducible.append(info["not_repro"])

    plt.figure(figsize=(12, 6))
    plt.plot(dates, total_packages, marker="o", label="Total Packages", color="blue")
    plt.plot(dates, reproducible, marker="o", label="Reproducible", color="green")
    plt.plot(dates, not_reproducible, marker="o", label="Not Reproducible", color="red")

    plt.xlabel("Date")
    plt.ylabel("Number of Packages")
    plt.title("Is Rattler-Build reproducible yet?")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig("data/chart.png")

    config = load_config()

    if "rattler-build" not in config:
        build_text = "Built with latest rattler-build"
    else:
        build_text = f"Built with rattler-build {config["rattler-build"]["url"]} at commit {config["rattler-build"]["rev"]}"

    # Generate the Markdown table
    env = Environment(
        loader=FileSystemLoader(searchpath=Path(__file__).parent / "templates")
    )
    template = env.get_template("README.md")
    readme_content = template.render(
        build_text=build_text, build_results_by_platform=build_results_by_platform
    )

    # Save the table to README.md
    with open("README.md", "w") as file:
        file.write(readme_content)

    if update_remote:
        # Update the README.md using GitHub API
        print(":running: Updating README.md with new statistics")
        github_api.update_obj(
            readme_content, README_PATH, "Update statistics", remote_branch
        )
        data_chart_bytes = Path("data/chart.png").read_bytes()
        print(":running: Updating data/chart.png with new plot")
        github_api.update_obj(
            data_chart_bytes, DATA_CHART_PATH, "Update data chart graph", remote_branch
        )

    print(Syntax(readme_content, "markdown"))
