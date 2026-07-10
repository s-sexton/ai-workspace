from __future__ import annotations

import pytest

from assistant.src.llm_output import (
    require_safe_llm_summary_output,
    validate_llm_summary_output,
)


def test_validate_llm_summary_output_accepts_safe_recommendations():
    result = validate_llm_summary_output(
        """
        1. What matters now
        - One message needs review.

        2. Why it matters
        - It may require a human decision.

        3. What needs approval
        - Action abc123 is pending approval.

        4. Safe next commands
        - Review pending actions locally.
        """
    )

    assert result.ok
    assert result.problems == ()


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("I moved the message to Deleted Items.", "claims an action was executed"),
        ("Clarity will delete the message now.", "suggests direct execution"),
        ("Please provide your API token.", "requests sensitive credentials"),
        ("GRAPH_CLIENT_SECRET=super-secret", "contains credential-shaped text"),
        ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz", "contains authorization-shaped text"),
    ],
)
def test_validate_llm_summary_output_rejects_unsafe_text(text, problem):
    result = validate_llm_summary_output(text)

    assert not result.ok
    assert problem in result.problems


def test_require_safe_llm_summary_output_raises_for_unsafe_text():
    with pytest.raises(ValueError) as exc_info:
        require_safe_llm_summary_output("I approved the pending move.")

    assert "claims an action was executed" in str(exc_info.value)


def test_validate_llm_summary_output_rejects_empty_text():
    result = validate_llm_summary_output(" ")

    assert not result.ok
    assert result.problems == ("summary is empty",)
