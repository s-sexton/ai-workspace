from __future__ import annotations

import pytest

from common.memory import DuckDbMemoryStore, MemoryStoreError


@pytest.fixture
def memory_store():
    store = DuckDbMemoryStore()
    store.initialize_schema()
    try:
        yield store
    finally:
        store.close()


def test_records_run_lifecycle(memory_store):
    run = memory_store.start_run(workflow="jira-report")

    finished = memory_store.finish_run(
        run.run_id,
        status="completed",
        summary="Generated the Jira report.",
    )

    assert finished.run_id == run.run_id
    assert finished.workflow == "jira-report"
    assert finished.assistant_name == "Clarity"
    assert finished.status == "completed"
    assert finished.summary == "Generated the Jira report."
    assert finished.completed_at is not None


def test_records_source_item_classification_and_feedback(memory_store):
    run = memory_store.start_run(workflow="jira-report")
    source = memory_store.record_source(
        source_type="jira",
        display_name="Jira Cloud",
        scope_label="project:ACCT",
    )
    item = memory_store.record_item_seen(
        source_id=source.source_id,
        external_id="ACCT-101",
        item_type="jira_issue",
        subject="Review billing export",
        sender_or_owner="Accounting",
        updated_at="2026-07-09T10:00:00-05:00",
        content_hash="abc123",
        first_seen_run_id=run.run_id,
    )
    classification = memory_store.record_classification(
        item_id=item.item_id,
        run_id=run.run_id,
        label="review",
        reason="Customer-impacting accounting work.",
        confidence=0.91,
    )
    feedback = memory_store.record_feedback(
        item_id=item.item_id,
        run_id=run.run_id,
        feedback_type="confirmed",
        feedback_text="This needed review.",
    )

    recent = memory_store.recent_memory()

    assert classification.label == "review"
    assert feedback.feedback_text == "This needed review."
    assert recent[0].item_id == item.item_id
    assert recent[0].source_type == "jira"
    assert recent[0].display_name == "Jira Cloud"
    assert recent[0].subject == "Review billing export"
    assert recent[0].label == "review"
    assert recent[0].reason == "Customer-impacting accounting work."


def test_records_and_lists_open_delegated_tasks(memory_store):
    run = memory_store.start_run(workflow="delegated-work")

    task = memory_store.create_delegated_task(
        created_run_id=run.run_id,
        title="Prepare ACCT review",
        request="Summarize ACCT tickets for review.",
        next_step="Generate a short report.",
    )

    open_tasks = memory_store.list_open_delegated_tasks()

    assert open_tasks == (task,)
    assert open_tasks[0].approval_required is True
    assert open_tasks[0].status == "requested"


def test_rejects_secret_markers(memory_store):
    with pytest.raises(MemoryStoreError) as exc_info:
        memory_store.start_run(workflow="authorization: bearer secret")

    assert "sensitive auth data" in str(exc_info.value)
    assert "authorization: bearer secret" not in repr(exc_info.value).lower()


def test_validates_confidence_range(memory_store):
    run = memory_store.start_run(workflow="jira-report")
    source = memory_store.record_source(
        source_type="jira",
        display_name="Jira Cloud",
        scope_label="project:STF",
    )
    item = memory_store.record_item_seen(
        source_id=source.source_id,
        external_id="STF-1",
        item_type="jira_issue",
        subject="Example issue",
        first_seen_run_id=run.run_id,
    )

    with pytest.raises(MemoryStoreError):
        memory_store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="noise",
            reason="Automated update.",
            confidence=1.5,
        )


def test_recent_memory_limit_must_be_positive(memory_store):
    with pytest.raises(MemoryStoreError):
        memory_store.recent_memory(limit=0)
