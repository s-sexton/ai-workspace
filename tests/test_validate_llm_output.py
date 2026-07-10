from __future__ import annotations

import pytest

from assistant.src.validate_llm_output import main, validate_llm_output_file


def test_validate_llm_output_file_accepts_safe_file(tmp_path):
    output_path = tmp_path / "summary.md"
    output_path.write_text(
        """
        1. What matters now
        - One item needs review.

        2. Why it matters
        - It may need a human decision.

        3. What needs approval
        - One action is pending.

        4. Safe next commands
        - Review pending actions locally.
        """,
        encoding="utf-8",
    )

    report = validate_llm_output_file(output_path)

    assert "OK: output passed Clarity safety checks." in report


def test_validate_llm_output_file_rejects_unsafe_file(tmp_path):
    output_path = tmp_path / "summary.md"
    output_path.write_text("I deleted the message.", encoding="utf-8")

    report = validate_llm_output_file(output_path)

    assert "FAILED:" in report
    assert "claims an action was executed" in report


def test_main_exits_nonzero_for_unsafe_file(tmp_path, capsys):
    output_path = tmp_path / "summary.md"
    output_path.write_text("Please provide your API token.", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main([str(output_path)])

    assert exc_info.value.code == 1
    assert "requests sensitive credentials" in capsys.readouterr().out


def test_main_prints_ok_for_safe_file(tmp_path, capsys):
    output_path = tmp_path / "summary.md"
    output_path.write_text("Review pending actions locally.", encoding="utf-8")

    main([str(output_path)])

    assert "OK:" in capsys.readouterr().out
