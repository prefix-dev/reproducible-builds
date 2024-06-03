from collections import defaultdict
import datetime
import glob
import json
import logging
import os
import tempfile
import matplotlib.pyplot as plt

from repror.conf import load_config


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
        platform_and_version = build_file.split("platform_")[1]
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


def plot(build_results_by_platform):
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")

    ubuntu_platform = {}

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
        rattler_tmpl_string = "Built with latest rattler-build"
    else:
        rattler_tmpl_string = f"Built with rattler-build {config["rattler-build"]["url"]} at commit {config["rattler-build"]["branch"]}"

    build_text = f"""
{rattler_tmpl_string}

Built on ubuntu 22.04 and rebuild
    """

    # Generate the Markdown table
    table = f"""
# Are we reproducible yet?

![License][license-badge]
[![Project Chat][chat-badge]][chat-url]


[license-badge]: https://img.shields.io/badge/license-BSD--3--Clause-blue?style=flat-square
[chat-badge]: https://img.shields.io/discord/1082332781146800168.svg?label=&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2&style=flat-square
[chat-url]: https://discord.gg/kKV8ZxyzY4


![Reproducibility Chart](data/chart.png)

{build_text}

| Recipe Name | Is Reproducible |
| --- | --- |\n"""
    for recipe, reproducible in ubuntu_platform.items():
        table += f"| {recipe} | {'Yes 🟢' if reproducible else 'No 🔴'} |\n"

    rebuild_table = f"""{table}\n\n"""

    for platform in build_results_by_platform:
        build_text = f"Built on {platform}"
        if platform == "macos":
            build_text += " 13 and rebuilt"
        elif platform == "windows":
            build_text += " 2022 and rebuilt"
        elif platform == "ubuntu":
            continue

        rebuild_table += f"""
{build_text}\n\n

| Recipe Name | Is Reproducible |
| --- | --- |\n"""

        for recipe, reproducible in build_results_by_platform[platform].items():
            rebuild_table += f"| {recipe} | {'Yes 🟢' if reproducible else 'No 🔴'} |\n"

    # Save the table to README.md
    with open("README.md", "w") as file:
        file.write(rebuild_table)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp_dir:
        build_results_by_platform = make_statistics(tmp_dir)

        plot(build_results_by_platform)
