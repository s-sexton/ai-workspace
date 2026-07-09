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


def test_returns_latest_run(memory_store):
    memory_store.start_run(
        workflow="jira-report",
        started_at="2026-07-09T10:00:00+00:00",
    )
    latest = memory_store.start_run(
        workflow="jira-report",
        started_at="2026-07-09T11:00:00+00:00",
    )

    assert memory_store.latest_run(workflow="jira-report") == latest
    assert memory_store.latest_run(workflow="missing") is None


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
    review_items = memory_store.recent_memory_by_label("review")
    recent_feedback = memory_store.recent_feedback()

    assert classification.label == "review"
    assert feedback.feedback_text == "This needed review."
    assert recent[0].item_id == item.item_id
    assert recent[0].source_type == "jira"
    assert recent[0].display_name == "Jira Cloud"
    assert recent[0].subject == "Review billing export"
    assert recent[0].label == "review"
    assert recent[0].reason == "Customer-impacting accounting work."
    assert review_items == recent
    assert len(recent_feedback) == 1
    assert recent_feedback[0].external_id == "ACCT-101"
    assert recent_feedback[0].subject == "Review billing export"
    assert recent_feedback[0].feedback_type == "confirmed"
    assert recent_feedback[0].feedback_text == "This needed review."


def test_finds_item_by_item_id_or_external_id(memory_store):
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
        subject="Build report",
        first_seen_run_id=run.run_id,
    )

    assert memory_store.find_item_seen(item.item_id) == item
    assert memory_store.find_item_seen("STF-1") == item
    assert memory_store.find_item_seen("missing") is None


def test_records_generated_artifact(memory_store):
    run = memory_store.start_run(workflow="jira-report")

    artifact = memory_store.record_generated_artifact(
        run_id=run.run_id,
        artifact_type="markdown_report",
        path="reports/jira-report.md",
        summary="Jira report with 2 issue(s).",
    )

    artifacts = memory_store.list_generated_artifacts(run_id=run.run_id)

    assert artifacts == (artifact,)
    assert artifacts[0].path == "reports/jira-report.md"
    assert artifacts[0].summary == "Jira report with 2 issue(s)."


def test_records_assistant_action(memory_store):
    run = memory_store.start_run(workflow="jira-report")

    action = memory_store.record_assistant_action(
        run_id=run.run_id,
        action_type="generate_jira_report",
        approval_status="not_required",
        action_target="reports/jira-report.md",
        result="Wrote reports/jira-report.md",
    )

    actions = memory_store.recent_actions()

    assert actions == (action,)
    assert actions[0].action_type == "generate_jira_report"
    assert actions[0].approval_status == "not_required"
    assert actions[0].action_target == "reports/jira-report.md"
    assert actions[0].result == "Wrote reports/jira-report.md"


def test_initialization_adds_action_target_to_existing_memory(tmp_path):
    memory_path = tmp_path / "memory.duckdb"
    store = DuckDbMemoryStore(memory_path)
    try:
        store._connection.execute(
            """
            CREATE TABLE assistant_actions (
                action_id VARCHAR PRIMARY KEY,
                run_id VARCHAR NOT NULL,
                item_id VARCHAR,
                action_type VARCHAR NOT NULL,
                approval_status VARCHAR NOT NULL,
                result VARCHAR,
                created_at VARCHAR NOT NULL
            )
            """
        )
        store.initialize_schema()
        run = store.start_run(workflow="migration-check")
        action = store.record_assistant_action(
            run_id=run.run_id,
            action_type="propose_email_move_review",
            approval_status="required",
            action_target="Clarity/Review",
        )
        assert action.action_target == "Clarity/Review"
    finally:
        store.close()


def test_updates_assistant_action_approval(memory_store):
    run = memory_store.start_run(workflow="email-review")
    action = memory_store.record_assistant_action(
        run_id=run.run_id,
        action_type="propose_email_move_noise",
        approval_status="required",
        action_target="Clarity/Noise",
        result="Proposed moving message metadata to Clarity/Noise.",
    )

    updated = memory_store.update_assistant_action_approval(
        action_id=action.action_id,
        approval_status="approved",
    )

    assert updated.action_id == action.action_id
    assert updated.approval_status == "approved"
    assert memory_store.pending_actions() == ()
    approved_actions = memory_store.actions_by_approval_status("approved")
    assert approved_actions[0].action_id == action.action_id
    assert approved_actions[0].approval_status == "approved"
    assert approved_actions[0].action_target == "Clarity/Noise"

    executed = memory_store.update_assistant_action_approval(
        action_id=action.action_id,
        approval_status="executed",
    )

    assert executed.approval_status == "executed"
    assert memory_store.actions_by_approval_status("approved") == ()
    executed_actions = memory_store.actions_by_approval_status("executed")
    assert executed_actions[0].action_id == action.action_id


def test_action_queue_includes_item_external_id(memory_store):
    run = memory_store.start_run(workflow="email-review")
    source = memory_store.record_source(
        source_type="email",
        display_name="clarity@sendthisfile.ai",
        scope_label="clarity@sendthisfile.ai",
    )
    item = memory_store.record_item_seen(
        source_id=source.source_id,
        external_id="graph-message-1",
        item_type="email_message",
        subject="Review this",
        first_seen_run_id=run.run_id,
    )
    action = memory_store.record_assistant_action(
        run_id=run.run_id,
        item_id=item.item_id,
        action_type="propose_email_move_review",
        approval_status="required",
        action_target="Clarity/Review",
    )

    pending = memory_store.pending_actions()

    assert pending[0].action_id == action.action_id
    assert pending[0].item_external_id == "graph-message-1"
    assert pending[0].item_subject == "Review this"


def test_rejects_invalid_assistant_action_approval(memory_store):
    run = memory_store.start_run(workflow="email-review")
    action = memory_store.record_assistant_action(
        run_id=run.run_id,
        action_type="propose_email_move_noise",
        approval_status="required",
    )

    with pytest.raises(MemoryStoreError):
        memory_store.update_assistant_action_approval(
            action_id=action.action_id,
            approval_status="maybe",
        )


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


def test_updates_delegated_task_status(memory_store):
    run = memory_store.start_run(workflow="delegated-work")
    task = memory_store.create_delegated_task(
        created_run_id=run.run_id,
        title="Prepare ACCT review",
        request="Summarize ACCT tickets for review.",
        next_step="Generate a short report.",
    )

    updated = memory_store.update_delegated_task_status(
        task_id=task.task_id,
        status="completed",
        next_step="Report reviewed.",
        completed_at="2026-07-09T20:00:00+00:00",
    )

    assert updated.status == "completed"
    assert updated.next_step == "Report reviewed."
    assert updated.completed_at == "2026-07-09T20:00:00+00:00"
    assert memory_store.list_open_delegated_tasks() == ()


def test_rejects_invalid_delegated_task_status(memory_store):
    run = memory_store.start_run(workflow="delegated-work")
    task = memory_store.create_delegated_task(
        created_run_id=run.run_id,
        title="Prepare ACCT review",
        request="Summarize ACCT tickets for review.",
    )

    with pytest.raises(MemoryStoreError):
        memory_store.update_delegated_task_status(
            task_id=task.task_id,
            status="maybe",
        )


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

    with pytest.raises(MemoryStoreError):
        memory_store.recent_feedback(limit=0)

    with pytest.raises(MemoryStoreError):
        memory_store.recent_actions(limit=0)

    with pytest.raises(MemoryStoreError):
        memory_store.pending_actions(limit=0)

    with pytest.raises(MemoryStoreError):
        memory_store.actions_by_approval_status("approved", limit=0)
