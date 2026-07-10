"""Console helpers for Windows-friendly CLI output."""

from __future__ import annotations

import sys


def print_text(text: object = "", *, end: str = "\n") -> None:
    """Print text without crashing when the console cannot encode a character."""

    output = f"{text}{end}"
    try:
        sys.stdout.write(output)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe_output = output.encode(encoding, errors="replace").decode(encoding)
        sys.stdout.write(safe_output)
