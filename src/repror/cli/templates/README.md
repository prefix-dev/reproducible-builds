# Are we reproducible yet?

![License][license-badge]
[![Project Chat][chat-badge]][chat-url]

[license-badge]: https://img.shields.io/badge/license-BSD--3--Clause-blue?style=flat-square
[chat-badge]: https://img.shields.io/discord/1082332781146800168.svg?label=&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2&style=flat-square
[chat-url]: https://discord.gg/kKV8ZxyzY4

![Reproducibility Chart](data/chart.png)

{{ build_text }}

{% for platform in build_results_by_platform %}
Built on {{ platform }}

| Recipe Name | Is Reproducible |
| --- | --- |
{% for recipe, reproducible in build_results_by_platform[platform].items() %}
| {{ recipe }} | {{ 'Yes 🟢' if reproducible else 'No 🔴' }} |
{% endfor %}
{% endfor %}
