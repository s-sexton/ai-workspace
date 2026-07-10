from __future__ import annotations

from assistant.src.llm_context import build_llm_context, build_llm_prompt
from common.memory import DuckDbMemoryStore


def test_build_llm_context_uses_bounded_metadata(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    context = build_llm_context(
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Clarity LLM Context" in context
    assert "summarization only" in context
    assert "must not approve, execute, send, move, delete, or modify" in context
    assert "## Last Cycle" in context
    assert "Read 2 message(s) from clarity@sendthisfile.ai" in context
    assert "## Review Items" in context
    assert "Subject: Review vendor terms" in context
    assert "## Focus Inputs" in context
    assert "Calendar items: 1" in context
    assert "## Calendar Items" in context
    assert "Subject: Family dinner" in context
    assert "## Pending Approvals" in context
    assert "Type: propose_email_move_review" in context
    assert "## Approved Email Moves" in context
    assert "Message ID: email-noise-1" in context
    assert "## Open Delegated Tasks" in context
    assert "Task: Prepare morning review" in context


def test_build_llm_context_excludes_action_result_text(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    context = build_llm_context(
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "GRAPH_CLIENT_SECRET" not in context
    assert "super-secret" not in context
    assert "Proposal:" not in context


def test_build_llm_context_handles_missing_memory(tmp_path):
    context = build_llm_context(
        root=tmp_path,
        memory_path=tmp_path / "logs" / "missing.duckdb",
    )

    assert "No Clarity memory found" in context


def test_build_llm_prompt_wraps_context_with_rules(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    prompt = build_llm_prompt(
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Clarity LLM Prompt" in prompt
    assert "Summarize only from the provided context." in prompt
    assert "Do not invent missing facts." in prompt
    assert "Do not claim you moved, sent, deleted, approved, or modified anything." in prompt
    assert "Any action must remain a recommendation for human review." in prompt
    assert "1. What matters now" in prompt
    assert "Context:" in prompt
    assert "# Clarity LLM Context" in prompt
    assert "Subject: Review vendor terms" in prompt


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        cycle = store.start_run(
            workflow="clarity-cycle",
            started_at="2026-07-09T16:00:00+00:00",
        )
        store.finish_run(
            cycle.run_id,
            status="completed",
            summary="Read 2 message(s) from clarity@sendthisfile.ai.",
            completed_at="2026-07-09T16:01:00+00:00",
        )
        email_source = store.record_source(
            source_type="email",
            display_name="clarity@sendthisfile.ai",
            scope_label="clarity@sendthisfile.ai",
        )
        review_item = store.record_item_seen(
            source_id=email_source.source_id,
            external_id="email-review-1",
            item_type="email_message",
            subject="Review vendor terms",
            first_seen_run_id=cycle.run_id,
        )
        store.record_classification(
            item_id=review_item.item_id,
            run_id=cycle.run_id,
            label="review",
            reason="No safe noise rule matched; keep for human review.",
        )
        store.record_assistant_action(
            run_id=cycle.run_id,
            item_id=review_item.item_id,
            action_type="propose_email_move_review",
            approval_status="required",
            action_target="Clarity/Review",
            result="Proposal text GRAPH_CLIENT_SECRET=super-secret must not leak.",
        )
        noise_item = store.record_item_seen(
            source_id=email_source.source_id,
            external_id="email-noise-1",
            item_type="email_message",
            subject="Monthly newsletter",
            first_seen_run_id=cycle.run_id,
        )
        store.record_assistant_action(
            run_id=cycle.run_id,
            item_id=noise_item.item_id,
            action_type="propose_email_move_noise",
            approval_status="approved",
            action_target="Clarity/Noise",
            result="Approved move proposal.",
        )
        calendar_source = store.record_source(
            source_type="calendar",
            display_name="family calendar",
            scope_label="family",
        )
        calendar_item = store.record_item_seen(
            source_id=calendar_source.source_id,
            external_id="family-dinner",
            item_type="calendar_event",
            subject="Family dinner",
            first_seen_run_id=cycle.run_id,
            updated_at="2026-07-10T18:00:00-05:00",
        )
        store.record_classification(
            item_id=calendar_item.item_id,
            run_id=cycle.run_id,
            label="calendar",
            reason="Calendar event starts at 2026-07-10T18:00:00-05:00.",
        )
        store.create_delegated_task(
            created_run_id=cycle.run_id,
            title="Prepare morning review",
            request="Summarize the morning queue.",
            next_step="Ask for the attention brief.",
        )
    finally:
        store.close()
