"""Provider-neutral LLM summary contract for Clarity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from assistant.src.llm_context import build_llm_prompt
from assistant.src.llm_output import require_safe_llm_summary_output
from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH


class LlmSummaryProvider(Protocol):
    """A future provider that can summarize a Clarity prompt."""

    def summarize(self, prompt: str) -> str:
        """Return summary text for a prompt."""


@dataclass(frozen=True)
class LlmSummaryResult:
    """Validated LLM summary output with the prompt that produced it."""

    prompt: str
    summary: str


def generate_llm_summary(
    *,
    summarizer: LlmSummaryProvider,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    limit: int = 10,
) -> LlmSummaryResult:
    """Generate and validate a future LLM summary using an injected provider."""

    prompt = build_llm_prompt(
        root=root,
        memory_path=memory_path,
        limit=limit,
    )
    summary = summarizer.summarize(prompt)
    return LlmSummaryResult(
        prompt=prompt,
        summary=require_safe_llm_summary_output(summary),
    )
