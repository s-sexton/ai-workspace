"""Validate LLM summary output before display or storage."""

from __future__ import annotations

import re
from dataclasses import dataclass


_FORBIDDEN_PATTERNS = (
    (re.compile(r"\b(i|we|clarity)\s+(moved|deleted|sent|approved|executed|modified)\b", re.I), "claims an action was executed"),
    (re.compile(r"\b(i|we|clarity)\s+(will|can|should)\s+(move|delete|send|approve|execute|modify)\b", re.I), "suggests direct execution"),
    (re.compile(r"\b(send|provide|enter|share)\s+(your\s+)?(api\s*token|access\s*token|password|client\s*secret|secret)\b", re.I), "requests sensitive credentials"),
    (re.compile(r"\b[a-z0-9_]*(api[_-]?token|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*\S+", re.I), "contains credential-shaped text"),
    (re.compile(r"\b(bearer|basic)\s+[a-z0-9._~+/=-]{12,}", re.I), "contains authorization-shaped text"),
)


@dataclass(frozen=True)
class LlmOutputValidation:
    """Validation result for LLM summary text."""

    ok: bool
    problems: tuple[str, ...] = ()


def validate_llm_summary_output(text: str) -> LlmOutputValidation:
    """Return whether LLM summary text respects Clarity's boundaries."""

    if not isinstance(text, str) or not text.strip():
        return LlmOutputValidation(ok=False, problems=("summary is empty",))

    problems = []
    for pattern, problem in _FORBIDDEN_PATTERNS:
        if pattern.search(text):
            problems.append(problem)

    return LlmOutputValidation(ok=not problems, problems=tuple(problems))


def require_safe_llm_summary_output(text: str) -> str:
    """Return text or raise when LLM summary text is unsafe."""

    validation = validate_llm_summary_output(text)
    if not validation.ok:
        raise ValueError("Unsafe LLM summary output: " + "; ".join(validation.problems))
    return text
