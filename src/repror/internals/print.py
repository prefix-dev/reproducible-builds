import re
import platform

from rich import print as rich_print


def strip_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f700-\U0001f77f"  # alchemical symbols
        "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
        "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa00-\U0001fa6f"  # Chess Symbols
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "\U00002700-\U000027bf"  # Dingbats
        "\U0001f1e0-\U0001f1ff"  # Flags (iOS)
        "\U00002600-\U000026ff"  # Miscellaneous Symbols
        "\U00002b50-\U00002b55"  # Additional symbols
        "]+",
        flags=re.UNICODE,
    )

    return emoji_pattern.sub(r"", text)


def print(text: str) -> str:
    if platform.system() == "Windows":
        rich_print(strip_emojis(text))
    rich_print(text)
