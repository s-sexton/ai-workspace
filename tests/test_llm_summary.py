from __future__ import annotations

import pytest

from assistant.src.llm_summary import generate_llm_summary
from common.memory import DuckDbMemoryStore


class StaticSummarizer:
    def __init__(self, summary):
        self.summary = summary
        self.prompts = []

    def summarize(self, prompt):
        self.prompts.append(prompt)
        return self.summary


def test_generate_llm_summary_uses_prompt_and_validates_output(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    summarizer = StaticSummarizer(
        """
        1. What matters now
        - One item needs review.

        2. Why it matters
        - It may require a decision.

        3. What needs approval
        - Action abc123 is pending approval.

        4. Safe next commands
        - Review pending actions locally.
        """
    )

    result = generate_llm_summary(
        summarizer=summarizer,
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Clarity LLM Prompt" in result.prompt
    assert "# Clarity LLM Context" in result.prompt
    assert "Subject: Review vendor terms" in result.prompt
    assert result.prompt == summarizer.prompts[0]
    assert "One item needs review" in result.summary


def test_generate_llm_summary_rejects_unsafe_provider_output(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    summarizer = StaticSummarizer("I moved the message to Deleted Items.")

    with pytest.raises(ValueError) as exc_info:
        generate_llm_summary(
            summarizer=summarizer,
            root=tmp_path,
            memory_path=memory_path,
        )

    assert "claims an action was executed" in str(exc_info.value)


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="clarity-cycle")
        source = store.record_source(
            source_type="email",
            display_name="clarity@sendthisfile.ai",
            scope_label="clarity@sendthisfile.ai",
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id="email-review-1",
            item_type="email_message",
            subject="Review vendor terms",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="review",
            reason="No safe noise rule matched; keep for human review.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Read 1 message(s) from clarity@sendthisfile.ai.",
        )
    finally:
        store.close()
