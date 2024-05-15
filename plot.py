      
import matplotlib.pyplot as plt
import datetime
import json


now_date = datetime.datetime.now().strftime("%Y-%m-%d")


with open(f'data/chart_data_{now_date}.txt', 'r') as f:
    total_packages, reproducible, not_reproducible = map(int, f.read().split())

# Append the current date and total packages to a CSV file
with open('data/history.json', 'r+') as history_file:
    previous_data = json.load(history_file)

    now_date = str(datetime.datetime.now().strftime("%Y-%m-%d"))

    previous_data[now_date] = {
        "total_packages": total_packages,
        "repro": reproducible,
        "not_repro": not_reproducible
    }

    history_file.seek(0)

    json.dump(previous_data, history_file)

    history_file.truncate()

with open(f'data/packages_info_{now_date}.json', 'r') as info:
    results = json.load(info)


# Read the CSV file to plot the data
dates = []
total_packages = []
reproducible = []
not_reproducible = []


for date in previous_data:
    dates.append(date)
    info = previous_data[date]

    total_packages.append(info["total_packages"])
    reproducible.append(info["repro"])
    not_reproducible.append(info["not_repro"])

plt.figure(figsize=(12, 6))
plt.plot(dates, total_packages, marker='o', label='Total Packages', color='blue')
plt.plot(dates, reproducible, marker='o', label='Reproducible', color='green')
plt.plot(dates, not_reproducible, marker='o', label='Not Reproducible', color='red')


plt.xlabel('Date')
plt.ylabel('Number of Packages')
plt.title('Is Rattler-Build reproducible yet?')
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig('data/chart.png')





# Generate the Markdown table
table = """
# Are we reproducible yet?

![License][license-badge]
[![Project Chat][chat-badge]][chat-url]


[license-badge]: https://img.shields.io/badge/license-BSD--3--Clause-blue?style=flat-square
[chat-badge]: https://img.shields.io/discord/1082332781146800168.svg?label=&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2&style=flat-square
[chat-url]: https://discord.gg/kKV8ZxyzY4


![Reproducibility Chart](data/chart.png)


| Recipe Name | Is Reproducible |\n| --- | --- |\n
"""
for recipe, reproducible in results.items():
    table += f"| {recipe} | {'Yes' if reproducible else 'No'} |\n"

# Save the table to README.md
with open("README.md", "w") as file:
    file.write(table)