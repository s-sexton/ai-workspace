from __future__ import annotations

from assistant.src.ask_memory import answer_memory_question, main
from common.memory import DuckDbMemoryStore


def test_answers_latest_jira_run(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "latest-jira-run",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Latest Jira Report Run" in answer
    assert "- Status: completed" in answer
    assert "- Summary: Generated Jira report with 2 issue(s)." in answer
    assert "- Artifact: reports/jira-report.md (markdown_report)" in answer
    assert "Artifact summary: Jira report with 2 issue(s)." in answer


def test_answers_last_clarity_cycle(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "last-cycle",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Latest Clarity Cycle" in answer
    assert "- Workflow: clarity-cycle" in answer
    assert "- Status: completed" in answer
    assert "- Summary: Read 2 message(s) from clarity@sendthisfile.ai" in answer
    assert "- Artifact: reports/clarity-cycle.md (markdown_cycle_report)" in answer


def test_answers_summary(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "summary",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Clarity Memory Summary" in answer
    assert "- Latest Jira run: Generated Jira report with 2 issue(s)." in answer
    assert "- Items marked for review: 2" in answer
    assert "- Items marked as noise: 1" in answer
    assert "- Recent feedback records: 1" in answer
    assert "- Open delegated tasks: 1" in answer
    assert "## Next Attention" in answer
    assert "Prepare ACCT review: Generate a short report." in answer


def test_answers_attention_brief(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "attention-brief",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Clarity Attention Brief" in answer
    assert "- Last cycle: Read 2 message(s) from clarity@sendthisfile.ai" in answer
    assert "- Items needing review: 2" in answer
    assert "- Pending approvals: 1" in answer
    assert "- Approved email moves: 1" in answer
    assert "- Open delegated tasks: 1" in answer
    assert "## Review" in answer
    assert "Review support queue trends" in answer
    assert "## Pending Approval" in answer
    assert "propose_email_move_noise - July product newsletter" in answer
    assert "## Approved Email Moves" in answer
    assert (
        "In mailbox scott.sexton@sendthisfile.com, move message "
        "email-review-1 to Clarity/Review"
    ) in answer
    assert "## Open Tasks" in answer
    assert "Prepare ACCT review [requested]" in answer


def test_answers_recent_items(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "recent-items",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Recent Items" in answer
    assert "Review support queue trends [review]" in answer
    assert "Build the first Jira report [review]" in answer
    assert "Source: Jira Cloud (jira)" in answer


def test_answers_review_items(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "review-items",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Items Marked For Review" in answer
    assert "Included in the Jira report for human review." in answer


def test_answers_noise_items(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "noise-items",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Items Marked As Noise" in answer
    assert "July product newsletter [noise]" in answer
    assert "Marketing or subscription-style message." in answer


def test_answers_open_tasks(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "open-tasks",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Open Delegated Tasks" in answer
    assert "Prepare ACCT review [requested, approval required]" in answer
    assert "Next step: Generate a short report." in answer


def test_answers_recent_feedback(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "feedback",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Recent Feedback" in answer
    assert "STF-1: noise - Build the first Jira report" in answer
    assert "Feedback: This was just an automated update." in answer


def test_answers_recent_actions(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "actions",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Recent Actions" in answer
    assert "generate_jira_report [not_required]" in answer
    assert "Result: Wrote reports/jira-report.md" in answer


def test_answers_pending_actions(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "pending-actions",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Pending Actions" in answer
    assert "propose_email_move_noise - July product newsletter [required]" in answer
    assert "Action:" in answer
    assert "Item: email-noise-1" in answer
    assert "Target: Clarity/Noise" in answer
    assert "Proposal: Proposed moving message metadata" in answer


def test_answers_approved_actions(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "approved-actions",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Approved Actions" in answer
    assert "propose_email_move_review - Review vendor terms [approved]" in answer
    assert "Action:" in answer
    assert "Item: email-review-1" in answer
    assert "Source: scott.sexton@sendthisfile.com" in answer
    assert "Target: Clarity/Review" in answer
    assert "Proposal: Proposed moving message metadata" in answer


def test_answers_email_move_plan(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_memory_question(
        "email-move-plan",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Email Move Plan" in answer
    assert (
        "In mailbox scott.sexton@sendthisfile.com, move message "
        "email-review-1 to Clarity/Review"
    ) in answer
    assert "Subject: Review vendor terms" in answer
    assert "Move message email-noise-1" not in answer


def test_missing_memory_returns_plain_message(tmp_path):
    answer = answer_memory_question(
        "recent-items",
        root=tmp_path,
        memory_path=tmp_path / "logs" / "missing.duckdb",
    )

    assert "No Clarity memory found" in answer


def test_main_prints_answer(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(["attention-brief", "--memory", str(memory_path)])

    output = capsys.readouterr().out
    assert "# Clarity Attention Brief" in output


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(
            workflow="jira-report",
            started_at="2026-07-09T15:00:00+00:00",
        )
        source = store.record_source(
            source_type="jira",
            display_name="Jira Cloud",
            scope_label="project in (STF, ACCT)",
        )
        for external_id, subject in (
            ("STF-1", "Build the first Jira report"),
            ("SUPP-2", "Review support queue trends"),
        ):
            item = store.record_item_seen(
                source_id=source.source_id,
                external_id=external_id,
                item_type="jira_issue",
                subject=subject,
                first_seen_run_id=run.run_id,
            )
            store.record_classification(
                item_id=item.item_id,
                run_id=run.run_id,
                label="review",
                reason="Included in the Jira report for human review.",
            )
            if external_id == "STF-1":
                store.record_feedback(
                    item_id=item.item_id,
                    run_id=run.run_id,
                    feedback_type="noise",
                    feedback_text="This was just an automated update.",
                )
        email_source = store.record_source(
            source_type="email",
            display_name="scott.sexton@sendthisfile.com",
            scope_label="scott.sexton@sendthisfile.com",
        )
        noise_item = store.record_item_seen(
            source_id=email_source.source_id,
            external_id="email-noise-1",
            item_type="email_message",
            subject="July product newsletter",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=noise_item.item_id,
            run_id=run.run_id,
            label="noise",
            reason="Marketing or subscription-style message.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=noise_item.item_id,
            action_type="propose_email_move_noise",
            approval_status="required",
            action_target="Clarity/Noise",
            result=(
                "Proposed moving message metadata for email-noise-1 "
                "to Clarity/Noise."
            ),
        )
        approved_item = store.record_item_seen(
            source_id=email_source.source_id,
            external_id="email-review-1",
            item_type="email_message",
            subject="Review vendor terms",
            first_seen_run_id=run.run_id,
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=approved_item.item_id,
            action_type="propose_email_move_review",
            approval_status="approved",
            action_target="Clarity/Review",
            result=(
                "Proposed moving message metadata for email-review-1 "
                "to Clarity/Review."
            ),
        )
        store.create_delegated_task(
            created_run_id=run.run_id,
            title="Prepare ACCT review",
            request="Summarize ACCT tickets for review.",
            next_step="Generate a short report.",
        )
        store.record_generated_artifact(
            run_id=run.run_id,
            artifact_type="markdown_report",
            path="reports/jira-report.md",
            summary="Jira report with 2 issue(s).",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="generate_jira_report",
            approval_status="not_required",
            result="Wrote reports/jira-report.md",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Generated Jira report with 2 issue(s).",
            completed_at="2026-07-09T15:01:00+00:00",
        )
        cycle_run = store.start_run(
            workflow="clarity-cycle",
            started_at="2026-07-09T16:00:00+00:00",
        )
        store.record_generated_artifact(
            run_id=cycle_run.run_id,
            artifact_type="markdown_cycle_report",
            path="reports/clarity-cycle.md",
            summary="Clarity cycle report for clarity@sendthisfile.ai.",
        )
        store.record_assistant_action(
            run_id=cycle_run.run_id,
            action_type="run_clarity_cycle",
            approval_status="not_required",
            result=(
                "Read 2 message(s) from clarity@sendthisfile.ai; "
                "review=1, noise=0, trash=1, proposed_actions=2."
            ),
        )
        store.finish_run(
            cycle_run.run_id,
            status="completed",
            summary=(
                "Read 2 message(s) from clarity@sendthisfile.ai; "
                "review=1, noise=0, trash=1, proposed_actions=2."
            ),
            completed_at="2026-07-09T16:01:00+00:00",
        )
    finally:
        store.close()
