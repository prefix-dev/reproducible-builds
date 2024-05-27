import sys
import matplotlib.pyplot as plt
import datetime
import json

from repror.conf import load_config


now_date = datetime.datetime.now().strftime("%Y-%m-%d")


platforms = sys.argv[1:]


by_platform = {}

ubuntu_platform = {}

for platform in platforms:
    with open(f"stat_data/{platform}_packages_info_{now_date}.json", "r") as f:
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
        reproducible = sum(value for value in by_platform[platform].values() if value)
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

print(previous_data)

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

build_text = f"""
Built with rattler-build {config["rattler-build"]["url"]} at commit {config["rattler-build"]["branch"]}

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

| Recipe Name | Is Reproducible |\n| --- | --- |
"""
for recipe, reproducible in ubuntu_platform.items():
    table += f"| {recipe} | {'Yes' if reproducible else 'No'} |\n"



rebuild_table = f"""{table}\n\n

"""


for platform in by_platform:
    build_text = f"Build on {platform}"
    if platform == "macos":
        build_text += " 13 and rebuild on 12"
    elif platform == "ubuntu":
        continue

    rebuild_table += f"""
{build_text}\n\n
    
| Recipe Name | Is Reproducible |\n| --- | --- |
"""
    for recipe, reproducible in by_platform[platform].items():
        rebuild_table += f"| {recipe} | {'Yes' if reproducible else 'No'} |\n"



# Save the table to README.md
with open("README.md", "w") as file:
    file.write(rebuild_table)
