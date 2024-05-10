      
import matplotlib.pyplot as plt
import datetime


now_date = datetime.datetime.now().strftime("%Y-%m-%d")


with open(f'data/chart_data_{now_date}.txt', 'r') as f:
    total_packages, reproducible, not_reproducible = map(int, f.read().split())

# Append the current date and total packages to a CSV file
with open('data/chart_data.csv', 'a') as f:
    f.write(f'{datetime.datetime.now().strftime("%Y-%m-%d")},{total_packages},{reproducible},{not_reproducible}\n')

# Read the CSV file to plot the data
dates = []
total_packages = []
reproducible = []
not_reproducible = []
with open('data/chart_data.csv', 'r') as f:
    for line in f:
        date, total, rep, not_rep = line.strip().split(',')
        dates.append(date)
        total_packages.append(int(total))
        reproducible.append(int(rep))
        not_reproducible.append(int(not_rep))

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
