"""Validate a local future LLM summary output file."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from assistant.src.llm_output import validate_llm_summary_output


def validate_llm_output_file(path: Path | str) -> str:
    """Return a human-readable validation report for a local output file."""

    output_path = Path(path)
    text = output_path.read_text(encoding="utf-8")
    validation = validate_llm_summary_output(text)
    if validation.ok:
        return "# LLM Output Validation\n\nOK: output passed Clarity safety checks."

    lines = ["# LLM Output Validation", "", "FAILED: output did not pass safety checks."]
    lines.append("")
    lines.append("## Problems")
    lines.extend(f"- {problem}" for problem in validation.problems)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    report = validate_llm_output_file(args.path)
    print(report)
    if "FAILED:" in report:
        raise SystemExit(1)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a local future LLM summary output file."
    )
    parser.add_argument("path", help="Path to local summary text or Markdown.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
