import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import matplotlib.pyplot as plt

from repror.conf import load_config


def make_statistics(platform_with_versions: list[str], temp_dir) -> Path:
    build_info_by_platform = {}
    rebuild_info_by_platform = {}

    total_build_info = {}
    total_rebuild_info = {}

    for platform_and_version in platform_with_versions:
        base_platform, from_version, to_version = platform_and_version.split("_")

        with open(
            f"build_info/{base_platform}/{base_platform}_{from_version}_build_info.json",
            "r",
        ) as f:
            build_info_by_platform[base_platform] = json.load(f)

        with open(
            f"build_info/{base_platform}/{base_platform}_{from_version}_{to_version}_rebuild_info.json",
            "r",
        ) as f:
            rebuild_info_by_platform[base_platform] = json.load(f)

        if base_platform == "ubuntu":
            total_build_info.update(build_info_by_platform["ubuntu"])
            total_rebuild_info.update(rebuild_info_by_platform["ubuntu"])

    # calculate entire statistics that will be used to render main table
    assert len(total_build_info) == len(total_rebuild_info)

    today_date = datetime.datetime.now().strftime("%Y-%m-%d")

    build_results_by_platform = {}

    stat_data_dir = Path(os.path.join(temp_dir, "stat_data"))

    # we should fail if it's already present
    stat_data_dir.mkdir(parents=True)

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

        with open(
            f"{stat_data_dir}/{platform}_packages_info_{today_date}.json", "w"
        ) as pkg_info:
            json.dump(build_results_by_platform[platform], pkg_info)

    return stat_data_dir


def plot(platforms, stat_dir: Path):
    now_date = datetime.datetime.now().strftime("%Y-%m-%d")

    by_platform = {}

    ubuntu_platform = {}

    for platform in platforms:
        with open(f"{stat_dir}/{platform}_packages_info_{now_date}.json", "r") as f:
            platform_build_info = json.load(f)

        by_platform[platform] = platform_build_info

        if platform == "ubuntu":
            ubuntu_platform = platform_build_info

    with open("data/history.json", "r+") as history_file:
        previous_data = json.load(history_file)

        now_date = str(datetime.datetime.now().strftime("%Y-%m-%d"))

        now_platform = {}
        for platform in by_platform:
            total_packages = len(by_platform[platform])
            reproducible = sum(
                value for value in by_platform[platform].values() if value
            )
            not_reproducible = sum(
                value for value in by_platform[platform].values() if not value
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
        info = previous_data[date]["ubuntu"]
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

Built on ubunutu 22.04 and rebuild on 20.04
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

    for platform in by_platform:
        build_text = f"Build on {platform}"
        if platform == "macos":
            build_text += " 13 and rebuild on 12"
        elif platform == "ubuntu":
            continue

        rebuild_table += f"""
{build_text}\n\n
        
| Recipe Name | Is Reproducible |
| --- | --- |\n"""

        for recipe, reproducible in by_platform[platform].items():
            rebuild_table += f"| {recipe} | {'Yes 🟢' if reproducible else 'No 🔴'} |\n"

    # Save the table to README.md
    with open("README.md", "w") as file:
        file.write(rebuild_table)


if __name__ == "__main__":
    platform_with_versions = sys.argv[1:]

    if "ubuntu_22.04_20.04" not in platform_with_versions:
        print(
            "ubuntu_22.04_20.04 platform is required ,for now, to calculate total statistics"
        )
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp_dir:
        stat_dir = make_statistics(platform_with_versions, tmp_dir)
        platforms = [platform.split("_")[0] for platform in platform_with_versions]
        plot(platforms, stat_dir)
