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
        "\U00002500-\U00002bef"  # various symbols
        "\U00002700-\U000027bf"  # Dingbats
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U0001f100-\U0001f1ff"  # Enclosed Alphanumeric Supplement
        "\U0001f200-\U0001f2ff"  # Enclosed Ideographic Supplement
        "\U0001f300-\U0001f5ff"  # Miscellaneous Symbols and Pictographs
        "\U0001f600-\U0001f64f"  # Emoticons
        "\U0001f680-\U0001f6ff"  # Transport and Map Symbols
        "\U0001f700-\U0001f77f"  # Alchemical Symbols
        "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
        "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa00-\U0001fa6f"  # Chess Symbols
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "\U0001fb00-\U0001fbff"  # Symbols for Legacy Computing
        "]+",
        flags=re.UNICODE,
    )

    # Regex to remove text-based emoji representations like :dancer:
    text_emoji_pattern = re.compile(r":[a-z_]+:", re.UNICODE)

    text = emoji_pattern.sub(r"", text)
    text = text_emoji_pattern.sub(r"", text)

    return text


def print(text: str) -> None:
    if platform.system() == "Windows":
        return rich_print(strip_emojis(text))
    rich_print(text)
